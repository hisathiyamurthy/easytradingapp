"""Zerodha broker integration."""
import hashlib
import hmac
import json
import time
from base64 import b64decode, b64encode
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import httpx
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from broker_integrations.base import (
    BrokerBase,
    BrokerConfig,
    BrokerName,
    BrokerRegistry,
    ConnectionStatus,
    CredentialField,
    FundLimit,
    MarketQuote,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Portfolio,
    ProductType,
)


@BrokerRegistry.register(BrokerName.ZERODHA)
class ZerodhaBroker(BrokerBase):
    """Zerodha Kite Connect API implementation."""

    BASE_URL = "https://api.kite.trade"
    LOGIN_URL = "https://kite.zerodha.com/connect/login"

    @staticmethod
    def get_credential_fields() -> list[CredentialField]:
        return [
            CredentialField(
                name="api_key",
                label="API Key",
                field_type="text",
                required=True,
                placeholder="Enter your Zerodha API Key",
                help_text="Get from https://developers.kite.trade",
            ),
            CredentialField(
                name="api_secret",
                label="API Secret",
                field_type="password",
                required=True,
                placeholder="Enter your API Secret",
                help_text="Keep this secret and never share",
            ),
            CredentialField(
                name="totp_secret",
                label="TOTP Secret",
                field_type="password",
                required=False,
                placeholder="Optional: For automated 2FA",
                help_text="Required only if enabling 2FA for sessions",
            ),
        ]

    @staticmethod
    def get_required_scopes() -> list[str]:
        return [
            "order",
            "trade",
            "position",
            "portfolio",
            "funds",
            "profile",
        ]

    def __init__(self, config: BrokerConfig, encryption_key: bytes):
        super().__init__(config, encryption_key)
        self.api_key = config.api_key
        self.api_secret = config.api_secret

    def _encrypt(self, data: str) -> str:
        """Encrypt data using AES."""
        cipher = Cipher(
            algorithms.AES(self.encryption_key),
            modes.GCM(self.encryption_key[:16]),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data.encode()) + encryptor.finalize()
        return b64encode(ciphertext).decode()

    def _decrypt(self, data: str) -> str:
        """Decrypt data using AES."""
        decoded = b64decode(data)
        cipher = Cipher(
            algorithms.AES(self.encryption_key),
            modes.GCM(self.encryption_key[:16]),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        return decryptor.update(decoded).decode()

    def _generate_signature(self, method: str, url: str, params: dict = None) -> str:
        """Generate HMAC SHA256 signature."""
        if params:
            param_str = urlencode(sorted(params.items()))
            url = f"{url}?{param_str}"
        
        message = f"{method.upper()}{url}"
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _get_headers(self) -> dict:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
            "X-Kite-Version": "3",
        }
        if self._access_token:
            headers["Authorization"] = f"token {self.api_key}:{self._access_token}"
        return headers

    async def test_connection(self) -> ConnectionStatus:
        """Test Zerodha connection."""
        try:
            response = await httpx.AsyncClient().get(
                f"{self.BASE_URL}/user/profile",
                headers=self._get_headers(),
                timeout=10,
            )
            
            if response.status_code == 200:
                data = response.json()
                return ConnectionStatus(
                    is_connected=True,
                    message="Connected successfully",
                    user_name=data.get("user_name"),
                    user_id=str(data.get("user_id")),
                    broker_name=BrokerName.ZERODHA,
                )
            else:
                return ConnectionStatus(
                    is_connected=False,
                    message=f"Connection failed: {response.text}",
                    broker_name=BrokerName.ZERODHA,
                )
        except Exception as e:
            return ConnectionStatus(
                is_connected=False,
                message=f"Connection error: {str(e)}",
                broker_name=BrokerName.ZERODHA,
            )

    async def authenticate(self, additional_params: dict) -> dict:
        """Authenticate with Zerodha using login flow."""
        request_token = additional_params.get("request_token")
        
        if not request_token:
            # Return login URL for user to authenticate
            checksum = hashlib.sha256(
                f"{self.api_key}{request_token}{self.api_secret}".encode()
            ).hexdigest()
            
            return {
                "login_url": f"{self.LOGIN_URL}?api_key={self.api_key}&checksum={checksum}",
                "requires_request_token": True,
            }

        # Exchange request token for access token
        params = {
            "api_key": self.api_key,
            "request_token": request_token,
            "checksum": self._generate_signature("POST", "/session/token", params),
        }

        response = await httpx.AsyncClient().post(
            f"{self.BASE_URL}/session/token",
            json=params,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            data = response.json()
            self._access_token = data["access_token"]
            self._feed_token = data.get("feed_token")
            
            return {
                "access_token": self._encrypt(self._access_token),
                "feed_token": self._encrypt(self._feed_token) if self._feed_token else None,
                "user_id": data.get("user_id"),
            }
        else:
            raise Exception(f"Authentication failed: {response.text}")

    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place an order on Zerodha."""
        # Map order type
        order_types_map = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.SL: "SL",
            OrderType.SLM: "SL-M",
        }
        
        product_types_map = {
            ProductType.CNC: "CNC",
            ProductType.MIS: "MIS",
            ProductType.NRML: "NRML",
        }

        order_params = {
            "exchange": order.exchange,
            "tradingsymbol": order.symbol,
            "transaction_type": order.side.value.upper(),
            "order_type": order_types_map.get(order.order_type, "MARKET"),
            "quantity": order.quantity,
            "product": product_types_map.get(order.product_type, "MIS"),
            "validity": order.validity,
        }

        if order.price:
            order_params["price"] = order.price
        if order.trigger_price:
            order_params["trigger_price"] = order.trigger_price
        if order.disclosed_quantity:
            order_params["disclosed_quantity"] = order.disclosed_quantity

        response = await httpx.AsyncClient().post(
            f"{self.BASE_URL}/orders/regular",
            json=order_params,
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            data = response.json()
            order_data = data.get("data", {})
            
            return OrderResponse(
                broker_order_id=str(order_data.get("order_id")),
                order_id=str(order_data.get("order_id")),
                symbol=order_data.get("tradingsymbol", order.symbol),
                exchange=order_data.get("exchange", order.exchange),
                side=OrderSide.BUY if order_data.get("transaction_type") == "BUY" else OrderSide.SELL,
                order_type=order.order_type,
                status=self._map_order_status(order_data.get("status")),
                quantity=order_data.get("quantity", order.quantity),
                filled_quantity=order_data.get("filled_quantity", 0),
                price=order.price,
                avg_fill_price=order_data.get("average_price"),
                created_at=datetime.fromisoformat(order_data.get("order_timestamp")),
                updated_at=datetime.now(),
                raw_response=order_data,
            )
        else:
            raise Exception(f"Order placement failed: {response.text}")

    def _map_order_status(self, status: str) -> OrderStatus:
        """Map Zerodha order status to standard status."""
        status_map = {
            "OPEN": OrderStatus.PENDING,
            "PARTIALLY FILLED": OrderStatus.PARTIALLY_FILLED,
            "COMPLETED": OrderStatus.FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "PENDING": OrderStatus.PENDING,
        }
        return status_map.get(status.upper(), OrderStatus.PENDING)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        response = await httpx.AsyncClient().delete(
            f"{self.BASE_URL}/orders/{order_id}",
            headers=self._get_headers(),
        )
        return response.status_code == 200

    async def modify_order(self, order_id: str, order: OrderRequest) -> OrderResponse:
        """Modify an order."""
        params = {
            "quantity": order.quantity,
            "order_type": order.order_type.value.upper(),
        }
        if order.price:
            params["price"] = order.price
        if order.trigger_price:
            params["trigger_price"] = order.trigger_price

        response = await httpx.AsyncClient().put(
            f"{self.BASE_URL}/orders/{order_id}",
            json=params,
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            return await self.get_order_status(order_id)
        else:
            raise Exception(f"Order modification failed: {response.text}")

    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status."""
        response = await httpx.AsyncClient().get(
            f"{self.BASE_URL}/orders/{order_id}",
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            data = response.json()
            order_data = data.get("data", {})
            
            return OrderResponse(
                broker_order_id=str(order_data.get("order_id")),
                order_id=str(order_data.get("order_id")),
                symbol=order_data.get("tradingsymbol"),
                exchange=order_data.get("exchange"),
                side=OrderSide.BUY if order_data.get("transaction_type") == "BUY" else OrderSide.SELL,
                order_type=OrderType(order_data.get("order_type", "market").lower()),
                status=self._map_order_status(order_data.get("status")),
                quantity=order_data.get("quantity"),
                filled_quantity=order_data.get("filled_quantity", 0),
                price=order_data.get("price"),
                avg_fill_price=order_data.get("average_price"),
                created_at=datetime.fromisoformat(order_data.get("order_timestamp")),
                updated_at=datetime.now(),
                raw_response=order_data,
            )
        else:
            raise Exception(f"Failed to get order status: {response.text}")

    async def get_positions(self) -> list[Position]:
        """Get open positions."""
        response = await httpx.AsyncClient().get(
            f"{self.BASE_URL}/portfolio/positions",
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            data = response.json()
            positions = []
            
            for pos in data.get("data", []):
                positions.append(
                    Position(
                        symbol=pos.get("tradingsymbol"),
                        exchange=pos.get("exchange"),
                        quantity=pos.get("quantity", 0),
                        avg_price=pos.get("average_price", 0),
                        current_price=pos.get("last_price", 0),
                        unrealized_pnl=pos.get("pnl", 0),
                        product_type=ProductType.MIS if pos.get("product") == "MIS" else ProductType.NRML,
                    )
                )
            return positions
        return []

    async def get_portfolio(self) -> list[Portfolio]:
        """Get portfolio holdings."""
        response = await httpx.AsyncClient().get(
            f"{self.BASE_URL}/portfolio/holdings",
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            data = response.json()
            holdings = []
            
            for holding in data.get("data", []):
                holdings.append(
                    Portfolio(
                        symbol=holding.get("tradingsymbol"),
                        exchange=holding.get("exchange"),
                        quantity=holding.get("quantity"),
                        avg_price=holding.get("average_price"),
                        ltp=holding.get("last_price", 0),
                        close=holding.get("close_price", 0),
                        pnl=holding.get("pnl", 0),
                        pnl_percent=holding.get("pnl_percent", 0),
                    )
                )
            return holdings
        return []

    async def get_fund_limits(self) -> FundLimit:
        """Get available funds."""
        response = await httpx.AsyncClient().get(
            f"{self.BASE_URL}/user/margins",
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            data = response.json()
            equity = data.get("data", {}).get("equity", {})
            
            return FundLimit(
                cash=equity.get("cash", 0),
                collateral=equity.get("collateral", 0),
                payable=equity.get("payable", 0),
                receivables=equity.get("receivables", 0),
                available_cash=equity.get("available_cash", 0),
                available_intraday_credit=equity.get("adhoc_margin", 0),
                available_margin=equity.get("available_margin", 0),
            )
        raise Exception("Failed to get fund limits")

    async def get_quote(self, symbol: str, exchange: str) -> MarketQuote:
        """Get market quote."""
        response = await httpx.AsyncClient().get(
            f"{self.BASE_URL}/quote",
            params={"tradingsymbol": symbol, "exchange": exchange},
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            data = response.json()
            quote = data.get("data", {}).get(f"{exchange}:{symbol}", {})
            
            return MarketQuote(
                symbol=symbol,
                exchange=exchange,
                last_price=quote.get("last_price", 0),
                open=quote.get("ohlc", {}).get("open", 0),
                high=quote.get("ohlc", {}).get("high", 0),
                low=quote.get("ohlc", {}).get("low", 0),
                close=quote.get("ohlc", {}).get("close", 0),
                volume=quote.get("volume", 0),
                bid=quote.get("depth", {}).get("buy", [{}])[0].get("price", 0),
                ask=quote.get("depth", {}).get("sell", [{}])[0].get("price", 0),
                bid_quantity=quote.get("depth", {}).get("buy", [{}])[0].get("quantity", 0),
                ask_quantity=quote.get("depth", {}).get("sell", [{}])[0].get("quantity", 0),
                timestamp=datetime.fromisoformat(quote.get("timestamp")),
            )
        raise Exception(f"Failed to get quote: {response.text}")

    async def get_historical_data(
        self,
        symbol: str,
        exchange: str,
        from_date: datetime,
        to_date: datetime,
        interval: str,
    ) -> list[dict]:
        """Get historical data."""
        params = {
            "symbol": f"{exchange}:{symbol}",
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
            "interval": interval,
            "oi": "1",
        }

        response = await httpx.AsyncClient().get(
            f"{self.BASE_URL}/historical",
            params=params,
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            data = response.json()
            candles = []
            
            for candle in data.get("data", {}).get("candles", []):
                candles.append({
                    "timestamp": datetime.fromisoformat(candle[0]),
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4],
                    "volume": candle[5],
                    "oi": candle[6] if len(candle) > 6 else 0,
                })
            return candles
        return []

    async def get_profile(self) -> dict:
        """Get user profile."""
        response = await httpx.AsyncClient().get(
            f"{self.BASE_URL}/user/profile",
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            return response.json().get("data", {})
        raise Exception("Failed to get profile")

    async def get_holdings(self) -> list[dict]:
        """Get holdings."""
        return await self.get_portfolio()

    async def get_orders(self, from_date: Optional[datetime] = None) -> list[OrderResponse]:
        """Get order history."""
        response = await httpx.AsyncClient().get(
            f"{self.BASE_URL}/orders",
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            data = response.json()
            orders = []
            
            for order in data.get("data", []):
                orders.append(OrderResponse(
                    broker_order_id=str(order.get("order_id")),
                    order_id=str(order.get("order_id")),
                    symbol=order.get("tradingsymbol"),
                    exchange=order.get("exchange"),
                    side=OrderSide.BUY if order.get("transaction_type") == "BUY" else OrderSide.SELL,
                    order_type=OrderType(order.get("order_type", "market").lower()),
                    status=self._map_order_status(order.get("status")),
                    quantity=order.get("quantity"),
                    filled_quantity=order.get("filled_quantity", 0),
                    price=order.get("price"),
                    avg_fill_price=order.get("average_price"),
                    created_at=datetime.fromisoformat(order.get("order_timestamp")),
                    updated_at=datetime.now(),
                    raw_response=order,
                ))
            return orders
        return []

    async def get_trades(self, from_date: Optional[datetime] = None) -> list[dict]:
        """Get trade history."""
        response = await httpx.AsyncClient().get(
            f"{self.BASE_URL}/trades",
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        return []

    async def close_connection(self):
        """Close broker connection."""
        self._access_token = None
        self._feed_token = None

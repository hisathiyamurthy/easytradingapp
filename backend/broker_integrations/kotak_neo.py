"""Kotak Neo broker integration."""
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Optional

import httpx
from cryptography.fernet import Fernet

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


@BrokerRegistry.register(BrokerName.KOTAK_NEO)
class KotakNeoBroker(BrokerBase):
    """Kotak Neo API implementation."""

    BASE_URL = "https://gw-napi.kotak.com"
    MARGIN_API_URL = "https://margin-kotak.kotak.com"
    ORDER_API_URL = "https://order.kotak.com"

    @staticmethod
    def get_credential_fields() -> list[CredentialField]:
        return [
            CredentialField(
                name="consumer_key",
                label="Consumer Key",
                field_type="text",
                required=True,
                placeholder="Enter your Kotak Neo Consumer Key",
            ),
            CredentialField(
                name="consumer_secret",
                label="Consumer Secret",
                field_type="password",
                required=True,
                placeholder="Enter your Consumer Secret",
            ),
            CredentialField(
                name="access_token",
                label="Access Token",
                field_type="password",
                required=True,
                placeholder="Enter Access Token",
            ),
            CredentialField(
                name="app_secret",
                label="App Secret",
                field_type="password",
                required=True,
                placeholder="Enter App Secret",
            ),
        ]

    @staticmethod
    def get_required_scopes() -> list[str]:
        return ["order", "trade", "position", "holdings", "user"]

    def __init__(self, config: BrokerConfig, encryption_key: bytes):
        super().__init__(config, encryption_key)
        self.consumer_key = config.api_key
        self.consumer_secret = config.api_secret
        self.access_token = config.additional_fields.get("access_token", "")
        self.app_secret = config.additional_fields.get("app_secret", "")

    def _generate_headers(self, pan: str = "") -> dict:
        """Generate headers for API requests."""
        timestamp = str(int(time.time() * 1000))
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "X-Kotak-ConsumerKey": self.consumer_key,
            "X-Kotak-Timestamp": timestamp,
            "X-Kotak-PAN": pan,
        }
        return headers

    def _generate_signature(self, method: str, path: str, body: str = "") -> str:
        """Generate signature for API request."""
        string_to_sign = method + path + self.access_token + self.app_secret + body
        signature = hmac.new(
            self.app_secret.encode(),
            string_to_sign.encode(),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(signature).decode()

    async def test_connection(self) -> ConnectionStatus:
        """Test Kotak Neo connection."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/v2/orders",
                    headers=self._generate_headers(),
                    timeout=10.0,
                )

                if response.status_code == 200:
                    return ConnectionStatus(
                        is_connected=True,
                        message="Connected successfully",
                        broker_name=BrokerName.KOTAK_NEO,
                    )
                elif response.status_code == 401:
                    return ConnectionStatus(
                        is_connected=False,
                        message="Invalid access token",
                        broker_name=BrokerName.KOTAK_NEO,
                    )
                else:
                    return ConnectionStatus(
                        is_connected=False,
                        message=f"Connection failed: {response.status_code}",
                        broker_name=BrokerName.KOTAK_NEO,
                    )
        except Exception as e:
            return ConnectionStatus(
                is_connected=False,
                message=f"Connection error: {str(e)}",
                broker_name=BrokerName.KOTAK_NEO,
            )

    async def authenticate(self, additional_params: dict) -> dict:
        """Authenticate with Kotak Neo."""
        url = f"{self.BASE_URL}/v2/session"
        body = json.dumps({
            "consumerKey": self.consumer_key,
            "consumerSecret": self.consumer_secret,
            "accessToken": self.access_token,
        })

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                content=body,
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                return {"authenticated": True, "data": data}
            raise Exception(f"Authentication failed: {response.text}")

    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place an order on Kotak Neo."""
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
            "instrumentToken": order.symbol,
            "exchange": order.exchange,
            "transactionType": order.side.value.upper(),
            "quantity": order.quantity,
            "orderType": order_types_map.get(order.order_type, "MARKET"),
            "productType": product_types_map.get(order.product_type, "MIS"),
            "duration": "DAY",
        }

        if order.price:
            order_params["price"] = str(order.price)
        if order.trigger_price:
            order_params["triggerPrice"] = str(order.trigger_price)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ORDER_API_URL}/v2/orders",
                json=order_params,
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code in [200, 201]:
                data = response.json()
                order_data = data.get("data", {})
                return OrderResponse(
                    broker_order_id=str(order_data.get("orderId", "")),
                    order_id=str(order_data.get("appOrderId", "")),
                    symbol=order_data.get("instrumentToken", order.symbol),
                    exchange=order.exchange,
                    side=OrderSide.BUY if order_data.get("transactionType") == "BUY" else OrderSide.SELL,
                    order_type=order.order_type,
                    status=self._map_order_status(order_data.get("status", "")),
                    quantity=order_data.get("quantity", order.quantity),
                    filled_quantity=order_data.get("filledQuantity", 0),
                    price=order_data.get("price"),
                    avg_fill_price=order_data.get("averagePrice"),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    raw_response=order_data,
                )
            else:
                raise Exception(f"Order placement failed: {response.text}")

    def _map_order_status(self, status: str) -> OrderStatus:
        """Map Kotak order status to standard status."""
        status_map = {
            "OPEN": OrderStatus.PENDING,
            "NEW": OrderStatus.SUBMITTED,
            "PARTIALLY FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
        }
        return status_map.get(status.upper(), OrderStatus.PENDING)

    async def cancel_order(self, order_id: str, exchange: str = "NSE") -> bool:
        """Cancel an order."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.ORDER_API_URL}/v2/orders/{order_id}",
                headers=self._generate_headers(),
                timeout=10.0,
            )
            return response.status_code in [200, 204]

    async def modify_order(self, order_id: str, order: OrderRequest) -> OrderResponse:
        """Modify an order."""
        order_params = {}
        if order.quantity:
            order_params["quantity"] = order.quantity
        if order.price:
            order_params["price"] = str(order.price)
        if order.trigger_price:
            order_params["triggerPrice"] = str(order.trigger_price)

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.ORDER_API_URL}/v2/orders/{order_id}",
                json=order_params,
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                return await self.place_order(order)
            raise Exception(f"Order modification failed: {response.text}")

    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.ORDER_API_URL}/v2/orders/{order_id}",
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                order_data = data.get("data", {})
                return OrderResponse(
                    broker_order_id=str(order_data.get("orderId", "")),
                    order_id=str(order_data.get("appOrderId", "")),
                    symbol=order_data.get("instrumentToken", ""),
                    exchange=order_data.get("exchange", ""),
                    side=OrderSide.BUY if order_data.get("transactionType") == "BUY" else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    status=self._map_order_status(order_data.get("status", "")),
                    quantity=order_data.get("quantity", 0),
                    filled_quantity=order_data.get("filledQuantity", 0),
                    price=order_data.get("price"),
                    avg_fill_price=order_data.get("averagePrice"),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    raw_response=order_data,
                )
            raise Exception(f"Failed to get order status: {response.text}")

    async def get_positions(self) -> list[Position]:
        """Get open positions."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.MARGIN_API_URL}/v2/positions",
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                positions = []
                for pos in data.get("data", []):
                    positions.append(
                        Position(
                            symbol=pos.get("instrumentToken", ""),
                            exchange=pos.get("exchange", ""),
                            quantity=int(pos.get("quantity", 0)),
                            avg_price=float(pos.get("averagePrice", 0)),
                            current_price=float(pos.get("ltp", 0)),
                            unrealized_pnl=float(pos.get("unrealizedPnl", 0)),
                            product_type=ProductType.MIS if pos.get("productType") == "MIS" else ProductType.NRML,
                        )
                    )
                return positions
            return []

    async def get_portfolio(self) -> list[Portfolio]:
        """Get portfolio holdings."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/v2/holdings",
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                holdings = []
                for holding in data.get("data", []):
                    holdings.append(
                        Portfolio(
                            symbol=holding.get("instrumentToken", ""),
                            exchange=holding.get("exchange", ""),
                            quantity=int(holding.get("quantity", 0)),
                            avg_price=float(holding.get("averagePrice", 0)),
                            ltp=float(holding.get("ltp", 0)),
                            close=float(holding.get("close", 0)),
                            pnl=float(holding.get("pnl", 0)),
                            pnl_percent=float(holding.get("pnlPercent", 0)),
                        )
                    )
                return holdings
            return []

    async def get_fund_limits(self) -> FundLimit:
        """Get available funds."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.MARGIN_API_URL}/v2/limits",
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                limits = data.get("data", {})
                return FundLimit(
                    cash=float(limits.get("cash", 0)),
                    collateral=float(limits.get("collateral", 0)),
                    payable=float(limits.get("payable", 0)),
                    receivables=float(limits.get("receivables", 0)),
                    available_cash=float(limits.get("net", 0)),
                    available_intraday_credit=float(limits.get("intradayPayin", 0)),
                    available_margin=float(limits.get("marginAvailable", 0)),
                )
            raise Exception("Failed to get fund limits")

    async def get_quote(self, symbol: str, exchange: str) -> MarketQuote:
        """Get market quote."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/v2/quote",
                params={"instrumentToken": symbol},
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                quote = data.get("data", {})
                return MarketQuote(
                    symbol=symbol,
                    exchange=exchange,
                    last_price=quote.get("lastPrice", 0),
                    open=quote.get("open", 0),
                    high=quote.get("high", 0),
                    low=quote.get("low", 0),
                    close=quote.get("close", 0),
                    volume=quote.get("volume", 0),
                    bid=quote.get("bestBid", 0),
                    ask=quote.get("bestAsk", 0),
                    bid_quantity=quote.get("bestBidQuantity", 0),
                    ask_quantity=quote.get("bestAskQuantity", 0),
                    timestamp=datetime.now(),
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
        async with httpx.AsyncClient() as client:
            params = {
                "instrumentToken": symbol,
                "from": from_date.strftime("%Y-%m-%d"),
                "to": to_date.strftime("%Y-%m-%d"),
                "interval": interval,
            }
            response = await client.get(
                f"{self.BASE_URL}/v2/candle",
                params=params,
                headers=self._generate_headers(),
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                candles = data.get("data", [])
                return [
                    {
                        "timestamp": datetime.fromisoformat(c.get("timestamp")),
                        "open": c.get("open"),
                        "high": c.get("high"),
                        "low": c.get("low"),
                        "close": c.get("close"),
                        "volume": c.get("volume"),
                    }
                    for c in candles
                ]
            return []

    async def close_connection(self):
        """Close broker connection."""
        pass

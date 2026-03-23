"""Upstox broker integration."""
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Optional

import httpx

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


@BrokerRegistry.register(BrokerName.UPSTOX)
class UpstoxBroker(BrokerBase):
    """Upstox API implementation."""

    BASE_URL = "https://api.upstox.com"
    LOGIN_URL = "https://api.upstox.com/login"

    @staticmethod
    def get_credential_fields() -> list[CredentialField]:
        return [
            CredentialField(
                name="api_key",
                label="API Key",
                field_type="text",
                required=True,
                placeholder="Enter your Upstox API Key",
            ),
            CredentialField(
                name="api_secret",
                label="API Secret",
                field_type="password",
                required=True,
                placeholder="Enter your API Secret",
            ),
            CredentialField(
                name="access_token",
                label="Access Token",
                field_type="password",
                required=True,
                placeholder="Enter Access Token",
            ),
        ]

    @staticmethod
    def get_required_scopes() -> list[str]:
        return ["order", "trade", "position", "holdings", "user"]

    def __init__(self, config: BrokerConfig, encryption_key: bytes):
        super().__init__(config, encryption_key)
        self.api_key = config.api_key
        self.api_secret = config.api_secret
        self.access_token = config.additional_fields.get("access_token", "")

    def _generate_headers(self) -> dict:
        """Generate headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }
        return headers

    def _generate_signature(self, method: str, path: str, body: str = "") -> str:
        """Generate signature for API request."""
        string_to_sign = method + path + self.api_key + self.access_token + self.api_secret + body
        signature = hmac.new(
            self.api_secret.encode(),
            string_to_sign.encode(),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(signature).decode()

    async def test_connection(self) -> ConnectionStatus:
        """Test Upstox connection."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/v2/user/get-profile",
                    headers=self._generate_headers(),
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    user_data = data.get("data", {})
                    return ConnectionStatus(
                        is_connected=True,
                        message="Connected successfully",
                        user_name=user_data.get("name", ""),
                        user_id=str(user_data.get("id", "")),
                        broker_name=BrokerName.UPSTOX,
                    )
                elif response.status_code == 401:
                    return ConnectionStatus(
                        is_connected=False,
                        message="Invalid access token",
                        broker_name=BrokerName.UPSTOX,
                    )
                else:
                    return ConnectionStatus(
                        is_connected=False,
                        message=f"Connection failed: {response.status_code}",
                        broker_name=BrokerName.UPSTOX,
                    )
        except Exception as e:
            return ConnectionStatus(
                is_connected=False,
                message=f"Connection error: {str(e)}",
                broker_name=BrokerName.UPSTOX,
            )

    async def authenticate(self, additional_params: dict) -> dict:
        """Authenticate with Upstox."""
        url = f"{self.BASE_URL}/v2/login/validate-token"
        body = json.dumps({
            "apiKey": self.api_key,
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
        """Place an order on Upstox."""
        order_types_map = {
            OrderType.MARKET: "Market",
            OrderType.LIMIT: "Limit",
            OrderType.SL: "StopLoss",
            OrderType.SLM: "StopLossMarket",
        }

        product_types_map = {
            ProductType.CNC: "CNC",
            ProductType.MIS: "MIS",
            ProductType.NRML: "NRML",
        }

        order_params = {
            "instrumentToken": order.symbol,
            "transactionType": order.side.value.upper(),
            "quantity": order.quantity,
            "orderType": order_types_map.get(order.order_type, "Market"),
            "product": product_types_map.get(order.product_type, "MIS"),
            "validity": "DAY",
        }

        if order.price:
            order_params["price"] = str(order.price)
        if order.trigger_price:
            order_params["triggerPrice"] = str(order.trigger_price)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/v2/order/place",
                json=order_params,
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code in [200, 201]:
                data = response.json()
                order_data = data.get("data", {})
                return OrderResponse(
                    broker_order_id=str(order_data.get("orderId", "")),
                    order_id=str(order_data.get("orderUniqueId", "")),
                    symbol=order_data.get("instrumentToken", order.symbol),
                    exchange=order.exchange,
                    side=OrderSide.BUY if order_data.get("transactionType") == "BUY" else OrderSide.SELL,
                    order_type=order.order_type,
                    status=self._map_order_status(order_data.get("orderStatus", "")),
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
        """Map Upstox order status to standard status."""
        status_map = {
            "OPEN": OrderStatus.PENDING,
            "NEW": OrderStatus.SUBMITTED,
            "PARTIALLY FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
        }
        return status_map.get(status.upper(), OrderStatus.PENDING)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.BASE_URL}/v2/order/cancel",
                json={"orderId": order_id},
                headers=self._generate_headers(),
                timeout=10.0,
            )
            return response.status_code in [200, 204]

    async def modify_order(self, order_id: str, order: OrderRequest) -> OrderResponse:
        """Modify an order."""
        order_params = {
            "orderId": order_id,
        }
        if order.quantity:
            order_params["quantity"] = order.quantity
        if order.price:
            order_params["price"] = str(order.price)
        if order.trigger_price:
            order_params["triggerPrice"] = str(order.trigger_price)

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.BASE_URL}/v2/order/modify",
                json=order_params,
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                return await self.get_order_status(order_id)
            raise Exception(f"Order modification failed: {response.text}")

    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/v2/order/details/{order_id}",
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                order_data = data.get("data", {})
                return OrderResponse(
                    broker_order_id=str(order_data.get("orderId", "")),
                    order_id=str(order_data.get("orderUniqueId", "")),
                    symbol=order_data.get("instrumentToken", ""),
                    exchange=order_data.get("exchange", ""),
                    side=OrderSide.BUY if order_data.get("transactionType") == "BUY" else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    status=self._map_order_status(order_data.get("orderStatus", "")),
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
                f"{self.BASE_URL}/v2/position/get-details",
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
                            product_type=ProductType.MIS if pos.get("product") == "MIS" else ProductType.NRML,
                        )
                    )
                return positions
            return []

    async def get_portfolio(self) -> list[Portfolio]:
        """Get portfolio holdings."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/v2/portfolio/get-holdings",
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
                            ltp=float(holding.get("lastPrice", 0)),
                            close=float(holding.get("closePrice", 0)),
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
                f"{self.BASE_URL}/v2/user/get-funds-and-margin",
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
                    receivables=0,
                    available_cash=float(limits.get("availableCash", 0)),
                    available_intraday_credit=0,
                    available_margin=float(limits.get("netMarginAvailable", 0)),
                )
            raise Exception("Failed to get fund limits")

    async def get_quote(self, symbol: str, exchange: str) -> MarketQuote:
        """Get market quote."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/v2/market-quote/quote",
                params={"instrumentKey": symbol},
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                quote = data.get("data", {}).get(symbol, {})
                return MarketQuote(
                    symbol=symbol,
                    exchange=exchange,
                    last_price=quote.get("lastPrice", 0),
                    open=quote.get("open", 0),
                    high=quote.get("high", 0),
                    low=quote.get("low", 0),
                    close=quote.get("close", 0),
                    volume=quote.get("volume", 0),
                    bid=quote.get("bid", {}).get("price", 0),
                    ask=quote.get("ask", {}).get("price", 0),
                    bid_quantity=quote.get("bid", {}).get("quantity", 0),
                    ask_quantity=quote.get("ask", {}).get("quantity", 0),
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
        interval_map = {
            "1m": "1minute",
            "5m": "5minute",
            "15m": "15minute",
            "30m": "30minute",
            "1h": "1hour",
            "1d": "day",
        }

        async with httpx.AsyncClient() as client:
            params = {
                "instrumentKey": symbol,
                "from": from_date.strftime("%Y-%m-%d"),
                "to": to_date.strftime("%Y-%m-%d"),
                "interval": interval_map.get(interval, "1minute"),
            }
            response = await client.get(
                f"{self.BASE_URL}/v2/market-quote/historical-candle",
                params=params,
                headers=self._generate_headers(),
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                candles = data.get("data", {}).get("candles", [])
                return [
                    {
                        "timestamp": datetime.fromisoformat(c[0]),
                        "open": c[1],
                        "high": c[2],
                        "low": c[3],
                        "close": c[4],
                        "volume": c[5],
                    }
                    for c in candles
                ]
            return []

    async def close_connection(self):
        """Close broker connection."""
        pass

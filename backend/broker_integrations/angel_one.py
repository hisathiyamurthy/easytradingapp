"""Angel One broker integration."""
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


@BrokerRegistry.register(BrokerName.ANGEL_ONE)
class AngelOneBroker(BrokerBase):
    """Angel One API implementation."""

    BASE_URL = "https://apiconnect.angelone.in"
    SMART_API_URL = "https://smartapi.angelone.in"

    @staticmethod
    def get_credential_fields() -> list[CredentialField]:
        return [
            CredentialField(
                name="api_key",
                label="API Key",
                field_type="text",
                required=True,
                placeholder="Enter your Angel One API Key",
            ),
            CredentialField(
                name="client_code",
                label="Client Code",
                field_type="text",
                required=True,
                placeholder="Enter your Client Code",
            ),
            CredentialField(
                name="password",
                label="Password",
                field_type="password",
                required=True,
                placeholder="Enter your Angel One Password",
            ),
            CredentialField(
                name="totp_secret",
                label="TOTP Secret",
                field_type="password",
                required=True,
                placeholder="Enter TOTP Secret for 2FA",
            ),
        ]

    @staticmethod
    def get_required_scopes() -> list[str]:
        return ["order", "trade", "position", "holdings", "user"]

    def __init__(self, config: BrokerConfig, encryption_key: bytes):
        super().__init__(config, encryption_key)
        self.api_key = config.api_key
        self.client_code = config.additional_fields.get("client_code", "")
        self.password = config.additional_fields.get("password", "")
        self.totp_secret = config.additional_fields.get("totp_secret", "")
        self.access_token = ""

    def _generate_headers(self) -> dict:
        """Generate headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00",
        }
        return headers

    def _generate_signature(self, method: str, path: str, body: str = "") -> str:
        """Generate signature for API request."""
        string_to_sign = method + path + self.api_key + self.access_token + str(int(time.time() * 1000)) + body
        signature = hmac.new(
            self.api_key.encode(),
            string_to_sign.encode(),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(signature).decode()

    async def test_connection(self) -> ConnectionStatus:
        """Test Angel One connection."""
        try:
            async with httpx.AsyncClient() as client:
                headers = self._generate_headers()
                headers["Authorization"] = f"Bearer {self.access_token}"

                response = await client.get(
                    f"{self.SMART_API_URL}/rest/auth/validateSession",
                    headers=headers,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    return ConnectionStatus(
                        is_connected=True,
                        message="Connected successfully",
                        user_name=self.client_code,
                        broker_name=BrokerName.ANGEL_ONE,
                    )
                elif response.status_code == 401:
                    return ConnectionStatus(
                        is_connected=False,
                        message="Invalid access token",
                        broker_name=BrokerName.ANGEL_ONE,
                    )
                else:
                    return ConnectionStatus(
                        is_connected=False,
                        message=f"Connection failed: {response.status_code}",
                        broker_name=BrokerName.ANGEL_ONE,
                    )
        except Exception as e:
            return ConnectionStatus(
                is_connected=False,
                message=f"Connection error: {str(e)}",
                broker_name=BrokerName.ANGEL_ONE,
            )

    async def authenticate(self, additional_params: dict) -> dict:
        """Authenticate with Angel One."""
        import pyotp

        url = f"{self.SMART_API_URL}/rest/auth/login"
        
        totp = pyotp.TOTP(self.totp_secret)
        totp_code = totp.now()

        body = json.dumps({
            "clientcode": self.client_code,
            "password": self.password,
            "yob": "",
            "攝取": totp_code,
        })

        headers = {
            "Content-Type": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00",
            "X-ApiKey": self.api_key,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                content=body,
                headers=headers,
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    self.access_token = data.get("data", {}).get("jwtToken", "")
                    return {"authenticated": True, "data": data}
            raise Exception(f"Authentication failed: {response.text}")

    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place an order on Angel One."""
        order_types_map = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.SL: "STOPLOSS_LIMIT",
            OrderType.SLM: "STOPLOSS_MARKET",
        }

        product_types_map = {
            ProductType.CNC: "CNC",
            ProductType.MIS: "MIS",
            ProductType.NRML: "NRML",
        }

        order_params = {
            "variety": "NORMAL",
            "symboltoken": order.symbol,
            "exchange": order.exchange.upper(),
            "transactiontype": order.side.value.upper(),
            "quantity": order.quantity,
            "ordertype": order_types_map.get(order.order_type, "MARKET"),
            "producttype": product_types_map.get(order.product_type, "MIS"),
            "duration": "DAY",
        }

        if order.price:
            order_params["price"] = str(order.price)
        if order.trigger_price:
            order_params["triggerprice"] = str(order.trigger_price)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.SMART_API_URL}/rest/auth/placeOrder",
                json=order_params,
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code in [200, 201]:
                data = response.json()
                if data.get("status"):
                    order_data = data.get("data", {})
                    return OrderResponse(
                        broker_order_id=str(order_data.get("orderid", "")),
                        order_id=str(order_data.get("orderid", "")),
                        symbol=order_data.get("symboltoken", order.symbol),
                        exchange=order.exchange,
                        side=OrderSide.BUY if order_data.get("transactiontype") == "BUY" else OrderSide.SELL,
                        order_type=order.order_type,
                        status=self._map_order_status(order_data.get("status", "")),
                        quantity=order_data.get("quantity", order.quantity),
                        filled_quantity=order_data.get("filledshares", 0),
                        price=order_data.get("price"),
                        avg_fill_price=order_data.get("averageprice"),
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        raw_response=order_data,
                )
            raise Exception(f"Order placement failed: {response.text}")

    def _map_order_status(self, status: str) -> OrderStatus:
        """Map Angel One order status to standard status."""
        status_map = {
            "OPEN": OrderStatus.PENDING,
            "NEW": OrderStatus.SUBMITTED,
            "PARTIALLY FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "PENDING": OrderStatus.PENDING,
        }
        return status_map.get(status.upper(), OrderStatus.PENDING)

    async def cancel_order(self, order_id: str, exchange: str = "NSE") -> bool:
        """Cancel an order."""
        order_params = {
            "variety": "NORMAL",
            "orderid": order_id,
            "exchange": exchange,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.SMART_API_URL}/rest/auth/cancelOrder",
                json=order_params,
                headers=self._generate_headers(),
                timeout=10.0,
            )
            data = response.json()
            return data.get("status", False)

    async def modify_order(self, order_id: str, order: OrderRequest) -> OrderResponse:
        """Modify an order."""
        order_params = {
            "variety": "NORMAL",
            "orderid": order_id,
            "quantity": order.quantity or "",
            "price": str(order.price) if order.price else "",
            "triggerprice": str(order.trigger_price) if order.trigger_price else "",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.SMART_API_URL}/rest/auth/modifyOrder",
                json=order_params,
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    return await self.get_order_status(order_id)
            raise Exception(f"Order modification failed: {response.text}")

    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.SMART_API_URL}/rest/auth/orderDetails/{order_id}",
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    order_data = data.get("data", {})
                    return OrderResponse(
                        broker_order_id=str(order_data.get("orderid", "")),
                        order_id=str(order_data.get("orderid", "")),
                        symbol=order_data.get("symboltoken", ""),
                        exchange=order_data.get("exchange", ""),
                        side=OrderSide.BUY if order_data.get("transactiontype") == "BUY" else OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        status=self._map_order_status(order_data.get("status", "")),
                        quantity=int(order_data.get("quantity", 0)),
                        filled_quantity=int(order_data.get("filledshares", 0)),
                        price=float(order_data.get("price", 0)) if order_data.get("price") else None,
                        avg_fill_price=float(order_data.get("averageprice", 0)) if order_data.get("averageprice") else None,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        raw_response=order_data,
                )
            raise Exception(f"Failed to get order status: {response.text}")

    async def get_positions(self) -> list[Position]:
        """Get open positions."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.SMART_API_URL}/rest/auth/position",
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    positions = []
                    for pos in data.get("data", []):
                        if int(pos.get("netquantity", 0)) != 0:
                            positions.append(
                                Position(
                                    symbol=pos.get("symboltoken", ""),
                                    exchange=pos.get("exchange", ""),
                                    quantity=abs(int(pos.get("netquantity", 0))),
                                    avg_price=float(pos.get("avgnetprice", 0)),
                                    current_price=float(pos.get("ltp", 0)),
                                    unrealized_pnl=float(pos.get("unrealizedPnl", 0)),
                                    product_type=ProductType.MIS if pos.get("producttype") == "MIS" else ProductType.NRML,
                                )
                            )
                    return positions
            return []

    async def get_portfolio(self) -> list[Portfolio]:
        """Get portfolio holdings."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.SMART_API_URL}/rest/auth/holdings",
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    holdings = []
                    for holding in data.get("data", []):
                        holdings.append(
                            Portfolio(
                                symbol=holding.get("symboltoken", ""),
                                exchange=holding.get("exchange", ""),
                                quantity=int(holding.get("quantity", 0)),
                                avg_price=float(holding.get("averageprice", 0)),
                                ltp=float(holding.get("ltp", 0)),
                                close=float(holding.get("close", 0)),
                                pnl=float(holding.get("pnl", 0)),
                                pnl_percent=float(holding.get("pnlpercent", 0)),
                            )
                        )
                    return holdings
            return []

    async def get_fund_limits(self) -> FundLimit:
        """Get available funds."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.SMART_API_URL}/rest/auth/margin",
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    limits = data.get("data", {})
                    return FundLimit(
                        cash=float(limits.get("cash", 0)),
                        collateral=float(limits.get("collateral", 0)),
                        payable=0,
                        receivables=0,
                        available_cash=float(limits.get("net", 0)),
                        available_intraday_credit=0,
                        available_margin=float(limits.get("marginAvailable", 0)),
                    )
            raise Exception("Failed to get fund limits")

    async def get_quote(self, symbol: str, exchange: str) -> MarketQuote:
        """Get market quote."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.SMART_API_URL}/rest/auth/quote/{exchange}/{symbol}",
                headers=self._generate_headers(),
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    quote = data.get("data", {})
                    return MarketQuote(
                        symbol=symbol,
                        exchange=exchange,
                        last_price=float(quote.get("lastPrice", 0)),
                        open=float(quote.get("open", 0)),
                        high=float(quote.get("high", 0)),
                        low=float(quote.get("low", 0)),
                        close=float(quote.get("close", 0)),
                        volume=int(quote.get("volume", 0)),
                        bid=float(quote.get("bestBid", 0)),
                        ask=float(quote.get("bestAsk", 0)),
                        bid_quantity=int(quote.get("bestBidQty", 0)),
                        ask_quantity=int(quote.get("bestAskQty", 0)),
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
            "1m": "ONE_MINUTE",
            "5m": "FIVE_MINUTE",
            "15m": "FIFTEEN_MINUTE",
            "30m": "THIRTY_MINUTE",
            "1h": "ONE_HOUR",
            "1d": "ONE_DAY",
        }

        async with httpx.AsyncClient() as client:
            params = {
                "symbol": symbol,
                "exchange": exchange,
                "fromdate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
                "todate": to_date.strftime("%Y-%m-%d %H:%M:%S"),
                "interval": interval_map.get(interval, "ONE_MINUTE"),
            }
            response = await client.get(
                f"{self.SMART_API_URL}/rest/authHistoricalData",
                params=params,
                headers=self._generate_headers(),
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
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
        self.access_token = ""

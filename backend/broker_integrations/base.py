"""Broker integration base module."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class BrokerName(str, Enum):
    ZERODHA = "zerodha"
    KOTAK_NEO = "kotak_neo"
    UPSTOX = "upstox"
    ANGEL_ONE = "angel_one"
    ALICE_BLUE = "alice_blue"
    FYERS = "fyers"
    HDFC_SECURITIES = "hdfc_securities"
    ICICI_DIRECT = "icici_direct"
    AXIS_DIRECT = "axis_direct"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    SL = "sl"
    SLM = "slm"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class ProductType(str, Enum):
    CNC = "cnc"  # Cash and Carry
    MIS = "mis"  # Margin Intraday Square-off
    NRML = "nrml"  # Normal


@dataclass
class CredentialField:
    """Dynamic credential field definition."""
    name: str
    label: str
    field_type: str  # text, password, dropdown
    required: bool = True
    placeholder: Optional[str] = None
    options: Optional[list[dict]] = None  # For dropdowns
    help_text: Optional[str] = None


@dataclass
class BrokerConfig:
    """Broker configuration."""
    broker_name: BrokerName
    api_key: str
    api_secret: str
    additional_fields: dict[str, str] = None


@dataclass
class OrderRequest:
    """Order request payload."""
    symbol: str
    exchange: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    product_type: ProductType = ProductType.MIS
    validity: str = "DAY"
    disclosed_quantity: int = 0


@dataclass
class OrderResponse:
    """Order response from broker."""
    broker_order_id: str
    order_id: str
    symbol: str
    exchange: str
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    quantity: int
    filled_quantity: int
    price: Optional[float]
    avg_fill_price: Optional[float]
    created_at: datetime
    updated_at: datetime
    raw_response: dict


@dataclass
class Position:
    """Position data."""
    symbol: str
    exchange: str
    quantity: int
    avg_price: float
    current_price: float
    unrealized_pnl: float
    product_type: ProductType


@dataclass
class Portfolio:
    """Portfolio holdings."""
    symbol: str
    exchange: str
    quantity: int
    avg_price: float
    ltp: float
    close: float
    pnl: float
    pnl_percent: float


@dataclass
class FundLimit:
    """Available funds and limits."""
    cash: float
    collateral: float
    payable: float
    receivables: float
    available_cash: float
    available_intraday_credit: float
    available_margin: float


@dataclass
class MarketQuote:
    """Market quote data."""
    symbol: str
    exchange: str
    last_price: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    bid: float
    ask: float
    bid_quantity: int
    ask_quantity: int
    timestamp: datetime


@dataclass
class ConnectionStatus:
    """Broker connection status."""
    is_connected: bool
    message: str
    user_name: Optional[str] = None
    user_id: Optional[str] = None
    broker_name: Optional[BrokerName] = None
    feed_token: Optional[str] = None
    api_token: Optional[str] = None


class BrokerBase(ABC):
    """Base class for broker integrations."""

    def __init__(self, config: BrokerConfig, encryption_key: bytes):
        self.config = config
        self.encryption_key = encryption_key
        self._access_token: Optional[str] = None
        self._feed_token: Optional[str] = None

    @staticmethod
    @abstractmethod
    def get_credential_fields() -> list[CredentialField]:
        """Return dynamic credential fields for this broker."""
        pass

    @staticmethod
    @abstractmethod
    def get_required_scopes() -> list[str]:
        """Return required API scopes."""
        pass

    @abstractmethod
    async def test_connection(self) -> ConnectionStatus:
        """Test broker connection."""
        pass

    @abstractmethod
    async def authenticate(self, additional_params: dict) -> dict:
        """Authenticate with broker API."""
        pass

    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place an order."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        pass

    @abstractmethod
    async def modify_order(self, order_id: str, order: OrderRequest) -> OrderResponse:
        """Modify an order."""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status."""
        pass

    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """Get open positions."""
        pass

    @abstractmethod
    async def get_portfolio(self) -> list[Portfolio]:
        """Get portfolio holdings."""
        pass

    @abstractmethod
    async def get_fund_limits(self) -> FundLimit:
        """Get available funds."""
        pass

    @abstractmethod
    async def get_quote(self, symbol: str, exchange: str) -> MarketQuote:
        """Get market quote."""
        pass

    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        exchange: str,
        from_date: datetime,
        to_date: datetime,
        interval: str,
    ) -> list[dict]:
        """Get historical data."""
        pass

    @abstractmethod
    async def get_profile(self) -> dict:
        """Get user profile."""
        pass

    @abstractmethod
    async def get_holdings(self) -> list[dict]:
        """Get holdings."""
        pass

    @abstractmethod
    async def get_orders(self, from_date: Optional[datetime] = None) -> list[OrderResponse]:
        """Get order history."""
        pass

    @abstractmethod
    async def get_trades(self, from_date: Optional[datetime] = None) -> list[dict]:
        """Get trade history."""
        pass

    @abstractmethod
    async def close_connection(self):
        """Close broker connection."""
        pass


class BrokerRegistry:
    """Registry for broker implementations."""

    _brokers: dict[BrokerName, type[BrokerBase]] = {}

    @classmethod
    def register(cls, broker_name: BrokerName):
        """Decorator to register a broker."""
        def decorator(broker_class: type[BrokerBase]):
            cls._brokers[broker_name] = broker_class
            return broker_class
        return decorator

    @classmethod
    def get_broker(cls, broker_name: BrokerName) -> type[BrokerBase]:
        """Get broker class by name."""
        if broker_name not in cls._brokers:
            raise ValueError(f"Broker {broker_name} not registered")
        return cls._brokers[broker_name]

    @classmethod
    def get_available_brokers(cls) -> dict[BrokerName, type[BrokerBase]]:
        """Get all registered brokers."""
        return cls._brokers.copy()

    @classmethod
    def get_broker_credential_fields(cls, broker_name: BrokerName) -> list[CredentialField]:
        """Get credential fields for a broker."""
        return cls.get_broker(broker_name).get_credential_fields()

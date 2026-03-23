"""Order Execution Layer - Broker APIs and Order Tracking."""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

import aio_pika

from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ProductType(str, Enum):
    CNC = "cnc"  # Cash and Carry
    MIS = "mis"  # Margin Intraday Square-off
    NRML = "nrml"  # Normal


class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill


@dataclass
class OrderRequest:
    """Order request to be sent to broker."""
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    strategy_id: Optional[str] = None
    broker_account_id: str = ""
    
    symbol: str = ""
    exchange: str = "NSE"
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: int = 0
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    product_type: ProductType = ProductType.MIS
    validity: TimeInForce = TimeInForce.DAY
    disclosed_quantity: int = 0
    
    # Metadata
    client_order_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OrderResponse:
    """Order response from broker."""
    id: str = ""
    broker_order_id: str = ""
    user_id: str = ""
    strategy_id: Optional[str] = None
    broker_account_id: str = ""
    
    symbol: str = ""
    exchange: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    status: OrderStatus = OrderStatus.PENDING
    
    quantity: int = 0
    filled_quantity: int = 0
    remaining_quantity: int = 0
    
    price: Optional[float] = None
    avg_fill_price: Optional[float] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    error_message: Optional[str] = None
    raw_response: dict = field(default_factory=dict)


@dataclass
class TradeInfo:
    """Trade/Execution information."""
    id: str = field(default_factory=lambda: str(uuid4()))
    order_id: str = ""
    user_id: str = ""
    
    trade_id: str = ""  # Broker's trade ID
    symbol: str = ""
    exchange: str = ""
    side: OrderSide = OrderSide.BUY
    
    quantity: int = 0
    price: float = 0
    commission: float = 0
    fees: float = 0
    
    executed_at: datetime = field(default_factory=datetime.utcnow)


class OrderExecutor:
    """Order execution manager with broker integration."""

    def __init__(self, broker_service, risk_service, event_bus=None):
        self.broker_service = broker_service
        self.risk_service = risk_service
        self.event_bus = event_bus
        
        # Order tracking
        self._orders: dict[str, OrderResponse] = {}
        self._order_locks: dict[str, asyncio.Lock] = {}
        
        # Idempotency tracking (maps client_order_id -> OrderResponse)
        self._idempotency_cache: dict[str, OrderResponse] = {}
        
        # Order queues per broker
        self._broker_queues: dict[str, asyncio.Queue] = {}

    async def _check_idempotency(self, client_order_id: str) -> Optional[OrderResponse]:
        """Check if an order with this idempotency key already exists."""
        return self._idempotency_cache.get(client_order_id)

    async def initialize(self):
        """Initialize the order executor."""
        logger.info("Order executor initialized")
        
        # Subscribe to order events if event bus available
        if self.event_bus:
            await self.event_bus.subscribe(
                "order_events",
                "orders",
                "order.*",
                self._handle_order_event,
            )

    async def place_order(self, request: OrderRequest) -> OrderResponse:
        """Place an order through the broker with idempotency check."""
        # Check for duplicate order using client_order_id (idempotency key)
        if request.client_order_id:
            existing = await self._check_idempotency(request.client_order_id)
            if existing:
                logger.info(f"Duplicate order detected: {request.client_order_id}, returning existing order {existing.id}")
                return existing
        
        async with self._get_order_lock(request.id):
            # Validate order
            validation = await self._validate_order(request)
            if not validation.is_valid:
                return self._create_error_response(
                    request,
                    validation.error_message or "Order validation failed",
                    OrderStatus.REJECTED,
                )

            # Check risk limits
            risk_check = await self.risk_service.check_order_risk(
                user_id=request.user_id,
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                price=request.price,
            )
            
            if not risk_check.approved:
                return self._create_error_response(
                    request,
                    risk_check.message,
                    OrderStatus.REJECTED,
                )

            # Create pending order
            order = OrderResponse(
                id=request.id,
                user_id=request.user_id,
                strategy_id=request.strategy_id,
                broker_account_id=request.broker_account_id,
                symbol=request.symbol,
                exchange=request.exchange,
                side=request.side,
                order_type=request.order_type,
                status=OrderStatus.PENDING,
                quantity=request.quantity,
                created_at=request.created_at,
            )

            self._orders[request.id] = order
            
            # Store in idempotency cache if client_order_id provided
            if request.client_order_id:
                self._idempotency_cache[request.client_order_id] = order

            try:
                # Submit to broker
                broker_response = await self._submit_to_broker(request)
                
                # Update order with broker response
                order.broker_order_id = broker_response.get("order_id", "")
                order.status = OrderStatus.SUBMITTED
                order.submitted_at = datetime.utcnow()
                order.raw_response = broker_response
                
                logger.info(
                    f"Order submitted: {order.id} -> {order.broker_order_id} "
                    f"({request.side.value} {request.quantity} {request.symbol})"
                )
                
                # Publish order event
                await self._publish_order_event("order_submitted", order)
                
                return order
                
            except Exception as e:
                logger.error(f"Order submission failed: {e}")
                order.status = OrderStatus.REJECTED
                order.error_message = str(e)
                return order

    async def cancel_order(self, order_id: str, user_id: str) -> OrderResponse:
        """Cancel an existing order."""
        async with self._get_order_lock(order_id):
            order = self._orders.get(order_id)
            
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            if order.user_id != user_id:
                raise PermissionError("Not authorized to cancel this order")
            
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                raise ValueError(f"Cannot cancel order in {order.status} status")

            try:
                # Submit cancellation to broker
                await self.broker_service.cancel_order(
                    order.broker_account_id,
                    order.broker_order_id,
                )
                
                order.status = OrderStatus.CANCELLED
                order.cancelled_at = datetime.utcnow()
                
                logger.info(f"Order cancelled: {order_id}")
                
                await self._publish_order_event("order_cancelled", order)
                
                return order
                
            except Exception as e:
                logger.error(f"Order cancellation failed: {e}")
                order.error_message = f"Cancellation failed: {str(e)}"
                return order

    async def modify_order(
        self,
        order_id: str,
        user_id: str,
        new_quantity: Optional[int] = None,
        new_price: Optional[float] = None,
        new_trigger_price: Optional[float] = None,
    ) -> OrderResponse:
        """Modify an existing order."""
        async with self._get_order_lock(order_id):
            order = self._orders.get(order_id)
            
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            if order.user_id != user_id:
                raise PermissionError("Not authorized to modify this order")
            
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                raise ValueError(f"Cannot modify order in {order.status} status")

            # Create modification request
            modify_request = OrderRequest(
                id=order_id,
                user_id=user_id,
                broker_account_id=order.broker_account_id,
                symbol=order.symbol,
                exchange=order.exchange,
                side=order.side,
                order_type=order.order_type,
                quantity=new_quantity or order.quantity,
                price=new_price or order.price,
                trigger_price=new_trigger_price or order.trigger_price,
            )

            try:
                broker_response = await self.broker_service.modify_order(
                    order.broker_account_id,
                    order.broker_order_id,
                    modify_request,
                )
                
                # Update order
                if new_quantity:
                    order.quantity = new_quantity
                if new_price:
                    order.price = new_price
                if new_trigger_price:
                    order.trigger_price = new_trigger_price
                
                order.updated_at = datetime.utcnow()
                order.raw_response = broker_response
                
                logger.info(f"Order modified: {order_id}")
                
                await self._publish_order_event("order_modified", order)
                
                return order
                
            except Exception as e:
                logger.error(f"Order modification failed: {e}")
                order.error_message = f"Modification failed: {str(e)}"
                return order

    async def get_order_status(self, order_id: str) -> Optional[OrderResponse]:
        """Get current order status."""
        return self._orders.get(order_id)

    async def get_user_orders(
        self,
        user_id: str,
        status: Optional[OrderStatus] = None,
        symbol: Optional[str] = None,
    ) -> list[OrderResponse]:
        """Get all orders for a user."""
        orders = [
            o for o in self._orders.values()
            if o.user_id == user_id
        ]
        
        if status:
            orders = [o for o in orders if o.status == status]
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        return sorted(orders, key=lambda x: x.created_at or datetime.min, reverse=True)

    async def sync_order_status(self, order_id: str) -> OrderResponse:
        """Synchronize order status with broker."""
        order = self._orders.get(order_id)
        
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if not order.broker_order_id:
            return order

        try:
            broker_order = await self.broker_service.get_order_status(
                order.broker_account_id,
                order.broker_order_id,
            )
            
            # Update local order
            order.status = self._map_broker_status(broker_order.get("status"))
            order.filled_quantity = broker_order.get("filled_quantity", 0)
            order.remaining_quantity = broker_order.get("remaining_quantity", 0)
            order.avg_fill_price = broker_order.get("avg_fill_price")
            order.updated_at = datetime.utcnow()
            
            if order.status == OrderStatus.FILLED:
                order.filled_at = datetime.utcnow()
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to sync order status: {e}")
            return order

    async def _validate_order(self, request: OrderRequest) -> 'OrderValidation':
        """Validate order parameters."""
        if request.quantity <= 0:
            return OrderValidation(False, "Quantity must be positive")
        
        if request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            if not request.price or request.price <= 0:
                return OrderValidation(False, "Limit price required for limit orders")
        
        if request.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            if not request.trigger_price or request.trigger_price <= 0:
                return OrderValidation(False, "Trigger price required for stop orders")
        
        return OrderValidation(True)

    def _get_order_lock(self, order_id: str) -> asyncio.Lock:
        """Get or create lock for order."""
        if order_id not in self._order_locks:
            self._order_locks[order_id] = asyncio.Lock()
        return self._order_locks[order_id]

    async def _submit_to_broker(self, request: OrderRequest) -> dict:
        """Submit order to broker."""
        broker_order = await self.broker_service.place_order(
            broker_account_id=request.broker_account_id,
            order_data={
                "symbol": request.symbol,
                "exchange": request.exchange,
                "side": request.side.value,
                "order_type": request.order_type.value,
                "quantity": request.quantity,
                "price": request.price,
                "trigger_price": request.trigger_price,
                "product_type": request.product_type.value,
                "validity": request.validity.value,
            },
        )
        return broker_order

    async def _handle_order_event(self, event: dict):
        """Handle order events from broker."""
        event_type = event.get("type")
        
        if event_type == "order_update":
            await self._handle_order_update(event)
        elif event_type == "trade":
            await self._handle_trade_event(event)

    async def _handle_order_update(self, event: dict):
        """Handle order status update from broker."""
        broker_order_id = event.get("broker_order_id")
        
        # Find order by broker order ID
        order = None
        for o in self._orders.values():
            if o.broker_order_id == broker_order_id:
                order = o
                break
        
        if not order:
            logger.warning(f"Order not found for update: {broker_order_id}")
            return

        # Update order
        order.status = self._map_broker_status(event.get("status"))
        order.filled_quantity = event.get("filled_quantity", 0)
        order.remaining_quantity = event.get("remaining_quantity", 0)
        order.avg_fill_price = event.get("avg_fill_price")
        order.updated_at = datetime.utcnow()

        if order.status == OrderStatus.FILLED:
            order.filled_at = datetime.utcnow()

        await self._publish_order_event("order_updated", order)

    async def _handle_trade_event(self, event: dict):
        """Handle trade/execution event from broker."""
        trade_data = event.get("trade", {})
        
        trade = TradeInfo(
            order_id=event.get("order_id"),
            user_id=event.get("user_id"),
            trade_id=trade_data.get("trade_id"),
            symbol=trade_data.get("symbol"),
            exchange=trade_data.get("exchange"),
            side=OrderSide(trade_data.get("side")),
            quantity=trade_data.get("quantity"),
            price=trade_data.get("price"),
            commission=trade_data.get("commission", 0),
            fees=trade_data.get("fees", 0),
            executed_at=datetime.fromisoformat(trade_data.get("executed_at")),
        )
        
        # Update order with fill
        order = self._orders.get(trade.order_id)
        if order:
            order.filled_quantity += trade.quantity
            order.remaining_quantity = order.quantity - order.filled_quantity
            
            if order.avg_fill_price:
                order.avg_fill_price = (
                    (order.avg_fill_price * (order.filled_quantity - trade.quantity) 
                     + trade.price * trade.quantity) 
                    / order.filled_quantity
                )
            else:
                order.avg_fill_price = trade.price
            
            if order.filled_quantity >= order.quantity:
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.utcnow()

        logger.info(
            f"Trade executed: {trade.trade_id} - {trade.side.value} "
            f"{trade.quantity} {trade.symbol} @ {trade.price}"
        )

    async def _publish_order_event(self, event_type: str, order: OrderResponse):
        """Publish order event."""
        if not self.event_bus:
            return
        
        await self.event_bus.publish(
            "order_updates",
            f"order.{order.user_id}",
            {
                "type": event_type,
                "order_id": order.id,
                "broker_order_id": order.broker_order_id,
                "user_id": order.user_id,
                "symbol": order.symbol,
                "status": order.status.value,
                "filled_quantity": order.filled_quantity,
                "avg_fill_price": order.avg_fill_price,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    def _map_broker_status(self, broker_status: str) -> OrderStatus:
        """Map broker status to standard status."""
        status_map = {
            "pending": OrderStatus.PENDING,
            "submitted": OrderStatus.SUBMITTED,
            "open": OrderStatus.SUBMITTED,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "partially filled": OrderStatus.PARTIALLY_FILLED,
            "filled": OrderStatus.FILLED,
            "completed": OrderStatus.FILLED,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "expired": OrderStatus.EXPIRED,
        }
        return status_map.get(broker_status.lower(), OrderStatus.PENDING)

    def _create_error_response(
        self,
        request: OrderRequest,
        error_message: str,
        status: OrderStatus,
    ) -> OrderResponse:
        """Create error response."""
        return OrderResponse(
            id=request.id,
            user_id=request.user_id,
            strategy_id=request.strategy_id,
            broker_account_id=request.broker_account_id,
            symbol=request.symbol,
            exchange=request.exchange,
            side=request.side,
            order_type=request.order_type,
            status=status,
            quantity=request.quantity,
            price=request.price,
            error_message=error_message,
            created_at=request.created_at,
        )


@dataclass
class OrderValidation:
    """Order validation result."""
    is_valid: bool
    error_message: Optional[str] = None


class OrderQueue:
    """Queue for managing order submission rate limiting."""

    def __init__(self, max_per_second: int = 10):
        self.max_per_second = max_per_second
        self._queue: asyncio.Queue = asyncio.Queue()
        self._last_submit_time: datetime = datetime.min
        self._lock = asyncio.Lock()

    async def enqueue(self, order: OrderRequest):
        """Add order to queue."""
        await self._queue.put(order)

    async def dequeue(self) -> Optional[OrderRequest]:
        """Get next order from queue."""
        async with self._lock:
            now = datetime.utcnow()
            
            # Rate limiting
            time_since_last = (now - self._last_submit_time).total_seconds()
            if time_since_last < (1 / self.max_per_second):
                await asyncio.sleep((1 / self.max_per_second) - time_since_last)
            
            try:
                order = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0,
                )
                self._last_submit_time = datetime.utcnow()
                return order
            except asyncio.TimeoutError:
                return None

    @property
    def size(self) -> int:
        return self._queue.qsize()


class OrderLifecycleManager:
    """Manages order lifecycle and state transitions."""

    def __init__(self, executor: OrderExecutor):
        self.executor = executor

    async def monitor_order(self, order_id: str, timeout: float = 60.0) -> OrderResponse:
        """Monitor order until completion or timeout."""
        start_time = datetime.utcnow()
        
        while True:
            order = await self.executor.get_order_status(order_id)
            
            if order.status in [
                OrderStatus.FILLED,
                OrderStatus.CANCELLED,
                OrderStatus.REJECTED,
                OrderStatus.EXPIRED,
            ]:
                return order
            
            # Check timeout
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout:
                return order
            
            # Sync with broker
            try:
                await self.executor.sync_order_status(order_id)
            except Exception as e:
                logger.warning(f"Failed to sync order: {e}")
            
            await asyncio.sleep(1)  # Poll every second

    async def wait_for_fill(
        self,
        order_id: str,
        max_wait_seconds: float = 30.0,
    ) -> tuple[bool, OrderResponse]:
        """Wait for order to be fully filled."""
        order = await self.monitor_order(order_id, max_wait_seconds)
        return order.status == OrderStatus.FILLED, order


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # This would be integrated with actual broker service
        print("Order Execution Layer initialized")
        
        # Example order request
        order_request = OrderRequest(
            user_id="user123",
            strategy_id="strategy456",
            broker_account_id="broker789",
            symbol="NIFTY",
            exchange="NSE",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            price=18000.0,
            product_type=ProductType.MIS,
            validity=TimeInForce.DAY,
        )
        
        print(f"Order Request: {order_request}")

    asyncio.run(main())

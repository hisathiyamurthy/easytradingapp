"""Event-driven strategy execution engine."""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

import aio_pika
import aio_pika.abc
from pydantic import BaseModel

from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class EventType(str, Enum):
    MARKET_DATA = "market_data"
    SIGNAL = "signal"
    ORDER = "order"
    ORDER_UPDATE = "order_update"
    TRADE = "trade"
    POSITION = "position"
    RISK_CHECK = "risk_check"
    STRATEGY_START = "strategy_start"
    STRATEGY_STOP = "strategy_stop"
    HEARTBEAT = "heartbeat"


class WorkerStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class MarketDataEvent:
    """Market data event."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: EventType = EventType.MARKET_DATA
    symbol: str
    exchange: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SignalEvent:
    """Trading signal event."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: EventType = EventType.SIGNAL
    strategy_id: str
    user_id: str
    symbol: str
    exchange: str
    signal_type: SignalType
    confidence: float = 1.0
    price: Optional[float] = None
    quantity: int = 1
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OrderEvent:
    """Order event."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: EventType = EventType.ORDER
    order_id: str
    strategy_id: str
    user_id: str
    symbol: str
    exchange: str
    side: str
    quantity: int
    order_type: str
    price: Optional[float] = None
    status: str = "pending"
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkerMetrics:
    """Worker metrics."""
    worker_id: str
    status: WorkerStatus
    messages_processed: int = 0
    messages_failed: int = 0
    last_processed_at: Optional[datetime] = None
    uptime_seconds: float = 0
    avg_processing_time_ms: float = 0


class EventBus:
    """Event bus for pub/sub messaging."""

    def __init__(self):
        self._connection: Optional[aio_pika.abc.AbstractConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None
        self._exchanges: dict[str, aio_pika.abc.AbstractExchange] = {}
        self._queues: dict[str, aio_pika.abc.AbstractQueue] = {}
        self._consumers: dict[str, asyncio.Task] = {}

    async def connect(self):
        """Connect to message broker."""
        self._connection = await aio_pika.connect_robust(
            settings.RABBITMQ_URL,
            heartbeat=30,
            reconnection_strategy=aio_pika.robust.RobustReconnectionStrategy(),
        )
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)
        logger.info("Event bus connected to RabbitMQ")

    async def disconnect(self):
        """Disconnect from message broker."""
        for consumer in self._consumers.values():
            consumer.cancel()
        
        for queue in self._queues.values():
            await queue.delete()
        
        for exchange in self._exchanges.values():
            await exchange.delete()
        
        if self._channel:
            await self._channel.close()
        if self._connection:
            await self._connection.close()
        
        logger.info("Event bus disconnected")

    async def declare_exchange(self, name: str, durable: bool = True) -> aio_pika.abc.AbstractExchange:
        """Declare an exchange."""
        if name not in self._exchanges:
            self._exchanges[name] = await self._channel.declare_exchange(
                name,
                aio_pika.ExchangeType.TOPIC,
                durable=durable,
            )
        return self._exchanges[name]

    async def declare_queue(self, name: str, durable: bool = True) -> aio_pika.abc.AbstractQueue:
        """Declare a queue."""
        if name not in self._queues:
            self._queues[name] = await self._channel.declare_queue(
                name,
                durable=durable,
                arguments={
                    "x-message-ttl": 86400000,  # 24 hours
                },
            )
        return self._queues[name]

    async def publish(self, exchange: str, routing_key: str, message: dict):
        """Publish message to exchange."""
        if exchange not in self._exchanges:
            await self.declare_exchange(exchange)
        
        await self._exchanges[exchange].publish(
            aio_pika.Message(
                body=json.dumps(message, default=str).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=routing_key,
        )

    async def subscribe(
        self,
        queue_name: str,
        exchange: str,
        routing_key: str,
        handler: Callable,
    ):
        """Subscribe to messages."""
        queue = await self.declare_queue(queue_name)
        exchange = await self.declare_exchange(exchange)
        
        await queue.bind(exchange, routing_key)
        
        consumer = asyncio.create_task(self._consume_messages(queue, handler))
        self._consumers[queue_name] = consumer
        logger.info(f"Subscribed to {queue_name} with routing key {routing_key}")

    async def _consume_messages(self, queue: aio_pika.abc.AbstractQueue, handler: Callable):
        """Consume messages from queue."""
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        data = json.loads(message.body.decode())
                        await handler(data)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")


class RetryPolicy:
    """Retry policy for fault tolerance."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay,
        )
        return delay

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.get_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries + 1} attempts failed: {e}"
                    )
        
        raise last_exception


class CircuitBreaker:
    """Circuit breaker for fault tolerance."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open

    @asynccontextmanager
    async def __call__(self):
        """Context manager for circuit breaker."""
        if self.state == "open":
            if self.last_failure_time:
                time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if time_since_failure >= self.recovery_timeout:
                    self.state = "half_open"
                    logger.info("Circuit breaker entering half-open state")
                else:
                    raise Exception("Circuit breaker is open")
        
        try:
            yield
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker closed")
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e


class StrategyWorker:
    """Base strategy worker for processing events."""

    def __init__(
        self,
        worker_id: str,
        event_bus: EventBus,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        self.worker_id = worker_id
        self.event_bus = event_bus
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_breaker = CircuitBreaker()
        self.metrics = WorkerMetrics(
            worker_id=worker_id,
            status=WorkerStatus.STARTING,
        )
        self._running = False
        self._start_time: Optional[datetime] = None

    async def start(self):
        """Start the worker."""
        self._running = True
        self._start_time = datetime.utcnow()
        self.metrics.status = WorkerStatus.RUNNING
        logger.info(f"Worker {self.worker_id} started")

    async def stop(self):
        """Stop the worker."""
        self._running = False
        self.metrics.status = WorkerStatus.STOPPED
        if self._start_time:
            self.metrics.uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds()
        logger.info(f"Worker {self.worker_id} stopped")

    async def process_event(self, event: dict):
        """Process an event."""
        start_time = datetime.utcnow()
        
        try:
            async with self.circuit_breaker():
                await self.handle_event(event)
            
            self.metrics.messages_processed += 1
            self.metrics.last_processed_at = datetime.utcnow()
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.metrics.avg_processing_time_ms = (
                (self.metrics.avg_processing_time_ms * (self.metrics.messages_processed - 1) + processing_time)
                / self.metrics.messages_processed
            )
            
        except Exception as e:
            self.metrics.messages_failed += 1
            logger.error(f"Worker {self.worker_id} failed to process event: {e}")
            raise

    @abstractmethod
    async def handle_event(self, event: dict):
        """Handle specific event type."""
        pass


class MarketDataWorker(StrategyWorker):
    """Worker for processing market data events."""

    def __init__(self, worker_id: str, event_bus: EventBus, data_handler):
        super().__init__(worker_id, event_bus)
        self.data_handler = data_handler
        self._price_cache: dict[str, float] = {}

    async def handle_event(self, event: dict):
        """Process market data event."""
        event_type = event.get("event_type")
        
        if event_type == EventType.MARKET_DATA.value:
            await self._process_market_data(event)
        else:
            logger.warning(f"Unknown event type: {event_type}")

    async def _process_market_data(self, event: dict):
        """Process and distribute market data."""
        symbol = event.get("symbol")
        
        # Update price cache
        self._price_cache[symbol] = event.get("close", 0)
        
        # Process through data handler
        await self.data_handler.process(event)
        
        # Publish to strategy evaluation topic
        await self.event_bus.publish(
            "market_data",
            f"market.{event.get('exchange')}.{symbol}",
            event,
        )


class SignalEvaluationWorker(StrategyWorker):
    """Worker for evaluating trading signals."""

    def __init__(self, worker_id: str, event_bus: EventBus, strategy_executor):
        super().__init__(worker_id, event_bus)
        self.strategy_executor = strategy_executor
        self._indicators_cache = {}

    async def handle_event(self, event: dict):
        """Process signal evaluation event."""
        event_type = event.get("event_type")
        
        if event_type == EventType.MARKET_DATA.value:
            await self._evaluate_strategies(event)
        elif event_type == EventType.SIGNAL.value:
            await self._forward_signal(event)

    async def _evaluate_strategies(self, event: dict):
        """Evaluate all strategies for the symbol."""
        symbol = event.get("symbol")
        
        # Get active strategies for this symbol
        strategies = await self.strategy_executor.get_strategies_for_symbol(symbol)
        
        for strategy in strategies:
            try:
                signal = await self.retry_policy.execute_with_retry(
                    self.strategy_executor.evaluate,
                    strategy,
                    event,
                )
                
                if signal and signal.signal_type != SignalType.HOLD:
                    # Publish signal event
                    await self.event_bus.publish(
                        "signals",
                        f"signal.{strategy.id}",
                        {
                            "event_type": EventType.SIGNAL.value,
                            "strategy_id": str(strategy.id),
                            "user_id": str(strategy.user_id),
                            "symbol": signal.symbol,
                            "exchange": signal.exchange,
                            "signal_type": signal.signal_type.value,
                            "confidence": signal.confidence,
                            "price": signal.price,
                            "quantity": signal.quantity,
                            "stop_loss": signal.stop_loss,
                            "take_profit": signal.take_profit,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
            except Exception as e:
                logger.error(f"Error evaluating strategy {strategy.id}: {e}")

    async def _forward_signal(self, event: dict):
        """Forward signal to order execution."""
        await self.event_bus.publish(
            "orders",
            f"order.{event.get('user_id')}",
            event,
        )


class OrderExecutionWorker(StrategyWorker):
    """Worker for executing orders."""

    def __init__(
        self,
        worker_id: str,
        event_bus: EventBus,
        broker_service,
        risk_service,
    ):
        super().__init__(worker_id, event_bus)
        self.broker_service = broker_service
        self.risk_service = risk_service

    async def handle_event(self, event: dict):
        """Process order execution event."""
        event_type = event.get("event_type")
        
        if event_type == EventType.SIGNAL.value:
            await self._execute_order(event)

    async def _execute_order(self, event: dict):
        """Execute order from signal."""
        strategy_id = event.get("strategy_id")
        user_id = event.get("user_id")
        symbol = event.get("symbol")
        side = event.get("signal_type")
        
        # Check risk limits
        risk_check = await self.risk_service.check_risk_limits(
            user_id=user_id,
            symbol=symbol,
            quantity=event.get("quantity", 1),
            price=event.get("price"),
        )
        
        if not risk_check.approved:
            logger.warning(f"Risk check failed for {user_id}/{symbol}: {risk_check.message}")
            await self.event_bus.publish(
                "risk_alerts",
                f"alert.{user_id}",
                {
                    "event_type": "risk_alert",
                    "user_id": user_id,
                    "strategy_id": strategy_id,
                    "symbol": symbol,
                    "message": risk_check.message,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            return

        # Place order with retry
        order_request = {
            "symbol": symbol,
            "exchange": event.get("exchange", "NSE"),
            "side": side,
            "order_type": "market",
            "quantity": event.get("quantity", 1),
            "product_type": "MIS",
        }

        try:
            order = await self.retry_policy.execute_with_retry(
                self.broker_service.place_order,
                user_id,
                order_request,
            )

            # Publish order event
            await self.event_bus.publish(
                "orders",
                f"order.{user_id}",
                {
                    "event_type": EventType.ORDER.value,
                    "order_id": order.order_id,
                    "strategy_id": strategy_id,
                    "user_id": user_id,
                    "symbol": symbol,
                    "status": order.status,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            raise


class StrategyExecutor:
    """Strategy executor that manages strategy evaluation."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._strategies: dict[str, dict] = {}
        self._indicators: dict[str, dict] = {}

    async def register_strategy(self, strategy_id: str, config: dict):
        """Register a strategy for execution."""
        self._strategies[strategy_id] = {
            "config": config,
            "indicators": {},
            "last_evaluated": None,
        }

    async def unregister_strategy(self, strategy_id: str):
        """Unregister a strategy."""
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]

    async def get_strategies_for_symbol(self, symbol: str) -> list[dict]:
        """Get all strategies that watch a symbol."""
        matching_strategies = []
        for strategy_id, strategy in self._strategies.items():
            watchlist = strategy["config"].get("watchlist", [])
            if symbol in watchlist:
                matching_strategies.append(strategy)
        return matching_strategies

    async def evaluate(self, strategy: dict, market_data: dict) -> Optional[SignalEvent]:
        """Evaluate a strategy against market data."""
        config = strategy["config"]
        
        # Get indicators
        indicators = await self._calculate_indicators(strategy, market_data)
        
        # Evaluate entry/exit conditions
        signal = await self._evaluate_conditions(config, indicators, market_data)
        
        return signal

    async def _calculate_indicators(self, strategy: dict, market_data: dict) -> dict:
        """Calculate technical indicators."""
        # Placeholder for indicator calculation
        return {
            "sma_20": market_data.get("close", 0),
            "sma_50": market_data.get("close", 0),
            "rsi": 50.0,
        }

    async def _evaluate_conditions(
        self,
        config: dict,
        indicators: dict,
        market_data: dict,
    ) -> Optional[SignalEvent]:
        """Evaluate trading conditions."""
        # Placeholder for condition evaluation
        # In production, this would evaluate strategy-specific conditions
        return None


class ExecutionEngine:
    """Main execution engine that orchestrates workers."""

    def __init__(self):
        self.event_bus = EventBus()
        self.workers: list[StrategyWorker] = []
        self.strategy_executor = StrategyExecutor(self.event_bus)
        self._running = False

    async def start(self):
        """Start the execution engine."""
        await self.event_bus.connect()
        
        # Start workers
        market_data_worker = MarketDataWorker(
            "market_data_1",
            self.event_bus,
            self.strategy_executor,
        )
        
        signal_worker = SignalEvaluationWorker(
            "signal_eval_1",
            self.event_bus,
            self.strategy_executor,
        )
        
        self.workers = [market_data_worker, signal_worker]
        
        for worker in self.workers:
            await worker.start()
        
        # Subscribe to events
        await self.event_bus.subscribe(
            "market_data_in",
            "market_data",
            "market.#",
            market_data_worker.process_event,
        )
        
        await self.event_bus.subscribe(
            "signals_in",
            "signals",
            "signal.*",
            signal_worker.process_event,
        )
        
        self._running = True
        logger.info("Execution engine started")

    async def stop(self):
        """Stop the execution engine."""
        self._running = False
        
        for worker in self.workers:
            await worker.stop()
        
        await self.event_bus.disconnect()
        logger.info("Execution engine stopped")

    async def get_metrics(self) -> list[WorkerMetrics]:
        """Get worker metrics."""
        return [worker.metrics for worker in self.workers]


# Singleton instance
_execution_engine: Optional[ExecutionEngine] = None


async def get_execution_engine() -> ExecutionEngine:
    """Get execution engine singleton."""
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine()
    return _execution_engine

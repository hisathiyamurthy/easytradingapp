"""Prometheus metrics service."""
import time
from collections import defaultdict
from typing import Dict, Optional

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST


class MetricsService:
    """Service for collecting and exposing Prometheus metrics."""
    
    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._init_default_metrics()
    
    def _init_default_metrics(self):
        """Initialize default application metrics."""
        self._counters["http_requests_total"] = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
        )
        
        self._histograms["http_request_duration_seconds"] = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )
        
        self._counters["orders_placed_total"] = Counter(
            "orders_placed_total",
            "Total orders placed",
            ["side", "status", "broker"],
        )
        
        self._counters["trades_executed_total"] = Counter(
            "trades_executed_total",
            "Total trades executed",
            ["symbol", "side"],
        )
        
        self._gauges["active_connections"] = Gauge(
            "active_connections",
            "Number of active WebSocket connections",
        )
        
        self._gauges["active_strategies"] = Gauge(
            "active_strategies",
            "Number of active trading strategies",
        )
        
        self._gauges["order_queue_size"] = Gauge(
            "order_queue_size",
            "Number of orders pending execution",
        )
        
        self._histograms["order_execution_duration_seconds"] = Histogram(
            "order_execution_duration_seconds",
            "Time to execute an order",
            ["broker"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record an HTTP request."""
        self._counters["http_requests_total"].labels(
            method=method,
            endpoint=endpoint,
            status=str(status),
        ).inc()
        
        self._histograms["http_request_duration_seconds"].labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)
    
    def record_order(self, side: str, status: str, broker: str):
        """Record an order placement."""
        self._counters["orders_placed_total"].labels(
            side=side,
            status=status,
            broker=broker,
        ).inc()
    
    def record_trade(self, symbol: str, side: str):
        """Record a trade execution."""
        self._counters["trades_executed_total"].labels(
            symbol=symbol,
            side=side,
        ).inc()
    
    def set_active_connections(self, count: int):
        """Set active WebSocket connections."""
        self._gauges["active_connections"].set(count)
    
    def set_active_strategies(self, count: int):
        """Set active trading strategies."""
        self._gauges["active_strategies"].set(count)
    
    def set_order_queue_size(self, size: int):
        """Set order queue size."""
        self._gauges["order_queue_size"].set(size)
    
    def record_order_execution_time(self, broker: str, duration: float):
        """Record order execution time."""
        self._histograms["order_execution_duration_seconds"].labels(
            broker=broker,
        ).observe(duration)
    
    def get_metrics(self) -> bytes:
        """Generate Prometheus metrics."""
        return generate_latest()


_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """Get metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service


class MetricsMiddleware:
    """Middleware for recording HTTP metrics."""
    
    def __init__(self, app):
        self.app = app
        self.metrics = get_metrics_service()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        start_time = time.time()
        
        status_code = 200
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)
        
        await self.app(scope, receive, send_wrapper)
        
        duration = time.time() - start_time
        endpoint = self._normalize_path(path)
        
        self.metrics.record_request(method, endpoint, status_code, duration)
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for metrics."""
        parts = path.split("/")
        if len(parts) > 3 and parts[2] in ["strategies", "orders", "trades"]:
            return f"/{parts[1]}/{{id}}"
        return path
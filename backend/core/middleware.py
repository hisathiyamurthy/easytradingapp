"""Correlation ID middleware for request tracing."""
import uuid
import logging
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get current correlation ID."""
    return correlation_id_var.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that adds correlation ID to each request."""
    
    def __init__(self, app, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(self.header_name)
        
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        correlation_id_var.set(correlation_id)
        
        request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        
        response.headers[self.header_name] = correlation_id
        
        return response


def setup_logging_correlation():
    """Configure logging to include correlation ID."""
    class CorrelationIdFilter(logging.Filter):
        def filter(self, record):
            record.correlation_id = get_correlation_id() or "-"
            return True
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s"
    )
    
    for handler in logging.getLogger().handlers:
        handler.addFilter(CorrelationIdFilter())
        handler.setFormatter(formatter)
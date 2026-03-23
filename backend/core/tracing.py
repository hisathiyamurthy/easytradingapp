"""Distributed tracing configuration with OpenTelemetry."""
import logging
from typing import Optional
from contextvars import ContextVar

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextFormatPropagator

logger = logging.getLogger(__name__)

_tracer: Optional[trace.Tracer] = None
_propagator = TraceContextTextFormatPropagator()


def setup_tracing(
    service_name: str = "easytradingapp",
    jaeger_agent_host: str = "localhost",
    jaeger_agent_port: int = 6831,
    enable_console: bool = False,
) -> trace.Tracer:
    """Setup OpenTelemetry tracing."""
    global _tracer
    
    provider = TracerProvider()
    
    if enable_console:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    
    try:
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_agent_host,
            agent_port=jaeger_agent_port,
        )
        provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
        logger.info(f"Jaeger tracing enabled: {jaeger_agent_host}:{jaeger_agent_port}")
    except Exception as e:
        logger.warning(f"Jaeger exporter not available: {e}")
    
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)
    
    return _tracer


def get_tracer() -> trace.Tracer:
    """Get the configured tracer."""
    global _tracer
    if _tracer is None:
        _tracer = setup_tracing()
    return _tracer


def instrument_fastapi(app):
    """Instrument FastAPI application."""
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")


def instrument_httpx():
    """Instrument HTTPX client."""
    try:
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument HTTPX: {e}")


def trace_async(func):
    """Decorator to trace async functions."""
    async def wrapper(*args, **kwargs):
        tracer = get_tracer()
        with tracer.start_as_current_span(func.__name__) as span:
            span.set_attribute("function.name", func.__name__)
            span.set_attribute("function.module", func.__module__)
            try:
                result = await func(*args, **kwargs)
                span.set_attribute("result.success", True)
                return result
            except Exception as e:
                span.set_attribute("result.success", False)
                span.set_attribute("error.message", str(e))
                raise
    return wrapper


def trace_sync(func):
    """Decorator to trace sync functions."""
    def wrapper(*args, **kwargs):
        tracer = get_tracer()
        with tracer.start_as_current_span(func.__name__) as span:
            span.set_attribute("function.name", func.__name__)
            span.set_attribute("function.module", func.__module__)
            try:
                result = func(*args, **kwargs)
                span.set_attribute("result.success", True)
                return result
            except Exception as e:
                span.set_attribute("result.success", False)
                span.set_attribute("error.message", str(e))
                raise
    return wrapper


class TracingContextVar:
    """Context variable for span context propagation."""
    
    span_context: ContextVar[Optional[trace.SpanContext]] = ContextVar(
        "span_context", default=None
    )
    
    @classmethod
    def set_span_context(cls, context: trace.SpanContext):
        cls.span_context.set(context)
    
    @classmethod
    def get_span_context(cls) -> Optional[trace.SpanContext]:
        return cls.span_context.get()
    
    @classmethod
    def clear(cls):
        cls.span_context.set(None)


def inject_trace_context() -> dict:
    """Inject trace context into carrier for propagation."""
    carrier = {}
    _propagator.inject(carrier)
    return carrier


def extract_trace_context(carrier: dict) -> trace.SpanContext:
    """Extract trace context from carrier."""
    context = _propagator.extract(carrier)
    return context


class TracingMiddleware:
    """Middleware for adding tracing to requests."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        tracer = get_tracer()
        
        headers = dict(scope.get("headers", []))
        
        with tracer.start_as_current_span(
            f"{scope['method']} {scope['path']}",
            kind=trace.SpanKind.SERVER,
        ) as span:
            span.set_attribute("http.method", scope["method"])
            span.set_attribute("http.url", scope.get("path", ""))
            span.set_attribute("http.scheme", scope.get("scheme", "http"))
            
            client_host = headers.get(b"host", b"").decode()
            span.set_attribute("http.client_host", client_host)
            
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    status = message.get("status", 200)
                    span.set_attribute("http.status_code", status)
                    span.set_attribute(
                        "http.status_text",
                        message.get("headers", []),
                    )
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
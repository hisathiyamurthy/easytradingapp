import logging
import sys
from datetime import datetime
from typing import Any
import json
from uuid import UUID
from typing import MutableMapping

class StructuredFormatter(logging.Formatter):
    """Structured logging formatter following agents.md standards."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": getattr(record, "service", "unknown"),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        
        request_id = getattr(record, "request_id", None)
        if request_id:
            log_data["request_id"] = str(request_id)
        user_id = getattr(record, "user_id", None)
        if user_id:
            log_data["user_id"] = str(user_id)
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


def setup_logging(service_name: str, level: int = logging.INFO) -> logging.Logger:
    """Setup structured logging for the service."""
    logger = logging.getLogger(service_name)
    logger.setLevel(level)
    logger.handlers.clear()
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    
    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """Custom adapter that adds context to logs."""
    
    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[str, MutableMapping[str, Any]]:
        return msg, kwargs


def get_logger(name: str, service: str = "backend") -> LoggerAdapter:
    """Get a logger with service context."""
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, {"service": service})

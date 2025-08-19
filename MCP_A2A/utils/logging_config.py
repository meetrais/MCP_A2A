"""
Logging configuration for the MCP A2A Trading System.
Provides structured logging with correlation IDs for request tracing.
"""

import logging
import sys
from typing import Optional
from datetime import datetime
import json
from contextvars import ContextVar

try:
    from ..config import SYSTEM_CONFIG
except ImportError:
    try:
        from config import SYSTEM_CONFIG
    except ImportError:
        # Fallback configuration
        SYSTEM_CONFIG = {
            "log_level": "INFO"
        }

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add correlation ID if available
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


def setup_logging(service_name: str, log_level: Optional[str] = None) -> None:
    """
    Set up structured logging for a service.
    
    Args:
        service_name: Name of the service for logging context
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    if log_level is None:
        log_level = SYSTEM_CONFIG["log_level"]
    
    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with structured formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    formatter = StructuredFormatter()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # Set service name in logger
    logger = logging.getLogger(service_name)
    logger.info(f"Logging initialized for service: {service_name}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
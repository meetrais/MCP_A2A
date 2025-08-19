"""
Correlation ID utilities for request tracing across services.
"""

import uuid
from typing import Optional
from contextvars import ContextVar

# Context variable to store correlation ID for the current request
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def generate_correlation_id() -> str:
    """
    Generate a new correlation ID.
    
    Returns:
        New UUID-based correlation ID
    """
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID for the current context.
    
    Args:
        correlation_id: Correlation ID to set
    """
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID.
    
    Returns:
        Current correlation ID or None if not set
    """
    return correlation_id_var.get()


def ensure_correlation_id() -> str:
    """
    Ensure a correlation ID exists, creating one if necessary.
    
    Returns:
        Current or newly created correlation ID
    """
    correlation_id = get_correlation_id()
    if correlation_id is None:
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)
    return correlation_id
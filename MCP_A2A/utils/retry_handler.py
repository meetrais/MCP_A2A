"""
Retry handler with exponential backoff and jitter.
"""

import asyncio
import random
import time
from typing import Callable, Any, Type, Union, List
from dataclasses import dataclass

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    backoff_factor: float = 1.0


class RetryExhaustedError(Exception):
    """Exception raised when all retry attempts are exhausted."""
    
    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(f"Retry exhausted after {attempts} attempts. Last error: {last_exception}")


class RetryHandler:
    """
    Handles retry logic with exponential backoff and jitter.
    """
    
    def __init__(self, config: RetryConfig = None):
        """
        Initialize retry handler.
        
        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
    
    async def execute(
        self,
        func: Callable,
        *args,
        retryable_exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            retryable_exceptions: Exception types that should trigger retry
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            RetryExhaustedError: If all retry attempts fail
        """
        if not isinstance(retryable_exceptions, (list, tuple)):
            retryable_exceptions = [retryable_exceptions]
        
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                logger.debug(f"Retry attempt {attempt}/{self.config.max_attempts}")
                
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                if attempt > 1:
                    logger.info(f"Function succeeded on attempt {attempt}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if this exception should trigger a retry
                if not any(isinstance(e, exc_type) for exc_type in retryable_exceptions):
                    logger.debug(f"Exception {type(e).__name__} is not retryable, failing immediately")
                    raise
                
                # If this is the last attempt, don't wait
                if attempt == self.config.max_attempts:
                    break
                
                # Calculate delay with exponential backoff
                delay = self._calculate_delay(attempt)
                
                logger.warning(f"Attempt {attempt} failed with {type(e).__name__}: {e}. "
                             f"Retrying in {delay:.2f} seconds...")
                
                await asyncio.sleep(delay)
        
        # All attempts exhausted
        logger.error(f"All {self.config.max_attempts} retry attempts failed")
        raise RetryExhaustedError(self.config.max_attempts, last_exception)
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt with exponential backoff and jitter.
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * (exponential_base ^ (attempt - 1))
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
        
        # Apply backoff factor
        delay *= self.config.backoff_factor
        
        # Cap at max delay
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to avoid thundering herd
        if self.config.jitter:
            # Add random jitter up to 25% of the delay
            jitter_amount = delay * 0.25
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    backoff_factor: float = 1.0,
    retryable_exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception
):
    """
    Decorator for adding retry logic to functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add jitter to delays
        backoff_factor: Factor to multiply delays by
        retryable_exceptions: Exception types that should trigger retry
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                backoff_factor=backoff_factor
            )
            
            handler = RetryHandler(config)
            return await handler.execute(func, *args, retryable_exceptions=retryable_exceptions, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in an event loop
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                backoff_factor=backoff_factor
            )
            
            handler = RetryHandler(config)
            
            # Create a sync version of execute
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        logger.info(f"Function succeeded on attempt {attempt}")
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if this exception should trigger a retry
                    if not isinstance(retryable_exceptions, (list, tuple)):
                        retryable_exceptions_list = [retryable_exceptions]
                    else:
                        retryable_exceptions_list = retryable_exceptions
                    
                    if not any(isinstance(e, exc_type) for exc_type in retryable_exceptions_list):
                        raise
                    
                    if attempt == max_attempts:
                        break
                    
                    delay = handler._calculate_delay(attempt)
                    logger.warning(f"Attempt {attempt} failed with {type(e).__name__}: {e}. "
                                 f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
            
            raise RetryExhaustedError(max_attempts, last_exception)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Convenience retry decorators for common scenarios
def retry_on_connection_error(max_attempts: int = 3, base_delay: float = 1.0):
    """Retry decorator for connection errors."""
    import httpx
    return retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        retryable_exceptions=[
            ConnectionError,
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.NetworkError
        ]
    )


def retry_on_server_error(max_attempts: int = 3, base_delay: float = 2.0):
    """Retry decorator for server errors (5xx HTTP status codes)."""
    import httpx
    return retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        retryable_exceptions=[
            httpx.HTTPStatusError,  # Will need additional logic to check status code
        ]
    )


def retry_on_timeout(max_attempts: int = 3, base_delay: float = 1.0):
    """Retry decorator for timeout errors."""
    import httpx
    return retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        retryable_exceptions=[
            asyncio.TimeoutError,
            httpx.TimeoutException
        ]
    )
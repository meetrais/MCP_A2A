"""
Circuit breaker pattern implementation for service resilience.
"""

import asyncio
import time
from typing import Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass, field

from .logging_config import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Circuit is open, requests fail fast
    HALF_OPEN = "HALF_OPEN"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout: float = 60.0      # Seconds before trying half-open
    success_threshold: int = 3          # Successes needed to close from half-open
    timeout: float = 30.0               # Request timeout in seconds


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: int = 0
    total_requests: int = 0


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting against cascading failures.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name of the circuit breaker for logging
            config: Configuration parameters
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized with config: {self.config}")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original function exceptions
        """
        async with self._lock:
            self.stats.total_requests += 1
            
            # Check if circuit should transition states
            await self._check_state_transition()
            
            # If circuit is open, fail fast
            if self.state == CircuitState.OPEN:
                logger.warning(f"Circuit breaker '{self.name}' is OPEN, failing fast")
                raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")
        
        # Execute the function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
            else:
                result = func(*args, **kwargs)
            
            # Record success
            await self._record_success()
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Circuit breaker '{self.name}' - request timed out after {self.config.timeout}s")
            await self._record_failure()
            raise
        except Exception as e:
            logger.warning(f"Circuit breaker '{self.name}' - request failed: {e}")
            await self._record_failure()
            raise
    
    async def _check_state_transition(self):
        """Check if circuit breaker should transition states."""
        current_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            # Check if we should open due to failures
            if self.stats.failure_count >= self.config.failure_threshold:
                await self._transition_to_open()
        
        elif self.state == CircuitState.OPEN:
            # Check if we should try half-open
            if (self.stats.last_failure_time and 
                current_time - self.stats.last_failure_time >= self.config.recovery_timeout):
                await self._transition_to_half_open()
        
        elif self.state == CircuitState.HALF_OPEN:
            # Check if we should close due to successes
            if self.stats.success_count >= self.config.success_threshold:
                await self._transition_to_closed()
    
    async def _record_success(self):
        """Record a successful request."""
        async with self._lock:
            self.stats.success_count += 1
            self.stats.last_success_time = time.time()
            
            # Reset failure count on success
            if self.state == CircuitState.CLOSED:
                self.stats.failure_count = 0
            
            logger.debug(f"Circuit breaker '{self.name}' - success recorded (count: {self.stats.success_count})")
    
    async def _record_failure(self):
        """Record a failed request."""
        async with self._lock:
            self.stats.failure_count += 1
            self.stats.last_failure_time = time.time()
            
            # Reset success count on failure
            if self.state == CircuitState.HALF_OPEN:
                self.stats.success_count = 0
            
            logger.debug(f"Circuit breaker '{self.name}' - failure recorded (count: {self.stats.failure_count})")
    
    async def _transition_to_open(self):
        """Transition circuit breaker to OPEN state."""
        self.state = CircuitState.OPEN
        self.stats.state_changes += 1
        self.stats.success_count = 0  # Reset success count
        
        logger.warning(f"Circuit breaker '{self.name}' transitioned to OPEN state "
                      f"(failures: {self.stats.failure_count})")
    
    async def _transition_to_half_open(self):
        """Transition circuit breaker to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.stats.state_changes += 1
        self.stats.success_count = 0  # Reset success count for testing
        
        logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN state")
    
    async def _transition_to_closed(self):
        """Transition circuit breaker to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.stats.state_changes += 1
        self.stats.failure_count = 0  # Reset failure count
        
        logger.info(f"Circuit breaker '{self.name}' transitioned to CLOSED state "
                   f"(successes: {self.stats.success_count})")
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time,
            "state_changes": self.stats.state_changes,
            "total_requests": self.stats.total_requests,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout
            }
        }
    
    async def reset(self):
        """Reset circuit breaker to initial state."""
        async with self._lock:
            self.state = CircuitState.CLOSED
            self.stats = CircuitBreakerStats()
            logger.info(f"Circuit breaker '{self.name}' reset to initial state")


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
    
    def get_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """
        Get or create a circuit breaker.
        
        Args:
            name: Circuit breaker name
            config: Configuration (only used for new breakers)
            
        Returns:
            Circuit breaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]
    
    def get_all_stats(self) -> dict:
        """Get statistics for all circuit breakers."""
        return {
            name: breaker.get_stats() 
            for name, breaker in self._breakers.items()
        }
    
    async def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            await breaker.reset()


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()
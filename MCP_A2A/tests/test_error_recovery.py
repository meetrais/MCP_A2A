"""
Unit tests for error recovery and resilience mechanisms.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from ..utils.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitState, CircuitBreakerError
)
from ..utils.retry_handler import (
    RetryHandler, RetryConfig, RetryExhaustedError, retry
)
from ..utils.error_recovery import (
    ErrorRecoveryManager, ServiceStatus, CachedDataFallback, 
    DefaultValueFallback, AlternativeServiceFallback
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker for testing."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,  # Short timeout for testing
            success_threshold=2,
            timeout=5.0
        )
        return CircuitBreaker("test_service", config)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(self, circuit_breaker):
        """Test circuit breaker in closed state."""
        async def successful_function():
            return "success"
        
        result = await circuit_breaker.call(successful_function)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.stats.success_count == 1
        assert circuit_breaker.stats.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self, circuit_breaker):
        """Test circuit breaker opens after threshold failures."""
        async def failing_function():
            raise Exception("Service error")
        
        # Execute failures up to threshold
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_function)
        
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.stats.failure_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_fails_fast_when_open(self, circuit_breaker):
        """Test circuit breaker fails fast when open."""
        # Force circuit to open state
        circuit_breaker.state = CircuitState.OPEN
        
        async def any_function():
            return "should not execute"
        
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(any_function)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_transition(self, circuit_breaker):
        """Test circuit breaker transitions to half-open after timeout."""
        # Force failures to open circuit
        async def failing_function():
            raise Exception("Service error")
        
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_function)
        
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Next call should transition to half-open
        async def successful_function():
            return "success"
        
        result = await circuit_breaker.call(successful_function)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_from_half_open(self, circuit_breaker):
        """Test circuit breaker closes from half-open after successes."""
        # Set to half-open state
        circuit_breaker.state = CircuitState.HALF_OPEN
        
        async def successful_function():
            return "success"
        
        # Execute successful calls to reach success threshold
        for i in range(2):
            result = await circuit_breaker.call(successful_function)
            assert result == "success"
        
        assert circuit_breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_timeout(self, circuit_breaker):
        """Test circuit breaker timeout handling."""
        async def slow_function():
            await asyncio.sleep(10)  # Longer than timeout
            return "should timeout"
        
        with pytest.raises(asyncio.TimeoutError):
            await circuit_breaker.call(slow_function)
        
        assert circuit_breaker.stats.failure_count == 1


class TestRetryHandler:
    """Test retry handler functionality."""
    
    @pytest.fixture
    def retry_handler(self):
        """Create retry handler for testing."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,  # Short delay for testing
            max_delay=1.0,
            exponential_base=2.0,
            jitter=False  # Disable jitter for predictable testing
        )
        return RetryHandler(config)
    
    @pytest.mark.asyncio
    async def test_retry_handler_success_first_attempt(self, retry_handler):
        """Test retry handler with success on first attempt."""
        async def successful_function():
            return "success"
        
        result = await retry_handler.execute(successful_function)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_handler_success_after_failures(self, retry_handler):
        """Test retry handler with success after initial failures."""
        call_count = 0
        
        async def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await retry_handler.execute(eventually_successful_function)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_handler_exhausted(self, retry_handler):
        """Test retry handler exhaustion after all attempts fail."""
        async def always_failing_function():
            raise Exception("Persistent failure")
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            await retry_handler.execute(always_failing_function)
        
        assert exc_info.value.attempts == 3
        assert "Persistent failure" in str(exc_info.value.last_exception)
    
    @pytest.mark.asyncio
    async def test_retry_handler_non_retryable_exception(self, retry_handler):
        """Test retry handler with non-retryable exception."""
        async def function_with_non_retryable_error():
            raise ValueError("Non-retryable error")
        
        # Only retry on ConnectionError, not ValueError
        with pytest.raises(ValueError):
            await retry_handler.execute(
                function_with_non_retryable_error,
                retryable_exceptions=[ConnectionError]
            )
    
    def test_retry_decorator_async(self):
        """Test retry decorator on async function."""
        call_count = 0
        
        @retry(max_attempts=3, base_delay=0.01)
        async def decorated_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        async def run_test():
            result = await decorated_function()
            assert result == "success"
            assert call_count == 3
        
        asyncio.run(run_test())
    
    def test_retry_decorator_sync(self):
        """Test retry decorator on sync function."""
        call_count = 0
        
        @retry(max_attempts=3, base_delay=0.01)
        def decorated_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = decorated_function()
        assert result == "success"
        assert call_count == 3


class TestFallbackStrategies:
    """Test fallback strategy implementations."""
    
    @pytest.mark.asyncio
    async def test_cached_data_fallback(self):
        """Test cached data fallback strategy."""
        fallback = CachedDataFallback(cache_ttl=60)
        
        # Cache some data
        fallback.cache_data("test_service", "test_method", {"data": "cached_value"})
        
        # Test fallback execution
        result = await fallback.execute(
            "test_service",
            Exception("Service unavailable"),
            method="test_method"
        )
        
        assert result == {"data": "cached_value"}
    
    @pytest.mark.asyncio
    async def test_cached_data_fallback_expired(self):
        """Test cached data fallback with expired cache."""
        fallback = CachedDataFallback(cache_ttl=0.1)  # Very short TTL
        
        # Cache some data
        fallback.cache_data("test_service", "test_method", {"data": "cached_value"})
        
        # Wait for cache to expire
        await asyncio.sleep(0.2)
        
        # Test fallback execution with expired cache
        original_error = Exception("Service unavailable")
        with pytest.raises(Exception) as exc_info:
            await fallback.execute(
                "test_service",
                original_error,
                method="test_method"
            )
        
        assert exc_info.value == original_error
    
    @pytest.mark.asyncio
    async def test_default_value_fallback(self):
        """Test default value fallback strategy."""
        defaults = {
            "test_service:test_method": {"default": "value"},
            "test_service": {"service_default": "value"}
        }
        fallback = DefaultValueFallback(defaults)
        
        # Test method-specific default
        result = await fallback.execute(
            "test_service",
            Exception("Service unavailable"),
            method="test_method"
        )
        assert result == {"default": "value"}
        
        # Test service-level default
        result = await fallback.execute(
            "test_service",
            Exception("Service unavailable"),
            method="other_method"
        )
        assert result == {"service_default": "value"}
    
    @pytest.mark.asyncio
    async def test_alternative_service_fallback(self):
        """Test alternative service fallback strategy."""
        async def alternative_function(**kwargs):
            return {"alternative": "result"}
        
        alternatives = {"test_service": alternative_function}
        fallback = AlternativeServiceFallback(alternatives)
        
        result = await fallback.execute(
            "test_service",
            Exception("Service unavailable")
        )
        
        assert result == {"alternative": "result"}


class TestErrorRecoveryManager:
    """Test error recovery manager functionality."""
    
    @pytest.fixture
    def recovery_manager(self):
        """Create error recovery manager for testing."""
        return ErrorRecoveryManager()
    
    @pytest.mark.asyncio
    async def test_execute_with_recovery_success(self, recovery_manager):
        """Test successful execution with recovery manager."""
        async def successful_function():
            return "success"
        
        result = await recovery_manager.execute_with_recovery(
            "test_service",
            successful_function
        )
        
        assert result == "success"
        assert "test_service" in recovery_manager.service_health
        assert recovery_manager.service_health["test_service"].status == ServiceStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_execute_with_recovery_fallback(self, recovery_manager):
        """Test execution with fallback when service fails."""
        async def failing_function():
            raise Exception("Service error")
        
        # Add a default fallback
        recovery_manager.add_fallback_strategy(
            "test_service",
            DefaultValueFallback({"test_service": {"fallback": "data"}})
        )
        
        result = await recovery_manager.execute_with_recovery(
            "test_service",
            failing_function
        )
        
        assert result == {"fallback": "data"}
        assert recovery_manager.service_health["test_service"].status == ServiceStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_execute_with_recovery_all_fail(self, recovery_manager):
        """Test execution when both service and fallbacks fail."""
        async def failing_function():
            raise Exception("Service error")
        
        with pytest.raises(Exception) as exc_info:
            await recovery_manager.execute_with_recovery(
                "test_service",
                failing_function
            )
        
        assert "Service error" in str(exc_info.value)
        assert recovery_manager.service_health["test_service"].status == ServiceStatus.UNHEALTHY
    
    def test_get_system_health(self, recovery_manager):
        """Test system health reporting."""
        # Manually set some service health states
        from ..utils.error_recovery import ServiceHealth
        
        recovery_manager.service_health["service1"] = ServiceHealth(
            "service1", ServiceStatus.HEALTHY, datetime.now()
        )
        recovery_manager.service_health["service2"] = ServiceHealth(
            "service2", ServiceStatus.DEGRADED, datetime.now()
        )
        recovery_manager.service_health["service3"] = ServiceHealth(
            "service3", ServiceStatus.UNHEALTHY, datetime.now()
        )
        
        health = recovery_manager.get_system_health()
        
        assert health["overall_status"] == "DEGRADED"  # Mixed health
        assert health["healthy_services"] == 1
        assert health["degraded_services"] == 1
        assert health["unhealthy_services"] == 1
        assert health["total_services"] == 3
        assert len(health["services"]) == 3
    
    @pytest.mark.asyncio
    async def test_reset_all_recovery_mechanisms(self, recovery_manager):
        """Test resetting all recovery mechanisms."""
        # Set up some state
        from ..utils.error_recovery import ServiceHealth
        recovery_manager.service_health["test_service"] = ServiceHealth(
            "test_service", ServiceStatus.UNHEALTHY, datetime.now()
        )
        
        # Reset everything
        await recovery_manager.reset_all_recovery_mechanisms()
        
        assert len(recovery_manager.service_health) == 0


class TestIntegration:
    """Test integration of error recovery components."""
    
    @pytest.mark.asyncio
    async def test_full_error_recovery_workflow(self):
        """Test complete error recovery workflow."""
        recovery_manager = ErrorRecoveryManager()
        
        # Add fallback strategy
        recovery_manager.add_fallback_strategy(
            "test_service",
            DefaultValueFallback({"test_service": {"status": "fallback_used"}})
        )
        
        call_count = 0
        
        async def unreliable_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 5:  # Fail first 5 attempts
                raise Exception("Service temporarily unavailable")
            return {"status": "success"}
        
        # This should eventually use fallback after circuit breaker opens
        result = await recovery_manager.execute_with_recovery(
            "test_service",
            unreliable_function
        )
        
        # Should get fallback result since service keeps failing
        assert result == {"status": "fallback_used"}
        
        # Service should be marked as degraded (using fallback)
        health = recovery_manager.get_system_health()
        assert health["services"]["test_service"]["status"] == "DEGRADED"
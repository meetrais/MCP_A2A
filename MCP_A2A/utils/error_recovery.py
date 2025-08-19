"""
Error recovery and fallback mechanisms for the trading system.
"""

import asyncio
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from .logging_config import get_logger
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, circuit_breaker_registry
from .retry_handler import RetryHandler, RetryConfig

logger = get_logger(__name__)


class ServiceStatus(Enum):
    """Service status enumeration."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


@dataclass
class ServiceHealth:
    """Service health information."""
    service_name: str
    status: ServiceStatus
    last_check: datetime
    error_count: int = 0
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    response_time: Optional[float] = None


class FallbackStrategy:
    """Base class for fallback strategies."""
    
    async def execute(self, service_name: str, original_error: Exception, **kwargs) -> Any:
        """Execute fallback strategy."""
        raise NotImplementedError


class CachedDataFallback(FallbackStrategy):
    """Fallback to cached data when service is unavailable."""
    
    def __init__(self, cache_ttl: int = 300):  # 5 minutes default
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = cache_ttl
    
    async def execute(self, service_name: str, original_error: Exception, **kwargs) -> Any:
        """Return cached data if available."""
        cache_key = f"{service_name}:{kwargs.get('method', 'default')}"
        
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            cache_time = cached_data.get('timestamp', datetime.min)
            
            if datetime.now() - cache_time < timedelta(seconds=self.cache_ttl):
                logger.info(f"Using cached data for {service_name} due to service unavailability")
                return cached_data['data']
        
        logger.warning(f"No valid cached data available for {service_name}")
        raise original_error
    
    def cache_data(self, service_name: str, method: str, data: Any):
        """Cache data for future fallback use."""
        cache_key = f"{service_name}:{method}"
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }


class DefaultValueFallback(FallbackStrategy):
    """Fallback to default values when service is unavailable."""
    
    def __init__(self, default_values: Dict[str, Any]):
        self.default_values = default_values
    
    async def execute(self, service_name: str, original_error: Exception, **kwargs) -> Any:
        """Return default value for the service."""
        method = kwargs.get('method', 'default')
        fallback_key = f"{service_name}:{method}"
        
        if fallback_key in self.default_values:
            logger.info(f"Using default value for {service_name}.{method}")
            return self.default_values[fallback_key]
        
        # Try service-level default
        if service_name in self.default_values:
            logger.info(f"Using service-level default for {service_name}")
            return self.default_values[service_name]
        
        logger.warning(f"No default value configured for {service_name}.{method}")
        raise original_error


class AlternativeServiceFallback(FallbackStrategy):
    """Fallback to alternative service when primary is unavailable."""
    
    def __init__(self, alternative_services: Dict[str, Callable]):
        self.alternative_services = alternative_services
    
    async def execute(self, service_name: str, original_error: Exception, **kwargs) -> Any:
        """Use alternative service."""
        if service_name in self.alternative_services:
            logger.info(f"Using alternative service for {service_name}")
            alternative_func = self.alternative_services[service_name]
            
            try:
                if asyncio.iscoroutinefunction(alternative_func):
                    return await alternative_func(**kwargs)
                else:
                    return alternative_func(**kwargs)
            except Exception as e:
                logger.error(f"Alternative service for {service_name} also failed: {e}")
                raise original_error
        
        logger.warning(f"No alternative service configured for {service_name}")
        raise original_error


class ErrorRecoveryManager:
    """Manages error recovery and fallback strategies for the trading system."""
    
    def __init__(self):
        self.service_health: Dict[str, ServiceHealth] = {}
        self.fallback_strategies: Dict[str, List[FallbackStrategy]] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_handlers: Dict[str, RetryHandler] = {}
        
        # Initialize default fallback strategies
        self._setup_default_fallbacks()
    
    def _setup_default_fallbacks(self):
        """Setup default fallback strategies for trading system services."""
        
        # Market data fallbacks
        market_data_defaults = {
            "market_data_mcp:get_stock_price": {
                "ticker": "UNKNOWN",
                "data": [
                    {
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "open": 100.0,
                        "high": 105.0,
                        "low": 95.0,
                        "close": 100.0,
                        "volume": 1000000
                    }
                ]
            },
            "market_data_mcp:get_market_news": {
                "ticker": "UNKNOWN",
                "news": [
                    {
                        "headline": "Market data temporarily unavailable",
                        "summary": "Using fallback data",
                        "sentiment": "neutral",
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "System",
                        "relevance_score": 0.5
                    }
                ]
            }
        }
        
        # Technical analysis fallbacks
        technical_defaults = {
            "technical_analysis_mcp:calculate_indicator": {
                "indicator": "UNKNOWN",
                "values": [50.0],  # Neutral RSI value
                "signal": "HOLD",
                "confidence": 0.0,
                "signal_reason": "Service unavailable - using neutral signal"
            }
        }
        
        # Trading execution fallbacks
        trading_defaults = {
            "trading_execution_mcp:execute_mock_trade": {
                "trade_id": None,
                "status": "FAILED",
                "error_message": "Trading service unavailable"
            },
            "trading_execution_mcp:get_portfolio_status": {
                "cash_balance": 100000.0,
                "positions": [],
                "total_equity_value": 0.0,
                "total_portfolio_value": 100000.0,
                "cash_percentage": 100.0,
                "number_of_positions": 0
            }
        }
        
        # Setup fallback strategies
        self.add_fallback_strategy("market_data_mcp", DefaultValueFallback(market_data_defaults))
        self.add_fallback_strategy("technical_analysis_mcp", DefaultValueFallback(technical_defaults))
        self.add_fallback_strategy("trading_execution_mcp", DefaultValueFallback(trading_defaults))
        
        # Add cached data fallback for all services
        cached_fallback = CachedDataFallback(cache_ttl=600)  # 10 minutes
        for service in ["market_data_mcp", "technical_analysis_mcp", "trading_execution_mcp",
                       "fundamental_analyst", "technical_analyst", "risk_manager", "trade_executor"]:
            self.add_fallback_strategy(service, cached_fallback)
    
    def add_fallback_strategy(self, service_name: str, strategy: FallbackStrategy):
        """Add a fallback strategy for a service."""
        if service_name not in self.fallback_strategies:
            self.fallback_strategies[service_name] = []
        self.fallback_strategies[service_name].append(strategy)
        logger.info(f"Added fallback strategy {type(strategy).__name__} for {service_name}")
    
    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for a service."""
        if service_name not in self.circuit_breakers:
            config = CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0,
                success_threshold=2,
                timeout=30.0
            )
            self.circuit_breakers[service_name] = CircuitBreaker(service_name, config)
        return self.circuit_breakers[service_name]
    
    def get_retry_handler(self, service_name: str) -> RetryHandler:
        """Get or create retry handler for a service."""
        if service_name not in self.retry_handlers:
            config = RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=10.0,
                exponential_base=2.0,
                jitter=True
            )
            self.retry_handlers[service_name] = RetryHandler(config)
        return self.retry_handlers[service_name]
    
    async def execute_with_recovery(
        self,
        service_name: str,
        func: Callable,
        *args,
        method: str = "default",
        **kwargs
    ) -> Any:
        """
        Execute function with comprehensive error recovery.
        
        Args:
            service_name: Name of the service
            func: Function to execute
            *args: Function arguments
            method: Method name for fallback identification
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or fallback result
        """
        circuit_breaker = self.get_circuit_breaker(service_name)
        retry_handler = self.get_retry_handler(service_name)
        
        try:
            # Execute with circuit breaker and retry
            result = await circuit_breaker.call(
                retry_handler.execute,
                func,
                *args,
                **kwargs
            )
            
            # Update service health on success
            self._update_service_health(service_name, ServiceStatus.HEALTHY)
            
            # Cache successful result if we have a cached fallback
            self._cache_successful_result(service_name, method, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Service {service_name} failed after all recovery attempts: {e}")
            
            # Update service health on failure
            self._update_service_health(service_name, ServiceStatus.UNHEALTHY, str(e))
            
            # Try fallback strategies
            return await self._execute_fallback(service_name, e, method=method, **kwargs)
    
    async def _execute_fallback(
        self,
        service_name: str,
        original_error: Exception,
        **kwargs
    ) -> Any:
        """Execute fallback strategies for a failed service."""
        if service_name not in self.fallback_strategies:
            logger.error(f"No fallback strategies configured for {service_name}")
            raise original_error
        
        for strategy in self.fallback_strategies[service_name]:
            try:
                logger.info(f"Trying fallback strategy {type(strategy).__name__} for {service_name}")
                result = await strategy.execute(service_name, original_error, **kwargs)
                
                # Mark service as degraded since we're using fallback
                self._update_service_health(service_name, ServiceStatus.DEGRADED)
                
                return result
                
            except Exception as e:
                logger.warning(f"Fallback strategy {type(strategy).__name__} failed: {e}")
                continue
        
        logger.error(f"All fallback strategies failed for {service_name}")
        raise original_error
    
    def _update_service_health(
        self,
        service_name: str,
        status: ServiceStatus,
        error: Optional[str] = None
    ):
        """Update service health status."""
        if service_name not in self.service_health:
            self.service_health[service_name] = ServiceHealth(
                service_name=service_name,
                status=status,
                last_check=datetime.now()
            )
        
        health = self.service_health[service_name]
        health.status = status
        health.last_check = datetime.now()
        
        if error:
            health.error_count += 1
            health.consecutive_failures += 1
            health.last_error = error
        else:
            health.consecutive_failures = 0
    
    def _cache_successful_result(self, service_name: str, method: str, result: Any):
        """Cache successful result for future fallback use."""
        for strategy in self.fallback_strategies.get(service_name, []):
            if isinstance(strategy, CachedDataFallback):
                strategy.cache_data(service_name, method, result)
                break
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        healthy_services = sum(1 for h in self.service_health.values() if h.status == ServiceStatus.HEALTHY)
        degraded_services = sum(1 for h in self.service_health.values() if h.status == ServiceStatus.DEGRADED)
        unhealthy_services = sum(1 for h in self.service_health.values() if h.status == ServiceStatus.UNHEALTHY)
        total_services = len(self.service_health)
        
        overall_status = "HEALTHY"
        if unhealthy_services > 0:
            overall_status = "DEGRADED" if unhealthy_services < total_services / 2 else "UNHEALTHY"
        elif degraded_services > 0:
            overall_status = "DEGRADED"
        
        return {
            "overall_status": overall_status,
            "healthy_services": healthy_services,
            "degraded_services": degraded_services,
            "unhealthy_services": unhealthy_services,
            "total_services": total_services,
            "services": {
                name: {
                    "status": health.status.value,
                    "last_check": health.last_check.isoformat(),
                    "error_count": health.error_count,
                    "consecutive_failures": health.consecutive_failures,
                    "last_error": health.last_error
                }
                for name, health in self.service_health.items()
            },
            "circuit_breakers": {
                name: breaker.get_stats()
                for name, breaker in self.circuit_breakers.items()
            }
        }
    
    async def reset_all_recovery_mechanisms(self):
        """Reset all circuit breakers and health status."""
        for breaker in self.circuit_breakers.values():
            await breaker.reset()
        
        self.service_health.clear()
        logger.info("All recovery mechanisms reset")


# Global error recovery manager instance
error_recovery_manager = ErrorRecoveryManager()
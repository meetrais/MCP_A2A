"""
Health check utilities for the MCP A2A Trading System.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import httpx

from .logging_config import get_logger
from .monitoring import metrics_collector
from .error_recovery import error_recovery_manager

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealthCheck:
    """Health check configuration for a service."""
    name: str
    url: str
    endpoint: str = "/"
    timeout: float = 5.0
    expected_status: int = 200
    check_interval: float = 30.0
    failure_threshold: int = 3
    recovery_threshold: int = 2


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    service_name: str
    status: HealthStatus
    response_time: Optional[float]
    timestamp: datetime
    error_message: Optional[str] = None
    details: Dict[str, Any] = None


class HealthChecker:
    """Performs health checks on services."""
    
    def __init__(self):
        self.service_configs: Dict[str, ServiceHealthCheck] = {}
        self.health_results: Dict[str, List[HealthCheckResult]] = {}
        self.running = False
        self.check_tasks: List[asyncio.Task] = []
    
    def register_service(self, config: ServiceHealthCheck):
        """Register a service for health checking."""
        self.service_configs[config.name] = config
        self.health_results[config.name] = []
        logger.info(f"Registered health check for service: {config.name}")
    
    def register_default_services(self):
        """Register default services for the trading system."""
        services = [
            ServiceHealthCheck("portfolio_manager", "http://localhost:8000"),
            ServiceHealthCheck("fundamental_analyst", "http://localhost:8001"),
            ServiceHealthCheck("technical_analyst", "http://localhost:8002"),
            ServiceHealthCheck("risk_manager", "http://localhost:8003"),
            ServiceHealthCheck("trade_executor", "http://localhost:8004"),
            ServiceHealthCheck("market_data_mcp", "http://localhost:9000"),
            ServiceHealthCheck("technical_analysis_mcp", "http://localhost:9001"),
            ServiceHealthCheck("trading_execution_mcp", "http://localhost:9002"),
        ]
        
        for service in services:
            self.register_service(service)
    
    async def check_service_health(self, service_name: str) -> HealthCheckResult:
        """Perform health check on a single service."""
        if service_name not in self.service_configs:
            return HealthCheckResult(
                service_name=service_name,
                status=HealthStatus.UNKNOWN,
                response_time=None,
                timestamp=datetime.now(),
                error_message="Service not registered for health checks"
            )
        
        config = self.service_configs[service_name]
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=config.timeout) as client:
                response = await client.get(f"{config.url}{config.endpoint}")
                response_time = time.time() - start_time
                
                if response.status_code == config.expected_status:
                    # Try to parse response for additional details
                    details = {}
                    try:
                        if response.headers.get("content-type", "").startswith("application/json"):
                            details = response.json()
                    except:
                        pass
                    
                    result = HealthCheckResult(
                        service_name=service_name,
                        status=HealthStatus.HEALTHY,
                        response_time=response_time,
                        timestamp=datetime.now(),
                        details=details
                    )
                else:
                    result = HealthCheckResult(
                        service_name=service_name,
                        status=HealthStatus.UNHEALTHY,
                        response_time=response_time,
                        timestamp=datetime.now(),
                        error_message=f"HTTP {response.status_code}: {response.text[:200]}"
                    )
        
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            result = HealthCheckResult(
                service_name=service_name,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                timestamp=datetime.now(),
                error_message=f"Timeout after {config.timeout}s"
            )
        
        except Exception as e:
            response_time = time.time() - start_time
            result = HealthCheckResult(
                service_name=service_name,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                timestamp=datetime.now(),
                error_message=str(e)
            )
        
        # Store result
        self.health_results[service_name].append(result)
        
        # Keep only last 100 results per service
        if len(self.health_results[service_name]) > 100:
            self.health_results[service_name] = self.health_results[service_name][-50:]
        
        # Record metrics
        await metrics_collector.record_performance(
            service_name,
            "health_check",
            result.response_time or 0.0,
            result.status == HealthStatus.HEALTHY
        )
        
        await metrics_collector.record_gauge(
            f"{service_name}_health_status",
            1.0 if result.status == HealthStatus.HEALTHY else 0.0
        )
        
        return result
    
    async def check_all_services(self) -> Dict[str, HealthCheckResult]:
        """Perform health checks on all registered services."""
        tasks = []
        for service_name in self.service_configs:
            task = asyncio.create_task(self.check_service_health(service_name))
            tasks.append((service_name, task))
        
        results = {}
        for service_name, task in tasks:
            try:
                result = await task
                results[service_name] = result
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                results[service_name] = HealthCheckResult(
                    service_name=service_name,
                    status=HealthStatus.UNKNOWN,
                    response_time=None,
                    timestamp=datetime.now(),
                    error_message=str(e)
                )
        
        return results
    
    def get_service_status(self, service_name: str) -> HealthStatus:
        """Get current status of a service based on recent health checks."""
        if service_name not in self.health_results or not self.health_results[service_name]:
            return HealthStatus.UNKNOWN
        
        config = self.service_configs.get(service_name)
        if not config:
            return HealthStatus.UNKNOWN
        
        recent_results = self.health_results[service_name][-config.failure_threshold:]
        
        # If we don't have enough results, return the latest status
        if len(recent_results) < config.failure_threshold:
            return recent_results[-1].status
        
        # Count failures in recent results
        failures = sum(1 for r in recent_results if r.status != HealthStatus.HEALTHY)
        
        if failures >= config.failure_threshold:
            return HealthStatus.UNHEALTHY
        elif failures > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        service_statuses = {}
        status_counts = {status.value: 0 for status in HealthStatus}
        
        for service_name in self.service_configs:
            status = self.get_service_status(service_name)
            service_statuses[service_name] = status.value
            status_counts[status.value] += 1
        
        # Determine overall system status
        total_services = len(self.service_configs)
        if total_services == 0:
            overall_status = HealthStatus.UNKNOWN
        elif status_counts[HealthStatus.UNHEALTHY.value] > total_services // 2:
            overall_status = HealthStatus.UNHEALTHY
        elif status_counts[HealthStatus.UNHEALTHY.value] > 0 or status_counts[HealthStatus.DEGRADED.value] > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Get latest health check results
        latest_results = {}
        for service_name in self.service_configs:
            if self.health_results[service_name]:
                latest = self.health_results[service_name][-1]
                latest_results[service_name] = {
                    "status": latest.status.value,
                    "response_time": latest.response_time,
                    "timestamp": latest.timestamp.isoformat(),
                    "error_message": latest.error_message
                }
        
        return {
            "overall_status": overall_status.value,
            "total_services": total_services,
            "healthy_services": status_counts[HealthStatus.HEALTHY.value],
            "degraded_services": status_counts[HealthStatus.DEGRADED.value],
            "unhealthy_services": status_counts[HealthStatus.UNHEALTHY.value],
            "unknown_services": status_counts[HealthStatus.UNKNOWN.value],
            "services": service_statuses,
            "latest_checks": latest_results
        }
    
    async def continuous_health_check(self, service_name: str):
        """Continuously check health of a service."""
        config = self.service_configs[service_name]
        
        while self.running:
            try:
                await self.check_service_health(service_name)
                await asyncio.sleep(config.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in continuous health check for {service_name}: {e}")
                await asyncio.sleep(config.check_interval)
    
    async def start_continuous_monitoring(self):
        """Start continuous health monitoring for all services."""
        if self.running:
            logger.warning("Health monitoring is already running")
            return
        
        self.running = True
        logger.info("Starting continuous health monitoring")
        
        # Start health check tasks for all services
        for service_name in self.service_configs:
            task = asyncio.create_task(self.continuous_health_check(service_name))
            self.check_tasks.append(task)
        
        logger.info(f"Started health monitoring for {len(self.check_tasks)} services")
    
    async def stop_continuous_monitoring(self):
        """Stop continuous health monitoring."""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping continuous health monitoring")
        
        # Cancel all health check tasks
        for task in self.check_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.check_tasks:
            await asyncio.gather(*self.check_tasks, return_exceptions=True)
        
        self.check_tasks.clear()
        logger.info("Health monitoring stopped")
    
    def get_health_history(
        self,
        service_name: str,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get health check history for a service."""
        if service_name not in self.health_results:
            return []
        
        results = self.health_results[service_name]
        
        if since:
            results = [r for r in results if r.timestamp >= since]
        
        # Sort by timestamp (newest first) and limit
        results = sorted(results, key=lambda r: r.timestamp, reverse=True)[:limit]
        
        return [
            {
                "status": r.status.value,
                "response_time": r.response_time,
                "timestamp": r.timestamp.isoformat(),
                "error_message": r.error_message,
                "details": r.details
            }
            for r in results
        ]


class SystemHealthMonitor:
    """High-level system health monitoring."""
    
    def __init__(self, health_checker: HealthChecker):
        self.health_checker = health_checker
        self.alerts_sent = set()
        self.alert_cooldown = timedelta(minutes=5)
        self.last_alert_time = {}
    
    async def check_and_alert(self):
        """Check system health and send alerts if needed."""
        system_health = self.health_checker.get_system_health()
        overall_status = HealthStatus(system_health["overall_status"])
        
        # Check if we should send an alert
        should_alert = False
        alert_message = ""
        
        if overall_status == HealthStatus.UNHEALTHY:
            should_alert = True
            alert_message = f"System is UNHEALTHY: {system_health['unhealthy_services']} services down"
        elif overall_status == HealthStatus.DEGRADED:
            should_alert = True
            alert_message = f"System is DEGRADED: {system_health['degraded_services']} services degraded, {system_health['unhealthy_services']} services down"
        
        # Check cooldown
        if should_alert:
            now = datetime.now()
            last_alert = self.last_alert_time.get(overall_status.value)
            
            if not last_alert or (now - last_alert) > self.alert_cooldown:
                await self.send_alert(alert_message, system_health)
                self.last_alert_time[overall_status.value] = now
    
    async def send_alert(self, message: str, health_data: Dict[str, Any]):
        """Send health alert (placeholder for actual alerting system)."""
        logger.warning(f"HEALTH ALERT: {message}")
        
        # In a real system, this would send alerts via:
        # - Email
        # - Slack/Teams
        # - PagerDuty
        # - SMS
        # etc.
        
        # For now, just log detailed health information
        unhealthy_services = [
            service for service, status in health_data["services"].items()
            if status in ["unhealthy", "degraded"]
        ]
        
        if unhealthy_services:
            logger.warning(f"Affected services: {', '.join(unhealthy_services)}")
    
    def get_alert_status(self) -> Dict[str, Any]:
        """Get current alert status."""
        return {
            "alerts_sent": len(self.alerts_sent),
            "last_alert_times": {
                status: time.isoformat() for status, time in self.last_alert_time.items()
            },
            "alert_cooldown_minutes": self.alert_cooldown.total_seconds() / 60
        }


# Global health checker instance
health_checker = HealthChecker()
system_health_monitor = SystemHealthMonitor(health_checker)
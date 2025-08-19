"""
Unit tests for monitoring and logging functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from ..utils.monitoring import (
    MetricsCollector, PerformanceMetrics, TradingSystemMonitor,
    performance_timer, MetricType
)
from ..utils.audit_logger import (
    AuditLogger, AuditEventType, AuditEvent
)
from ..utils.health_check import (
    HealthChecker, ServiceHealthCheck, HealthStatus, SystemHealthMonitor
)


class TestMetricsCollector:
    """Test metrics collection functionality."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create metrics collector for testing."""
        return MetricsCollector()
    
    @pytest.mark.asyncio
    async def test_record_counter(self, metrics_collector):
        """Test counter metric recording."""
        await metrics_collector.record_counter("test_counter", 5.0, {"service": "test"})
        await metrics_collector.record_counter("test_counter", 3.0, {"service": "test"})
        
        value = metrics_collector.get_counter_value("test_counter", {"service": "test"})
        assert value == 8.0
    
    @pytest.mark.asyncio
    async def test_record_gauge(self, metrics_collector):
        """Test gauge metric recording."""
        await metrics_collector.record_gauge("test_gauge", 100.0, {"service": "test"})
        await metrics_collector.record_gauge("test_gauge", 150.0, {"service": "test"})
        
        # Gauge should only keep the latest value
        value = metrics_collector.get_gauge_value("test_gauge", {"service": "test"})
        assert value == 150.0
    
    @pytest.mark.asyncio
    async def test_record_histogram(self, metrics_collector):
        """Test histogram metric recording."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            await metrics_collector.record_histogram("test_histogram", value)
        
        stats = metrics_collector.get_histogram_stats("test_histogram")
        assert stats["count"] == 5
        assert stats["sum"] == 150.0
        assert stats["avg"] == 30.0
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
    
    @pytest.mark.asyncio
    async def test_record_performance(self, metrics_collector):
        """Test performance metrics recording."""
        await metrics_collector.record_performance("test_service", "test_op", 0.5, True)
        await metrics_collector.record_performance("test_service", "test_op", 0.3, True)
        await metrics_collector.record_performance("test_service", "test_op", 1.0, False)
        
        metrics = metrics_collector.get_performance_metrics("test_service")
        assert "test_op" in metrics
        
        op_metrics = metrics["test_op"]
        assert op_metrics["total_requests"] == 3
        assert op_metrics["successful_requests"] == 2
        assert op_metrics["failed_requests"] == 1
        assert op_metrics["success_rate"] == pytest.approx(66.67, rel=1e-2)
    
    def test_performance_metrics_calculations(self):
        """Test performance metrics calculations."""
        perf_metrics = PerformanceMetrics()
        
        # Record some requests
        perf_metrics.record_request(0.5, True)
        perf_metrics.record_request(0.3, True)
        perf_metrics.record_request(1.0, False)
        perf_metrics.record_request(0.7, True)
        
        assert perf_metrics.total_requests == 4
        assert perf_metrics.successful_requests == 3
        assert perf_metrics.failed_requests == 1
        assert perf_metrics.success_rate == 75.0
        assert perf_metrics.average_response_time == 0.625
        assert perf_metrics.min_response_time == 0.3
        assert perf_metrics.max_response_time == 1.0
    
    @pytest.mark.asyncio
    async def test_performance_timer(self, metrics_collector):
        """Test performance timer context manager."""
        async with performance_timer("test_service", "test_operation") as timer:
            await asyncio.sleep(0.1)  # Simulate work
        
        # Check that metrics were recorded
        metrics = metrics_collector.get_performance_metrics("test_service")
        assert "test_operation" in metrics
        assert metrics["test_operation"]["total_requests"] == 1
        assert metrics["test_operation"]["successful_requests"] == 1
    
    @pytest.mark.asyncio
    async def test_performance_timer_with_failure(self, metrics_collector):
        """Test performance timer with failure."""
        try:
            async with performance_timer("test_service", "failing_operation") as timer:
                raise Exception("Test failure")
        except Exception:
            pass
        
        # Check that failure was recorded
        metrics = metrics_collector.get_performance_metrics("test_service")
        assert "failing_operation" in metrics
        assert metrics["failing_operation"]["total_requests"] == 1
        assert metrics["failing_operation"]["failed_requests"] == 1


class TestTradingSystemMonitor:
    """Test trading system monitoring functionality."""
    
    @pytest.fixture
    def trading_monitor(self):
        """Create trading monitor for testing."""
        metrics_collector = MetricsCollector()
        return TradingSystemMonitor(metrics_collector)
    
    @pytest.mark.asyncio
    async def test_record_trade_execution(self, trading_monitor):
        """Test trade execution recording."""
        await trading_monitor.record_trade_execution(True, 1000.0)
        await trading_monitor.record_trade_execution(True, 2000.0)
        await trading_monitor.record_trade_execution(False, 0.0)
        
        summary = trading_monitor.get_trading_summary()
        assert summary["total_trades"] == 3
        assert summary["successful_trades"] == 2
        assert summary["failed_trades"] == 1
        assert summary["trade_success_rate"] == pytest.approx(66.67, rel=1e-2)
        assert summary["total_trade_value"] == 3000.0
    
    @pytest.mark.asyncio
    async def test_record_portfolio_update(self, trading_monitor):
        """Test portfolio update recording."""
        await trading_monitor.record_portfolio_update(50000.0, 5)
        
        summary = trading_monitor.get_trading_summary()
        assert summary["current_portfolio_value"] == 50000.0
        assert summary["active_positions"] == 5
    
    @pytest.mark.asyncio
    async def test_record_analysis_result(self, trading_monitor):
        """Test analysis result recording."""
        await trading_monitor.record_analysis_result("fundamental", True, 0.8)
        await trading_monitor.record_analysis_result("technical", True, 0.7)
        await trading_monitor.record_analysis_result("fundamental", False)
        
        # Check that counters were recorded
        counter_value = trading_monitor.metrics.get_counter_value(
            "analysis_requests", 
            {"type": "fundamental", "success": "True"}
        )
        assert counter_value == 1.0
    
    @pytest.mark.asyncio
    async def test_record_risk_decision(self, trading_monitor):
        """Test risk decision recording."""
        await trading_monitor.record_risk_decision("APPROVE")
        await trading_monitor.record_risk_decision("DENY")
        await trading_monitor.record_risk_decision("APPROVE")
        
        approve_count = trading_monitor.metrics.get_counter_value(
            "risk_decisions",
            {"decision": "APPROVE"}
        )
        assert approve_count == 2.0


class TestAuditLogger:
    """Test audit logging functionality."""
    
    @pytest.fixture
    def audit_logger(self):
        """Create audit logger for testing."""
        return AuditLogger()
    
    def test_log_event(self, audit_logger):
        """Test basic event logging."""
        audit_logger.log_event(
            AuditEventType.TRADE_EXECUTED,
            "trade_executor",
            "execute_trade",
            {"ticker": "AAPL", "quantity": 100},
            success=True
        )
        
        assert len(audit_logger.audit_events) == 1
        event = audit_logger.audit_events[0]
        assert event.event_type == AuditEventType.TRADE_EXECUTED
        assert event.service_name == "trade_executor"
        assert event.operation == "execute_trade"
        assert event.success is True
        assert event.details["ticker"] == "AAPL"
    
    def test_log_workflow_events(self, audit_logger):
        """Test workflow-specific logging methods."""
        workflow_id = "test-workflow-123"
        strategy = {"goal": "Test strategy"}
        
        audit_logger.log_workflow_started(workflow_id, strategy)
        audit_logger.log_workflow_completed(workflow_id, {"success": True})
        
        assert len(audit_logger.audit_events) == 2
        
        start_event = audit_logger.audit_events[0]
        assert start_event.event_type == AuditEventType.WORKFLOW_STARTED
        assert start_event.details["workflow_id"] == workflow_id
        
        complete_event = audit_logger.audit_events[1]
        assert complete_event.event_type == AuditEventType.WORKFLOW_COMPLETED
    
    def test_log_trade_events(self, audit_logger):
        """Test trade-specific logging methods."""
        proposal = {
            "ticker": "AAPL",
            "action": "BUY",
            "quantity": 100,
            "estimated_price": 150.0
        }
        
        audit_logger.log_trade_proposal(proposal)
        audit_logger.log_trade_approved(proposal)
        
        result = {
            "trade_id": "trade-123",
            "executed_price": 149.50,
            "executed_quantity": 100
        }
        audit_logger.log_trade_execution(proposal, result, success=True)
        
        assert len(audit_logger.audit_events) == 3
        
        # Check trade proposal event
        proposal_event = audit_logger.audit_events[0]
        assert proposal_event.event_type == AuditEventType.TRADE_PROPOSAL
        assert proposal_event.details["ticker"] == "AAPL"
        
        # Check trade execution event
        execution_event = audit_logger.audit_events[2]
        assert execution_event.event_type == AuditEventType.TRADE_EXECUTED
        assert execution_event.details["trade_id"] == "trade-123"
    
    def test_get_audit_trail_filtering(self, audit_logger):
        """Test audit trail filtering."""
        # Add events with different correlation IDs
        with patch('MCP_A2A.utils.correlation_id.get_correlation_id', return_value="corr-1"):
            audit_logger.log_event(AuditEventType.TRADE_EXECUTED, "service1", "op1")
        
        with patch('MCP_A2A.utils.correlation_id.get_correlation_id', return_value="corr-2"):
            audit_logger.log_event(AuditEventType.TRADE_FAILED, "service2", "op2")
        
        # Filter by correlation ID
        trail = audit_logger.get_audit_trail(correlation_id="corr-1")
        assert len(trail) == 1
        assert trail[0]["correlation_id"] == "corr-1"
        
        # Filter by service name
        trail = audit_logger.get_audit_trail(service_name="service2")
        assert len(trail) == 1
        assert trail[0]["service_name"] == "service2"
        
        # Filter by event type
        trail = audit_logger.get_audit_trail(event_type=AuditEventType.TRADE_EXECUTED)
        assert len(trail) == 1
        assert trail[0]["event_type"] == "trade_executed"
    
    def test_get_trading_audit_summary(self, audit_logger):
        """Test trading audit summary."""
        # Add various trading events
        audit_logger.log_event(AuditEventType.TRADE_EXECUTED, "executor", "execute")
        audit_logger.log_event(AuditEventType.TRADE_EXECUTED, "executor", "execute")
        audit_logger.log_event(AuditEventType.TRADE_FAILED, "executor", "execute")
        audit_logger.log_event(AuditEventType.TRADE_APPROVED, "risk", "approve")
        audit_logger.log_event(AuditEventType.TRADE_DENIED, "risk", "deny")
        
        summary = audit_logger.get_trading_audit_summary()
        
        assert summary["total_events"] == 5
        assert summary["trading_metrics"]["trades_executed"] == 2
        assert summary["trading_metrics"]["trades_failed"] == 1
        assert summary["trading_metrics"]["trades_approved"] == 1
        assert summary["trading_metrics"]["trades_denied"] == 1
        assert summary["trading_metrics"]["trade_success_rate"] == pytest.approx(66.67, rel=1e-2)


class TestHealthChecker:
    """Test health checking functionality."""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker for testing."""
        return HealthChecker()
    
    def test_register_service(self, health_checker):
        """Test service registration."""
        config = ServiceHealthCheck(
            name="test_service",
            url="http://localhost:8000",
            timeout=5.0
        )
        
        health_checker.register_service(config)
        
        assert "test_service" in health_checker.service_configs
        assert health_checker.service_configs["test_service"] == config
    
    @pytest.mark.asyncio
    async def test_check_service_health_success(self, health_checker):
        """Test successful health check."""
        config = ServiceHealthCheck(
            name="test_service",
            url="http://localhost:8000"
        )
        health_checker.register_service(config)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_response.headers.get.return_value = "application/json"
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await health_checker.check_service_health("test_service")
            
            assert result.status == HealthStatus.HEALTHY
            assert result.response_time is not None
            assert result.details == {"status": "healthy"}
    
    @pytest.mark.asyncio
    async def test_check_service_health_failure(self, health_checker):
        """Test failed health check."""
        config = ServiceHealthCheck(
            name="test_service",
            url="http://localhost:8000"
        )
        health_checker.register_service(config)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            
            result = await health_checker.check_service_health("test_service")
            
            assert result.status == HealthStatus.UNHEALTHY
            assert "Connection refused" in result.error_message
    
    @pytest.mark.asyncio
    async def test_check_service_health_timeout(self, health_checker):
        """Test health check timeout."""
        config = ServiceHealthCheck(
            name="test_service",
            url="http://localhost:8000",
            timeout=1.0
        )
        health_checker.register_service(config)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )
            
            result = await health_checker.check_service_health("test_service")
            
            assert result.status == HealthStatus.UNHEALTHY
            assert "Timeout" in result.error_message
    
    def test_get_service_status(self, health_checker):
        """Test service status determination."""
        config = ServiceHealthCheck(
            name="test_service",
            url="http://localhost:8000",
            failure_threshold=3
        )
        health_checker.register_service(config)
        
        # Simulate health check results
        from ..utils.health_check import HealthCheckResult
        
        # Add healthy results
        for _ in range(2):
            result = HealthCheckResult(
                service_name="test_service",
                status=HealthStatus.HEALTHY,
                response_time=0.1,
                timestamp=datetime.now()
            )
            health_checker.health_results["test_service"].append(result)
        
        # Add one unhealthy result
        result = HealthCheckResult(
            service_name="test_service",
            status=HealthStatus.UNHEALTHY,
            response_time=None,
            timestamp=datetime.now(),
            error_message="Service error"
        )
        health_checker.health_results["test_service"].append(result)
        
        # Should be degraded (some failures but not enough to be unhealthy)
        status = health_checker.get_service_status("test_service")
        assert status == HealthStatus.DEGRADED
    
    def test_get_system_health(self, health_checker):
        """Test system health aggregation."""
        # Register multiple services
        services = ["service1", "service2", "service3"]
        for service in services:
            config = ServiceHealthCheck(name=service, url=f"http://localhost:800{services.index(service)}")
            health_checker.register_service(config)
        
        # Mock service statuses
        with patch.object(health_checker, 'get_service_status') as mock_status:
            mock_status.side_effect = [
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY
            ]
            
            system_health = health_checker.get_system_health()
            
            assert system_health["overall_status"] == "degraded"
            assert system_health["total_services"] == 3
            assert system_health["healthy_services"] == 1
            assert system_health["degraded_services"] == 1
            assert system_health["unhealthy_services"] == 1


class TestSystemHealthMonitor:
    """Test system health monitoring."""
    
    @pytest.fixture
    def health_monitor(self):
        """Create health monitor for testing."""
        health_checker = HealthChecker()
        return SystemHealthMonitor(health_checker)
    
    @pytest.mark.asyncio
    async def test_check_and_alert_unhealthy(self, health_monitor):
        """Test alerting for unhealthy system."""
        # Mock unhealthy system
        mock_health = {
            "overall_status": "unhealthy",
            "unhealthy_services": 3,
            "degraded_services": 0,
            "services": {"service1": "unhealthy", "service2": "unhealthy", "service3": "unhealthy"}
        }
        
        with patch.object(health_monitor.health_checker, 'get_system_health', return_value=mock_health), \
             patch.object(health_monitor, 'send_alert') as mock_alert:
            
            await health_monitor.check_and_alert()
            
            mock_alert.assert_called_once()
            args = mock_alert.call_args[0]
            assert "UNHEALTHY" in args[0]
    
    @pytest.mark.asyncio
    async def test_alert_cooldown(self, health_monitor):
        """Test alert cooldown mechanism."""
        # Set a recent alert time
        health_monitor.last_alert_time["unhealthy"] = datetime.now()
        
        mock_health = {
            "overall_status": "unhealthy",
            "unhealthy_services": 2,
            "degraded_services": 0,
            "services": {"service1": "unhealthy", "service2": "unhealthy"}
        }
        
        with patch.object(health_monitor.health_checker, 'get_system_health', return_value=mock_health), \
             patch.object(health_monitor, 'send_alert') as mock_alert:
            
            await health_monitor.check_and_alert()
            
            # Should not send alert due to cooldown
            mock_alert.assert_not_called()
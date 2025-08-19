"""
Unit tests for main orchestration script.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import subprocess

from ..main import (
    start_service, wait_for_service, check_service_health,
    perform_system_health_check, demonstrate_trading_workflow,
    shutdown_all_services, running_processes
)


class TestServiceManagement:
    """Test service management functionality."""
    
    def test_start_service(self):
        """Test service startup."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            process = start_service(
                "MCP_A2A.mcp_servers.market_data_server",
                9000,
                "MarketData MCP Server"
            )
            
            assert process == mock_process
            assert mock_process in running_processes
            
            # Verify correct command was called
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            assert "uvicorn" in args
            assert "MCP_A2A.mcp_servers.market_data_server:app" in args
            assert "--port" in args
            assert "9000" in args
    
    @pytest.mark.asyncio
    async def test_wait_for_service_success(self):
        """Test waiting for service to become available - success case."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await wait_for_service("http://localhost:9000/", "Test Service", timeout=5)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_wait_for_service_timeout(self):
        """Test waiting for service to become available - timeout case."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock connection error (service not available)
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            
            result = await wait_for_service("http://localhost:9000/", "Test Service", timeout=1)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_service_health_healthy(self):
        """Test service health check - healthy service."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"service": "Test Service", "status": "running"}
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await check_service_health("http://localhost:9000/", "Test Service")
            
            assert result["service"] == "Test Service"
            assert result["status"] == "healthy"
            assert "response" in result
    
    @pytest.mark.asyncio
    async def test_check_service_health_unhealthy(self):
        """Test service health check - unhealthy service."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await check_service_health("http://localhost:9000/", "Test Service")
            
            assert result["service"] == "Test Service"
            assert result["status"] == "unhealthy"
            assert "HTTP 500" in result["error"]
    
    @pytest.mark.asyncio
    async def test_check_service_health_unreachable(self):
        """Test service health check - unreachable service."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            
            result = await check_service_health("http://localhost:9000/", "Test Service")
            
            assert result["service"] == "Test Service"
            assert result["status"] == "unreachable"
            assert "Connection refused" in result["error"]
    
    def test_shutdown_all_services(self):
        """Test graceful service shutdown."""
        # Create mock processes
        mock_process1 = MagicMock()
        mock_process1.pid = 12345
        mock_process1.poll.return_value = None  # Still running
        
        mock_process2 = MagicMock()
        mock_process2.pid = 12346
        mock_process2.poll.return_value = 0  # Already terminated
        
        # Add to running processes
        running_processes.clear()
        running_processes.extend([mock_process1, mock_process2])
        
        shutdown_all_services()
        
        # Verify process1 was terminated (was running)
        mock_process1.terminate.assert_called_once()
        mock_process1.wait.assert_called_once()
        
        # Verify process2 was not terminated (already stopped)
        mock_process2.terminate.assert_not_called()
        
        # Verify processes list is cleared
        assert len(running_processes) == 0
    
    def test_shutdown_all_services_force_kill(self):
        """Test service shutdown with force kill."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Still running
        mock_process.wait.side_effect = [subprocess.TimeoutExpired("cmd", 10), None]  # First wait times out
        
        running_processes.clear()
        running_processes.append(mock_process)
        
        shutdown_all_services()
        
        # Verify terminate was called first
        mock_process.terminate.assert_called_once()
        
        # Verify kill was called after timeout
        mock_process.kill.assert_called_once()
        
        # Verify two wait calls (one that timed out, one after kill)
        assert mock_process.wait.call_count == 2


class TestSystemHealthCheck:
    """Test system health check functionality."""
    
    @pytest.mark.asyncio
    async def test_perform_system_health_check_all_healthy(self):
        """Test system health check with all services healthy."""
        with patch('MCP_A2A.main.check_service_health') as mock_check:
            mock_check.return_value = {
                "service": "Test Service",
                "status": "healthy",
                "response": {"status": "running"}
            }
            
            result = await perform_system_health_check()
            
            assert result["overall_status"] == "healthy"
            assert result["healthy_services"] == result["total_services"]
            assert result["total_services"] == 8  # All services
            assert len(result["services"]) == 8
    
    @pytest.mark.asyncio
    async def test_perform_system_health_check_some_unhealthy(self):
        """Test system health check with some services unhealthy."""
        def mock_health_check(url, service_name):
            if "market_data" in url:
                return {
                    "service": service_name,
                    "status": "unhealthy",
                    "error": "Service error"
                }
            else:
                return {
                    "service": service_name,
                    "status": "healthy",
                    "response": {"status": "running"}
                }
        
        with patch('MCP_A2A.main.check_service_health', side_effect=mock_health_check):
            result = await perform_system_health_check()
            
            assert result["overall_status"] == "degraded"
            assert result["healthy_services"] == 7  # 7 out of 8 healthy
            assert result["total_services"] == 8


class TestTradingWorkflowDemo:
    """Test trading workflow demonstration."""
    
    @pytest.mark.asyncio
    async def test_demonstrate_trading_workflow_success(self):
        """Test successful trading workflow demonstration."""
        mock_response_data = {
            "workflow_id": "demo-123",
            "status": "COMPLETED",
            "success": True,
            "selected_ticker": "AAPL",
            "trade_execution": {
                "success": True,
                "trade_id": "trade-456",
                "executed_price": 149.50,
                "executed_quantity": 166,
                "total_value": 24817.0
            },
            "execution_time_seconds": 15.2
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await demonstrate_trading_workflow()
            
            assert result["success"] is True
            assert result["status"] == "COMPLETED"
            assert result["selected_ticker"] == "AAPL"
            assert result["trade_execution"]["trade_id"] == "trade-456"
    
    @pytest.mark.asyncio
    async def test_demonstrate_trading_workflow_failure(self):
        """Test failed trading workflow demonstration."""
        mock_response_data = {
            "workflow_id": "demo-123",
            "status": "FAILED",
            "success": False,
            "errors": ["Insufficient cash for trade execution"],
            "selected_ticker": "AAPL"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await demonstrate_trading_workflow()
            
            assert result["success"] is False
            assert result["status"] == "FAILED"
            assert "Insufficient cash" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_demonstrate_trading_workflow_http_error(self):
        """Test trading workflow demonstration with HTTP error."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await demonstrate_trading_workflow()
            
            assert result["success"] is False
            assert result["status"] == "FAILED"
            assert "HTTP 500" in result["error"]
    
    @pytest.mark.asyncio
    async def test_demonstrate_trading_workflow_connection_error(self):
        """Test trading workflow demonstration with connection error."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            
            result = await demonstrate_trading_workflow()
            
            assert result["success"] is False
            assert result["status"] == "ERROR"
            assert "Connection refused" in result["error"]


class TestIntegration:
    """Test integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_service_startup_sequence(self):
        """Test that services start in correct order."""
        started_services = []
        
        def mock_start_service(module_path, port, service_name):
            started_services.append(service_name)
            mock_process = MagicMock()
            mock_process.pid = len(started_services)
            running_processes.append(mock_process)
            return mock_process
        
        def mock_wait_for_service(url, service_name, timeout=30):
            return True  # All services start successfully
        
        with patch('MCP_A2A.main.start_service', side_effect=mock_start_service), \
             patch('MCP_A2A.main.wait_for_service', side_effect=mock_wait_for_service):
            
            from MCP_A2A.main import start_all_services
            result = await start_all_services()
            
            assert result is True
            assert len(started_services) == 8
            
            # Verify MCP servers start before agents
            mcp_servers = [name for name in started_services if "MCP Server" in name]
            agents = [name for name in started_services if "Agent" in name]
            
            assert len(mcp_servers) == 3
            assert len(agents) == 5
            
            # Find indices of last MCP server and first agent
            last_mcp_index = max(started_services.index(name) for name in mcp_servers)
            first_agent_index = min(started_services.index(name) for name in agents)
            
            # MCP servers should start before agents
            assert last_mcp_index < first_agent_index
    
    def teardown_method(self):
        """Clean up after each test."""
        running_processes.clear()
"""
Smoke tests for MCP A2A Trading System.

Quick validation tests to ensure basic system functionality.
"""

import asyncio
import pytest
import httpx
from typing import Dict, Any

from MCP_A2A.config import SERVICE_URLS
from MCP_A2A.tests.test_config import get_test_config, get_test_strategy


class TestSmokeTests:
    """Basic smoke tests for system validation."""
    
    @pytest.fixture
    async def http_client(self):
        """HTTP client fixture."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            yield client
    
    async def test_all_services_health(self, http_client):
        """Test that all services respond to health checks."""
        services = [
            ("PortfolioManager", SERVICE_URLS["portfolio_manager"]),
            ("FundamentalAnalyst", SERVICE_URLS["fundamental_analyst"]),
            ("TechnicalAnalyst", SERVICE_URLS["technical_analyst"]),
            ("RiskManager", SERVICE_URLS["risk_manager"]),
            ("TradeExecutor", SERVICE_URLS["trade_executor"]),
            ("MarketDataMCP", SERVICE_URLS["market_data_mcp"]),
            ("TechnicalAnalysisMCP", SERVICE_URLS["technical_analysis_mcp"]),
            ("TradingExecutionMCP", SERVICE_URLS["trading_execution_mcp"])
        ]
        
        for name, url in services:
            try:
                response = await http_client.get(f"{url}/health")
                assert response.status_code == 200, f"{name} health check failed"
                
                health_data = response.json()
                assert health_data.get("status") == "healthy", f"{name} reports unhealthy status"
                
            except Exception as e:
                pytest.fail(f"{name} health check failed with error: {e}")
    
    async def test_portfolio_manager_basic_endpoint(self, http_client):
        """Test basic Portfolio Manager endpoint functionality."""
        # Test the main strategy endpoint exists and accepts requests
        strategy = get_test_strategy("conservative_strategy")
        
        response = await http_client.post(
            f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
            json=strategy
        )
        
        # Should get a valid response (success or handled error)
        assert response.status_code in [200, 400, 500]
        
        if response.status_code == 200:
            result = response.json()
            assert "workflow_id" in result or "status" in result
    
    async def test_mcp_servers_basic_functionality(self, http_client):
        """Test basic MCP server functionality."""
        
        # Test MarketDataMCP
        market_data_request = {
            "function": "get_stock_price",
            "arguments": {"ticker": "AAPL"}
        }
        
        response = await http_client.post(
            f"{SERVICE_URLS['market_data_mcp']}/mcp",
            json=market_data_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "data" in data
        
        # Test TechnicalAnalysisMCP
        tech_request = {
            "function": "calculate_indicator",
            "arguments": {
                "price_data": [100, 101, 102, 101, 100],
                "indicator_name": "RSI",
                "params": {"period": 14}
            }
        }
        
        response = await http_client.post(
            f"{SERVICE_URLS['technical_analysis_mcp']}/mcp",
            json=tech_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "indicator" in data
        assert "values" in data
        
        # Test TradingExecutionMCP
        portfolio_request = {
            "function": "get_portfolio_status",
            "arguments": {}
        }
        
        response = await http_client.post(
            f"{SERVICE_URLS['trading_execution_mcp']}/mcp",
            json=portfolio_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "cash_balance" in data
        assert "positions" in data
    
    async def test_a2a_protocol_basic_communication(self, http_client):
        """Test basic A2A protocol communication."""
        
        # Test A2A endpoint on FundamentalAnalyst
        a2a_request = {
            "jsonrpc": "2.0",
            "method": "analyze_companies",
            "params": {
                "sector": "technology",
                "criteria": "growth"
            },
            "id": "test-001"
        }
        
        response = await http_client.post(
            f"{SERVICE_URLS['fundamental_analyst']}/a2a",
            json=a2a_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "jsonrpc" in data
        assert data["jsonrpc"] == "2.0"
        assert "id" in data
        assert data["id"] == "test-001"
        assert "result" in data or "error" in data
    
    async def test_system_configuration_validity(self):
        """Test that system configuration is valid."""
        config = get_test_config()
        
        # Verify required configuration sections exist
        assert "timeout" in config
        assert "retry" in config
        assert "portfolio" in config
        assert "test_strategies" in config
        
        # Verify timeout values are reasonable
        assert config["timeout"]["service_startup"] > 0
        assert config["timeout"]["request_timeout"] > 0
        assert config["timeout"]["workflow_timeout"] > 0
        
        # Verify portfolio configuration
        assert config["portfolio"]["initial_cash"] > 0
        assert 0 < config["portfolio"]["max_position_size"] <= 1
        assert 0 < config["portfolio"]["min_cash_reserve"] <= 1
        
        # Verify test strategies exist
        assert len(config["test_strategies"]) > 0
        
        for strategy_name, strategy in config["test_strategies"].items():
            assert "goal" in strategy
            assert "risk_tolerance" in strategy
            assert "max_investment" in strategy
            assert strategy["max_investment"] > 0
    
    async def test_service_urls_accessibility(self, http_client):
        """Test that all configured service URLs are accessible."""
        
        for service_name, url in SERVICE_URLS.items():
            try:
                # Just test that we can connect (don't require specific endpoints)
                response = await http_client.get(url, timeout=5.0)
                # Accept any response that indicates the service is running
                assert response.status_code in [200, 404, 405, 422]
                
            except httpx.ConnectError:
                pytest.fail(f"Cannot connect to {service_name} at {url}")
            except httpx.TimeoutException:
                pytest.fail(f"Timeout connecting to {service_name} at {url}")
    
    async def test_concurrent_health_checks(self, http_client):
        """Test concurrent access to health endpoints."""
        
        services = list(SERVICE_URLS.values())
        
        # Create concurrent health check tasks
        async def check_health(url):
            response = await http_client.get(f"{url}/health")
            return response.status_code == 200
        
        tasks = [check_health(url) for url in services]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful health checks
        successful_checks = sum(1 for result in results if result is True)
        
        # At least 80% of services should be healthy
        min_healthy = int(len(services) * 0.8)
        assert successful_checks >= min_healthy, f"Only {successful_checks}/{len(services)} services are healthy"


if __name__ == "__main__":
    # Run smoke tests
    pytest.main([__file__, "-v", "--tb=short"])
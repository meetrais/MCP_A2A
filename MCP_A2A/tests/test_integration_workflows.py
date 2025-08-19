"""
Integration tests for complete MCP A2A Trading System workflows.

This module contains comprehensive end-to-end tests that validate the entire
trading system workflow from strategy initiation to trade execution.
"""

import asyncio
import json
import pytest
import httpx
from typing import Dict, Any
from unittest.mock import AsyncMock, patch
import time
import uuid

from MCP_A2A.config import SERVICE_URLS
from MCP_A2A.models.trading_models import InvestmentStrategy, TradeProposal
from MCP_A2A.utils.a2a_client import A2AClient
from MCP_A2A.tests.test_config import get_test_config, get_test_strategy


class IntegrationTestHelper:
    """Helper class for integration testing with service management."""
    
    def __init__(self):
        self.services_started = False
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def wait_for_service(self, url: str, max_retries: int = 30) -> bool:
        """Wait for a service to become available."""
        for _ in range(max_retries):
            try:
                response = await self.client.get(f"{url}/health")
                if response.status_code == 200:
                    return True
            except:
                pass
            await asyncio.sleep(1)
        return False
    
    async def wait_for_all_services(self) -> bool:
        """Wait for all services to become available."""
        services_to_check = [
            SERVICE_URLS["portfolio_manager"],
            SERVICE_URLS["fundamental_analyst"],
            SERVICE_URLS["technical_analyst"],
            SERVICE_URLS["risk_manager"],
            SERVICE_URLS["trade_executor"],
            SERVICE_URLS["market_data_mcp"],
            SERVICE_URLS["technical_analysis_mcp"],
            SERVICE_URLS["trading_execution_mcp"]
        ]
        
        for service_url in services_to_check:
            if not await self.wait_for_service(service_url):
                return False
        return True
    
    async def reset_portfolio(self):
        """Reset portfolio to initial state for testing."""
        try:
            response = await self.client.post(
                f"{SERVICE_URLS['trading_execution_mcp']}/mcp",
                json={
                    "function": "reset_portfolio",
                    "arguments": {}
                }
            )
            return response.status_code == 200
        except:
            return False
    
    async def get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status."""
        response = await self.client.post(
            f"{SERVICE_URLS['trading_execution_mcp']}/mcp",
            json={
                "function": "get_portfolio_status",
                "arguments": {}
            }
        )
        if response.status_code == 200:
            return response.json()
        return {}
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.client.aclose()


@pytest.fixture
async def integration_helper():
    """Fixture providing integration test helper."""
    helper = IntegrationTestHelper()
    
    # Wait for services to be available
    services_ready = await helper.wait_for_all_services()
    if not services_ready:
        pytest.skip("Services not available for integration testing")
    
    # Reset portfolio state
    await helper.reset_portfolio()
    
    yield helper
    
    await helper.cleanup()


class TestCompleteWorkflows:
    """Test complete trading workflows end-to-end."""
    
    async def test_successful_trading_workflow(self, integration_helper):
        """
        Test a complete successful trading workflow:
        Strategy -> Fundamental Analysis -> Technical Analysis -> Risk Approval -> Trade Execution
        """
        # Step 1: Initiate trading strategy
        strategy = get_test_strategy("successful_tech_strategy")
        
        response = await integration_helper.client.post(
            f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
            json=strategy
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify workflow completion
        assert "workflow_id" in result
        assert "status" in result
        assert result["status"] in ["completed", "success"]
        
        # Verify trade execution occurred
        assert "trade_result" in result
        trade_result = result["trade_result"]
        assert trade_result["status"] == "EXECUTED"
        assert "ticker" in trade_result
        assert "quantity" in trade_result
        assert trade_result["quantity"] > 0
        
        # Verify portfolio was updated
        portfolio = await integration_helper.get_portfolio_status()
        assert portfolio["cash_balance"] < 100000.0  # Money was spent
        assert len(portfolio["positions"]) > 0  # Position was created
        
        # Verify audit trail exists
        assert "audit_trail" in result
        audit_trail = result["audit_trail"]
        assert len(audit_trail) >= 4  # At least 4 steps in workflow
        
        # Verify each step was logged
        step_types = [step["step"] for step in audit_trail]
        expected_steps = ["fundamental_analysis", "technical_analysis", "risk_evaluation", "trade_execution"]
        for expected_step in expected_steps:
            assert expected_step in step_types
    
    async def test_fundamental_analysis_rejection_workflow(self, integration_helper):
        """
        Test workflow where fundamental analysis rejects all candidates.
        """
        # Strategy targeting a sector with poor fundamentals
        strategy = get_test_strategy("failing_strategy")
        
        response = await integration_helper.client.post(
            f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
            json=strategy
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify workflow stopped at fundamental analysis
        assert result["status"] in ["no_suitable_candidates", "rejected"]
        assert "fundamental_analysis" in result
        
        # Verify no trade was executed
        assert "trade_result" not in result or result.get("trade_result", {}).get("status") != "EXECUTED"
        
        # Verify portfolio unchanged
        portfolio = await integration_helper.get_portfolio_status()
        assert portfolio["cash_balance"] == 100000.0  # No money spent
        assert len(portfolio["positions"]) == 0  # No positions created
        
        # Verify audit trail shows rejection
        assert "audit_trail" in result
        audit_trail = result["audit_trail"]
        fundamental_step = next((step for step in audit_trail if step["step"] == "fundamental_analysis"), None)
        assert fundamental_step is not None
        assert "no suitable candidates" in fundamental_step.get("result", "").lower()
    
    async def test_technical_analysis_hold_signal_workflow(self, integration_helper):
        """
        Test workflow where technical analysis generates HOLD signal.
        """
        # Use a strategy that will pass fundamental but get HOLD from technical
        strategy = {
            "goal": "Find tech stocks but only buy at optimal entry points",
            "sector_preference": "technology",
            "risk_tolerance": "high",
            "max_investment": 30000.0,
            "time_horizon": "short"  # Short horizon may trigger HOLD signals
        }
        
        response = await integration_helper.client.post(
            f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
            json=strategy
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # May result in HOLD or proceed depending on technical signals
        # If HOLD, verify workflow stops appropriately
        if result["status"] == "hold_signal":
            assert "technical_analysis" in result
            technical_result = result["technical_analysis"]
            assert technical_result["signal"] == "HOLD"
            
            # Verify no trade executed
            assert "trade_result" not in result or result.get("trade_result", {}).get("status") != "EXECUTED"
            
            # Verify portfolio unchanged
            portfolio = await integration_helper.get_portfolio_status()
            assert portfolio["cash_balance"] == 100000.0
            assert len(portfolio["positions"]) == 0
        
        # Verify audit trail includes technical analysis
        assert "audit_trail" in result
        audit_trail = result["audit_trail"]
        technical_step = next((step for step in audit_trail if step["step"] == "technical_analysis"), None)
        assert technical_step is not None
    
    async def test_risk_management_trade_denial_workflow(self, integration_helper):
        """
        Test workflow where risk management denies the trade.
        """
        # First, execute a large trade to reduce available capital
        large_strategy = {
            "goal": "Make a large investment in tech stocks",
            "sector_preference": "technology",
            "risk_tolerance": "high",
            "max_investment": 80000.0,  # Large investment
            "time_horizon": "long"
        }
        
        # Execute first trade
        response1 = await integration_helper.client.post(
            f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
            json=large_strategy
        )
        
        # Now try another large trade that should be denied by risk management
        risky_strategy = {
            "goal": "Make another large investment",
            "sector_preference": "technology",
            "risk_tolerance": "high",
            "max_investment": 50000.0,  # This should exceed risk limits
            "time_horizon": "medium"
        }
        
        response2 = await integration_helper.client.post(
            f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
            json=risky_strategy
        )
        
        assert response2.status_code == 200
        result = response2.json()
        
        # Verify risk management denied the trade
        if result["status"] == "risk_denied":
            assert "risk_evaluation" in result
            risk_result = result["risk_evaluation"]
            assert risk_result["decision"] == "DENY"
            assert "reasoning" in risk_result
            
            # Verify no second trade executed
            assert "trade_result" not in result or result.get("trade_result", {}).get("status") != "EXECUTED"
            
            # Verify audit trail shows risk denial
            assert "audit_trail" in result
            audit_trail = result["audit_trail"]
            risk_step = next((step for step in audit_trail if step["step"] == "risk_evaluation"), None)
            assert risk_step is not None
            assert "deny" in risk_step.get("result", "").lower()
    
    async def test_trade_execution_failure_workflow(self, integration_helper):
        """
        Test workflow where trade execution fails.
        """
        # Mock trade execution to fail
        with patch('MCP_A2A.agents.trade_executor_agent.TradeExecutorAgent.execute_trade') as mock_execute:
            mock_execute.return_value = {
                "status": "FAILED",
                "error": "Insufficient liquidity",
                "ticker": "AAPL",
                "action": "BUY",
                "quantity": 100
            }
            
            strategy = {
                "goal": "Buy tech stocks",
                "sector_preference": "technology",
                "risk_tolerance": "medium",
                "max_investment": 20000.0,
                "time_horizon": "medium"
            }
            
            response = await integration_helper.client.post(
                f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
                json=strategy
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Verify trade execution failure was handled
            assert result["status"] == "execution_failed"
            assert "trade_result" in result
            trade_result = result["trade_result"]
            assert trade_result["status"] == "FAILED"
            assert "error" in trade_result
            
            # Verify portfolio unchanged due to failed trade
            portfolio = await integration_helper.get_portfolio_status()
            assert portfolio["cash_balance"] == 100000.0  # No money spent
            assert len(portfolio["positions"]) == 0  # No positions created
            
            # Verify audit trail shows execution failure
            assert "audit_trail" in result
            audit_trail = result["audit_trail"]
            execution_step = next((step for step in audit_trail if step["step"] == "trade_execution"), None)
            assert execution_step is not None
            assert "failed" in execution_step.get("result", "").lower()


class TestPerformanceAndThroughput:
    """Test system performance and throughput capabilities."""
    
    async def test_concurrent_strategy_execution(self, integration_helper):
        """
        Test system handling of multiple concurrent strategy requests.
        """
        strategies = [
            {
                "goal": f"Strategy {i}: Find growth stocks",
                "sector_preference": "technology",
                "risk_tolerance": "medium",
                "max_investment": 5000.0,
                "time_horizon": "medium"
            }
            for i in range(3)  # Test with 3 concurrent strategies
        ]
        
        # Execute strategies concurrently
        start_time = time.time()
        
        tasks = []
        for strategy in strategies:
            task = integration_helper.client.post(
                f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
                json=strategy
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify all requests completed successfully
        successful_responses = 0
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code == 200
                result = response.json()
                assert "workflow_id" in result
                successful_responses += 1
        
        # Verify reasonable performance (should complete within 60 seconds)
        assert execution_time < 60.0
        assert successful_responses >= 2  # At least 2 out of 3 should succeed
        
        # Verify portfolio state is consistent
        portfolio = await integration_helper.get_portfolio_status()
        assert portfolio["cash_balance"] <= 100000.0
        assert portfolio["total_value"] > 0
    
    async def test_system_throughput_measurement(self, integration_helper):
        """
        Measure system throughput with sequential requests.
        """
        num_requests = 5
        strategies = [
            {
                "goal": f"Throughput test {i}",
                "sector_preference": "technology",
                "risk_tolerance": "low",
                "max_investment": 2000.0,
                "time_horizon": "short"
            }
            for i in range(num_requests)
        ]
        
        start_time = time.time()
        successful_requests = 0
        
        for strategy in strategies:
            try:
                response = await integration_helper.client.post(
                    f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
                    json=strategy
                )
                if response.status_code == 200:
                    successful_requests += 1
            except Exception:
                pass  # Count failures but continue
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate throughput
        throughput = successful_requests / total_time if total_time > 0 else 0
        
        # Verify reasonable throughput (at least 0.1 requests per second)
        assert throughput > 0.1
        assert successful_requests >= num_requests // 2  # At least 50% success rate
        
        print(f"System throughput: {throughput:.2f} requests/second")
        print(f"Successful requests: {successful_requests}/{num_requests}")


class TestErrorRecoveryAndResilience:
    """Test system error recovery and resilience capabilities."""
    
    async def test_service_unavailable_recovery(self, integration_helper):
        """
        Test system behavior when a service becomes temporarily unavailable.
        """
        strategy = {
            "goal": "Test service recovery",
            "sector_preference": "technology",
            "risk_tolerance": "medium",
            "max_investment": 10000.0,
            "time_horizon": "medium"
        }
        
        # Mock one service to be temporarily unavailable
        with patch('httpx.AsyncClient.post') as mock_post:
            # First call fails, second succeeds (simulating recovery)
            mock_post.side_effect = [
                httpx.ConnectError("Service unavailable"),
                httpx.Response(200, json={"result": "success"})
            ]
            
            response = await integration_helper.client.post(
                f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
                json=strategy
            )
            
            # System should handle the error gracefully
            assert response.status_code in [200, 503]  # Success or service unavailable
            
            if response.status_code == 200:
                result = response.json()
                # Verify system recovered and completed workflow
                assert "workflow_id" in result
            else:
                # Verify proper error response
                error_result = response.json()
                assert "error" in error_result
    
    async def test_partial_system_failure_handling(self, integration_helper):
        """
        Test system behavior during partial failures.
        """
        strategy = {
            "goal": "Test partial failure handling",
            "sector_preference": "technology",
            "risk_tolerance": "medium",
            "max_investment": 15000.0,
            "time_horizon": "medium"
        }
        
        # Mock technical analysis to fail but other services work
        with patch('MCP_A2A.agents.technical_analyst_agent.TechnicalAnalystAgent.analyze_ticker') as mock_technical:
            mock_technical.side_effect = Exception("Technical analysis service error")
            
            response = await integration_helper.client.post(
                f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
                json=strategy
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # System should handle partial failure gracefully
            assert "workflow_id" in result
            assert result["status"] in ["partial_failure", "degraded", "completed"]
            
            # Verify error was logged in audit trail
            assert "audit_trail" in result
            audit_trail = result["audit_trail"]
            error_logged = any("error" in step.get("result", "").lower() for step in audit_trail)
            assert error_logged


class TestDataConsistencyAndIntegrity:
    """Test data consistency and integrity across the system."""
    
    async def test_portfolio_state_consistency(self, integration_helper):
        """
        Test that portfolio state remains consistent across multiple operations.
        """
        # Get initial portfolio state
        initial_portfolio = await integration_helper.get_portfolio_status()
        initial_cash = initial_portfolio["cash_balance"]
        initial_positions = len(initial_portfolio["positions"])
        
        # Execute a trade
        strategy = {
            "goal": "Test portfolio consistency",
            "sector_preference": "technology",
            "risk_tolerance": "medium",
            "max_investment": 10000.0,
            "time_horizon": "medium"
        }
        
        response = await integration_helper.client.post(
            f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
            json=strategy
        )
        
        assert response.status_code == 200
        result = response.json()
        
        if result["status"] == "completed" and "trade_result" in result:
            trade_result = result["trade_result"]
            
            if trade_result["status"] == "EXECUTED":
                # Verify portfolio state consistency
                final_portfolio = await integration_helper.get_portfolio_status()
                
                # Cash should decrease by trade amount
                trade_value = trade_result["total_value"]
                expected_cash = initial_cash - trade_value
                assert abs(final_portfolio["cash_balance"] - expected_cash) < 0.01
                
                # Should have one more position
                assert len(final_portfolio["positions"]) == initial_positions + 1
                
                # Total portfolio value should be preserved (cash + positions)
                total_position_value = sum(pos["current_value"] for pos in final_portfolio["positions"])
                total_portfolio_value = final_portfolio["cash_balance"] + total_position_value
                
                # Allow small variance for price changes
                assert abs(total_portfolio_value - initial_cash) < 100.0
    
    async def test_audit_trail_completeness(self, integration_helper):
        """
        Test that audit trails are complete and consistent.
        """
        strategy = {
            "goal": "Test audit trail completeness",
            "sector_preference": "technology",
            "risk_tolerance": "medium",
            "max_investment": 8000.0,
            "time_horizon": "medium"
        }
        
        response = await integration_helper.client.post(
            f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
            json=strategy
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify audit trail exists and is complete
        assert "audit_trail" in result
        audit_trail = result["audit_trail"]
        assert len(audit_trail) > 0
        
        # Verify each audit entry has required fields
        for entry in audit_trail:
            assert "step" in entry
            assert "timestamp" in entry
            assert "result" in entry
            assert "duration" in entry or "execution_time" in entry
        
        # Verify chronological order
        timestamps = [entry["timestamp"] for entry in audit_trail]
        assert timestamps == sorted(timestamps)
        
        # Verify workflow steps are logical
        steps = [entry["step"] for entry in audit_trail]
        if "trade_execution" in steps:
            # If trade was executed, all previous steps should be present
            assert "fundamental_analysis" in steps
            assert "risk_evaluation" in steps
            
            # Technical analysis should come after fundamental
            fund_idx = steps.index("fundamental_analysis")
            if "technical_analysis" in steps:
                tech_idx = steps.index("technical_analysis")
                assert tech_idx > fund_idx


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])
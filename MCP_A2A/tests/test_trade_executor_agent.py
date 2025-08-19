"""
Unit tests for TradeExecutor Agent.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from ..agents.trade_executor_agent import (
    app, validate_trade_execution_request, analyze_execution_result,
    execute_approved_trade_internal, execute_approved_trade, ExecutionResult
)
from ..models.trading_models import TradeProposal, TradeAction


class TestTradeExecutorAgent:
    """Test TradeExecutor Agent functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "TradeExecutor Agent"
        assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_a2a_endpoint_execute_approved_trade(self, client):
        """Test A2A endpoint for trade execution."""
        with patch('MCP_A2A.agents.trade_executor_agent.execute_approved_trade') as mock_execute:
            mock_execute.return_value = {
                "execution_status": "SUCCESS",
                "success": True,
                "message": "Trade executed successfully",
                "trade_id": "test-123"
            }
            
            response = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "execute_approved_trade",
                    "params": {
                        "ticker": "AAPL",
                        "action": "BUY",
                        "quantity": 10,
                        "estimated_price": 150.0,
                        "rationale": "Approved trade"
                    },
                    "id": "test-123"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == "test-123"
            assert "result" in data
            assert data["result"]["success"] is True
    
    @pytest.mark.asyncio
    async def test_a2a_endpoint_get_execution_status(self, client):
        """Test A2A endpoint for execution status."""
        with patch('MCP_A2A.agents.trade_executor_agent.get_execution_status') as mock_status:
            mock_status.return_value = {
                "found": True,
                "trade_id": "test-123",
                "status": "EXECUTED"
            }
            
            response = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "get_execution_status",
                    "params": {"trade_id": "test-123"},
                    "id": "status-123"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["result"]["found"] is True
    
    def test_direct_execute_endpoint(self, client):
        """Test direct execution endpoint."""
        trade_proposal = {
            "ticker": "GOOGL",
            "action": "BUY",
            "quantity": 5,
            "estimated_price": 140.0,
            "rationale": "Direct execution test"
        }
        
        with patch('MCP_A2A.agents.trade_executor_agent.execute_approved_trade_internal') as mock_execute:
            mock_execute.return_value = {
                "execution_status": "SUCCESS",
                "success": True,
                "message": "Trade executed"
            }
            
            response = client.post(
                "/execute",
                json={
                    "trade_proposal": trade_proposal,
                    "execution_type": "MARKET"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_status_endpoint(self, client):
        """Test status endpoint."""
        with patch('MCP_A2A.agents.trade_executor_agent.get_execution_status') as mock_status:
            mock_status.return_value = {
                "found": True,
                "trade_id": "test-456",
                "status": "EXECUTED"
            }
            
            response = client.get("/status/test-456")
            assert response.status_code == 200
            data = response.json()
            assert data["found"] is True
            assert data["trade_id"] == "test-456"


class TestTradeValidation:
    """Test trade execution validation."""
    
    @pytest.fixture
    def valid_trade_proposal(self):
        """Create valid trade proposal."""
        return TradeProposal(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=150.0,
            rationale="Valid trade proposal"
        )
    
    def test_validate_valid_trade_proposal(self, valid_trade_proposal):
        """Test validation of valid trade proposal."""
        result = validate_trade_execution_request(valid_trade_proposal)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_invalid_ticker(self):
        """Test validation with invalid ticker."""
        invalid_trade = TradeProposal(
            ticker="",  # Empty ticker
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=150.0,
            rationale="Invalid ticker"
        )
        
        result = validate_trade_execution_request(invalid_trade)
        
        assert result["valid"] is False
        assert any("ticker" in error.lower() for error in result["errors"])
    
    def test_validate_invalid_quantity(self):
        """Test validation with invalid quantity."""
        invalid_trade = TradeProposal(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=0,  # Invalid quantity
            estimated_price=150.0,
            rationale="Invalid quantity"
        )
        
        result = validate_trade_execution_request(invalid_trade)
        
        assert result["valid"] is False
        assert any("quantity" in error.lower() for error in result["errors"])
    
    def test_validate_invalid_price(self):
        """Test validation with invalid price."""
        invalid_trade = TradeProposal(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=0.0,  # Invalid price
            rationale="Invalid price"
        )
        
        result = validate_trade_execution_request(invalid_trade)
        
        assert result["valid"] is False
        assert any("price" in error.lower() for error in result["errors"])
    
    def test_validate_high_risk_warning(self):
        """Test validation generates warning for high risk trades."""
        high_risk_trade = TradeProposal(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=150.0,
            rationale="High risk trade",
            risk_level="HIGH"
        )
        
        result = validate_trade_execution_request(high_risk_trade)
        
        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert any("risk" in warning.lower() for warning in result["warnings"])
    
    def test_validate_low_confidence_warning(self):
        """Test validation generates warning for low confidence trades."""
        low_confidence_trade = TradeProposal(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=150.0,
            rationale="Low confidence trade",
            technical_confidence=0.3,
            fundamental_score=40.0
        )
        
        result = validate_trade_execution_request(low_confidence_trade)
        
        assert result["valid"] is True
        assert len(result["warnings"]) >= 2  # Both technical and fundamental warnings


class TestExecutionResultAnalysis:
    """Test execution result analysis."""
    
    @pytest.fixture
    def sample_trade_proposal(self):
        """Create sample trade proposal."""
        return TradeProposal(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=150.0,
            rationale="Sample trade"
        )
    
    def test_analyze_successful_execution(self, sample_trade_proposal):
        """Test analysis of successful execution."""
        execution_result = {
            "status": "EXECUTED",
            "trade_id": "test-123",
            "ticker": "AAPL",
            "action": "BUY",
            "quantity": 50,
            "price": 149.50,  # Close to estimated price
            "total_value": 7475.0,
            "fees": 1.0,
            "timestamp": "2024-01-01T10:00:00Z"
        }
        
        analysis = analyze_execution_result(execution_result, sample_trade_proposal)
        
        assert analysis["execution_status"] == ExecutionResult.SUCCESS
        assert analysis["success"] is True
        assert analysis["trade_id"] == "test-123"
        assert analysis["executed_quantity"] == 50
        assert analysis["executed_price"] == 149.50
        assert analysis["slippage"] == 0.50
        assert analysis["slippage_pct"] < 1.0  # Less than 1% slippage
    
    def test_analyze_failed_execution(self, sample_trade_proposal):
        """Test analysis of failed execution."""
        execution_result = {
            "status": "FAILED",
            "error_message": "Insufficient funds",
            "trade_id": None,
            "ticker": "AAPL",
            "action": "BUY",
            "quantity": 0,
            "price": 0.0,
            "total_value": 0.0,
            "fees": 0.0
        }
        
        analysis = analyze_execution_result(execution_result, sample_trade_proposal)
        
        assert analysis["execution_status"] == ExecutionResult.FAILED
        assert analysis["success"] is False
        assert "Insufficient funds" in analysis["message"]
        assert analysis["trade_id"] is None
        assert analysis["executed_quantity"] == 0
    
    def test_analyze_execution_with_high_slippage(self, sample_trade_proposal):
        """Test analysis of execution with high price slippage."""
        execution_result = {
            "status": "EXECUTED",
            "trade_id": "test-456",
            "ticker": "AAPL",
            "action": "BUY",
            "quantity": 50,
            "price": 160.0,  # 6.7% higher than estimated 150.0
            "total_value": 8000.0,
            "fees": 1.0,
            "timestamp": "2024-01-01T10:00:00Z"
        }
        
        analysis = analyze_execution_result(execution_result, sample_trade_proposal)
        
        assert analysis["execution_status"] == ExecutionResult.PARTIAL
        assert analysis["success"] is True  # Still successful but with slippage
        assert "deviated" in analysis["message"]
        assert analysis["slippage"] == 10.0
        assert analysis["slippage_pct"] > 5.0  # More than 5% slippage
    
    def test_analyze_rejected_execution(self, sample_trade_proposal):
        """Test analysis of rejected execution."""
        execution_result = {
            "status": "REJECTED",
            "trade_id": None,
            "ticker": "AAPL",
            "action": "BUY",
            "quantity": 0,
            "price": 0.0,
            "total_value": 0.0,
            "fees": 0.0
        }
        
        analysis = analyze_execution_result(execution_result, sample_trade_proposal)
        
        assert analysis["execution_status"] == ExecutionResult.REJECTED
        assert analysis["success"] is False
        assert "rejected" in analysis["message"].lower()


class TestTradeExecutionIntegration:
    """Test integrated trade execution functionality."""
    
    @pytest.fixture
    def sample_trade_proposal(self):
        """Create sample trade proposal."""
        return TradeProposal(
            ticker="MSFT",
            action=TradeAction.BUY,
            quantity=25,
            estimated_price=380.0,
            rationale="Integration test trade",
            fundamental_score=75.0,
            technical_confidence=0.8,
            risk_level="medium"
        )
    
    @pytest.mark.asyncio
    async def test_execute_approved_trade_internal_success(self, sample_trade_proposal):
        """Test successful trade execution."""
        mock_execution_result = {
            "status": "EXECUTED",
            "trade_id": "integration-123",
            "ticker": "MSFT",
            "action": "BUY",
            "quantity": 25,
            "price": 378.50,
            "total_value": 9462.50,
            "fees": 1.0,
            "timestamp": "2024-01-01T10:00:00Z"
        }
        
        with patch('MCP_A2A.agents.trade_executor_agent.execute_trade_via_mcp') as mock_execute:
            mock_execute.return_value = mock_execution_result
            
            result = await execute_approved_trade_internal(sample_trade_proposal)
            
            assert result["execution_status"] == ExecutionResult.SUCCESS
            assert result["success"] is True
            assert result["trade_id"] == "integration-123"
            assert result["executed_quantity"] == 25
            assert result["executed_price"] == 378.50
    
    @pytest.mark.asyncio
    async def test_execute_approved_trade_internal_validation_failure(self):
        """Test trade execution with validation failure."""
        invalid_trade = TradeProposal(
            ticker="",  # Invalid ticker
            action=TradeAction.BUY,
            quantity=0,  # Invalid quantity
            estimated_price=0.0,  # Invalid price
            rationale="Invalid trade"
        )
        
        result = await execute_approved_trade_internal(invalid_trade)
        
        assert result["execution_status"] == ExecutionResult.REJECTED
        assert result["success"] is False
        assert "Validation failed" in result["message"]
        assert "validation_errors" in result
        assert len(result["validation_errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_execute_approved_trade_internal_mcp_failure(self, sample_trade_proposal):
        """Test trade execution with MCP failure."""
        with patch('MCP_A2A.agents.trade_executor_agent.execute_trade_via_mcp') as mock_execute:
            mock_execute.side_effect = Exception("MCP connection failed")
            
            result = await execute_approved_trade_internal(sample_trade_proposal)
            
            assert result["execution_status"] == ExecutionResult.FAILED
            assert result["success"] is False
            assert "system error" in result["message"].lower()
            assert "system_error" in result
    
    @pytest.mark.asyncio
    async def test_execute_approved_trade_a2a_method(self):
        """Test A2A method for trade execution."""
        mock_result = {
            "execution_status": ExecutionResult.SUCCESS,
            "success": True,
            "message": "Trade executed successfully",
            "trade_id": "a2a-test-123",
            "executed_quantity": 10,
            "executed_price": 175.0
        }
        
        with patch('MCP_A2A.agents.trade_executor_agent.execute_approved_trade_internal') as mock_internal:
            mock_internal.return_value = mock_result
            
            result = await execute_approved_trade(
                ticker="AAPL",
                action="BUY",
                quantity=10,
                estimated_price=175.0,
                rationale="A2A test trade"
            )
            
            assert result["success"] is True
            assert result["trade_id"] == "a2a-test-123"
            assert result["executed_quantity"] == 10
    
    @pytest.mark.asyncio
    async def test_get_execution_status_found(self):
        """Test getting execution status for existing trade."""
        mock_trade_history = {
            "trades": [
                {
                    "trade_id": "status-test-123",
                    "status": "EXECUTED",
                    "ticker": "AAPL",
                    "action": "BUY",
                    "quantity": 50,
                    "price": 150.0,
                    "total_value": 7500.0,
                    "timestamp": "2024-01-01T10:00:00Z",
                    "fees": 1.0
                }
            ]
        }
        
        with patch('MCP_A2A.agents.trade_executor_agent.http_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_trade_history
            mock_client.get.return_value = mock_response
            
            from ..agents.trade_executor_agent import get_execution_status
            result = await get_execution_status("status-test-123")
            
            assert result["found"] is True
            assert result["trade_id"] == "status-test-123"
            assert result["status"] == "EXECUTED"
            assert result["ticker"] == "AAPL"
    
    @pytest.mark.asyncio
    async def test_get_execution_status_not_found(self):
        """Test getting execution status for non-existent trade."""
        mock_trade_history = {"trades": []}
        
        with patch('MCP_A2A.agents.trade_executor_agent.http_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_trade_history
            mock_client.get.return_value = mock_response
            
            from ..agents.trade_executor_agent import get_execution_status
            result = await get_execution_status("nonexistent-123")
            
            assert result["found"] is False
            assert result["trade_id"] == "nonexistent-123"
            assert "not found" in result["message"].lower()
"""
Unit tests for TradingExecution MCP Server.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from ..mcp_servers.trading_execution_server import (
    app, portfolio, validate_trade, execute_trade_internal, 
    get_simulated_price, calculate_trade_fees
)
from ..models.trading_models import TradeAction, Portfolio
from ..config import TRADING_CONFIG


class TestTradingExecutionServer:
    """Test TradingExecution MCP Server functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture(autouse=True)
    def reset_portfolio(self):
        """Reset portfolio before each test."""
        global portfolio
        portfolio.cash_balance = TRADING_CONFIG["initial_cash"]
        portfolio.positions.clear()
        portfolio.trade_history.clear()
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "TradingExecution MCP Server"
        assert data["status"] == "running"
    
    def test_get_portfolio_status_empty(self, client):
        """Test portfolio status with empty portfolio."""
        response = client.get("/mcp/get_portfolio_status")
        assert response.status_code == 200
        data = response.json()
        assert data["cash_balance"] == TRADING_CONFIG["initial_cash"]
        assert data["positions"] == []
        assert data["total_equity_value"] == 0.0
        assert data["number_of_positions"] == 0
    
    def test_execute_buy_trade_success(self, client):
        """Test successful buy trade execution."""
        with patch('MCP_A2A.mcp_servers.trading_execution_server.get_simulated_price', return_value=100.0):
            response = client.post(
                "/mcp/execute_mock_trade",
                json={
                    "ticker": "AAPL",
                    "action": "BUY",
                    "quantity": 10,
                    "trade_type": "MARKET"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "EXECUTED"
            assert data["ticker"] == "AAPL"
            assert data["action"] == "BUY"
            assert data["quantity"] == 10
            assert data["price"] == 100.0
            assert data["total_value"] == 1000.0
            assert "trade_id" in data
    
    def test_execute_sell_trade_success(self, client):
        """Test successful sell trade execution."""
        # First buy some shares
        with patch('MCP_A2A.mcp_servers.trading_execution_server.get_simulated_price', return_value=100.0):
            client.post(
                "/mcp/execute_mock_trade",
                json={
                    "ticker": "AAPL",
                    "action": "BUY",
                    "quantity": 20,
                    "trade_type": "MARKET"
                }
            )
            
            # Then sell some shares
            response = client.post(
                "/mcp/execute_mock_trade",
                json={
                    "ticker": "AAPL",
                    "action": "SELL",
                    "quantity": 10,
                    "trade_type": "MARKET"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "EXECUTED"
            assert data["action"] == "SELL"
            assert data["quantity"] == 10
    
    def test_execute_buy_insufficient_cash(self, client):
        """Test buy trade with insufficient cash."""
        with patch('MCP_A2A.mcp_servers.trading_execution_server.get_simulated_price', return_value=100000.0):
            response = client.post(
                "/mcp/execute_mock_trade",
                json={
                    "ticker": "EXPENSIVE",
                    "action": "BUY",
                    "quantity": 10,
                    "trade_type": "MARKET"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "FAILED"
            assert "Insufficient cash" in data["error_message"]
    
    def test_execute_sell_no_position(self, client):
        """Test sell trade with no existing position."""
        response = client.post(
            "/mcp/execute_mock_trade",
            json={
                "ticker": "NONEXISTENT",
                "action": "SELL",
                "quantity": 10,
                "trade_type": "MARKET"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FAILED"
        assert "No position" in data["error_message"]
    
    def test_execute_sell_insufficient_shares(self, client):
        """Test sell trade with insufficient shares."""
        # Buy 5 shares
        with patch('MCP_A2A.mcp_servers.trading_execution_server.get_simulated_price', return_value=100.0):
            client.post(
                "/mcp/execute_mock_trade",
                json={
                    "ticker": "AAPL",
                    "action": "BUY",
                    "quantity": 5,
                    "trade_type": "MARKET"
                }
            )
            
            # Try to sell 10 shares
            response = client.post(
                "/mcp/execute_mock_trade",
                json={
                    "ticker": "AAPL",
                    "action": "SELL",
                    "quantity": 10,
                    "trade_type": "MARKET"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "FAILED"
            assert "Insufficient shares" in data["error_message"]
    
    def test_portfolio_status_with_positions(self, client):
        """Test portfolio status after executing trades."""
        with patch('MCP_A2A.mcp_servers.trading_execution_server.get_simulated_price', return_value=100.0):
            # Execute a buy trade
            client.post(
                "/mcp/execute_mock_trade",
                json={
                    "ticker": "AAPL",
                    "action": "BUY",
                    "quantity": 10,
                    "trade_type": "MARKET"
                }
            )
            
            response = client.get("/mcp/get_portfolio_status")
            assert response.status_code == 200
            data = response.json()
            
            assert data["number_of_positions"] == 1
            assert len(data["positions"]) == 1
            assert data["positions"][0]["ticker"] == "AAPL"
            assert data["positions"][0]["quantity"] == 10
            assert data["cash_balance"] < TRADING_CONFIG["initial_cash"]  # Cash reduced by trade
    
    def test_get_trade_history(self, client):
        """Test trade history retrieval."""
        with patch('MCP_A2A.mcp_servers.trading_execution_server.get_simulated_price', return_value=100.0):
            # Execute some trades
            client.post(
                "/mcp/execute_mock_trade",
                json={
                    "ticker": "AAPL",
                    "action": "BUY",
                    "quantity": 10,
                    "trade_type": "MARKET"
                }
            )
            
            response = client.get("/mcp/get_trade_history")
            assert response.status_code == 200
            data = response.json()
            
            assert "trades" in data
            assert "total_trades" in data
            assert data["total_trades"] == 1
            assert len(data["trades"]) == 1
            assert data["trades"][0]["ticker"] == "AAPL"
    
    def test_update_market_prices(self, client):
        """Test market price updates."""
        response = client.post(
            "/mcp/update_market_prices",
            json={
                "prices": {
                    "AAPL": 150.0,
                    "GOOGL": 120.0
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "AAPL" in data["updated_tickers"]
        assert "GOOGL" in data["updated_tickers"]
    
    def test_reset_portfolio(self, client):
        """Test portfolio reset functionality."""
        # First execute a trade
        with patch('MCP_A2A.mcp_servers.trading_execution_server.get_simulated_price', return_value=100.0):
            client.post(
                "/mcp/execute_mock_trade",
                json={
                    "ticker": "AAPL",
                    "action": "BUY",
                    "quantity": 10,
                    "trade_type": "MARKET"
                }
            )
        
        # Reset portfolio
        response = client.post("/mcp/reset_portfolio")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify portfolio is reset
        status_response = client.get("/mcp/get_portfolio_status")
        status_data = status_response.json()
        assert status_data["cash_balance"] == TRADING_CONFIG["initial_cash"]
        assert status_data["number_of_positions"] == 0
    
    def test_get_risk_metrics_empty_portfolio(self, client):
        """Test risk metrics with empty portfolio."""
        response = client.get("/mcp/get_risk_metrics")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_portfolio_value" in data
        assert "cash_percentage" in data
        assert "risk_violations" in data
        assert "risk_compliance" in data
        assert data["number_of_positions"] == 0
    
    def test_get_risk_metrics_with_positions(self, client):
        """Test risk metrics with positions."""
        with patch('MCP_A2A.mcp_servers.trading_execution_server.get_simulated_price', return_value=100.0):
            # Execute a trade
            client.post(
                "/mcp/execute_mock_trade",
                json={
                    "ticker": "AAPL",
                    "action": "BUY",
                    "quantity": 100,
                    "trade_type": "MARKET"
                }
            )
            
            response = client.get("/mcp/get_risk_metrics")
            assert response.status_code == 200
            data = response.json()
            
            assert data["number_of_positions"] == 1
            assert "AAPL" in data["position_concentrations"]
            assert data["largest_position_percentage"] > 0


class TestTradingLogic:
    """Test core trading logic functions."""
    
    @pytest.fixture(autouse=True)
    def reset_portfolio(self):
        """Reset portfolio before each test."""
        global portfolio
        portfolio.cash_balance = TRADING_CONFIG["initial_cash"]
        portfolio.positions.clear()
        portfolio.trade_history.clear()
    
    def test_get_simulated_price(self):
        """Test simulated price generation."""
        price = get_simulated_price("AAPL")
        assert price > 0
        assert isinstance(price, float)
        
        # Test unknown ticker
        unknown_price = get_simulated_price("UNKNOWN")
        assert unknown_price > 0
    
    def test_calculate_trade_fees(self):
        """Test trade fee calculation."""
        fees = calculate_trade_fees(1000.0)
        assert fees == 1.0  # Flat $1 fee
        
        fees = calculate_trade_fees(10000.0)
        assert fees == 1.0  # Still flat $1 fee
    
    def test_validate_buy_trade_success(self):
        """Test successful buy trade validation."""
        from ..mcp_servers.trading_execution_server import TradeRequest
        
        request = TradeRequest(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=10,
            trade_type="MARKET"
        )
        
        with patch('MCP_A2A.mcp_servers.trading_execution_server.get_simulated_price', return_value=100.0):
            result = validate_trade(request)
            assert result["valid"] is True
            assert len(result["errors"]) == 0
            assert result["current_price"] == 100.0
            assert result["trade_value"] == 1000.0
    
    def test_validate_buy_trade_insufficient_cash(self):
        """Test buy trade validation with insufficient cash."""
        from ..mcp_servers.trading_execution_server import TradeRequest
        
        request = TradeRequest(
            ticker="EXPENSIVE",
            action=TradeAction.BUY,
            quantity=10,
            trade_type="MARKET"
        )
        
        with patch('MCP_A2A.mcp_servers.trading_execution_server.get_simulated_price', return_value=50000.0):
            result = validate_trade(request)
            assert result["valid"] is False
            assert any("Insufficient cash" in error for error in result["errors"])
    
    def test_validate_sell_trade_no_position(self):
        """Test sell trade validation with no position."""
        from ..mcp_servers.trading_execution_server import TradeRequest
        
        request = TradeRequest(
            ticker="NONEXISTENT",
            action=TradeAction.SELL,
            quantity=10,
            trade_type="MARKET"
        )
        
        result = validate_trade(request)
        assert result["valid"] is False
        assert any("No position" in error for error in result["errors"])
    
    def test_execute_buy_trade_internal(self):
        """Test internal buy trade execution."""
        from ..mcp_servers.trading_execution_server import TradeRequest
        
        request = TradeRequest(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=10,
            trade_type="MARKET"
        )
        
        validation_result = {
            "current_price": 100.0,
            "trade_value": 1000.0,
            "fees": 1.0
        }
        
        initial_cash = portfolio.cash_balance
        trade = execute_trade_internal(request, validation_result)
        
        assert trade.ticker == "AAPL"
        assert trade.action == TradeAction.BUY
        assert trade.quantity == 10
        assert trade.price == 100.0
        
        # Check portfolio updates
        assert portfolio.cash_balance == initial_cash - 1001.0  # 1000 + 1 fee
        assert "AAPL" in portfolio.positions
        assert portfolio.positions["AAPL"].quantity == 10
    
    def test_execute_sell_trade_internal(self):
        """Test internal sell trade execution."""
        from ..mcp_servers.trading_execution_server import TradeRequest
        from ..models.trading_models import Position
        
        # Set up existing position
        portfolio.positions["AAPL"] = Position(
            ticker="AAPL",
            quantity=20,
            avg_cost=90.0,
            current_price=100.0
        )
        
        request = TradeRequest(
            ticker="AAPL",
            action=TradeAction.SELL,
            quantity=10,
            trade_type="MARKET"
        )
        
        validation_result = {
            "current_price": 100.0,
            "trade_value": 1000.0,
            "fees": 1.0
        }
        
        initial_cash = portfolio.cash_balance
        trade = execute_trade_internal(request, validation_result)
        
        assert trade.action == TradeAction.SELL
        assert trade.quantity == 10
        
        # Check portfolio updates
        assert portfolio.cash_balance == initial_cash + 999.0  # 1000 - 1 fee
        assert portfolio.positions["AAPL"].quantity == 10  # 20 - 10
    
    def test_position_averaging(self):
        """Test position cost averaging on multiple buys."""
        from ..mcp_servers.trading_execution_server import TradeRequest
        
        # First buy
        request1 = TradeRequest(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=10,
            trade_type="MARKET"
        )
        
        validation_result1 = {
            "current_price": 100.0,
            "trade_value": 1000.0,
            "fees": 1.0
        }
        
        execute_trade_internal(request1, validation_result1)
        
        # Second buy at different price
        request2 = TradeRequest(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=10,
            trade_type="MARKET"
        )
        
        validation_result2 = {
            "current_price": 120.0,
            "trade_value": 1200.0,
            "fees": 1.0
        }
        
        execute_trade_internal(request2, validation_result2)
        
        # Check averaged cost
        position = portfolio.positions["AAPL"]
        assert position.quantity == 20
        expected_avg_cost = (1000.0 + 1200.0) / 20  # 110.0
        assert abs(position.avg_cost - expected_avg_cost) < 0.01
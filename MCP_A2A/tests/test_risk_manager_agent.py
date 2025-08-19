"""
Unit tests for RiskManager Agent.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from ..agents.risk_manager_agent import (
    app, evaluate_position_size_risk, evaluate_cash_reserve_risk,
    evaluate_diversification_risk, evaluate_trade_quality_risk,
    evaluate_trade_proposal_internal, evaluate_trade_proposal, RiskDecision
)
from ..models.trading_models import TradeProposal, TradeAction


class TestRiskManagerAgent:
    """Test RiskManager Agent functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "RiskManager Agent"
        assert data["status"] == "running"
    
    def test_get_risk_limits(self, client):
        """Test risk limits endpoint."""
        response = client.get("/risk_limits")
        assert response.status_code == 200
        data = response.json()
        
        assert "position_limits" in data
        assert "cash_limits" in data
        assert "diversification_limits" in data
        assert "quality_limits" in data
        
        assert "max_position_size_pct" in data["position_limits"]
        assert "min_cash_reserve_pct" in data["cash_limits"]
    
    @pytest.mark.asyncio
    async def test_a2a_endpoint_evaluate_trade_proposal(self, client):
        """Test A2A endpoint for trade proposal evaluation."""
        with patch('MCP_A2A.agents.risk_manager_agent.evaluate_trade_proposal') as mock_evaluate:
            mock_evaluate.return_value = {
                "decision": "APPROVE",
                "rationale": "Trade approved",
                "violations": [],
                "warnings": []
            }
            
            response = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "evaluate_trade_proposal",
                    "params": {
                        "ticker": "AAPL",
                        "action": "BUY",
                        "quantity": 10,
                        "estimated_price": 150.0,
                        "rationale": "Strong fundamentals"
                    },
                    "id": "test-123"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == "test-123"
            assert "result" in data
            assert data["result"]["decision"] == "APPROVE"


class TestPositionSizeRisk:
    """Test position size risk evaluation."""
    
    @pytest.fixture
    def sample_portfolio(self):
        """Create sample portfolio status."""
        return {
            "total_portfolio_value": 100000.0,
            "cash_balance": 20000.0,
            "positions": [
                {
                    "ticker": "AAPL",
                    "quantity": 50,
                    "current_value": 7500.0
                },
                {
                    "ticker": "GOOGL",
                    "quantity": 20,
                    "current_value": 5000.0
                }
            ]
        }
    
    @pytest.fixture
    def buy_trade_proposal(self):
        """Create sample buy trade proposal."""
        return TradeProposal(
            ticker="MSFT",
            action=TradeAction.BUY,
            quantity=25,
            estimated_price=400.0,  # $10,000 trade
            rationale="Strong technical signals"
        )
    
    def test_position_size_within_limits(self, buy_trade_proposal, sample_portfolio):
        """Test position size evaluation within limits."""
        result = evaluate_position_size_risk(buy_trade_proposal, sample_portfolio)
        
        assert result["passed"] is True
        assert len(result["violations"]) == 0
        assert "trade_value" in result["metrics"]
        assert result["metrics"]["trade_value"] == 10000.0
    
    def test_position_size_exceeds_single_trade_limit(self, sample_portfolio):
        """Test position size exceeding single trade limit."""
        large_trade = TradeProposal(
            ticker="EXPENSIVE",
            action=TradeAction.BUY,
            quantity=100,
            estimated_price=200.0,  # $20,000 trade (exceeds $10,000 limit)
            rationale="Large position"
        )
        
        result = evaluate_position_size_risk(large_trade, sample_portfolio)
        
        assert result["passed"] is False
        assert len(result["violations"]) > 0
        assert "exceeds maximum single trade limit" in result["violations"][0]
    
    def test_position_size_exceeds_portfolio_percentage(self, sample_portfolio):
        """Test position size exceeding portfolio percentage limit."""
        # Create trade that would be >10% of portfolio
        large_percentage_trade = TradeProposal(
            ticker="NEWSTOCK",
            action=TradeAction.BUY,
            quantity=30,
            estimated_price=400.0,  # $12,000 = 12% of $100,000 portfolio
            rationale="Large percentage position"
        )
        
        result = evaluate_position_size_risk(large_percentage_trade, sample_portfolio)
        
        assert result["passed"] is False
        assert len(result["violations"]) > 0
        assert "exceeding maximum" in result["violations"][0]
    
    def test_position_size_adding_to_existing_position(self, sample_portfolio):
        """Test position size when adding to existing position."""
        # Add to existing AAPL position (currently $7,500)
        add_to_position = TradeProposal(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=20,
            estimated_price=150.0,  # $3,000 more, total would be $10,500 = 10.5%
            rationale="Adding to position"
        )
        
        result = evaluate_position_size_risk(add_to_position, sample_portfolio)
        
        assert result["passed"] is False
        assert len(result["violations"]) > 0
        assert "Total position in AAPL" in result["violations"][0]
    
    def test_position_size_approaching_limit_warning(self, sample_portfolio):
        """Test position size approaching limit generates warning."""
        # Trade that approaches but doesn't exceed limit (8% of portfolio)
        approaching_limit = TradeProposal(
            ticker="NEWSTOCK",
            action=TradeAction.BUY,
            quantity=20,
            estimated_price=400.0,  # $8,000 = 8% of portfolio
            rationale="Approaching limit"
        )
        
        result = evaluate_position_size_risk(approaching_limit, sample_portfolio)
        
        assert result["passed"] is True
        assert len(result["violations"]) == 0
        assert len(result["warnings"]) > 0
        assert "approaching maximum" in result["warnings"][0]
    
    def test_position_size_sell_order(self, sample_portfolio):
        """Test position size evaluation for sell orders."""
        sell_trade = TradeProposal(
            ticker="AAPL",
            action=TradeAction.SELL,
            quantity=25,
            estimated_price=150.0,
            rationale="Taking profits"
        )
        
        result = evaluate_position_size_risk(sell_trade, sample_portfolio)
        
        # Sell orders don't increase position size, so should pass
        assert result["passed"] is True
        assert len(result["violations"]) == 0


class TestCashReserveRisk:
    """Test cash reserve risk evaluation."""
    
    @pytest.fixture
    def sample_portfolio(self):
        """Create sample portfolio status."""
        return {
            "total_portfolio_value": 100000.0,
            "cash_balance": 25000.0,  # 25% cash
            "positions": []
        }
    
    def test_cash_reserve_sufficient(self, sample_portfolio):
        """Test cash reserve evaluation with sufficient cash."""
        buy_trade = TradeProposal(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=150.0,  # $7,500 trade
            rationale="Good opportunity"
        )
        
        result = evaluate_cash_reserve_risk(buy_trade, sample_portfolio)
        
        assert result["passed"] is True
        assert len(result["violations"]) == 0
        assert result["metrics"]["remaining_cash_pct"] > 20  # Above minimum
    
    def test_cash_reserve_insufficient_cash(self, sample_portfolio):
        """Test cash reserve evaluation with insufficient cash."""
        large_trade = TradeProposal(
            ticker="EXPENSIVE",
            action=TradeAction.BUY,
            quantity=200,
            estimated_price=150.0,  # $30,000 trade (more than $25,000 cash)
            rationale="Too expensive"
        )
        
        result = evaluate_cash_reserve_risk(large_trade, sample_portfolio)
        
        assert result["passed"] is False
        assert len(result["violations"]) > 0
        assert "Insufficient cash" in result["violations"][0]
    
    def test_cash_reserve_below_minimum(self, sample_portfolio):
        """Test cash reserve falling below minimum."""
        # Trade that would leave less than 20% cash
        trade_leaving_low_cash = TradeProposal(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=100,
            estimated_price=150.0,  # $15,000 trade, leaving $10,000 = 10% cash
            rationale="Leaves low cash"
        )
        
        result = evaluate_cash_reserve_risk(trade_leaving_low_cash, sample_portfolio)
        
        assert result["passed"] is False
        assert len(result["violations"]) > 0
        assert "below minimum reserve" in result["violations"][0]
    
    def test_cash_reserve_approaching_minimum_warning(self, sample_portfolio):
        """Test cash reserve approaching minimum generates warning."""
        # Trade that approaches but doesn't violate minimum (leaves 25% cash)
        approaching_minimum = TradeProposal(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=100.0,  # $5,000 trade, leaving $20,000 = 20% cash
            rationale="Approaching minimum"
        )
        
        result = evaluate_cash_reserve_risk(approaching_minimum, sample_portfolio)
        
        assert result["passed"] is True
        assert len(result["violations"]) == 0
        # Should generate warning as it's at exactly the minimum
    
    def test_cash_reserve_sell_order(self, sample_portfolio):
        """Test cash reserve evaluation for sell orders."""
        sell_trade = TradeProposal(
            ticker="AAPL",
            action=TradeAction.SELL,
            quantity=50,
            estimated_price=150.0,
            rationale="Taking profits"
        )
        
        result = evaluate_cash_reserve_risk(sell_trade, sample_portfolio)
        
        # Sell orders don't affect cash reserves negatively
        assert result["passed"] is True
        assert len(result["violations"]) == 0


class TestDiversificationRisk:
    """Test diversification risk evaluation."""
    
    @pytest.fixture
    def diversified_portfolio(self):
        """Create diversified portfolio status."""
        positions = []
        for i in range(10):
            positions.append({
                "ticker": f"STOCK{i}",
                "quantity": 10,
                "current_value": 5000.0
            })
        
        return {
            "total_portfolio_value": 100000.0,
            "cash_balance": 50000.0,
            "positions": positions
        }
    
    @pytest.fixture
    def over_diversified_portfolio(self):
        """Create over-diversified portfolio status."""
        positions = []
        for i in range(25):  # Exceeds recommended maximum of 20
            positions.append({
                "ticker": f"STOCK{i}",
                "quantity": 10,
                "current_value": 2000.0
            })
        
        return {
            "total_portfolio_value": 100000.0,
            "cash_balance": 50000.0,
            "positions": positions
        }
    
    def test_diversification_within_limits(self, diversified_portfolio):
        """Test diversification evaluation within limits."""
        new_position_trade = TradeProposal(
            ticker="NEWSTOCK",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=100.0,
            rationale="New position"
        )
        
        result = evaluate_diversification_risk(new_position_trade, diversified_portfolio)
        
        assert result["passed"] is True
        assert len(result["violations"]) == 0
    
    def test_diversification_exceeds_position_limit(self, over_diversified_portfolio):
        """Test diversification exceeding position limit."""
        new_position_trade = TradeProposal(
            ticker="ANOTHERSTOCK",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=100.0,
            rationale="Too many positions"
        )
        
        result = evaluate_diversification_risk(new_position_trade, over_diversified_portfolio)
        
        assert result["passed"] is False
        assert len(result["violations"]) > 0
        assert "exceeding recommended maximum" in result["violations"][0]
    
    def test_diversification_adding_to_existing_position(self, diversified_portfolio):
        """Test diversification when adding to existing position."""
        add_to_existing = TradeProposal(
            ticker="STOCK1",  # Existing position
            action=TradeAction.BUY,
            quantity=20,
            estimated_price=100.0,
            rationale="Adding to existing"
        )
        
        result = evaluate_diversification_risk(add_to_existing, diversified_portfolio)
        
        # Adding to existing position doesn't increase position count
        assert result["passed"] is True
        assert len(result["violations"]) == 0


class TestTradeQualityRisk:
    """Test trade quality risk evaluation."""
    
    def test_trade_quality_high_scores(self):
        """Test trade quality with high fundamental and technical scores."""
        high_quality_trade = TradeProposal(
            ticker="QUALITY",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=100.0,
            rationale="High quality trade",
            fundamental_score=85.0,
            technical_confidence=0.8,
            risk_level="low"
        )
        
        result = evaluate_trade_quality_risk(high_quality_trade)
        
        assert result["passed"] is True
        assert len(result["violations"]) == 0
        assert len(result["warnings"]) == 0
    
    def test_trade_quality_low_fundamental_score(self):
        """Test trade quality with low fundamental score."""
        low_fundamental_trade = TradeProposal(
            ticker="LOWFUND",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=100.0,
            rationale="Low fundamental score",
            fundamental_score=20.0,  # Below minimum of 30
            technical_confidence=0.8,
            risk_level="medium"
        )
        
        result = evaluate_trade_quality_risk(low_fundamental_trade)
        
        assert result["passed"] is False
        assert len(result["violations"]) > 0
        assert "too low" in result["violations"][0]
    
    def test_trade_quality_low_technical_confidence(self):
        """Test trade quality with low technical confidence."""
        low_technical_trade = TradeProposal(
            ticker="LOWTECH",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=100.0,
            rationale="Low technical confidence",
            fundamental_score=70.0,
            technical_confidence=0.2,  # Below minimum of 0.3
            risk_level="medium"
        )
        
        result = evaluate_trade_quality_risk(low_technical_trade)
        
        assert result["passed"] is False
        assert len(result["violations"]) > 0
        assert "too low" in result["violations"][0]
    
    def test_trade_quality_high_risk_level(self):
        """Test trade quality with high risk level."""
        high_risk_trade = TradeProposal(
            ticker="RISKY",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=100.0,
            rationale="High risk trade",
            fundamental_score=70.0,
            technical_confidence=0.7,
            risk_level="very high"
        )
        
        result = evaluate_trade_quality_risk(high_risk_trade)
        
        assert result["passed"] is False
        assert len(result["violations"]) > 0
        assert "very high risk" in result["violations"][0]
    
    def test_trade_quality_warnings(self):
        """Test trade quality generating warnings."""
        warning_trade = TradeProposal(
            ticker="WARNING",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=100.0,
            rationale="Warning level trade",
            fundamental_score=45.0,  # Below average but above minimum
            technical_confidence=0.4,  # Below average but above minimum
            risk_level="high"  # High but not very high
        )
        
        result = evaluate_trade_quality_risk(warning_trade)
        
        assert result["passed"] is True  # No violations
        assert len(result["warnings"]) >= 2  # Should have warnings for both scores and risk


class TestIntegratedRiskEvaluation:
    """Test integrated risk evaluation functionality."""
    
    @pytest.mark.asyncio
    async def test_evaluate_trade_proposal_approve(self):
        """Test trade proposal evaluation that should be approved."""
        mock_portfolio = {
            "total_portfolio_value": 100000.0,
            "cash_balance": 50000.0,
            "number_of_positions": 5,
            "positions": []
        }
        
        with patch('MCP_A2A.agents.risk_manager_agent.fetch_portfolio_status') as mock_fetch:
            mock_fetch.return_value = mock_portfolio
            
            result = await evaluate_trade_proposal(
                ticker="AAPL",
                action="BUY",
                quantity=50,
                estimated_price=100.0,
                rationale="Good opportunity",
                fundamental_score=80.0,
                technical_confidence=0.8,
                risk_level="low"
            )
            
            assert result["decision"] == RiskDecision.APPROVE
            assert len(result["violations"]) == 0
    
    @pytest.mark.asyncio
    async def test_evaluate_trade_proposal_deny(self):
        """Test trade proposal evaluation that should be denied."""
        mock_portfolio = {
            "total_portfolio_value": 100000.0,
            "cash_balance": 5000.0,  # Very low cash
            "number_of_positions": 5,
            "positions": []
        }
        
        with patch('MCP_A2A.agents.risk_manager_agent.fetch_portfolio_status') as mock_fetch:
            mock_fetch.return_value = mock_portfolio
            
            result = await evaluate_trade_proposal(
                ticker="EXPENSIVE",
                action="BUY",
                quantity=100,
                estimated_price=100.0,  # $10,000 trade with only $5,000 cash
                rationale="Expensive trade",
                fundamental_score=20.0,  # Low fundamental score
                technical_confidence=0.2,  # Low technical confidence
                risk_level="high"
            )
            
            assert result["decision"] == RiskDecision.DENY
            assert len(result["violations"]) > 0
    
    @pytest.mark.asyncio
    async def test_evaluate_trade_proposal_conditional_approve(self):
        """Test trade proposal evaluation with conditional approval."""
        mock_portfolio = {
            "total_portfolio_value": 100000.0,
            "cash_balance": 25000.0,
            "number_of_positions": 18,  # Approaching limit of 20
            "positions": []
        }
        
        with patch('MCP_A2A.agents.risk_manager_agent.fetch_portfolio_status') as mock_fetch:
            mock_fetch.return_value = mock_portfolio
            
            result = await evaluate_trade_proposal(
                ticker="WARNING",
                action="BUY",
                quantity=50,
                estimated_price=100.0,
                rationale="Warning level trade",
                fundamental_score=45.0,  # Below average
                technical_confidence=0.4,  # Below average
                risk_level="medium"
            )
            
            assert result["decision"] == RiskDecision.CONDITIONAL_APPROVE
            assert len(result["violations"]) == 0
            assert len(result["warnings"]) > 0
    
    @pytest.mark.asyncio
    async def test_evaluate_trade_proposal_portfolio_unavailable(self):
        """Test trade proposal evaluation when portfolio status unavailable."""
        with patch('MCP_A2A.agents.risk_manager_agent.fetch_portfolio_status') as mock_fetch:
            mock_fetch.return_value = None
            
            result = await evaluate_trade_proposal(
                ticker="AAPL",
                action="BUY",
                quantity=50,
                estimated_price=100.0,
                rationale="Portfolio unavailable"
            )
            
            assert result["decision"] == RiskDecision.DENY
            assert "Portfolio status unavailable" in result["violations"]
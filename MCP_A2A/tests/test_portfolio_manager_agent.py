"""
Unit tests for PortfolioManager Agent.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from ..agents.portfolio_manager_agent import (
    app, WorkflowState, perform_fundamental_analysis, perform_technical_analysis,
    create_trade_proposal, evaluate_risk, execute_trade, execute_trading_strategy_internal,
    WorkflowStatus
)
from ..models.trading_models import InvestmentStrategy, TradeAction


class TestPortfolioManagerAgent:
    """Test PortfolioManager Agent functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "PortfolioManager Agent"
        assert data["status"] == "running"
    
    def test_start_strategy_endpoint(self, client):
        """Test start strategy endpoint."""
        with patch('MCP_A2A.agents.portfolio_manager_agent.execute_trading_strategy_internal') as mock_execute:
            mock_execute.return_value = {
                "workflow_id": "test-123",
                "status": "COMPLETED",
                "success": True,
                "selected_ticker": "AAPL"
            }
            
            response = client.post(
                "/start_strategy",
                json={
                    "goal": "Find a good tech stock to buy",
                    "sector_preference": "technology",
                    "max_investment": 10000.0
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["selected_ticker"] == "AAPL"
    
    def test_list_workflows_endpoint(self, client):
        """Test list workflows endpoint."""
        response = client.get("/workflows")
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert "total" in data
        assert isinstance(data["workflows"], list)


class TestWorkflowState:
    """Test WorkflowState functionality."""
    
    @pytest.fixture
    def sample_strategy(self):
        """Create sample investment strategy."""
        return InvestmentStrategy(
            goal="Test investment strategy",
            sector_preference="technology",
            risk_tolerance="medium",
            max_investment=25000.0
        )
    
    def test_workflow_state_creation(self, sample_strategy):
        """Test workflow state creation."""
        workflow = WorkflowState(sample_strategy, "test-workflow-123")
        
        assert workflow.workflow_id == "test-workflow-123"
        assert workflow.strategy == sample_strategy
        assert workflow.status == WorkflowStatus.INITIATED
        assert workflow.selected_ticker is None
        assert len(workflow.errors) == 0
        assert len(workflow.warnings) == 0
        assert len(workflow.audit_trail) == 0
    
    def test_workflow_audit_trail(self, sample_strategy):
        """Test workflow audit trail functionality."""
        workflow = WorkflowState(sample_strategy, "test-workflow-123")
        
        workflow.add_audit_entry("test_stage", "test_action", {"key": "value"})
        
        assert len(workflow.audit_trail) == 1
        entry = workflow.audit_trail[0]
        assert entry["stage"] == "test_stage"
        assert entry["action"] == "test_action"
        assert entry["details"]["key"] == "value"
        assert "timestamp" in entry


class TestFundamentalAnalysis:
    """Test fundamental analysis workflow step."""
    
    @pytest.fixture
    def sample_workflow(self):
        """Create sample workflow."""
        strategy = InvestmentStrategy(
            goal="Test strategy",
            sector_preference="technology"
        )
        return WorkflowState(strategy, "test-123")
    
    @pytest.mark.asyncio
    async def test_perform_fundamental_analysis_success(self, sample_workflow):
        """Test successful fundamental analysis."""
        mock_response = {
            "companies": [
                {
                    "ticker": "AAPL",
                    "score": 85.0,
                    "recommendation": "BUY",
                    "confidence": 0.9
                },
                {
                    "ticker": "GOOGL",
                    "score": 78.0,
                    "recommendation": "BUY",
                    "confidence": 0.8
                }
            ],
            "total_analyzed": 2,
            "top_recommendation": {"ticker": "AAPL"}
        }
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.return_value = mock_response
            
            result = await perform_fundamental_analysis(sample_workflow)
            
            assert result is True
            assert sample_workflow.status == WorkflowStatus.FUNDAMENTAL_ANALYSIS
            assert sample_workflow.selected_ticker == "AAPL"
            assert sample_workflow.fundamental_results == mock_response
            assert len(sample_workflow.audit_trail) >= 2  # started and completed
    
    @pytest.mark.asyncio
    async def test_perform_fundamental_analysis_no_companies(self, sample_workflow):
        """Test fundamental analysis with no companies found."""
        mock_response = {
            "companies": [],
            "total_analyzed": 0
        }
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.return_value = mock_response
            
            result = await perform_fundamental_analysis(sample_workflow)
            
            assert result is False
            assert len(sample_workflow.errors) > 0
            assert "No companies found" in sample_workflow.errors[0]
    
    @pytest.mark.asyncio
    async def test_perform_fundamental_analysis_client_error(self, sample_workflow):
        """Test fundamental analysis with client error."""
        from ..utils.a2a_client import A2AClientError
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.side_effect = A2AClientError("Connection failed")
            
            result = await perform_fundamental_analysis(sample_workflow)
            
            assert result is False
            assert len(sample_workflow.errors) > 0
            assert "Fundamental analysis failed" in sample_workflow.errors[0]


class TestTechnicalAnalysis:
    """Test technical analysis workflow step."""
    
    @pytest.fixture
    def sample_workflow(self):
        """Create sample workflow with selected ticker."""
        strategy = InvestmentStrategy(goal="Test strategy")
        workflow = WorkflowState(strategy, "test-123")
        workflow.selected_ticker = "AAPL"
        return workflow
    
    @pytest.mark.asyncio
    async def test_perform_technical_analysis_success(self, sample_workflow):
        """Test successful technical analysis."""
        mock_response = {
            "ticker": "AAPL",
            "signal": "BUY",
            "confidence": 0.8,
            "rationale": "Strong bullish signals",
            "price_targets": {
                "entry_price": 150.0,
                "target_price": 160.0,
                "stop_loss": 145.0
            }
        }
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.return_value = mock_response
            
            result = await perform_technical_analysis(sample_workflow)
            
            assert result is True
            assert sample_workflow.status == WorkflowStatus.TECHNICAL_ANALYSIS
            assert sample_workflow.technical_results == mock_response
    
    @pytest.mark.asyncio
    async def test_perform_technical_analysis_hold_signal(self, sample_workflow):
        """Test technical analysis with HOLD signal."""
        mock_response = {
            "ticker": "AAPL",
            "signal": "HOLD",
            "confidence": 0.5,
            "rationale": "Mixed signals"
        }
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.return_value = mock_response
            
            result = await perform_technical_analysis(sample_workflow)
            
            assert result is True  # Still continues but with warning
            assert len(sample_workflow.warnings) > 0
            assert "HOLD" in sample_workflow.warnings[0]
    
    @pytest.mark.asyncio
    async def test_perform_technical_analysis_low_confidence(self, sample_workflow):
        """Test technical analysis with low confidence."""
        mock_response = {
            "ticker": "AAPL",
            "signal": "BUY",
            "confidence": 0.3,  # Low confidence
            "rationale": "Weak signals"
        }
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.return_value = mock_response
            
            result = await perform_technical_analysis(sample_workflow)
            
            assert result is True
            assert len(sample_workflow.warnings) > 0
            assert "Low technical confidence" in sample_workflow.warnings[0]


class TestTradeProposalCreation:
    """Test trade proposal creation."""
    
    @pytest.fixture
    def sample_workflow_with_analysis(self):
        """Create workflow with analysis results."""
        strategy = InvestmentStrategy(goal="Test strategy", max_investment=20000.0)
        workflow = WorkflowState(strategy, "test-123")
        workflow.selected_ticker = "AAPL"
        
        # Mock fundamental results
        workflow.fundamental_results = {
            "companies": [
                {
                    "ticker": "AAPL",
                    "score": 85.0,
                    "strengths": ["Strong revenue growth", "Solid balance sheet"],
                    "recommendation": "BUY"
                }
            ]
        }
        
        # Mock technical results
        workflow.technical_results = {
            "signal": "BUY",
            "confidence": 0.8,
            "rationale": "Strong bullish momentum",
            "price_targets": {
                "entry_price": 150.0,
                "target_price": 160.0,
                "stop_loss": 145.0
            }
        }
        
        return workflow
    
    @pytest.mark.asyncio
    async def test_create_trade_proposal(self, sample_workflow_with_analysis):
        """Test trade proposal creation."""
        proposal = await create_trade_proposal(sample_workflow_with_analysis)
        
        assert proposal.ticker == "AAPL"
        assert proposal.action == TradeAction.BUY
        assert proposal.quantity > 0
        assert proposal.estimated_price == 150.0
        assert proposal.fundamental_score == 85.0
        assert proposal.technical_confidence == 0.8
        assert "Strong revenue growth" in proposal.rationale
        assert "Strong bullish momentum" in proposal.rationale
    
    @pytest.mark.asyncio
    async def test_create_trade_proposal_quantity_calculation(self, sample_workflow_with_analysis):
        """Test trade proposal quantity calculation."""
        # Set max investment to $15,000, with entry price of $150
        # Should result in quantity of 100 shares (15000/150)
        sample_workflow_with_analysis.strategy.max_investment = 15000.0
        
        proposal = await create_trade_proposal(sample_workflow_with_analysis)
        
        expected_quantity = int(15000.0 / 150.0)  # 100 shares
        assert proposal.quantity == expected_quantity
        assert proposal.estimated_price == 150.0
    
    @pytest.mark.asyncio
    async def test_create_trade_proposal_risk_level(self, sample_workflow_with_analysis):
        """Test trade proposal risk level determination."""
        # Test low risk (high scores)
        proposal = await create_trade_proposal(sample_workflow_with_analysis)
        assert proposal.risk_level == "low"  # 85 fundamental + 0.8 technical = low risk
        
        # Test high risk (low scores)
        sample_workflow_with_analysis.fundamental_results["companies"][0]["score"] = 40.0
        sample_workflow_with_analysis.technical_results["confidence"] = 0.3
        
        proposal = await create_trade_proposal(sample_workflow_with_analysis)
        assert proposal.risk_level == "high"


class TestRiskEvaluation:
    """Test risk evaluation workflow step."""
    
    @pytest.fixture
    def sample_workflow_with_proposal(self):
        """Create workflow with trade proposal."""
        strategy = InvestmentStrategy(goal="Test strategy")
        workflow = WorkflowState(strategy, "test-123")
        workflow.selected_ticker = "AAPL"
        
        from ..models.trading_models import TradeProposal
        workflow.trade_proposal = TradeProposal(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=150.0,
            rationale="Test trade"
        )
        
        return workflow
    
    @pytest.mark.asyncio
    async def test_evaluate_risk_approved(self, sample_workflow_with_proposal):
        """Test risk evaluation with approval."""
        mock_response = {
            "decision": "APPROVE",
            "rationale": "Trade approved - all risk checks passed",
            "violations": [],
            "warnings": []
        }
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.return_value = mock_response
            
            result = await evaluate_risk(sample_workflow_with_proposal)
            
            assert result is True
            assert sample_workflow_with_proposal.status == WorkflowStatus.RISK_EVALUATION
            assert sample_workflow_with_proposal.risk_evaluation == mock_response
    
    @pytest.mark.asyncio
    async def test_evaluate_risk_conditional_approval(self, sample_workflow_with_proposal):
        """Test risk evaluation with conditional approval."""
        mock_response = {
            "decision": "CONDITIONAL_APPROVE",
            "rationale": "Trade conditionally approved with warnings",
            "violations": [],
            "warnings": ["Position size approaching limit"]
        }
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.return_value = mock_response
            
            result = await evaluate_risk(sample_workflow_with_proposal)
            
            assert result is True
            assert len(sample_workflow_with_proposal.warnings) > 0
            assert "Position size approaching limit" in sample_workflow_with_proposal.warnings
    
    @pytest.mark.asyncio
    async def test_evaluate_risk_denied(self, sample_workflow_with_proposal):
        """Test risk evaluation with denial."""
        mock_response = {
            "decision": "DENY",
            "rationale": "Trade denied due to risk violations",
            "violations": ["Insufficient cash", "Position size too large"],
            "warnings": []
        }
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.return_value = mock_response
            
            result = await evaluate_risk(sample_workflow_with_proposal)
            
            assert result is False
            assert len(sample_workflow_with_proposal.errors) >= 2
            assert "Insufficient cash" in sample_workflow_with_proposal.errors
            assert "Position size too large" in sample_workflow_with_proposal.errors


class TestTradeExecution:
    """Test trade execution workflow step."""
    
    @pytest.fixture
    def sample_workflow_with_proposal(self):
        """Create workflow with trade proposal."""
        strategy = InvestmentStrategy(goal="Test strategy")
        workflow = WorkflowState(strategy, "test-123")
        workflow.selected_ticker = "AAPL"
        
        from ..models.trading_models import TradeProposal
        workflow.trade_proposal = TradeProposal(
            ticker="AAPL",
            action=TradeAction.BUY,
            quantity=50,
            estimated_price=150.0,
            rationale="Test trade"
        )
        
        return workflow
    
    @pytest.mark.asyncio
    async def test_execute_trade_success(self, sample_workflow_with_proposal):
        """Test successful trade execution."""
        mock_response = {
            "success": True,
            "execution_status": "SUCCESS",
            "trade_id": "exec-123",
            "executed_price": 149.50,
            "executed_quantity": 50,
            "total_value": 7475.0,
            "message": "Trade executed successfully"
        }
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.return_value = mock_response
            
            result = await execute_trade(sample_workflow_with_proposal)
            
            assert result is True
            assert sample_workflow_with_proposal.status == WorkflowStatus.TRADE_EXECUTION
            assert sample_workflow_with_proposal.execution_results == mock_response
    
    @pytest.mark.asyncio
    async def test_execute_trade_failure(self, sample_workflow_with_proposal):
        """Test failed trade execution."""
        mock_response = {
            "success": False,
            "execution_status": "FAILED",
            "trade_id": None,
            "message": "Insufficient funds for trade execution"
        }
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.return_value = mock_response
            
            result = await execute_trade(sample_workflow_with_proposal)
            
            assert result is False
            assert len(sample_workflow_with_proposal.errors) > 0
            assert "Insufficient funds" in sample_workflow_with_proposal.errors[0]


class TestCompleteWorkflow:
    """Test complete workflow integration."""
    
    @pytest.mark.asyncio
    async def test_execute_trading_strategy_internal_success(self):
        """Test successful complete workflow execution."""
        strategy = InvestmentStrategy(
            goal="Find a good tech stock to buy",
            sector_preference="technology",
            max_investment=10000.0
        )
        
        # Mock all agent responses
        fundamental_response = {
            "companies": [{"ticker": "AAPL", "score": 85.0, "strengths": ["Strong growth"]}],
            "total_analyzed": 1
        }
        
        technical_response = {
            "signal": "BUY",
            "confidence": 0.8,
            "price_targets": {"entry_price": 150.0}
        }
        
        risk_response = {
            "decision": "APPROVE",
            "violations": [],
            "warnings": []
        }
        
        execution_response = {
            "success": True,
            "trade_id": "test-123",
            "executed_price": 149.50
        }
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.side_effect = [
                fundamental_response,
                technical_response,
                risk_response,
                execution_response
            ]
            
            result = await execute_trading_strategy_internal(strategy)
            
            assert result["success"] is True
            assert result["status"] == "COMPLETED"
            assert result["selected_ticker"] == "AAPL"
            assert "trade_execution" in result
            assert result["trade_execution"]["success"] is True
    
    @pytest.mark.asyncio
    async def test_execute_trading_strategy_internal_fundamental_failure(self):
        """Test workflow failure at fundamental analysis stage."""
        strategy = InvestmentStrategy(goal="Test strategy")
        
        # Mock fundamental analysis failure
        fundamental_response = {
            "companies": [],  # No companies found
            "total_analyzed": 0
        }
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.return_value = fundamental_response
            
            result = await execute_trading_strategy_internal(strategy)
            
            assert result["success"] is False
            assert result["status"] == "FAILED"
            assert len(result["errors"]) > 0
            assert "No companies found" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_execute_trading_strategy_internal_risk_denial(self):
        """Test workflow failure at risk evaluation stage."""
        strategy = InvestmentStrategy(goal="Test strategy")
        
        # Mock responses up to risk evaluation
        fundamental_response = {
            "companies": [{"ticker": "AAPL", "score": 85.0}],
            "total_analyzed": 1
        }
        
        technical_response = {
            "signal": "BUY",
            "confidence": 0.8,
            "price_targets": {"entry_price": 150.0}
        }
        
        risk_response = {
            "decision": "DENY",
            "violations": ["Insufficient cash"],
            "warnings": []
        }
        
        with patch('MCP_A2A.agents.portfolio_manager_agent.a2a_client') as mock_client:
            mock_client.call_agent.side_effect = [
                fundamental_response,
                technical_response,
                risk_response
            ]
            
            result = await execute_trading_strategy_internal(strategy)
            
            assert result["success"] is False
            assert result["status"] == "FAILED"
            assert "Insufficient cash" in result["errors"]
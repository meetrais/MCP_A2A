"""
PortfolioManagerAgent - The orchestrator and strategic decision-maker.
"""

from typing import Dict, List, Optional
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from enum import Enum

from ..models.trading_models import InvestmentStrategy, TradeProposal, TradeAction
from ..utils.logging_config import setup_logging, get_logger
from ..utils.a2a_server import A2AServer, create_a2a_endpoint
from ..utils.a2a_client import A2AClient, A2AClientError
from ..utils.correlation_id import generate_correlation_id, set_correlation_id
from ..config import PORTS, SERVICE_URLS

# Initialize logging
setup_logging("portfolio_manager_agent")
logger = get_logger(__name__)

app = FastAPI(
    title="PortfolioManager Agent",
    description="Orchestrates trading strategies and coordinates all analyst agents",
    version="1.0.0"
)

# Initialize A2A server and client
a2a_server = A2AServer()
a2a_client = A2AClient()

# Workflow status enum
class WorkflowStatus(str, Enum):
    INITIATED = "INITIATED"
    FUNDAMENTAL_ANALYSIS = "FUNDAMENTAL_ANALYSIS"
    TECHNICAL_ANALYSIS = "TECHNICAL_ANALYSIS"
    RISK_EVALUATION = "RISK_EVALUATION"
    TRADE_EXECUTION = "TRADE_EXECUTION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

# Request models
class StrategyRequest(BaseModel):
    """Request to start a trading strategy."""
    goal: str = Field(..., description="High-level investment goal")
    sector_preference: Optional[str] = Field(None, description="Preferred sector")
    risk_tolerance: str = Field(default="medium", description="Risk tolerance (low/medium/high)")
    max_investment: float = Field(default=50000.0, description="Maximum investment amount")
    time_horizon: str = Field(default="short", description="Investment time horizon")


class WorkflowState:
    """Maintains state for a trading workflow."""
    
    def __init__(self, strategy: InvestmentStrategy, workflow_id: str):
        self.workflow_id = workflow_id
        self.strategy = strategy
        self.status = WorkflowStatus.INITIATED
        self.start_time = datetime.now()
        self.fundamental_results = None
        self.technical_results = None
        self.risk_evaluation = None
        self.execution_results = None
        self.selected_ticker = None
        self.trade_proposal = None
        self.errors = []
        self.warnings = []
        self.audit_trail = []
    
    def add_audit_entry(self, stage: str, action: str, details: Dict = None):
        """Add entry to audit trail."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "action": action,
            "details": details or {}
        }
        self.audit_trail.append(entry)
        logger.info(f"Workflow {self.workflow_id} - {stage}: {action}")


# Global workflow storage (in production, this would be persistent)
active_workflows: Dict[str, WorkflowState] = {}


async def perform_fundamental_analysis(workflow: WorkflowState) -> bool:
    """
    Perform fundamental analysis via FundamentalAnalystAgent.
    
    Args:
        workflow: Current workflow state
        
    Returns:
        True if successful, False otherwise
    """
    try:
        workflow.status = WorkflowStatus.FUNDAMENTAL_ANALYSIS
        workflow.add_audit_entry("fundamental_analysis", "started")
        
        # Call FundamentalAnalystAgent
        fundamental_url = SERVICE_URLS["fundamental_analyst"]
        response = await a2a_client.call_agent(
            fundamental_url,
            "perform_fundamental_analysis",
            sector=workflow.strategy.sector_preference,
            max_companies=5
        )
        
        workflow.fundamental_results = response
        workflow.add_audit_entry("fundamental_analysis", "completed", {
            "companies_analyzed": response.get("total_analyzed", 0),
            "top_recommendation": response.get("top_recommendation", {}).get("ticker") if response.get("top_recommendation") else None
        })
        
        # Select best candidate
        companies = response.get("companies", [])
        if not companies:
            workflow.errors.append("No companies found in fundamental analysis")
            return False
        
        # Select the top-rated company
        best_company = companies[0]  # Already sorted by score
        workflow.selected_ticker = best_company["ticker"]
        
        logger.info(f"Selected ticker {workflow.selected_ticker} for workflow {workflow.workflow_id}")
        return True
        
    except A2AClientError as e:
        error_msg = f"Fundamental analysis failed: {e}"
        workflow.errors.append(error_msg)
        workflow.add_audit_entry("fundamental_analysis", "failed", {"error": str(e)})
        logger.error(error_msg)
        return False
    except Exception as e:
        error_msg = f"Unexpected error in fundamental analysis: {e}"
        workflow.errors.append(error_msg)
        workflow.add_audit_entry("fundamental_analysis", "error", {"error": str(e)})
        logger.error(error_msg)
        return False


async def perform_technical_analysis(workflow: WorkflowState) -> bool:
    """
    Perform technical analysis via TechnicalAnalystAgent.
    
    Args:
        workflow: Current workflow state
        
    Returns:
        True if successful, False otherwise
    """
    try:
        workflow.status = WorkflowStatus.TECHNICAL_ANALYSIS
        workflow.add_audit_entry("technical_analysis", "started", {"ticker": workflow.selected_ticker})
        
        # Call TechnicalAnalystAgent
        technical_url = SERVICE_URLS["technical_analyst"]
        response = await a2a_client.call_agent(
            technical_url,
            "perform_technical_analysis",
            ticker=workflow.selected_ticker,
            indicators=["RSI", "SMA", "EMA", "MACD"],
            lookback_days=50
        )
        
        workflow.technical_results = response
        workflow.add_audit_entry("technical_analysis", "completed", {
            "signal": response.get("signal"),
            "confidence": response.get("confidence"),
            "ticker": workflow.selected_ticker
        })
        
        # Check if we have a tradeable signal
        signal = response.get("signal", "HOLD")
        confidence = response.get("confidence", 0.0)
        
        if signal == "HOLD":
            workflow.warnings.append(f"Technical analysis suggests HOLD for {workflow.selected_ticker}")
            # For demo purposes, we'll continue anyway but note the warning
        
        if confidence < 0.5:
            workflow.warnings.append(f"Low technical confidence: {confidence:.2f}")
        
        logger.info(f"Technical analysis for {workflow.selected_ticker}: {signal} (confidence: {confidence:.2f})")
        return True
        
    except A2AClientError as e:
        error_msg = f"Technical analysis failed: {e}"
        workflow.errors.append(error_msg)
        workflow.add_audit_entry("technical_analysis", "failed", {"error": str(e)})
        logger.error(error_msg)
        return False
    except Exception as e:
        error_msg = f"Unexpected error in technical analysis: {e}"
        workflow.errors.append(error_msg)
        workflow.add_audit_entry("technical_analysis", "error", {"error": str(e)})
        logger.error(error_msg)
        return False


async def create_trade_proposal(workflow: WorkflowState) -> TradeProposal:
    """
    Create trade proposal based on analysis results.
    
    Args:
        workflow: Current workflow state
        
    Returns:
        Trade proposal
    """
    # Get analysis results
    fundamental = workflow.fundamental_results
    technical = workflow.technical_results
    
    # Find the selected company in fundamental results
    selected_company = None
    for company in fundamental.get("companies", []):
        if company["ticker"] == workflow.selected_ticker:
            selected_company = company
            break
    
    # Determine trade parameters
    signal = technical.get("signal", "HOLD")
    action = TradeAction.BUY if signal == "BUY" else TradeAction.SELL if signal == "SELL" else TradeAction.BUY
    
    # Calculate quantity based on max investment and price targets
    price_targets = technical.get("price_targets", {})
    estimated_price = price_targets.get("entry_price", 100.0)  # Default fallback
    
    # Calculate quantity (limit to max investment)
    max_trade_value = min(workflow.strategy.max_investment, 10000.0)  # Also respect single trade limit
    quantity = max(1, int(max_trade_value / estimated_price))
    
    # Create rationale
    fundamental_score = selected_company.get("score", 0) if selected_company else 0
    technical_confidence = technical.get("confidence", 0.0)
    
    rationale_parts = []
    if selected_company:
        rationale_parts.append(f"Fundamental score: {fundamental_score:.1f}")
        if selected_company.get("strengths"):
            rationale_parts.append(f"Strengths: {', '.join(selected_company['strengths'][:2])}")
    
    rationale_parts.append(f"Technical signal: {signal} (confidence: {technical_confidence:.2f})")
    if technical.get("rationale"):
        rationale_parts.append(technical["rationale"])
    
    rationale = "; ".join(rationale_parts)
    
    # Determine risk level
    risk_level = "medium"
    if fundamental_score < 50 or technical_confidence < 0.4:
        risk_level = "high"
    elif fundamental_score > 80 and technical_confidence > 0.8:
        risk_level = "low"
    
    trade_proposal = TradeProposal(
        ticker=workflow.selected_ticker,
        action=action,
        quantity=quantity,
        estimated_price=estimated_price,
        rationale=rationale,
        expected_return=None,  # Could be calculated from price targets
        risk_level=risk_level,
        fundamental_score=fundamental_score,
        technical_confidence=technical_confidence
    )
    
    workflow.trade_proposal = trade_proposal
    workflow.add_audit_entry("trade_proposal", "created", {
        "ticker": trade_proposal.ticker,
        "action": trade_proposal.action.value,
        "quantity": trade_proposal.quantity,
        "estimated_price": trade_proposal.estimated_price,
        "risk_level": trade_proposal.risk_level
    })
    
    return trade_proposal


async def evaluate_risk(workflow: WorkflowState) -> bool:
    """
    Evaluate trade proposal via RiskManagerAgent.
    
    Args:
        workflow: Current workflow state
        
    Returns:
        True if approved, False if denied
    """
    try:
        workflow.status = WorkflowStatus.RISK_EVALUATION
        workflow.add_audit_entry("risk_evaluation", "started")
        
        # Call RiskManagerAgent
        risk_manager_url = SERVICE_URLS["risk_manager"]
        response = await a2a_client.call_agent(
            risk_manager_url,
            "evaluate_trade_proposal",
            ticker=workflow.trade_proposal.ticker,
            action=workflow.trade_proposal.action.value,
            quantity=workflow.trade_proposal.quantity,
            estimated_price=workflow.trade_proposal.estimated_price,
            rationale=workflow.trade_proposal.rationale,
            risk_level=workflow.trade_proposal.risk_level,
            fundamental_score=workflow.trade_proposal.fundamental_score,
            technical_confidence=workflow.trade_proposal.technical_confidence
        )
        
        workflow.risk_evaluation = response
        decision = response.get("decision", "DENY")
        
        workflow.add_audit_entry("risk_evaluation", "completed", {
            "decision": decision,
            "violations": response.get("violations", []),
            "warnings": response.get("warnings", [])
        })
        
        # Add any warnings to workflow
        warnings = response.get("warnings", [])
        workflow.warnings.extend(warnings)
        
        if decision == "APPROVE":
            logger.info(f"Trade approved by risk manager for workflow {workflow.workflow_id}")
            return True
        elif decision == "CONDITIONAL_APPROVE":
            logger.info(f"Trade conditionally approved with warnings for workflow {workflow.workflow_id}")
            return True
        else:
            violations = response.get("violations", [])
            workflow.errors.extend(violations)
            logger.warning(f"Trade denied by risk manager for workflow {workflow.workflow_id}: {violations}")
            return False
        
    except A2AClientError as e:
        error_msg = f"Risk evaluation failed: {e}"
        workflow.errors.append(error_msg)
        workflow.add_audit_entry("risk_evaluation", "failed", {"error": str(e)})
        logger.error(error_msg)
        return False
    except Exception as e:
        error_msg = f"Unexpected error in risk evaluation: {e}"
        workflow.errors.append(error_msg)
        workflow.add_audit_entry("risk_evaluation", "error", {"error": str(e)})
        logger.error(error_msg)
        return False


async def execute_trade(workflow: WorkflowState) -> bool:
    """
    Execute approved trade via TradeExecutorAgent.
    
    Args:
        workflow: Current workflow state
        
    Returns:
        True if successful, False otherwise
    """
    try:
        workflow.status = WorkflowStatus.TRADE_EXECUTION
        workflow.add_audit_entry("trade_execution", "started")
        
        # Call TradeExecutorAgent
        trade_executor_url = SERVICE_URLS["trade_executor"]
        response = await a2a_client.call_agent(
            trade_executor_url,
            "execute_approved_trade",
            ticker=workflow.trade_proposal.ticker,
            action=workflow.trade_proposal.action.value,
            quantity=workflow.trade_proposal.quantity,
            estimated_price=workflow.trade_proposal.estimated_price,
            rationale=workflow.trade_proposal.rationale,
            risk_level=workflow.trade_proposal.risk_level,
            fundamental_score=workflow.trade_proposal.fundamental_score,
            technical_confidence=workflow.trade_proposal.technical_confidence
        )
        
        workflow.execution_results = response
        success = response.get("success", False)
        
        workflow.add_audit_entry("trade_execution", "completed", {
            "success": success,
            "execution_status": response.get("execution_status"),
            "trade_id": response.get("trade_id"),
            "executed_price": response.get("executed_price"),
            "message": response.get("message")
        })
        
        if success:
            logger.info(f"Trade executed successfully for workflow {workflow.workflow_id}: {response.get('message')}")
            return True
        else:
            error_msg = f"Trade execution failed: {response.get('message', 'Unknown error')}"
            workflow.errors.append(error_msg)
            logger.error(error_msg)
            return False
        
    except A2AClientError as e:
        error_msg = f"Trade execution failed: {e}"
        workflow.errors.append(error_msg)
        workflow.add_audit_entry("trade_execution", "failed", {"error": str(e)})
        logger.error(error_msg)
        return False
    except Exception as e:
        error_msg = f"Unexpected error in trade execution: {e}"
        workflow.errors.append(error_msg)
        workflow.add_audit_entry("trade_execution", "error", {"error": str(e)})
        logger.error(error_msg)
        return False


async def execute_trading_strategy_internal(strategy: InvestmentStrategy) -> Dict:
    """
    Execute complete trading strategy workflow.
    
    Args:
        strategy: Investment strategy to execute
        
    Returns:
        Dictionary with workflow results
    """
    # Create workflow
    workflow_id = generate_correlation_id()
    set_correlation_id(workflow_id)
    workflow = WorkflowState(strategy, workflow_id)
    active_workflows[workflow_id] = workflow
    
    logger.info(f"Starting trading strategy workflow {workflow_id}: {strategy.goal}")
    workflow.add_audit_entry("workflow", "started", {"goal": strategy.goal})
    
    try:
        # Step 1: Fundamental Analysis
        if not await perform_fundamental_analysis(workflow):
            workflow.status = WorkflowStatus.FAILED
            workflow.add_audit_entry("workflow", "failed", {"stage": "fundamental_analysis"})
            return create_workflow_result(workflow)
        
        # Step 2: Technical Analysis
        if not await perform_technical_analysis(workflow):
            workflow.status = WorkflowStatus.FAILED
            workflow.add_audit_entry("workflow", "failed", {"stage": "technical_analysis"})
            return create_workflow_result(workflow)
        
        # Step 3: Create Trade Proposal
        await create_trade_proposal(workflow)
        
        # Step 4: Risk Evaluation
        if not await evaluate_risk(workflow):
            workflow.status = WorkflowStatus.FAILED
            workflow.add_audit_entry("workflow", "failed", {"stage": "risk_evaluation"})
            return create_workflow_result(workflow)
        
        # Step 5: Trade Execution
        if not await execute_trade(workflow):
            workflow.status = WorkflowStatus.FAILED
            workflow.add_audit_entry("workflow", "failed", {"stage": "trade_execution"})
            return create_workflow_result(workflow)
        
        # Success!
        workflow.status = WorkflowStatus.COMPLETED
        workflow.add_audit_entry("workflow", "completed")
        logger.info(f"Trading strategy workflow {workflow_id} completed successfully")
        
        return create_workflow_result(workflow)
        
    except Exception as e:
        workflow.status = WorkflowStatus.FAILED
        error_msg = f"Unexpected workflow error: {e}"
        workflow.errors.append(error_msg)
        workflow.add_audit_entry("workflow", "error", {"error": str(e)})
        logger.error(f"Workflow {workflow_id} failed: {e}")
        return create_workflow_result(workflow)


def create_workflow_result(workflow: WorkflowState) -> Dict:
    """
    Create workflow result summary.
    
    Args:
        workflow: Completed workflow state
        
    Returns:
        Dictionary with workflow results
    """
    result = {
        "workflow_id": workflow.workflow_id,
        "status": workflow.status.value,
        "success": workflow.status == WorkflowStatus.COMPLETED,
        "strategy": {
            "goal": workflow.strategy.goal,
            "sector_preference": workflow.strategy.sector_preference,
            "risk_tolerance": workflow.strategy.risk_tolerance.value,
            "max_investment": workflow.strategy.max_investment
        },
        "selected_ticker": workflow.selected_ticker,
        "errors": workflow.errors,
        "warnings": workflow.warnings,
        "execution_time_seconds": (datetime.now() - workflow.start_time).total_seconds()
    }
    
    # Add stage-specific results
    if workflow.fundamental_results:
        result["fundamental_analysis"] = {
            "companies_analyzed": workflow.fundamental_results.get("total_analyzed", 0),
            "top_recommendation": workflow.fundamental_results.get("top_recommendation")
        }
    
    if workflow.technical_results:
        result["technical_analysis"] = {
            "signal": workflow.technical_results.get("signal"),
            "confidence": workflow.technical_results.get("confidence"),
            "rationale": workflow.technical_results.get("rationale")
        }
    
    if workflow.risk_evaluation:
        result["risk_evaluation"] = {
            "decision": workflow.risk_evaluation.get("decision"),
            "violations": workflow.risk_evaluation.get("violations", []),
            "warnings": workflow.risk_evaluation.get("warnings", [])
        }
    
    if workflow.execution_results:
        result["trade_execution"] = {
            "success": workflow.execution_results.get("success"),
            "trade_id": workflow.execution_results.get("trade_id"),
            "executed_price": workflow.execution_results.get("executed_price"),
            "executed_quantity": workflow.execution_results.get("executed_quantity"),
            "total_value": workflow.execution_results.get("total_value"),
            "message": workflow.execution_results.get("message")
        }
    
    if workflow.trade_proposal:
        result["trade_proposal"] = {
            "ticker": workflow.trade_proposal.ticker,
            "action": workflow.trade_proposal.action.value,
            "quantity": workflow.trade_proposal.quantity,
            "estimated_price": workflow.trade_proposal.estimated_price,
            "rationale": workflow.trade_proposal.rationale
        }
    
    result["audit_trail"] = workflow.audit_trail
    
    return result


# A2A method handlers (for potential agent-to-agent communication)
async def get_workflow_status(workflow_id: str) -> Dict:
    """
    Get status of a workflow.
    
    Args:
        workflow_id: Workflow ID to check
        
    Returns:
        Dictionary with workflow status
    """
    if workflow_id not in active_workflows:
        return {
            "found": False,
            "workflow_id": workflow_id,
            "message": "Workflow not found"
        }
    
    workflow = active_workflows[workflow_id]
    return {
        "found": True,
        "workflow_id": workflow_id,
        "status": workflow.status.value,
        "selected_ticker": workflow.selected_ticker,
        "errors": workflow.errors,
        "warnings": workflow.warnings
    }


# Register A2A methods
a2a_server.register_method("get_workflow_status", get_workflow_status)

# FastAPI endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "PortfolioManager Agent", "status": "running", "version": "1.0.0"}


@app.post("/a2a")
async def a2a_endpoint(request: Request):
    """A2A protocol endpoint."""
    return await create_a2a_endpoint(a2a_server)(request)


@app.post("/start_strategy")
async def start_strategy(request: StrategyRequest) -> Dict:
    """
    Start a trading strategy workflow.
    
    Args:
        request: Strategy request
        
    Returns:
        Workflow execution results
    """
    try:
        # Create investment strategy
        strategy = InvestmentStrategy(
            goal=request.goal,
            sector_preference=request.sector_preference,
            risk_tolerance=request.risk_tolerance,
            max_investment=request.max_investment,
            time_horizon=request.time_horizon
        )
        
        # Execute strategy
        result = await execute_trading_strategy_internal(strategy)
        
        return result
        
    except Exception as e:
        logger.error(f"Error starting strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflow/{workflow_id}")
async def get_workflow(workflow_id: str) -> Dict:
    """
    Get workflow status and results.
    
    Args:
        workflow_id: Workflow ID
        
    Returns:
        Workflow information
    """
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = active_workflows[workflow_id]
    return create_workflow_result(workflow)


@app.get("/workflows")
async def list_workflows() -> Dict:
    """
    List all active workflows.
    
    Returns:
        List of workflows
    """
    workflows = []
    for workflow_id, workflow in active_workflows.items():
        workflows.append({
            "workflow_id": workflow_id,
            "status": workflow.status.value,
            "selected_ticker": workflow.selected_ticker,
            "start_time": workflow.start_time.isoformat(),
            "goal": workflow.strategy.goal
        })
    
    return {"workflows": workflows, "total": len(workflows)}


if __name__ == "__main__":
    import uvicorn
    
    port = PORTS["portfolio_manager"]
    logger.info(f"Starting PortfolioManager Agent on port {port}")
    
    uvicorn.run(
        "portfolio_manager_agent:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
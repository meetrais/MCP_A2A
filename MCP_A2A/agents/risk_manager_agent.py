"""
RiskManagerAgent - The safety and compliance officer for trade approval.
"""

from typing import Dict, List, Optional
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from enum import Enum

from ..models.trading_models import TradeProposal, TradeAction
from ..utils.logging_config import setup_logging, get_logger
from ..utils.a2a_server import A2AServer, create_a2a_endpoint
from ..utils.http_client import HTTPClient
from ..config import PORTS, SERVICE_URLS, TRADING_CONFIG

# Initialize logging
setup_logging("risk_manager_agent")
logger = get_logger(__name__)

app = FastAPI(
    title="RiskManager Agent",
    description="Evaluates trade proposals against risk parameters and compliance rules",
    version="1.0.0"
)

# Initialize A2A server and HTTP client
a2a_server = A2AServer()
http_client = HTTPClient()

# Risk decision enum
class RiskDecision(str, Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"
    CONDITIONAL_APPROVE = "CONDITIONAL_APPROVE"

# Request models
class RiskEvaluationRequest(BaseModel):
    """Request for risk evaluation of a trade proposal."""
    trade_proposal: TradeProposal = Field(..., description="Trade proposal to evaluate")
    override_rules: List[str] = Field(default_factory=list, description="Risk rules to override")


async def fetch_portfolio_status() -> Optional[Dict]:
    """
    Fetch current portfolio status from TradingExecutionMCP.
    
    Returns:
        Portfolio status data or None if failed
    """
    try:
        trading_execution_url = SERVICE_URLS["trading_execution_mcp"]
        response = await http_client.get(f"{trading_execution_url}/mcp/get_portfolio_status")
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to fetch portfolio status: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching portfolio status: {e}")
        return None


async def fetch_risk_metrics() -> Optional[Dict]:
    """
    Fetch current portfolio risk metrics from TradingExecutionMCP.
    
    Returns:
        Risk metrics data or None if failed
    """
    try:
        trading_execution_url = SERVICE_URLS["trading_execution_mcp"]
        response = await http_client.get(f"{trading_execution_url}/mcp/get_risk_metrics")
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to fetch risk metrics: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching risk metrics: {e}")
        return None


def evaluate_position_size_risk(
    trade_proposal: TradeProposal,
    portfolio_status: Dict
) -> Dict:
    """
    Evaluate position size risk for the trade proposal.
    
    Args:
        trade_proposal: Trade proposal to evaluate
        portfolio_status: Current portfolio status
        
    Returns:
        Dictionary with position size risk evaluation
    """
    violations = []
    warnings = []
    
    total_portfolio_value = portfolio_status.get("total_portfolio_value", 0)
    if total_portfolio_value <= 0:
        return {
            "passed": False,
            "violations": ["Cannot determine portfolio value for position sizing"],
            "warnings": []
        }
    
    # Calculate trade value
    trade_value = trade_proposal.estimated_price * trade_proposal.quantity
    
    # Check maximum single trade value
    max_trade_value = TRADING_CONFIG["max_single_trade_value"]
    if trade_value > max_trade_value:
        violations.append(
            f"Trade value ${trade_value:,.2f} exceeds maximum single trade limit of ${max_trade_value:,.2f}"
        )
    
    # Check position size as percentage of portfolio
    position_percentage = (trade_value / total_portfolio_value) * 100
    max_position_pct = TRADING_CONFIG["max_position_size_pct"]
    
    if trade_proposal.action == TradeAction.BUY:
        # For buy orders, check if new position would exceed limits
        current_positions = portfolio_status.get("positions", [])
        current_position_value = 0
        
        # Find existing position in the same ticker
        for position in current_positions:
            if position["ticker"] == trade_proposal.ticker:
                current_position_value = position["current_value"]
                break
        
        total_position_value = current_position_value + trade_value
        total_position_percentage = (total_position_value / total_portfolio_value) * 100
        
        if total_position_percentage > max_position_pct:
            violations.append(
                f"Total position in {trade_proposal.ticker} would be {total_position_percentage:.1f}% "
                f"of portfolio, exceeding maximum of {max_position_pct}%"
            )
        elif total_position_percentage > max_position_pct * 0.8:  # 80% of limit
            warnings.append(
                f"Total position in {trade_proposal.ticker} would be {total_position_percentage:.1f}% "
                f"of portfolio, approaching maximum of {max_position_pct}%"
            )
    
    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "metrics": {
            "trade_value": trade_value,
            "position_percentage": position_percentage,
            "max_position_pct": max_position_pct
        }
    }


def evaluate_cash_reserve_risk(
    trade_proposal: TradeProposal,
    portfolio_status: Dict
) -> Dict:
    """
    Evaluate cash reserve risk for the trade proposal.
    
    Args:
        trade_proposal: Trade proposal to evaluate
        portfolio_status: Current portfolio status
        
    Returns:
        Dictionary with cash reserve risk evaluation
    """
    violations = []
    warnings = []
    
    if trade_proposal.action != TradeAction.BUY:
        # Cash reserve only applies to buy orders
        return {"passed": True, "violations": [], "warnings": []}
    
    cash_balance = portfolio_status.get("cash_balance", 0)
    total_portfolio_value = portfolio_status.get("total_portfolio_value", 0)
    
    if total_portfolio_value <= 0:
        return {
            "passed": False,
            "violations": ["Cannot determine portfolio value for cash reserve calculation"],
            "warnings": []
        }
    
    # Calculate trade cost (including estimated fees)
    trade_value = trade_proposal.estimated_price * trade_proposal.quantity
    estimated_fees = 1.0  # Flat $1 fee
    total_cost = trade_value + estimated_fees
    
    # Check if we have enough cash
    if cash_balance < total_cost:
        violations.append(
            f"Insufficient cash: need ${total_cost:,.2f}, have ${cash_balance:,.2f}"
        )
        return {
            "passed": False,
            "violations": violations,
            "warnings": warnings
        }
    
    # Check cash reserve after trade
    remaining_cash = cash_balance - total_cost
    remaining_cash_percentage = (remaining_cash / total_portfolio_value) * 100
    min_cash_pct = TRADING_CONFIG["min_cash_reserve_pct"]
    
    if remaining_cash_percentage < min_cash_pct:
        violations.append(
            f"Trade would leave {remaining_cash_percentage:.1f}% cash, "
            f"below minimum reserve of {min_cash_pct}%"
        )
    elif remaining_cash_percentage < min_cash_pct * 1.5:  # 150% of minimum
        warnings.append(
            f"Trade would leave {remaining_cash_percentage:.1f}% cash, "
            f"approaching minimum reserve of {min_cash_pct}%"
        )
    
    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "metrics": {
            "current_cash": cash_balance,
            "trade_cost": total_cost,
            "remaining_cash": remaining_cash,
            "remaining_cash_pct": remaining_cash_percentage,
            "min_cash_pct": min_cash_pct
        }
    }


def evaluate_diversification_risk(
    trade_proposal: TradeProposal,
    portfolio_status: Dict
) -> Dict:
    """
    Evaluate diversification risk for the trade proposal.
    
    Args:
        trade_proposal: Trade proposal to evaluate
        portfolio_status: Current portfolio status
        
    Returns:
        Dictionary with diversification risk evaluation
    """
    violations = []
    warnings = []
    
    # For this simulation, we'll implement basic sector concentration limits
    # In a real system, this would integrate with sector classification data
    
    positions = portfolio_status.get("positions", [])
    total_portfolio_value = portfolio_status.get("total_portfolio_value", 0)
    
    if total_portfolio_value <= 0:
        return {"passed": True, "violations": [], "warnings": []}
    
    # Count number of positions
    num_positions = len(positions)
    max_positions = 20  # Reasonable limit for diversification
    
    if trade_proposal.action == TradeAction.BUY:
        # Check if this would be a new position
        existing_position = any(pos["ticker"] == trade_proposal.ticker for pos in positions)
        if not existing_position:
            if num_positions >= max_positions:
                violations.append(
                    f"Portfolio already has {num_positions} positions, "
                    f"exceeding recommended maximum of {max_positions}"
                )
            elif num_positions >= max_positions * 0.8:  # 80% of limit
                warnings.append(
                    f"Portfolio has {num_positions} positions, "
                    f"approaching maximum of {max_positions}"
                )
    
    # Check for over-concentration in single positions
    max_single_position_pct = TRADING_CONFIG["max_position_size_pct"]
    for position in positions:
        position_pct = (position["current_value"] / total_portfolio_value) * 100
        if position_pct > max_single_position_pct:
            warnings.append(
                f"Existing position in {position['ticker']} is {position_pct:.1f}% "
                f"of portfolio, exceeding recommended maximum of {max_single_position_pct}%"
            )
    
    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "metrics": {
            "num_positions": num_positions,
            "max_positions": max_positions
        }
    }


def evaluate_trade_quality_risk(trade_proposal: TradeProposal) -> Dict:
    """
    Evaluate trade quality and confidence risk.
    
    Args:
        trade_proposal: Trade proposal to evaluate
        
    Returns:
        Dictionary with trade quality risk evaluation
    """
    violations = []
    warnings = []
    
    # Check fundamental analysis confidence
    if trade_proposal.fundamental_score is not None:
        if trade_proposal.fundamental_score < 30:
            violations.append(
                f"Fundamental score of {trade_proposal.fundamental_score} is too low (minimum 30)"
            )
        elif trade_proposal.fundamental_score < 50:
            warnings.append(
                f"Fundamental score of {trade_proposal.fundamental_score} is below average"
            )
    
    # Check technical analysis confidence
    if trade_proposal.technical_confidence is not None:
        if trade_proposal.technical_confidence < 0.3:
            violations.append(
                f"Technical confidence of {trade_proposal.technical_confidence:.2f} is too low (minimum 0.3)"
            )
        elif trade_proposal.technical_confidence < 0.5:
            warnings.append(
                f"Technical confidence of {trade_proposal.technical_confidence:.2f} is below average"
            )
    
    # Check risk level
    if trade_proposal.risk_level.upper() == "HIGH":
        warnings.append("Trade is classified as high risk")
    elif trade_proposal.risk_level.upper() == "VERY HIGH":
        violations.append("Trade is classified as very high risk")
    
    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "metrics": {
            "fundamental_score": trade_proposal.fundamental_score,
            "technical_confidence": trade_proposal.technical_confidence,
            "risk_level": trade_proposal.risk_level
        }
    }


async def evaluate_trade_proposal_internal(
    trade_proposal: TradeProposal,
    override_rules: List[str] = None
) -> Dict:
    """
    Perform comprehensive risk evaluation of a trade proposal.
    
    Args:
        trade_proposal: Trade proposal to evaluate
        override_rules: List of risk rules to override
        
    Returns:
        Dictionary with complete risk evaluation
    """
    if override_rules is None:
        override_rules = []
    
    logger.info(f"Evaluating trade proposal: {trade_proposal.action} {trade_proposal.quantity} {trade_proposal.ticker}")
    
    try:
        # Fetch current portfolio status
        portfolio_status = await fetch_portfolio_status()
        if not portfolio_status:
            return {
                "decision": RiskDecision.DENY,
                "rationale": "Unable to fetch portfolio status for risk evaluation",
                "violations": ["Portfolio status unavailable"],
                "warnings": [],
                "risk_metrics": {}
            }
        
        # Perform risk evaluations
        evaluations = {}
        all_violations = []
        all_warnings = []
        
        # Position size risk
        if "position_size" not in override_rules:
            position_eval = evaluate_position_size_risk(trade_proposal, portfolio_status)
            evaluations["position_size"] = position_eval
            all_violations.extend(position_eval["violations"])
            all_warnings.extend(position_eval["warnings"])
        
        # Cash reserve risk
        if "cash_reserve" not in override_rules:
            cash_eval = evaluate_cash_reserve_risk(trade_proposal, portfolio_status)
            evaluations["cash_reserve"] = cash_eval
            all_violations.extend(cash_eval["violations"])
            all_warnings.extend(cash_eval["warnings"])
        
        # Diversification risk
        if "diversification" not in override_rules:
            diversification_eval = evaluate_diversification_risk(trade_proposal, portfolio_status)
            evaluations["diversification"] = diversification_eval
            all_violations.extend(diversification_eval["violations"])
            all_warnings.extend(diversification_eval["warnings"])
        
        # Trade quality risk
        if "trade_quality" not in override_rules:
            quality_eval = evaluate_trade_quality_risk(trade_proposal)
            evaluations["trade_quality"] = quality_eval
            all_violations.extend(quality_eval["violations"])
            all_warnings.extend(quality_eval["warnings"])
        
        # Make final decision
        if all_violations:
            decision = RiskDecision.DENY
            rationale = f"Trade denied due to {len(all_violations)} risk violation(s)"
        elif all_warnings:
            decision = RiskDecision.CONDITIONAL_APPROVE
            rationale = f"Trade conditionally approved with {len(all_warnings)} warning(s)"
        else:
            decision = RiskDecision.APPROVE
            rationale = "Trade approved - all risk checks passed"
        
        result = {
            "decision": decision,
            "rationale": rationale,
            "violations": all_violations,
            "warnings": all_warnings,
            "risk_evaluations": evaluations,
            "portfolio_status": {
                "total_value": portfolio_status.get("total_portfolio_value", 0),
                "cash_balance": portfolio_status.get("cash_balance", 0),
                "num_positions": portfolio_status.get("number_of_positions", 0)
            }
        }
        
        logger.info(f"Risk evaluation complete: {decision} - {rationale}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in risk evaluation: {e}")
        return {
            "decision": RiskDecision.DENY,
            "rationale": f"Risk evaluation failed: {str(e)}",
            "violations": ["Risk evaluation system error"],
            "warnings": [],
            "risk_metrics": {}
        }


# A2A method handlers
async def evaluate_trade_proposal(
    ticker: str,
    action: str,
    quantity: int,
    estimated_price: float,
    rationale: str,
    expected_return: Optional[float] = None,
    risk_level: str = "medium",
    fundamental_score: Optional[float] = None,
    technical_confidence: Optional[float] = None,
    override_rules: List[str] = None
) -> Dict:
    """
    Evaluate a trade proposal for risk compliance.
    
    Args:
        ticker: Stock ticker symbol
        action: Trade action (BUY/SELL)
        quantity: Number of shares
        estimated_price: Estimated execution price
        rationale: Trade rationale
        expected_return: Expected return percentage
        risk_level: Risk level assessment
        fundamental_score: Fundamental analysis score
        technical_confidence: Technical analysis confidence
        override_rules: Risk rules to override
        
    Returns:
        Dictionary with risk evaluation results
    """
    logger.info(f"Received trade proposal evaluation request: {action} {quantity} {ticker}")
    
    try:
        # Create trade proposal object
        trade_proposal = TradeProposal(
            ticker=ticker,
            action=TradeAction(action.upper()),
            quantity=quantity,
            estimated_price=estimated_price,
            rationale=rationale,
            expected_return=expected_return,
            risk_level=risk_level,
            fundamental_score=fundamental_score,
            technical_confidence=technical_confidence
        )
        
        # Perform risk evaluation
        evaluation_result = await evaluate_trade_proposal_internal(trade_proposal, override_rules)
        
        return evaluation_result
        
    except Exception as e:
        logger.error(f"Error in trade proposal evaluation: {e}")
        raise


# Register A2A methods
a2a_server.register_method("evaluate_trade_proposal", evaluate_trade_proposal)

# FastAPI endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "RiskManager Agent", "status": "running", "version": "1.0.0"}


@app.post("/a2a")
async def a2a_endpoint(request: Request):
    """A2A protocol endpoint."""
    return await create_a2a_endpoint(a2a_server)(request)


@app.post("/evaluate")
async def evaluate_endpoint(request: RiskEvaluationRequest) -> Dict:
    """
    Direct evaluation endpoint for testing.
    
    Args:
        request: Risk evaluation request
        
    Returns:
        Risk evaluation results
    """
    return await evaluate_trade_proposal_internal(
        request.trade_proposal,
        request.override_rules
    )


@app.get("/risk_limits")
async def get_risk_limits() -> Dict:
    """
    Get current risk limits and configuration.
    
    Returns:
        Dictionary with risk limits
    """
    return {
        "position_limits": {
            "max_position_size_pct": TRADING_CONFIG["max_position_size_pct"],
            "max_single_trade_value": TRADING_CONFIG["max_single_trade_value"]
        },
        "cash_limits": {
            "min_cash_reserve_pct": TRADING_CONFIG["min_cash_reserve_pct"]
        },
        "diversification_limits": {
            "max_positions": 20,
            "max_sector_concentration_pct": TRADING_CONFIG.get("max_sector_concentration_pct", 30.0)
        },
        "quality_limits": {
            "min_fundamental_score": 30,
            "min_technical_confidence": 0.3
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    port = PORTS["risk_manager"]
    logger.info(f"Starting RiskManager Agent on port {port}")
    
    uvicorn.run(
        "risk_manager_agent:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
"""
TradeExecutorAgent - The executioner that handles final trade execution.
"""

from typing import Dict, Optional
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from enum import Enum

from ..models.trading_models import TradeProposal, TradeAction, TradeStatus
from ..utils.logging_config import setup_logging, get_logger
from ..utils.a2a_server import A2AServer, create_a2a_endpoint
from ..utils.http_client import HTTPClient
from ..config import PORTS, SERVICE_URLS

# Initialize logging
setup_logging("trade_executor_agent")
logger = get_logger(__name__)

app = FastAPI(
    title="TradeExecutor Agent",
    description="Executes approved trades and manages trade confirmations",
    version="1.0.0"
)

# Initialize A2A server and HTTP client
a2a_server = A2AServer()
http_client = HTTPClient()

# Execution result enum
class ExecutionResult(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"

# Request models
class TradeExecutionRequest(BaseModel):
    """Request for trade execution."""
    trade_proposal: TradeProposal = Field(..., description="Approved trade proposal to execute")
    execution_type: str = Field(default="MARKET", description="Execution type (MARKET/LIMIT)")
    timeout_seconds: int = Field(default=30, description="Execution timeout in seconds")


async def execute_trade_via_mcp(
    ticker: str,
    action: str,
    quantity: int,
    trade_type: str = "MARKET",
    limit_price: Optional[float] = None
) -> Dict:
    """
    Execute trade via TradingExecutionMCP server.
    
    Args:
        ticker: Stock ticker symbol
        action: Trade action (BUY/SELL)
        quantity: Number of shares
        trade_type: Trade type (MARKET/LIMIT)
        limit_price: Limit price for LIMIT orders
        
    Returns:
        Trade execution result from MCP server
    """
    try:
        trading_execution_url = SERVICE_URLS["trading_execution_mcp"]
        
        trade_request = {
            "ticker": ticker,
            "action": action,
            "quantity": quantity,
            "trade_type": trade_type
        }
        
        if limit_price is not None:
            trade_request["limit_price"] = limit_price
        
        logger.info(f"Executing trade via MCP: {action} {quantity} {ticker}")
        
        response = await http_client.post(
            f"{trading_execution_url}/mcp/execute_mock_trade",
            json_data=trade_request
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Trade execution response: {result.get('status', 'UNKNOWN')}")
            return result
        else:
            logger.error(f"Trade execution failed with HTTP {response.status_code}: {response.text}")
            return {
                "trade_id": None,
                "ticker": ticker,
                "action": action,
                "quantity": quantity,
                "price": 0.0,
                "total_value": 0.0,
                "status": "FAILED",
                "error_message": f"HTTP {response.status_code}: {response.text}",
                "timestamp": None,
                "fees": 0.0
            }
            
    except Exception as e:
        logger.error(f"Error executing trade via MCP: {e}")
        return {
            "trade_id": None,
            "ticker": ticker,
            "action": action,
            "quantity": quantity,
            "price": 0.0,
            "total_value": 0.0,
            "status": "FAILED",
            "error_message": f"Execution error: {str(e)}",
            "timestamp": None,
            "fees": 0.0
        }


def validate_trade_execution_request(trade_proposal: TradeProposal) -> Dict:
    """
    Validate trade execution request before attempting execution.
    
    Args:
        trade_proposal: Trade proposal to validate
        
    Returns:
        Dictionary with validation result
    """
    errors = []
    warnings = []
    
    # Basic validation
    if not trade_proposal.ticker or len(trade_proposal.ticker.strip()) == 0:
        errors.append("Invalid ticker symbol")
    
    if trade_proposal.quantity <= 0:
        errors.append("Quantity must be positive")
    
    if trade_proposal.estimated_price <= 0:
        errors.append("Estimated price must be positive")
    
    # Trade action validation
    if trade_proposal.action not in [TradeAction.BUY, TradeAction.SELL]:
        errors.append(f"Invalid trade action: {trade_proposal.action}")
    
    # Risk level warnings
    if trade_proposal.risk_level and trade_proposal.risk_level.upper() in ["HIGH", "VERY HIGH"]:
        warnings.append(f"Executing {trade_proposal.risk_level} risk trade")
    
    # Confidence warnings
    if trade_proposal.technical_confidence and trade_proposal.technical_confidence < 0.5:
        warnings.append(f"Low technical confidence: {trade_proposal.technical_confidence:.2f}")
    
    if trade_proposal.fundamental_score and trade_proposal.fundamental_score < 60:
        warnings.append(f"Below average fundamental score: {trade_proposal.fundamental_score}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def analyze_execution_result(execution_result: Dict, trade_proposal: TradeProposal) -> Dict:
    """
    Analyze trade execution result and provide detailed feedback.
    
    Args:
        execution_result: Result from MCP trade execution
        trade_proposal: Original trade proposal
        
    Returns:
        Dictionary with execution analysis
    """
    status = execution_result.get("status", "UNKNOWN")
    
    if status == "EXECUTED":
        execution_status = ExecutionResult.SUCCESS
        
        # Check if execution price is reasonable compared to estimated price
        executed_price = execution_result.get("price", 0.0)
        estimated_price = trade_proposal.estimated_price
        
        if executed_price > 0 and estimated_price > 0:
            price_deviation = abs(executed_price - estimated_price) / estimated_price
            if price_deviation > 0.05:  # More than 5% deviation
                execution_status = ExecutionResult.PARTIAL
                message = f"Trade executed but price deviated {price_deviation:.1%} from estimate"
            else:
                message = "Trade executed successfully at expected price"
        else:
            message = "Trade executed successfully"
        
        success = True
        
    elif status == "FAILED":
        execution_status = ExecutionResult.FAILED
        error_message = execution_result.get("error_message", "Unknown execution error")
        message = f"Trade execution failed: {error_message}"
        success = False
        
    else:
        execution_status = ExecutionResult.REJECTED
        message = f"Trade execution rejected with status: {status}"
        success = False
    
    # Calculate execution metrics
    executed_quantity = execution_result.get("quantity", 0)
    executed_price = execution_result.get("price", 0.0)
    total_value = execution_result.get("total_value", 0.0)
    fees = execution_result.get("fees", 0.0)
    
    return {
        "execution_status": execution_status,
        "success": success,
        "message": message,
        "trade_id": execution_result.get("trade_id"),
        "executed_quantity": executed_quantity,
        "executed_price": executed_price,
        "total_value": total_value,
        "fees": fees,
        "timestamp": execution_result.get("timestamp"),
        "slippage": abs(executed_price - trade_proposal.estimated_price) if executed_price > 0 else 0.0,
        "slippage_pct": abs(executed_price - trade_proposal.estimated_price) / trade_proposal.estimated_price * 100 
                       if executed_price > 0 and trade_proposal.estimated_price > 0 else 0.0
    }


async def execute_approved_trade_internal(
    trade_proposal: TradeProposal,
    execution_type: str = "MARKET",
    timeout_seconds: int = 30
) -> Dict:
    """
    Execute an approved trade proposal.
    
    Args:
        trade_proposal: Approved trade proposal
        execution_type: Type of execution (MARKET/LIMIT)
        timeout_seconds: Execution timeout
        
    Returns:
        Dictionary with complete execution results
    """
    logger.info(f"Executing approved trade: {trade_proposal.action} {trade_proposal.quantity} {trade_proposal.ticker}")
    
    try:
        # Validate trade execution request
        validation_result = validate_trade_execution_request(trade_proposal)
        
        if not validation_result["valid"]:
            logger.error(f"Trade execution validation failed: {validation_result['errors']}")
            return {
                "execution_status": ExecutionResult.REJECTED,
                "success": False,
                "message": f"Validation failed: {'; '.join(validation_result['errors'])}",
                "trade_id": None,
                "executed_quantity": 0,
                "executed_price": 0.0,
                "total_value": 0.0,
                "fees": 0.0,
                "timestamp": None,
                "validation_errors": validation_result["errors"],
                "validation_warnings": validation_result["warnings"]
            }
        
        # Log any validation warnings
        if validation_result["warnings"]:
            for warning in validation_result["warnings"]:
                logger.warning(f"Trade execution warning: {warning}")
        
        # Execute trade via MCP
        execution_result = await execute_trade_via_mcp(
            ticker=trade_proposal.ticker,
            action=trade_proposal.action.value,
            quantity=trade_proposal.quantity,
            trade_type=execution_type
        )
        
        # Analyze execution result
        analysis = analyze_execution_result(execution_result, trade_proposal)
        
        # Add validation warnings to analysis
        analysis["validation_warnings"] = validation_result["warnings"]
        
        # Log execution result
        if analysis["success"]:
            logger.info(f"Trade execution successful: {analysis['message']}")
        else:
            logger.error(f"Trade execution failed: {analysis['message']}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error in trade execution: {e}")
        return {
            "execution_status": ExecutionResult.FAILED,
            "success": False,
            "message": f"Execution system error: {str(e)}",
            "trade_id": None,
            "executed_quantity": 0,
            "executed_price": 0.0,
            "total_value": 0.0,
            "fees": 0.0,
            "timestamp": None,
            "system_error": str(e)
        }


# A2A method handlers
async def execute_approved_trade(
    ticker: str,
    action: str,
    quantity: int,
    estimated_price: float,
    rationale: str,
    execution_type: str = "MARKET",
    timeout_seconds: int = 30,
    expected_return: Optional[float] = None,
    risk_level: str = "medium",
    fundamental_score: Optional[float] = None,
    technical_confidence: Optional[float] = None
) -> Dict:
    """
    Execute an approved trade.
    
    Args:
        ticker: Stock ticker symbol
        action: Trade action (BUY/SELL)
        quantity: Number of shares
        estimated_price: Estimated execution price
        rationale: Trade rationale
        execution_type: Execution type (MARKET/LIMIT)
        timeout_seconds: Execution timeout
        expected_return: Expected return percentage
        risk_level: Risk level assessment
        fundamental_score: Fundamental analysis score
        technical_confidence: Technical analysis confidence
        
    Returns:
        Dictionary with execution results
    """
    logger.info(f"Received trade execution request: {action} {quantity} {ticker}")
    
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
        
        # Execute the trade
        execution_result = await execute_approved_trade_internal(
            trade_proposal, execution_type, timeout_seconds
        )
        
        return execution_result
        
    except Exception as e:
        logger.error(f"Error in trade execution request: {e}")
        raise


async def get_execution_status(trade_id: str) -> Dict:
    """
    Get execution status for a specific trade.
    
    Args:
        trade_id: Trade ID to check
        
    Returns:
        Dictionary with trade status
    """
    logger.info(f"Checking execution status for trade {trade_id}")
    
    try:
        # In a real system, this would query the execution system
        # For simulation, we'll check the trading execution MCP
        trading_execution_url = SERVICE_URLS["trading_execution_mcp"]
        
        response = await http_client.get(
            f"{trading_execution_url}/mcp/get_trade_history",
            params={"limit": 100}
        )
        
        if response.status_code == 200:
            trade_history = response.json()
            
            # Find the specific trade
            for trade in trade_history.get("trades", []):
                if trade.get("trade_id") == trade_id:
                    return {
                        "found": True,
                        "trade_id": trade_id,
                        "status": trade.get("status"),
                        "ticker": trade.get("ticker"),
                        "action": trade.get("action"),
                        "quantity": trade.get("quantity"),
                        "price": trade.get("price"),
                        "total_value": trade.get("total_value"),
                        "timestamp": trade.get("timestamp"),
                        "fees": trade.get("fees")
                    }
            
            return {
                "found": False,
                "trade_id": trade_id,
                "message": "Trade not found in execution history"
            }
        else:
            return {
                "found": False,
                "trade_id": trade_id,
                "message": f"Unable to retrieve trade history: HTTP {response.status_code}"
            }
            
    except Exception as e:
        logger.error(f"Error checking execution status: {e}")
        return {
            "found": False,
            "trade_id": trade_id,
            "message": f"Error checking status: {str(e)}"
        }


# Register A2A methods
a2a_server.register_method("execute_approved_trade", execute_approved_trade)
a2a_server.register_method("get_execution_status", get_execution_status)

# FastAPI endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "TradeExecutor Agent", "status": "running", "version": "1.0.0"}


@app.post("/a2a")
async def a2a_endpoint(request: Request):
    """A2A protocol endpoint."""
    return await create_a2a_endpoint(a2a_server)(request)


@app.post("/execute")
async def execute_endpoint(request: TradeExecutionRequest) -> Dict:
    """
    Direct execution endpoint for testing.
    
    Args:
        request: Trade execution request
        
    Returns:
        Execution results
    """
    return await execute_approved_trade_internal(
        request.trade_proposal,
        request.execution_type,
        request.timeout_seconds
    )


@app.get("/status/{trade_id}")
async def status_endpoint(trade_id: str) -> Dict:
    """
    Get execution status for a trade.
    
    Args:
        trade_id: Trade ID to check
        
    Returns:
        Trade status information
    """
    return await get_execution_status(trade_id)


if __name__ == "__main__":
    import uvicorn
    
    port = PORTS["trade_executor"]
    logger.info(f"Starting TradeExecutor Agent on port {port}")
    
    uvicorn.run(
        "trade_executor_agent:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
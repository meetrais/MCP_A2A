"""
TradingExecutionMCP Server - Simulates brokerage connection for paper trading.
"""

from typing import Dict, List, Optional
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..models.trading_models import Portfolio, Position, Trade, TradeAction, TradeStatus
from ..utils.logging_config import setup_logging, get_logger
from ..config import PORTS, TRADING_CONFIG

# Initialize logging
setup_logging("trading_execution_mcp")
logger = get_logger(__name__)

app = FastAPI(
    title="TradingExecution MCP Server",
    description="Simulates brokerage connection for paper trading and portfolio management",
    version="1.0.0"
)

# Global portfolio state (in-memory for simulation)
portfolio = Portfolio(cash_balance=TRADING_CONFIG["initial_cash"])

# Request models
class TradeRequest(BaseModel):
    """Request to execute a trade."""
    ticker: str = Field(..., description="Stock ticker symbol")
    action: TradeAction = Field(..., description="Trade action (BUY/SELL)")
    quantity: int = Field(..., gt=0, description="Number of shares")
    trade_type: str = Field(default="MARKET", description="Trade type (MARKET/LIMIT)")
    limit_price: Optional[float] = Field(None, gt=0, description="Limit price for LIMIT orders")

class PriceUpdateRequest(BaseModel):
    """Request to update current market prices for portfolio valuation."""
    prices: Dict[str, float] = Field(..., description="Current market prices by ticker")


def get_simulated_price(ticker: str) -> float:
    """Get simulated current market price for a ticker."""
    # Simulated prices based on common stocks
    simulated_prices = {
        "AAPL": 175.0,
        "GOOGL": 140.0,
        "MSFT": 380.0,
        "TSLA": 250.0,
        "NVDA": 500.0,
        "META": 320.0
    }
    
    # Add some random variation (±2%)
    import random
    base_price = simulated_prices.get(ticker, 100.0)
    variation = random.uniform(-0.02, 0.02)
    return round(base_price * (1 + variation), 2)


def calculate_trade_fees(trade_value: float) -> float:
    """Calculate trading fees (simplified)."""
    # Flat fee of $1 per trade (typical for modern brokers)
    return 1.0


def validate_trade(trade_request: TradeRequest) -> Dict[str, str]:
    """
    Validate trade request against portfolio and risk rules.
    
    Returns:
        Dictionary with validation result and any error messages
    """
    errors = []
    
    # Get current market price
    current_price = get_simulated_price(trade_request.ticker)
    trade_value = current_price * trade_request.quantity
    fees = calculate_trade_fees(trade_value)
    
    if trade_request.action == TradeAction.BUY:
        # Check if we have enough cash
        total_cost = trade_value + fees
        if portfolio.cash_balance < total_cost:
            errors.append(f"Insufficient cash: need ${total_cost:.2f}, have ${portfolio.cash_balance:.2f}")
        
        # Check position size limits
        total_portfolio_value = portfolio.total_portfolio_value
        if total_portfolio_value > 0:
            position_percentage = (trade_value / total_portfolio_value) * 100
            max_position_pct = TRADING_CONFIG["max_position_size_pct"]
            
            if position_percentage > max_position_pct:
                errors.append(f"Position size too large: {position_percentage:.1f}% > {max_position_pct}%")
        
        # Check single trade value limit
        max_trade_value = TRADING_CONFIG["max_single_trade_value"]
        if trade_value > max_trade_value:
            errors.append(f"Trade value too large: ${trade_value:.2f} > ${max_trade_value:.2f}")
    
    elif trade_request.action == TradeAction.SELL:
        # Check if we have enough shares
        if trade_request.ticker not in portfolio.positions:
            errors.append(f"No position in {trade_request.ticker} to sell")
        else:
            current_position = portfolio.positions[trade_request.ticker]
            if current_position.quantity < trade_request.quantity:
                errors.append(f"Insufficient shares: trying to sell {trade_request.quantity}, have {current_position.quantity}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "current_price": current_price,
        "trade_value": trade_value,
        "fees": fees
    }


def execute_trade_internal(trade_request: TradeRequest, validation_result: Dict) -> Trade:
    """
    Execute the trade and update portfolio state.
    
    Args:
        trade_request: The trade to execute
        validation_result: Pre-computed validation results
        
    Returns:
        Trade record
    """
    global portfolio
    
    trade_id = str(uuid.uuid4())
    current_price = validation_result["current_price"]
    trade_value = validation_result["trade_value"]
    fees = validation_result["fees"]
    
    # Create trade record
    trade = Trade(
        trade_id=trade_id,
        ticker=trade_request.ticker,
        action=trade_request.action,
        quantity=trade_request.quantity,
        price=current_price,
        total_value=trade_value,
        status=TradeStatus.EXECUTED,
        fees=fees
    )
    
    # Update portfolio
    if trade_request.action == TradeAction.BUY:
        # Deduct cash
        portfolio.cash_balance -= (trade_value + fees)
        
        # Add or update position
        if trade_request.ticker in portfolio.positions:
            # Update existing position
            existing_position = portfolio.positions[trade_request.ticker]
            total_shares = existing_position.quantity + trade_request.quantity
            total_cost = (existing_position.avg_cost * existing_position.quantity) + trade_value
            new_avg_cost = total_cost / total_shares
            
            portfolio.positions[trade_request.ticker] = Position(
                ticker=trade_request.ticker,
                quantity=total_shares,
                avg_cost=round(new_avg_cost, 2),
                current_price=current_price
            )
        else:
            # Create new position
            portfolio.positions[trade_request.ticker] = Position(
                ticker=trade_request.ticker,
                quantity=trade_request.quantity,
                avg_cost=current_price,
                current_price=current_price
            )
    
    elif trade_request.action == TradeAction.SELL:
        # Add cash
        portfolio.cash_balance += (trade_value - fees)
        
        # Update or remove position
        existing_position = portfolio.positions[trade_request.ticker]
        remaining_shares = existing_position.quantity - trade_request.quantity
        
        if remaining_shares == 0:
            # Remove position entirely
            del portfolio.positions[trade_request.ticker]
        else:
            # Update position quantity
            portfolio.positions[trade_request.ticker] = Position(
                ticker=trade_request.ticker,
                quantity=remaining_shares,
                avg_cost=existing_position.avg_cost,
                current_price=current_price
            )
    
    # Add trade to history
    portfolio.trade_history.append(trade)
    
    logger.info(f"Executed trade: {trade.action} {trade.quantity} {trade.ticker} @ ${trade.price}")
    
    return trade


def update_portfolio_prices(prices: Dict[str, float]) -> None:
    """Update current market prices for all positions."""
    global portfolio
    
    for ticker, position in portfolio.positions.items():
        if ticker in prices:
            position.current_price = prices[ticker]
    
    logger.info(f"Updated prices for {len(prices)} positions")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "TradingExecution MCP Server", "status": "running", "version": "1.0.0"}


@app.post("/mcp/execute_mock_trade")
async def execute_mock_trade(request: TradeRequest) -> Dict:
    """
    Execute a simulated trade.
    
    Args:
        request: Trade execution request
        
    Returns:
        Dictionary containing trade confirmation details
    """
    try:
        logger.info(f"Processing trade request: {request.action} {request.quantity} {request.ticker}")
        
        # Validate trade
        validation_result = validate_trade(request)
        
        if not validation_result["valid"]:
            logger.warning(f"Trade validation failed: {validation_result['errors']}")
            return {
                "trade_id": None,
                "ticker": request.ticker,
                "action": request.action.value,
                "quantity": request.quantity,
                "price": validation_result.get("current_price", 0.0),
                "total_value": validation_result.get("trade_value", 0.0),
                "status": TradeStatus.FAILED.value,
                "timestamp": datetime.now().isoformat(),
                "error_message": "; ".join(validation_result["errors"]),
                "fees": validation_result.get("fees", 0.0)
            }
        
        # Execute trade
        trade = execute_trade_internal(request, validation_result)
        
        logger.info(f"Trade executed successfully: {trade.trade_id}")
        
        return {
            "trade_id": trade.trade_id,
            "ticker": trade.ticker,
            "action": trade.action.value,
            "quantity": trade.quantity,
            "price": trade.price,
            "total_value": trade.total_value,
            "status": trade.status.value,
            "timestamp": trade.timestamp.isoformat(),
            "fees": trade.fees
        }
        
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/mcp/get_portfolio_status")
async def get_portfolio_status() -> Dict:
    """
    Get current portfolio status.
    
    Returns:
        Dictionary containing portfolio state
    """
    try:
        logger.info("Fetching portfolio status")
        
        # Update current prices for all positions
        current_prices = {}
        for ticker in portfolio.positions.keys():
            current_prices[ticker] = get_simulated_price(ticker)
        
        if current_prices:
            update_portfolio_prices(current_prices)
        
        # Build response
        positions_data = []
        for ticker, position in portfolio.positions.items():
            positions_data.append({
                "ticker": ticker,
                "quantity": position.quantity,
                "avg_cost": position.avg_cost,
                "current_price": position.current_price,
                "current_value": position.current_value,
                "unrealized_pnl": position.unrealized_pnl,
                "unrealized_pnl_pct": position.unrealized_pnl_pct
            })
        
        result = {
            "cash_balance": round(portfolio.cash_balance, 2),
            "positions": positions_data,
            "total_equity_value": round(portfolio.total_equity_value, 2),
            "total_portfolio_value": round(portfolio.total_portfolio_value, 2),
            "cash_percentage": round(portfolio.cash_percentage, 2),
            "number_of_positions": len(portfolio.positions),
            "trade_count": len(portfolio.trade_history)
        }
        
        logger.info(f"Portfolio value: ${result['total_portfolio_value']:.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching portfolio status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/mcp/get_trade_history")
async def get_trade_history(limit: int = 50) -> Dict:
    """
    Get trade history.
    
    Args:
        limit: Maximum number of trades to return
        
    Returns:
        Dictionary containing trade history
    """
    try:
        logger.info(f"Fetching trade history (limit: {limit})")
        
        # Get recent trades
        recent_trades = portfolio.trade_history[-limit:] if limit > 0 else portfolio.trade_history
        
        trades_data = []
        for trade in recent_trades:
            trades_data.append({
                "trade_id": trade.trade_id,
                "ticker": trade.ticker,
                "action": trade.action.value,
                "quantity": trade.quantity,
                "price": trade.price,
                "total_value": trade.total_value,
                "status": trade.status.value,
                "timestamp": trade.timestamp.isoformat(),
                "fees": trade.fees
            })
        
        return {
            "trades": trades_data,
            "total_trades": len(portfolio.trade_history)
        }
        
    except Exception as e:
        logger.error(f"Error fetching trade history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/mcp/update_market_prices")
async def update_market_prices(request: PriceUpdateRequest) -> Dict:
    """
    Update current market prices for portfolio valuation.
    
    Args:
        request: Price update request with current market prices
        
    Returns:
        Dictionary confirming price updates
    """
    try:
        logger.info(f"Updating market prices for {len(request.prices)} tickers")
        
        update_portfolio_prices(request.prices)
        
        return {
            "status": "success",
            "updated_tickers": list(request.prices.keys()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating market prices: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/mcp/reset_portfolio")
async def reset_portfolio() -> Dict:
    """
    Reset portfolio to initial state (for testing/demo purposes).
    
    Returns:
        Dictionary confirming portfolio reset
    """
    try:
        global portfolio
        
        logger.info("Resetting portfolio to initial state")
        
        portfolio = Portfolio(cash_balance=TRADING_CONFIG["initial_cash"])
        
        return {
            "status": "success",
            "message": "Portfolio reset to initial state",
            "initial_cash": TRADING_CONFIG["initial_cash"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error resetting portfolio: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/mcp/get_risk_metrics")
async def get_risk_metrics() -> Dict:
    """
    Get portfolio risk metrics.
    
    Returns:
        Dictionary containing risk analysis
    """
    try:
        logger.info("Calculating portfolio risk metrics")
        
        total_value = portfolio.total_portfolio_value
        
        # Position concentration analysis
        position_concentrations = {}
        largest_position_pct = 0.0
        
        for ticker, position in portfolio.positions.items():
            position_pct = portfolio.get_position_percentage(ticker)
            position_concentrations[ticker] = position_pct
            largest_position_pct = max(largest_position_pct, position_pct)
        
        # Risk rule compliance
        cash_pct = portfolio.cash_percentage
        min_cash_pct = TRADING_CONFIG["min_cash_reserve_pct"]
        max_position_pct = TRADING_CONFIG["max_position_size_pct"]
        
        risk_violations = []
        if cash_pct < min_cash_pct:
            risk_violations.append(f"Cash reserve below minimum: {cash_pct:.1f}% < {min_cash_pct}%")
        
        if largest_position_pct > max_position_pct:
            risk_violations.append(f"Position size exceeds limit: {largest_position_pct:.1f}% > {max_position_pct}%")
        
        return {
            "total_portfolio_value": round(total_value, 2),
            "cash_percentage": round(cash_pct, 2),
            "largest_position_percentage": round(largest_position_pct, 2),
            "position_concentrations": {k: round(v, 2) for k, v in position_concentrations.items()},
            "risk_violations": risk_violations,
            "risk_compliance": len(risk_violations) == 0,
            "number_of_positions": len(portfolio.positions)
        }
        
    except Exception as e:
        logger.error(f"Error calculating risk metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    
    port = PORTS["trading_execution_mcp"]
    logger.info(f"Starting TradingExecution MCP Server on port {port}")
    
    uvicorn.run(
        "trading_execution_server:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
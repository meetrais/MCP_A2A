"""
Trading-related data models for the MCP A2A Trading System.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class RiskTolerance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TimeHorizon(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class InvestmentStrategy(BaseModel):
    """Investment strategy input from user."""
    
    goal: str = Field(..., description="High-level investment goal")
    sector_preference: Optional[str] = Field(default=None, description="Preferred sector (e.g., 'tech', 'healthcare')")
    risk_tolerance: RiskTolerance = Field(default=RiskTolerance.MEDIUM, description="Risk tolerance level")
    max_investment: float = Field(default=50000.0, description="Maximum investment amount")
    time_horizon: TimeHorizon = Field(default=TimeHorizon.SHORT, description="Investment time horizon")


class FundamentalAnalysis(BaseModel):
    """Fundamental analysis result for a company."""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    score: float = Field(..., ge=0, le=100, description="Fundamental strength score (0-100)")
    strengths: List[str] = Field(default_factory=list, description="Company strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Company weaknesses")
    recommendation: str = Field(..., description="Analysis recommendation")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in analysis (0-1)")


class TechnicalAnalysis(BaseModel):
    """Technical analysis result for a stock."""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    signal: Signal = Field(..., description="Trading signal")
    confidence: float = Field(..., ge=0, le=1, description="Signal confidence (0-1)")
    indicators: Dict[str, float] = Field(default_factory=dict, description="Technical indicator values")
    entry_price: Optional[float] = Field(default=None, description="Suggested entry price")
    stop_loss: Optional[float] = Field(default=None, description="Suggested stop loss price")
    target_price: Optional[float] = Field(default=None, description="Suggested target price")
    rationale: str = Field(..., description="Analysis rationale")


class TradeProposal(BaseModel):
    """Trade proposal for risk evaluation."""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    action: TradeAction = Field(..., description="Trade action (BUY/SELL)")
    quantity: int = Field(..., gt=0, description="Number of shares")
    estimated_price: float = Field(..., gt=0, description="Estimated execution price")
    rationale: str = Field(..., description="Trade rationale")
    expected_return: Optional[float] = Field(default=None, description="Expected return percentage")
    risk_level: str = Field(..., description="Risk level assessment")
    fundamental_score: Optional[float] = Field(default=None, description="Fundamental analysis score")
    technical_confidence: Optional[float] = Field(default=None, description="Technical analysis confidence")


class Position(BaseModel):
    """Portfolio position in a stock."""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    quantity: int = Field(..., description="Number of shares held")
    avg_cost: float = Field(..., gt=0, description="Average cost per share")
    current_price: float = Field(..., gt=0, description="Current market price")
    
    @property
    def current_value(self) -> float:
        """Calculate current position value."""
        return self.quantity * self.current_price
    
    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized profit/loss."""
        return (self.current_price - self.avg_cost) * self.quantity
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """Calculate unrealized profit/loss percentage."""
        return (self.current_price - self.avg_cost) / self.avg_cost * 100


class Trade(BaseModel):
    """Executed trade record."""
    
    trade_id: str = Field(..., description="Unique trade identifier")
    ticker: str = Field(..., description="Stock ticker symbol")
    action: TradeAction = Field(..., description="Trade action (BUY/SELL)")
    quantity: int = Field(..., gt=0, description="Number of shares")
    price: float = Field(..., gt=0, description="Execution price per share")
    total_value: float = Field(..., gt=0, description="Total trade value")
    timestamp: datetime = Field(default_factory=datetime.now, description="Trade execution timestamp")
    status: TradeStatus = Field(..., description="Trade status")
    fees: float = Field(default=0.0, description="Trading fees")


class Portfolio(BaseModel):
    """Portfolio state and holdings."""
    
    cash_balance: float = Field(default=100000.0, description="Available cash balance")
    positions: Dict[str, Position] = Field(default_factory=dict, description="Stock positions")
    trade_history: List[Trade] = Field(default_factory=list, description="Historical trades")
    
    @property
    def total_equity_value(self) -> float:
        """Calculate total value of equity positions."""
        return sum(position.current_value for position in self.positions.values())
    
    @property
    def total_portfolio_value(self) -> float:
        """Calculate total portfolio value (cash + equity)."""
        return self.cash_balance + self.total_equity_value
    
    @property
    def cash_percentage(self) -> float:
        """Calculate cash as percentage of total portfolio."""
        total_value = self.total_portfolio_value
        return (self.cash_balance / total_value * 100) if total_value > 0 else 100.0
    
    def get_position_percentage(self, ticker: str) -> float:
        """Get position size as percentage of total portfolio."""
        if ticker not in self.positions:
            return 0.0
        position_value = self.positions[ticker].current_value
        total_value = self.total_portfolio_value
        return (position_value / total_value * 100) if total_value > 0 else 0.0
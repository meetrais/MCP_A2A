"""
Market data models for the MCP A2A Trading System.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class PriceData(BaseModel):
    """Single day price data (OHLCV)."""
    
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    open: float = Field(..., gt=0, description="Opening price")
    high: float = Field(..., gt=0, description="High price")
    low: float = Field(..., gt=0, description="Low price")
    close: float = Field(..., gt=0, description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")


class StockPrice(BaseModel):
    """Historical stock price data."""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    data: List[PriceData] = Field(..., description="Historical price data")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class MarketNews(BaseModel):
    """Market news item."""
    
    headline: str = Field(..., description="News headline")
    summary: str = Field(..., description="News summary")
    sentiment: Sentiment = Field(..., description="News sentiment")
    date: str = Field(..., description="Publication date")
    source: str = Field(..., description="News source")
    relevance_score: float = Field(default=1.0, ge=0, le=1, description="Relevance score (0-1)")


class FinancialStatement(BaseModel):
    """Simplified financial statement data."""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    revenue: float = Field(..., description="Total revenue")
    net_income: float = Field(..., description="Net income")
    total_assets: float = Field(..., gt=0, description="Total assets")
    total_debt: float = Field(..., ge=0, description="Total debt")
    cash: float = Field(..., ge=0, description="Cash and cash equivalents")
    shares_outstanding: int = Field(..., gt=0, description="Shares outstanding")
    period: str = Field(..., description="Reporting period (e.g., 'Q1 2024')")
    
    @property
    def debt_to_equity_ratio(self) -> float:
        """Calculate debt-to-equity ratio."""
        equity = self.total_assets - self.total_debt
        return self.total_debt / equity if equity > 0 else float('inf')
    
    @property
    def return_on_assets(self) -> float:
        """Calculate return on assets (ROA)."""
        return self.net_income / self.total_assets if self.total_assets > 0 else 0.0
    
    @property
    def earnings_per_share(self) -> float:
        """Calculate earnings per share (EPS)."""
        return self.net_income / self.shares_outstanding if self.shares_outstanding > 0 else 0.0


class TechnicalIndicator(BaseModel):
    """Technical indicator calculation result."""
    
    indicator: str = Field(..., description="Indicator name (e.g., 'RSI', 'SMA')")
    values: List[float] = Field(..., description="Indicator values")
    signal: Optional[str] = Field(default=None, description="Generated signal")
    confidence: float = Field(default=0.0, ge=0, le=1, description="Signal confidence")
    parameters: dict = Field(default_factory=dict, description="Indicator parameters used")
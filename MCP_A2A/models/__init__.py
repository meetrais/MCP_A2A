"""
Shared data models for the MCP A2A Trading System.
"""

from .a2a_protocol import A2ARequest, A2AResponse, A2AError
from .trading_models import (
    InvestmentStrategy,
    FundamentalAnalysis,
    TechnicalAnalysis,
    TradeProposal,
    Portfolio,
    Position,
    Trade
)
from .market_data import StockPrice, MarketNews, FinancialStatement

__all__ = [
    "A2ARequest",
    "A2AResponse", 
    "A2AError",
    "InvestmentStrategy",
    "FundamentalAnalysis",
    "TechnicalAnalysis",
    "TradeProposal",
    "Portfolio",
    "Position",
    "Trade",
    "StockPrice",
    "MarketNews",
    "FinancialStatement"
]
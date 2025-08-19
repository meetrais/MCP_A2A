"""
MarketDataMCP Server - Provides simulated financial market data.
"""

from typing import Dict, List
from datetime import datetime, timedelta
import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ..models.market_data import StockPrice, PriceData, MarketNews, FinancialStatement, Sentiment
from ..utils.logging_config import setup_logging, get_logger
from ..config import PORTS

# Initialize logging
setup_logging("market_data_mcp")
logger = get_logger(__name__)

app = FastAPI(
    title="MarketData MCP Server",
    description="Provides simulated financial market data for the trading system",
    version="1.0.0"
)

# Simulated data storage
SIMULATED_STOCKS = {
    "AAPL": {
        "name": "Apple Inc.",
        "sector": "Technology",
        "base_price": 175.0,
        "volatility": 0.02
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "sector": "Technology", 
        "base_price": 140.0,
        "volatility": 0.025
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "sector": "Technology",
        "base_price": 380.0,
        "volatility": 0.018
    },
    "TSLA": {
        "name": "Tesla Inc.",
        "sector": "Automotive",
        "base_price": 250.0,
        "volatility": 0.04
    },
    "NVDA": {
        "name": "NVIDIA Corporation",
        "sector": "Technology",
        "base_price": 500.0,
        "volatility": 0.035
    },
    "META": {
        "name": "Meta Platforms Inc.",
        "sector": "Technology",
        "base_price": 320.0,
        "volatility": 0.03
    }
}

# Request/Response models
class StockPriceRequest(BaseModel):
    ticker: str
    days: int = 30

class MarketNewsRequest(BaseModel):
    ticker: str
    limit: int = 10

class FinancialStatementRequest(BaseModel):
    ticker: str


def generate_price_data(ticker: str, days: int = 30) -> List[PriceData]:
    """Generate simulated historical price data."""
    if ticker not in SIMULATED_STOCKS:
        raise ValueError(f"Unknown ticker: {ticker}")
    
    stock_info = SIMULATED_STOCKS[ticker]
    base_price = stock_info["base_price"]
    volatility = stock_info["volatility"]
    
    prices = []
    current_price = base_price
    
    # Generate data for the specified number of days
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-i-1)).strftime("%Y-%m-%d")
        
        # Random walk with volatility
        price_change = random.gauss(0, volatility) * current_price
        current_price = max(current_price + price_change, 1.0)  # Ensure positive price
        
        # Generate OHLC data
        high = current_price * (1 + random.uniform(0, 0.02))
        low = current_price * (1 - random.uniform(0, 0.02))
        open_price = current_price * (1 + random.uniform(-0.01, 0.01))
        close_price = current_price
        volume = random.randint(1000000, 50000000)
        
        prices.append(PriceData(
            date=date,
            open=round(open_price, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=round(close_price, 2),
            volume=volume
        ))
    
    return prices


def generate_market_news(ticker: str, limit: int = 10) -> List[MarketNews]:
    """Generate simulated market news."""
    if ticker not in SIMULATED_STOCKS:
        raise ValueError(f"Unknown ticker: {ticker}")
    
    stock_info = SIMULATED_STOCKS[ticker]
    company_name = stock_info["name"]
    
    # News templates
    positive_news = [
        f"{company_name} reports strong quarterly earnings, beating analyst expectations",
        f"{company_name} announces breakthrough innovation in core technology",
        f"{company_name} expands into new markets with strategic partnership",
        f"{company_name} receives upgrade from major investment firm",
        f"{company_name} CEO optimistic about future growth prospects",
        f"{company_name} launches new product line with strong market reception"
    ]
    
    negative_news = [
        f"{company_name} faces regulatory challenges in key markets",
        f"{company_name} reports lower than expected revenue guidance",
        f"{company_name} dealing with supply chain disruptions",
        f"{company_name} faces increased competition in core business",
        f"{company_name} announces cost-cutting measures amid market pressures",
        f"{company_name} stock downgraded by analysts citing concerns"
    ]
    
    neutral_news = [
        f"{company_name} announces routine board meeting scheduled",
        f"{company_name} files quarterly SEC reports",
        f"{company_name} participates in industry conference",
        f"{company_name} announces dividend payment schedule",
        f"{company_name} updates corporate governance policies",
        f"{company_name} releases sustainability report"
    ]
    
    news_items = []
    for i in range(min(limit, 10)):
        # Random sentiment distribution: 40% positive, 30% negative, 30% neutral
        sentiment_choice = random.choices(
            [Sentiment.POSITIVE, Sentiment.NEGATIVE, Sentiment.NEUTRAL],
            weights=[0.4, 0.3, 0.3]
        )[0]
        
        if sentiment_choice == Sentiment.POSITIVE:
            headline = random.choice(positive_news)
            summary = f"Positive development for {company_name} showing strong market position."
        elif sentiment_choice == Sentiment.NEGATIVE:
            headline = random.choice(negative_news)
            summary = f"Challenges ahead for {company_name} requiring strategic adjustments."
        else:
            headline = random.choice(neutral_news)
            summary = f"Routine corporate activity from {company_name}."
        
        date = (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")
        
        news_items.append(MarketNews(
            headline=headline,
            summary=summary,
            sentiment=sentiment_choice,
            date=date,
            source=random.choice(["Reuters", "Bloomberg", "CNBC", "MarketWatch", "Yahoo Finance"]),
            relevance_score=random.uniform(0.7, 1.0)
        ))
    
    return news_items


def generate_financial_statement(ticker: str) -> FinancialStatement:
    """Generate simulated financial statement data."""
    if ticker not in SIMULATED_STOCKS:
        raise ValueError(f"Unknown ticker: {ticker}")
    
    stock_info = SIMULATED_STOCKS[ticker]
    base_price = stock_info["base_price"]
    
    # Generate realistic financial metrics based on stock price
    market_cap_multiplier = random.uniform(20, 40)
    shares_outstanding = int(random.uniform(1e9, 5e9))
    
    # Revenue based on market cap
    revenue = base_price * shares_outstanding * random.uniform(0.8, 1.5)
    
    # Profit margins vary by company
    profit_margin = random.uniform(0.15, 0.35)
    net_income = revenue * profit_margin
    
    # Assets and debt
    total_assets = revenue * random.uniform(1.5, 3.0)
    debt_ratio = random.uniform(0.2, 0.4)
    total_debt = total_assets * debt_ratio
    
    # Cash position
    cash = total_assets * random.uniform(0.1, 0.25)
    
    return FinancialStatement(
        ticker=ticker,
        revenue=round(revenue, 0),
        net_income=round(net_income, 0),
        total_assets=round(total_assets, 0),
        total_debt=round(total_debt, 0),
        cash=round(cash, 0),
        shares_outstanding=shares_outstanding,
        period="Q4 2024"
    )


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "MarketData MCP Server", "status": "running", "version": "1.0.0"}


@app.post("/mcp/get_stock_price")
async def get_stock_price(request: StockPriceRequest) -> Dict:
    """
    Get simulated historical stock price data.
    
    Args:
        request: Stock price request with ticker and optional days parameter
        
    Returns:
        Dictionary containing stock price data
    """
    try:
        logger.info(f"Fetching stock price data for {request.ticker}")
        
        price_data = generate_price_data(request.ticker, request.days)
        
        result = StockPrice(
            ticker=request.ticker,
            data=price_data
        )
        
        logger.info(f"Generated {len(price_data)} price points for {request.ticker}")
        
        return result.dict()
        
    except ValueError as e:
        logger.error(f"Invalid ticker: {request.ticker}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating stock price data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/mcp/get_market_news")
async def get_market_news(request: MarketNewsRequest) -> Dict:
    """
    Get simulated market news for a stock.
    
    Args:
        request: Market news request with ticker and limit
        
    Returns:
        Dictionary containing list of news items
    """
    try:
        logger.info(f"Fetching market news for {request.ticker}")
        
        news_items = generate_market_news(request.ticker, request.limit)
        
        logger.info(f"Generated {len(news_items)} news items for {request.ticker}")
        
        return {"ticker": request.ticker, "news": [item.dict() for item in news_items]}
        
    except ValueError as e:
        logger.error(f"Invalid ticker: {request.ticker}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating market news: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/mcp/get_financial_statements")
async def get_financial_statements(request: FinancialStatementRequest) -> Dict:
    """
    Get simulated financial statement data.
    
    Args:
        request: Financial statement request with ticker
        
    Returns:
        Dictionary containing financial statement data
    """
    try:
        logger.info(f"Fetching financial statements for {request.ticker}")
        
        financial_data = generate_financial_statement(request.ticker)
        
        logger.info(f"Generated financial statement for {request.ticker}")
        
        return financial_data.dict()
        
    except ValueError as e:
        logger.error(f"Invalid ticker: {request.ticker}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating financial statements: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/mcp/available_tickers")
async def get_available_tickers() -> Dict:
    """
    Get list of available stock tickers.
    
    Returns:
        Dictionary containing available tickers and their info
    """
    logger.info("Fetching available tickers")
    
    return {
        "tickers": {
            ticker: {
                "name": info["name"],
                "sector": info["sector"]
            }
            for ticker, info in SIMULATED_STOCKS.items()
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    port = PORTS["market_data_mcp"]
    logger.info(f"Starting MarketData MCP Server on port {port}")
    
    uvicorn.run(
        "market_data_server:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
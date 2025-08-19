"""
FundamentalAnalystAgent - Assesses company financial health and intrinsic value.
"""

from typing import Dict, List, Optional
import asyncio
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from ..models.trading_models import FundamentalAnalysis
from ..models.market_data import FinancialStatement, MarketNews, Sentiment
from ..utils.logging_config import setup_logging, get_logger
from ..utils.a2a_server import A2AServer, create_a2a_endpoint
from ..utils.http_client import HTTPClient
from ..config import PORTS, SERVICE_URLS

# Initialize logging
setup_logging("fundamental_analyst_agent")
logger = get_logger(__name__)

app = FastAPI(
    title="FundamentalAnalyst Agent",
    description="Assesses company financial health and provides investment recommendations",
    version="1.0.0"
)

# Initialize A2A server and HTTP client
a2a_server = A2AServer()
http_client = HTTPClient()

# Request models
class AnalysisRequest(BaseModel):
    """Request for fundamental analysis."""
    sector: Optional[str] = Field(None, description="Preferred sector filter")
    criteria: Dict = Field(default_factory=dict, description="Analysis criteria")
    max_companies: int = Field(default=5, description="Maximum companies to analyze")


async def fetch_financial_data(ticker: str) -> Optional[FinancialStatement]:
    """
    Fetch financial statement data from MarketDataMCP.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Financial statement data or None if failed
    """
    try:
        market_data_url = SERVICE_URLS["market_data_mcp"]
        response = await http_client.post(
            f"{market_data_url}/mcp/get_financial_statements",
            json_data={"ticker": ticker}
        )
        
        if response.status_code == 200:
            data = response.json()
            return FinancialStatement(**data)
        else:
            logger.warning(f"Failed to fetch financial data for {ticker}: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching financial data for {ticker}: {e}")
        return None


async def fetch_market_news(ticker: str, limit: int = 10) -> List[MarketNews]:
    """
    Fetch market news from MarketDataMCP.
    
    Args:
        ticker: Stock ticker symbol
        limit: Maximum number of news items
        
    Returns:
        List of market news items
    """
    try:
        market_data_url = SERVICE_URLS["market_data_mcp"]
        response = await http_client.post(
            f"{market_data_url}/mcp/get_market_news",
            json_data={"ticker": ticker, "limit": limit}
        )
        
        if response.status_code == 200:
            data = response.json()
            return [MarketNews(**item) for item in data["news"]]
        else:
            logger.warning(f"Failed to fetch news for {ticker}: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        return []


async def get_available_tickers() -> List[str]:
    """
    Get list of available tickers from MarketDataMCP.
    
    Returns:
        List of available ticker symbols
    """
    try:
        market_data_url = SERVICE_URLS["market_data_mcp"]
        response = await http_client.get(f"{market_data_url}/mcp/available_tickers")
        
        if response.status_code == 200:
            data = response.json()
            return list(data["tickers"].keys())
        else:
            logger.warning(f"Failed to fetch available tickers: {response.status_code}")
            return ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "META"]  # Fallback
            
    except Exception as e:
        logger.error(f"Error fetching available tickers: {e}")
        return ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "META"]  # Fallback


def calculate_financial_score(financial_data: FinancialStatement) -> float:
    """
    Calculate fundamental strength score based on financial metrics.
    
    Args:
        financial_data: Financial statement data
        
    Returns:
        Score from 0-100 indicating financial strength
    """
    score = 0.0
    
    # Profitability metrics (40% of score)
    if financial_data.net_income > 0:
        score += 20  # Profitable company
        
        # Return on Assets
        roa = financial_data.return_on_assets
        if roa > 0.15:
            score += 10
        elif roa > 0.10:
            score += 7
        elif roa > 0.05:
            score += 4
        
        # Profit margin
        profit_margin = financial_data.net_income / financial_data.revenue if financial_data.revenue > 0 else 0
        if profit_margin > 0.20:
            score += 10
        elif profit_margin > 0.15:
            score += 7
        elif profit_margin > 0.10:
            score += 4
    
    # Financial stability (30% of score)
    debt_to_equity = financial_data.debt_to_equity_ratio
    if debt_to_equity < 0.3:
        score += 15  # Low debt
    elif debt_to_equity < 0.5:
        score += 10
    elif debt_to_equity < 1.0:
        score += 5
    
    # Cash position (15% of score)
    cash_ratio = financial_data.cash / financial_data.total_assets if financial_data.total_assets > 0 else 0
    if cash_ratio > 0.20:
        score += 15
    elif cash_ratio > 0.15:
        score += 10
    elif cash_ratio > 0.10:
        score += 7
    elif cash_ratio > 0.05:
        score += 4
    
    # Revenue scale (15% of score)
    if financial_data.revenue > 50_000_000_000:  # $50B+
        score += 15
    elif financial_data.revenue > 10_000_000_000:  # $10B+
        score += 12
    elif financial_data.revenue > 1_000_000_000:  # $1B+
        score += 8
    elif financial_data.revenue > 100_000_000:  # $100M+
        score += 4
    
    return min(score, 100.0)


def analyze_news_sentiment(news_items: List[MarketNews]) -> Dict:
    """
    Analyze overall news sentiment for a company.
    
    Args:
        news_items: List of news items
        
    Returns:
        Dictionary with sentiment analysis results
    """
    if not news_items:
        return {
            "overall_sentiment": "neutral",
            "sentiment_score": 0.0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0
        }
    
    positive_count = sum(1 for item in news_items if item.sentiment == Sentiment.POSITIVE)
    negative_count = sum(1 for item in news_items if item.sentiment == Sentiment.NEGATIVE)
    neutral_count = sum(1 for item in news_items if item.sentiment == Sentiment.NEUTRAL)
    
    total_items = len(news_items)
    
    # Calculate weighted sentiment score (-1 to +1)
    sentiment_score = (positive_count - negative_count) / total_items
    
    # Determine overall sentiment
    if sentiment_score > 0.2:
        overall_sentiment = "positive"
    elif sentiment_score < -0.2:
        overall_sentiment = "negative"
    else:
        overall_sentiment = "neutral"
    
    return {
        "overall_sentiment": overall_sentiment,
        "sentiment_score": sentiment_score,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "total_news": total_items
    }


def generate_analysis_insights(
    ticker: str,
    financial_data: FinancialStatement,
    news_sentiment: Dict,
    financial_score: float
) -> Dict:
    """
    Generate detailed analysis insights and recommendations.
    
    Args:
        ticker: Stock ticker
        financial_data: Financial statement data
        news_sentiment: News sentiment analysis
        financial_score: Calculated financial score
        
    Returns:
        Dictionary with analysis insights
    """
    strengths = []
    weaknesses = []
    
    # Financial strengths/weaknesses
    if financial_data.net_income > 0:
        strengths.append(f"Profitable with ${financial_data.net_income:,.0f} net income")
    else:
        weaknesses.append(f"Unprofitable with ${abs(financial_data.net_income):,.0f} net loss")
    
    roa = financial_data.return_on_assets
    if roa > 0.10:
        strengths.append(f"Strong ROA of {roa:.1%}")
    elif roa < 0.05:
        weaknesses.append(f"Low ROA of {roa:.1%}")
    
    debt_ratio = financial_data.debt_to_equity_ratio
    if debt_ratio < 0.5:
        strengths.append(f"Conservative debt level (D/E: {debt_ratio:.2f})")
    elif debt_ratio > 1.0:
        weaknesses.append(f"High debt burden (D/E: {debt_ratio:.2f})")
    
    cash_ratio = financial_data.cash / financial_data.total_assets
    if cash_ratio > 0.15:
        strengths.append(f"Strong cash position ({cash_ratio:.1%} of assets)")
    elif cash_ratio < 0.05:
        weaknesses.append(f"Limited cash reserves ({cash_ratio:.1%} of assets)")
    
    # News sentiment insights
    if news_sentiment["overall_sentiment"] == "positive":
        strengths.append(f"Positive market sentiment ({news_sentiment['positive_count']} positive news)")
    elif news_sentiment["overall_sentiment"] == "negative":
        weaknesses.append(f"Negative market sentiment ({news_sentiment['negative_count']} negative news)")
    
    # Generate recommendation
    if financial_score >= 80:
        recommendation = "STRONG BUY - Excellent financial metrics and strong fundamentals"
    elif financial_score >= 70:
        recommendation = "BUY - Good financial health with solid fundamentals"
    elif financial_score >= 60:
        recommendation = "HOLD - Adequate fundamentals but some concerns"
    elif financial_score >= 50:
        recommendation = "WEAK HOLD - Below average fundamentals, monitor closely"
    else:
        recommendation = "AVOID - Poor financial metrics and weak fundamentals"
    
    # Calculate confidence based on data quality and consistency
    confidence = 0.8  # Base confidence
    
    # Adjust based on news sentiment alignment
    if (financial_score > 70 and news_sentiment["overall_sentiment"] == "positive") or \
       (financial_score < 50 and news_sentiment["overall_sentiment"] == "negative"):
        confidence += 0.1  # Sentiment aligns with fundamentals
    elif (financial_score > 70 and news_sentiment["overall_sentiment"] == "negative") or \
         (financial_score < 50 and news_sentiment["overall_sentiment"] == "positive"):
        confidence -= 0.1  # Sentiment conflicts with fundamentals
    
    confidence = max(0.5, min(1.0, confidence))  # Clamp between 0.5 and 1.0
    
    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendation": recommendation,
        "confidence": confidence
    }


async def analyze_company(ticker: str) -> Optional[FundamentalAnalysis]:
    """
    Perform comprehensive fundamental analysis on a company.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Fundamental analysis result or None if failed
    """
    logger.info(f"Starting fundamental analysis for {ticker}")
    
    try:
        # Fetch financial data and news concurrently
        financial_task = fetch_financial_data(ticker)
        news_task = fetch_market_news(ticker, 10)
        
        financial_data, news_items = await asyncio.gather(financial_task, news_task)
        
        if not financial_data:
            logger.warning(f"No financial data available for {ticker}")
            return None
        
        # Calculate financial score
        financial_score = calculate_financial_score(financial_data)
        
        # Analyze news sentiment
        news_sentiment = analyze_news_sentiment(news_items)
        
        # Generate insights
        insights = generate_analysis_insights(ticker, financial_data, news_sentiment, financial_score)
        
        # Create analysis result
        analysis = FundamentalAnalysis(
            ticker=ticker,
            score=financial_score,
            strengths=insights["strengths"],
            weaknesses=insights["weaknesses"],
            recommendation=insights["recommendation"],
            confidence=insights["confidence"]
        )
        
        logger.info(f"Completed analysis for {ticker}: score={financial_score:.1f}, recommendation={insights['recommendation']}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {e}")
        return None


# A2A method handlers
async def perform_fundamental_analysis(
    sector: Optional[str] = None,
    criteria: Dict = None,
    max_companies: int = 5
) -> Dict:
    """
    Perform fundamental analysis on multiple companies.
    
    Args:
        sector: Preferred sector filter (not implemented in simulation)
        criteria: Analysis criteria (not implemented in simulation)
        max_companies: Maximum number of companies to analyze
        
    Returns:
        Dictionary with analysis results
    """
    logger.info(f"Performing fundamental analysis (max_companies: {max_companies})")
    
    try:
        # Get available tickers
        available_tickers = await get_available_tickers()
        
        # Limit to requested number of companies
        tickers_to_analyze = available_tickers[:max_companies]
        
        # Analyze companies concurrently
        analysis_tasks = [analyze_company(ticker) for ticker in tickers_to_analyze]
        analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Filter successful analyses and sort by score
        successful_analyses = []
        for result in analysis_results:
            if isinstance(result, FundamentalAnalysis):
                successful_analyses.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Analysis failed: {result}")
        
        # Sort by score (highest first)
        successful_analyses.sort(key=lambda x: x.score, reverse=True)
        
        # Prepare response
        companies = []
        for analysis in successful_analyses:
            companies.append({
                "ticker": analysis.ticker,
                "score": analysis.score,
                "recommendation": analysis.recommendation,
                "confidence": analysis.confidence,
                "strengths": analysis.strengths,
                "weaknesses": analysis.weaknesses
            })
        
        result = {
            "companies": companies,
            "total_analyzed": len(successful_analyses),
            "analysis_criteria": {
                "sector": sector,
                "max_companies": max_companies
            },
            "top_recommendation": companies[0] if companies else None
        }
        
        logger.info(f"Analysis complete: {len(successful_analyses)} companies analyzed")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in fundamental analysis: {e}")
        raise


# Register A2A methods
a2a_server.register_method("perform_fundamental_analysis", perform_fundamental_analysis)

# FastAPI endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "FundamentalAnalyst Agent", "status": "running", "version": "1.0.0"}


@app.post("/a2a")
async def a2a_endpoint(request: Request):
    """A2A protocol endpoint."""
    return await create_a2a_endpoint(a2a_server)(request)


@app.post("/analyze")
async def analyze_endpoint(request: AnalysisRequest) -> Dict:
    """
    Direct analysis endpoint for testing.
    
    Args:
        request: Analysis request
        
    Returns:
        Analysis results
    """
    return await perform_fundamental_analysis(
        sector=request.sector,
        criteria=request.criteria,
        max_companies=request.max_companies
    )


if __name__ == "__main__":
    import uvicorn
    
    port = PORTS["fundamental_analyst"]
    logger.info(f"Starting FundamentalAnalyst Agent on port {port}")
    
    uvicorn.run(
        "fundamental_analyst_agent:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
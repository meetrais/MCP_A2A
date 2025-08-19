"""
Unit tests for FundamentalAnalyst Agent.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from ..agents.fundamental_analyst_agent import (
    app, calculate_financial_score, analyze_news_sentiment,
    generate_analysis_insights, analyze_company, perform_fundamental_analysis
)
from ..models.market_data import FinancialStatement, MarketNews, Sentiment


class TestFundamentalAnalystAgent:
    """Test FundamentalAnalyst Agent functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "FundamentalAnalyst Agent"
        assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_a2a_endpoint_fundamental_analysis(self, client):
        """Test A2A endpoint for fundamental analysis."""
        with patch('MCP_A2A.agents.fundamental_analyst_agent.perform_fundamental_analysis') as mock_analysis:
            mock_analysis.return_value = {
                "companies": [
                    {
                        "ticker": "AAPL",
                        "score": 85.0,
                        "recommendation": "BUY",
                        "confidence": 0.9
                    }
                ],
                "total_analyzed": 1
            }
            
            response = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "perform_fundamental_analysis",
                    "params": {"max_companies": 1},
                    "id": "test-123"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == "test-123"
            assert "result" in data
            assert data["result"]["total_analyzed"] == 1
    
    def test_direct_analyze_endpoint(self, client):
        """Test direct analysis endpoint."""
        with patch('MCP_A2A.agents.fundamental_analyst_agent.perform_fundamental_analysis') as mock_analysis:
            mock_analysis.return_value = {
                "companies": [],
                "total_analyzed": 0
            }
            
            response = client.post(
                "/analyze",
                json={
                    "sector": "technology",
                    "max_companies": 3
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "companies" in data
            assert "total_analyzed" in data


class TestFinancialScoring:
    """Test financial scoring functionality."""
    
    @pytest.fixture
    def strong_financials(self):
        """Create strong financial statement."""
        return FinancialStatement(
            ticker="STRONG",
            revenue=100_000_000_000,  # $100B
            net_income=20_000_000_000,  # $20B profit
            total_assets=150_000_000_000,  # $150B assets
            total_debt=30_000_000_000,  # $30B debt (low D/E)
            cash=30_000_000_000,  # $30B cash (20% of assets)
            shares_outstanding=1_000_000_000,
            period="Q4 2024"
        )
    
    @pytest.fixture
    def weak_financials(self):
        """Create weak financial statement."""
        return FinancialStatement(
            ticker="WEAK",
            revenue=1_000_000_000,  # $1B
            net_income=-100_000_000,  # $100M loss
            total_assets=2_000_000_000,  # $2B assets
            total_debt=1_800_000_000,  # $1.8B debt (high D/E)
            cash=50_000_000,  # $50M cash (2.5% of assets)
            shares_outstanding=100_000_000,
            period="Q4 2024"
        )
    
    def test_calculate_strong_financial_score(self, strong_financials):
        """Test financial score calculation for strong company."""
        score = calculate_financial_score(strong_financials)
        assert score >= 80  # Should be high score
        assert score <= 100
    
    def test_calculate_weak_financial_score(self, weak_financials):
        """Test financial score calculation for weak company."""
        score = calculate_financial_score(weak_financials)
        assert score <= 30  # Should be low score
        assert score >= 0
    
    def test_financial_score_profitability_component(self):
        """Test profitability component of financial score."""
        # Profitable company
        profitable = FinancialStatement(
            ticker="PROFIT",
            revenue=10_000_000_000,
            net_income=2_000_000_000,  # 20% margin
            total_assets=15_000_000_000,
            total_debt=3_000_000_000,
            cash=2_000_000_000,
            shares_outstanding=1_000_000_000,
            period="Q4 2024"
        )
        
        # Unprofitable company
        unprofitable = FinancialStatement(
            ticker="LOSS",
            revenue=10_000_000_000,
            net_income=-500_000_000,  # Loss
            total_assets=15_000_000_000,
            total_debt=3_000_000_000,
            cash=2_000_000_000,
            shares_outstanding=1_000_000_000,
            period="Q4 2024"
        )
        
        profitable_score = calculate_financial_score(profitable)
        unprofitable_score = calculate_financial_score(unprofitable)
        
        assert profitable_score > unprofitable_score
    
    def test_financial_score_debt_component(self):
        """Test debt component of financial score."""
        # Low debt company
        low_debt = FinancialStatement(
            ticker="LOWDEBT",
            revenue=10_000_000_000,
            net_income=1_000_000_000,
            total_assets=20_000_000_000,
            total_debt=2_000_000_000,  # 10% debt ratio
            cash=3_000_000_000,
            shares_outstanding=1_000_000_000,
            period="Q4 2024"
        )
        
        # High debt company
        high_debt = FinancialStatement(
            ticker="HIGHDEBT",
            revenue=10_000_000_000,
            net_income=1_000_000_000,
            total_assets=20_000_000_000,
            total_debt=18_000_000_000,  # 90% debt ratio
            cash=1_000_000_000,
            shares_outstanding=1_000_000_000,
            period="Q4 2024"
        )
        
        low_debt_score = calculate_financial_score(low_debt)
        high_debt_score = calculate_financial_score(high_debt)
        
        assert low_debt_score > high_debt_score


class TestNewsSentimentAnalysis:
    """Test news sentiment analysis functionality."""
    
    @pytest.fixture
    def positive_news(self):
        """Create positive news items."""
        return [
            MarketNews(
                headline="Company reports strong earnings",
                summary="Positive results",
                sentiment=Sentiment.POSITIVE,
                date="2024-01-01",
                source="Reuters"
            ),
            MarketNews(
                headline="New product launch successful",
                summary="Market reception positive",
                sentiment=Sentiment.POSITIVE,
                date="2024-01-02",
                source="Bloomberg"
            )
        ]
    
    @pytest.fixture
    def negative_news(self):
        """Create negative news items."""
        return [
            MarketNews(
                headline="Company faces regulatory issues",
                summary="Challenges ahead",
                sentiment=Sentiment.NEGATIVE,
                date="2024-01-01",
                source="Reuters"
            ),
            MarketNews(
                headline="Revenue guidance lowered",
                summary="Disappointing outlook",
                sentiment=Sentiment.NEGATIVE,
                date="2024-01-02",
                source="Bloomberg"
            )
        ]
    
    @pytest.fixture
    def mixed_news(self):
        """Create mixed sentiment news items."""
        return [
            MarketNews(
                headline="Strong earnings reported",
                summary="Positive results",
                sentiment=Sentiment.POSITIVE,
                date="2024-01-01",
                source="Reuters"
            ),
            MarketNews(
                headline="Regulatory challenges ahead",
                summary="Some concerns",
                sentiment=Sentiment.NEGATIVE,
                date="2024-01-02",
                source="Bloomberg"
            ),
            MarketNews(
                headline="Routine board meeting",
                summary="Standard update",
                sentiment=Sentiment.NEUTRAL,
                date="2024-01-03",
                source="CNBC"
            )
        ]
    
    def test_analyze_positive_news_sentiment(self, positive_news):
        """Test analysis of positive news sentiment."""
        result = analyze_news_sentiment(positive_news)
        
        assert result["overall_sentiment"] == "positive"
        assert result["sentiment_score"] > 0.2
        assert result["positive_count"] == 2
        assert result["negative_count"] == 0
        assert result["neutral_count"] == 0
        assert result["total_news"] == 2
    
    def test_analyze_negative_news_sentiment(self, negative_news):
        """Test analysis of negative news sentiment."""
        result = analyze_news_sentiment(negative_news)
        
        assert result["overall_sentiment"] == "negative"
        assert result["sentiment_score"] < -0.2
        assert result["positive_count"] == 0
        assert result["negative_count"] == 2
        assert result["neutral_count"] == 0
        assert result["total_news"] == 2
    
    def test_analyze_mixed_news_sentiment(self, mixed_news):
        """Test analysis of mixed news sentiment."""
        result = analyze_news_sentiment(mixed_news)
        
        assert result["overall_sentiment"] == "neutral"
        assert -0.2 <= result["sentiment_score"] <= 0.2
        assert result["positive_count"] == 1
        assert result["negative_count"] == 1
        assert result["neutral_count"] == 1
        assert result["total_news"] == 3
    
    def test_analyze_empty_news_sentiment(self):
        """Test analysis with no news items."""
        result = analyze_news_sentiment([])
        
        assert result["overall_sentiment"] == "neutral"
        assert result["sentiment_score"] == 0.0
        assert result["positive_count"] == 0
        assert result["negative_count"] == 0
        assert result["neutral_count"] == 0
        assert result["total_news"] == 0


class TestAnalysisInsights:
    """Test analysis insights generation."""
    
    @pytest.fixture
    def sample_financials(self):
        """Create sample financial data."""
        return FinancialStatement(
            ticker="SAMPLE",
            revenue=50_000_000_000,
            net_income=8_000_000_000,
            total_assets=80_000_000_000,
            total_debt=20_000_000_000,
            cash=15_000_000_000,
            shares_outstanding=1_000_000_000,
            period="Q4 2024"
        )
    
    @pytest.fixture
    def positive_sentiment(self):
        """Create positive sentiment data."""
        return {
            "overall_sentiment": "positive",
            "sentiment_score": 0.6,
            "positive_count": 6,
            "negative_count": 2,
            "neutral_count": 2,
            "total_news": 10
        }
    
    def test_generate_strong_buy_insights(self, sample_financials, positive_sentiment):
        """Test insights generation for strong buy recommendation."""
        high_score = 85.0
        insights = generate_analysis_insights(
            "SAMPLE", sample_financials, positive_sentiment, high_score
        )
        
        assert "STRONG BUY" in insights["recommendation"]
        assert insights["confidence"] > 0.8
        assert len(insights["strengths"]) > 0
        assert "Profitable" in insights["strengths"][0]
    
    def test_generate_avoid_insights(self, positive_sentiment):
        """Test insights generation for avoid recommendation."""
        weak_financials = FinancialStatement(
            ticker="WEAK",
            revenue=1_000_000_000,
            net_income=-200_000_000,  # Loss
            total_assets=2_000_000_000,
            total_debt=1_900_000_000,  # High debt
            cash=10_000_000,  # Low cash
            shares_outstanding=100_000_000,
            period="Q4 2024"
        )
        
        low_score = 25.0
        insights = generate_analysis_insights(
            "WEAK", weak_financials, positive_sentiment, low_score
        )
        
        assert "AVOID" in insights["recommendation"]
        assert len(insights["weaknesses"]) > 0
        assert any("loss" in weakness.lower() for weakness in insights["weaknesses"])
    
    def test_confidence_adjustment_for_sentiment_alignment(self, sample_financials):
        """Test confidence adjustment based on sentiment alignment."""
        positive_sentiment = {"overall_sentiment": "positive"}
        negative_sentiment = {"overall_sentiment": "negative"}
        
        # High score with positive sentiment (aligned)
        aligned_insights = generate_analysis_insights(
            "ALIGNED", sample_financials, positive_sentiment, 80.0
        )
        
        # High score with negative sentiment (conflicted)
        conflicted_insights = generate_analysis_insights(
            "CONFLICTED", sample_financials, negative_sentiment, 80.0
        )
        
        assert aligned_insights["confidence"] > conflicted_insights["confidence"]


class TestCompanyAnalysis:
    """Test company analysis functionality."""
    
    @pytest.mark.asyncio
    async def test_analyze_company_success(self):
        """Test successful company analysis."""
        mock_financial_data = FinancialStatement(
            ticker="TEST",
            revenue=10_000_000_000,
            net_income=2_000_000_000,
            total_assets=15_000_000_000,
            total_debt=3_000_000_000,
            cash=2_500_000_000,
            shares_outstanding=1_000_000_000,
            period="Q4 2024"
        )
        
        mock_news = [
            MarketNews(
                headline="Positive news",
                summary="Good results",
                sentiment=Sentiment.POSITIVE,
                date="2024-01-01",
                source="Reuters"
            )
        ]
        
        with patch('MCP_A2A.agents.fundamental_analyst_agent.fetch_financial_data') as mock_fetch_financial, \
             patch('MCP_A2A.agents.fundamental_analyst_agent.fetch_market_news') as mock_fetch_news:
            
            mock_fetch_financial.return_value = mock_financial_data
            mock_fetch_news.return_value = mock_news
            
            result = await analyze_company("TEST")
            
            assert result is not None
            assert result.ticker == "TEST"
            assert result.score > 0
            assert result.confidence > 0
            assert len(result.strengths) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_company_no_financial_data(self):
        """Test company analysis with no financial data."""
        with patch('MCP_A2A.agents.fundamental_analyst_agent.fetch_financial_data') as mock_fetch_financial, \
             patch('MCP_A2A.agents.fundamental_analyst_agent.fetch_market_news') as mock_fetch_news:
            
            mock_fetch_financial.return_value = None
            mock_fetch_news.return_value = []
            
            result = await analyze_company("NODATA")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_perform_fundamental_analysis(self):
        """Test perform_fundamental_analysis function."""
        mock_analysis = MagicMock()
        mock_analysis.ticker = "AAPL"
        mock_analysis.score = 85.0
        mock_analysis.recommendation = "BUY"
        mock_analysis.confidence = 0.9
        mock_analysis.strengths = ["Strong financials"]
        mock_analysis.weaknesses = ["High valuation"]
        
        with patch('MCP_A2A.agents.fundamental_analyst_agent.get_available_tickers') as mock_tickers, \
             patch('MCP_A2A.agents.fundamental_analyst_agent.analyze_company') as mock_analyze:
            
            mock_tickers.return_value = ["AAPL", "GOOGL", "MSFT"]
            mock_analyze.return_value = mock_analysis
            
            result = await perform_fundamental_analysis(max_companies=2)
            
            assert "companies" in result
            assert "total_analyzed" in result
            assert result["total_analyzed"] == 2
            assert len(result["companies"]) == 2
            assert result["companies"][0]["ticker"] == "AAPL"
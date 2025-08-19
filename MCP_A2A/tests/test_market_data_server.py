"""
Unit tests for MarketData MCP Server.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from ..mcp_servers.market_data_server import app, generate_price_data, generate_market_news, generate_financial_statement


class TestMarketDataServer:
    """Test MarketData MCP Server functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "MarketData MCP Server"
        assert data["status"] == "running"
    
    def test_get_available_tickers(self, client):
        """Test available tickers endpoint."""
        response = client.get("/mcp/available_tickers")
        assert response.status_code == 200
        data = response.json()
        assert "tickers" in data
        assert "AAPL" in data["tickers"]
        assert "name" in data["tickers"]["AAPL"]
        assert "sector" in data["tickers"]["AAPL"]
    
    def test_get_stock_price_valid_ticker(self, client):
        """Test stock price endpoint with valid ticker."""
        response = client.post(
            "/mcp/get_stock_price",
            json={"ticker": "AAPL", "days": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert "data" in data
        assert len(data["data"]) == 10
        
        # Check price data structure
        price_point = data["data"][0]
        assert "date" in price_point
        assert "open" in price_point
        assert "high" in price_point
        assert "low" in price_point
        assert "close" in price_point
        assert "volume" in price_point
    
    def test_get_stock_price_invalid_ticker(self, client):
        """Test stock price endpoint with invalid ticker."""
        response = client.post(
            "/mcp/get_stock_price",
            json={"ticker": "INVALID", "days": 10}
        )
        assert response.status_code == 400
    
    def test_get_market_news_valid_ticker(self, client):
        """Test market news endpoint with valid ticker."""
        response = client.post(
            "/mcp/get_market_news",
            json={"ticker": "GOOGL", "limit": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "GOOGL"
        assert "news" in data
        assert len(data["news"]) == 5
        
        # Check news item structure
        news_item = data["news"][0]
        assert "headline" in news_item
        assert "summary" in news_item
        assert "sentiment" in news_item
        assert "date" in news_item
        assert "source" in news_item
        assert "relevance_score" in news_item
    
    def test_get_market_news_invalid_ticker(self, client):
        """Test market news endpoint with invalid ticker."""
        response = client.post(
            "/mcp/get_market_news",
            json={"ticker": "INVALID", "limit": 5}
        )
        assert response.status_code == 400
    
    def test_get_financial_statements_valid_ticker(self, client):
        """Test financial statements endpoint with valid ticker."""
        response = client.post(
            "/mcp/get_financial_statements",
            json={"ticker": "MSFT"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "MSFT"
        assert "revenue" in data
        assert "net_income" in data
        assert "total_assets" in data
        assert "total_debt" in data
        assert "cash" in data
        assert "shares_outstanding" in data
        assert "period" in data
        
        # Check that financial metrics are reasonable
        assert data["revenue"] > 0
        assert data["total_assets"] > 0
        assert data["shares_outstanding"] > 0
    
    def test_get_financial_statements_invalid_ticker(self, client):
        """Test financial statements endpoint with invalid ticker."""
        response = client.post(
            "/mcp/get_financial_statements",
            json={"ticker": "INVALID"}
        )
        assert response.status_code == 400


class TestDataGeneration:
    """Test data generation functions."""
    
    def test_generate_price_data(self):
        """Test price data generation."""
        price_data = generate_price_data("AAPL", 5)
        assert len(price_data) == 5
        
        for price_point in price_data:
            assert price_point.open > 0
            assert price_point.high > 0
            assert price_point.low > 0
            assert price_point.close > 0
            assert price_point.volume > 0
            assert price_point.high >= price_point.low
    
    def test_generate_price_data_invalid_ticker(self):
        """Test price data generation with invalid ticker."""
        with pytest.raises(ValueError):
            generate_price_data("INVALID", 5)
    
    def test_generate_market_news(self):
        """Test market news generation."""
        news_items = generate_market_news("TSLA", 3)
        assert len(news_items) == 3
        
        for news_item in news_items:
            assert news_item.headline
            assert news_item.summary
            assert news_item.sentiment in ["positive", "negative", "neutral"]
            assert news_item.source
            assert 0 <= news_item.relevance_score <= 1
    
    def test_generate_market_news_invalid_ticker(self):
        """Test market news generation with invalid ticker."""
        with pytest.raises(ValueError):
            generate_market_news("INVALID", 3)
    
    def test_generate_financial_statement(self):
        """Test financial statement generation."""
        financial_data = generate_financial_statement("NVDA")
        
        assert financial_data.ticker == "NVDA"
        assert financial_data.revenue > 0
        assert financial_data.total_assets > 0
        assert financial_data.shares_outstanding > 0
        assert financial_data.period == "Q4 2024"
        
        # Test calculated properties
        assert financial_data.debt_to_equity_ratio >= 0
        assert financial_data.return_on_assets >= 0
        assert financial_data.earnings_per_share != 0
    
    def test_generate_financial_statement_invalid_ticker(self):
        """Test financial statement generation with invalid ticker."""
        with pytest.raises(ValueError):
            generate_financial_statement("INVALID")
    
    def test_price_data_consistency(self):
        """Test that generated price data is consistent."""
        # Generate data multiple times and check for reasonable variation
        price_data_1 = generate_price_data("AAPL", 10)
        price_data_2 = generate_price_data("AAPL", 10)
        
        # Data should be different (random generation)
        assert price_data_1 != price_data_2
        
        # But should have same structure
        assert len(price_data_1) == len(price_data_2)
        
        for i in range(len(price_data_1)):
            assert price_data_1[i].date == price_data_2[i].date  # Same dates
    
    def test_news_sentiment_distribution(self):
        """Test that news sentiment has reasonable distribution."""
        # Generate many news items and check sentiment distribution
        all_sentiments = []
        for _ in range(100):
            news_items = generate_market_news("AAPL", 10)
            all_sentiments.extend([item.sentiment for item in news_items])
        
        # Should have all three sentiment types
        sentiments_set = set(all_sentiments)
        assert "positive" in sentiments_set
        assert "negative" in sentiments_set
        assert "neutral" in sentiments_set
    
    def test_financial_metrics_reasonableness(self):
        """Test that financial metrics are reasonable."""
        for ticker in ["AAPL", "GOOGL", "MSFT"]:
            financial_data = generate_financial_statement(ticker)
            
            # Basic sanity checks
            assert financial_data.revenue > 0
            assert financial_data.total_assets > financial_data.total_debt
            assert financial_data.cash >= 0
            assert financial_data.shares_outstanding > 0
            
            # Ratios should be reasonable
            assert 0 <= financial_data.debt_to_equity_ratio <= 2.0  # Reasonable debt levels
            assert -0.5 <= financial_data.return_on_assets <= 0.5  # Reasonable ROA
"""
Unit tests for TechnicalAnalyst Agent.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from ..agents.technical_analyst_agent import (
    app, combine_indicator_signals, calculate_price_targets,
    perform_technical_analysis_internal, perform_technical_analysis
)
from ..models.trading_models import Signal
from ..models.market_data import StockPrice, PriceData


class TestTechnicalAnalystAgent:
    """Test TechnicalAnalyst Agent functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "TechnicalAnalyst Agent"
        assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_a2a_endpoint_technical_analysis(self, client):
        """Test A2A endpoint for technical analysis."""
        with patch('MCP_A2A.agents.technical_analyst_agent.perform_technical_analysis') as mock_analysis:
            mock_analysis.return_value = {
                "ticker": "AAPL",
                "signal": "BUY",
                "confidence": 0.8,
                "rationale": "Strong bullish signals",
                "indicators": {"RSI": [65.0]},
                "price_targets": {"entry_price": 150.0, "target_price": 160.0, "stop_loss": 145.0}
            }
            
            response = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "perform_technical_analysis",
                    "params": {"ticker": "AAPL"},
                    "id": "test-123"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == "test-123"
            assert "result" in data
            assert data["result"]["ticker"] == "AAPL"
            assert data["result"]["signal"] == "BUY"
    
    def test_direct_analyze_endpoint(self, client):
        """Test direct analysis endpoint."""
        with patch('MCP_A2A.agents.technical_analyst_agent.perform_technical_analysis') as mock_analysis:
            mock_analysis.return_value = {
                "ticker": "GOOGL",
                "signal": "HOLD",
                "confidence": 0.5,
                "rationale": "Mixed signals"
            }
            
            response = client.post(
                "/analyze",
                json={
                    "ticker": "GOOGL",
                    "indicators": ["RSI", "SMA"],
                    "lookback_days": 30
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "GOOGL"
            assert data["signal"] == "HOLD"


class TestSignalCombination:
    """Test signal combination functionality."""
    
    def test_combine_bullish_signals(self):
        """Test combination of bullish indicator signals."""
        indicator_results = [
            {
                "indicator": "RSI",
                "signal": "BUY",
                "confidence": 0.8,
                "signal_reason": "RSI oversold"
            },
            {
                "indicator": "SMA",
                "signal": "BUY",
                "confidence": 0.7,
                "signal_reason": "Price above SMA"
            },
            {
                "indicator": "MACD",
                "signal": "BUY",
                "confidence": 0.6,
                "signal_reason": "MACD bullish crossover"
            }
        ]
        
        result = combine_indicator_signals(indicator_results)
        
        assert result["signal"] == Signal.BUY
        assert result["confidence"] > 0.6
        assert "BUY" in result["rationale"]
        assert result["signal_breakdown"]["buy_count"] == 3
        assert result["signal_breakdown"]["total_indicators"] == 3
    
    def test_combine_bearish_signals(self):
        """Test combination of bearish indicator signals."""
        indicator_results = [
            {
                "indicator": "RSI",
                "signal": "SELL",
                "confidence": 0.9,
                "signal_reason": "RSI overbought"
            },
            {
                "indicator": "SMA",
                "signal": "SELL",
                "confidence": 0.8,
                "signal_reason": "Price below SMA"
            }
        ]
        
        result = combine_indicator_signals(indicator_results)
        
        assert result["signal"] == Signal.SELL
        assert result["confidence"] > 0.7
        assert "SELL" in result["rationale"]
        assert result["signal_breakdown"]["sell_count"] == 2
    
    def test_combine_mixed_signals(self):
        """Test combination of mixed indicator signals."""
        indicator_results = [
            {
                "indicator": "RSI",
                "signal": "BUY",
                "confidence": 0.6,
                "signal_reason": "RSI oversold"
            },
            {
                "indicator": "SMA",
                "signal": "SELL",
                "confidence": 0.7,
                "signal_reason": "Price below SMA"
            },
            {
                "indicator": "MACD",
                "signal": "HOLD",
                "confidence": 0.5,
                "signal_reason": "MACD neutral"
            }
        ]
        
        result = combine_indicator_signals(indicator_results)
        
        # With mixed signals, should default to HOLD or the strongest signal
        assert result["signal"] in [Signal.HOLD, Signal.SELL]  # SELL has higher confidence
        assert "Mixed signals" in result["rationale"]
        assert result["signal_breakdown"]["buy_count"] == 1
        assert result["signal_breakdown"]["sell_count"] == 1
        assert result["signal_breakdown"]["hold_count"] == 1
    
    def test_combine_empty_signals(self):
        """Test combination with no indicator signals."""
        result = combine_indicator_signals([])
        
        assert result["signal"] == Signal.HOLD
        assert result["confidence"] == 0.0
        assert "No indicator data" in result["rationale"]
    
    def test_combine_invalid_signals(self):
        """Test combination with invalid indicator results."""
        indicator_results = [
            {"invalid": "data"},
            None,
            {"signal": "BUY"}  # Missing confidence
        ]
        
        result = combine_indicator_signals(indicator_results)
        
        assert result["signal"] == Signal.BUY  # Only valid signal
        assert result["confidence"] == 0.0  # No confidence provided


class TestPriceTargets:
    """Test price target calculation functionality."""
    
    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data."""
        return [
            PriceData(date="2024-01-01", open=100.0, high=105.0, low=98.0, close=102.0, volume=1000000),
            PriceData(date="2024-01-02", open=102.0, high=108.0, low=101.0, close=106.0, volume=1200000),
            PriceData(date="2024-01-03", open=106.0, high=110.0, low=104.0, close=108.0, volume=1100000),
            PriceData(date="2024-01-04", open=108.0, high=112.0, low=106.0, close=110.0, volume=1300000),
            PriceData(date="2024-01-05", open=110.0, high=115.0, low=108.0, close=112.0, volume=1400000),
            # Add more data points to meet minimum requirement
            *[PriceData(date=f"2024-01-{i:02d}", open=110.0, high=115.0, low=108.0, close=112.0, volume=1000000) 
              for i in range(6, 25)]
        ]
    
    def test_calculate_buy_price_targets(self, sample_price_data):
        """Test price target calculation for buy signals."""
        current_price = 112.0
        
        targets = calculate_price_targets(
            current_price, Signal.BUY, 0.8, sample_price_data
        )
        
        assert targets["entry_price"] == current_price
        assert targets["target_price"] is not None
        assert targets["target_price"] > current_price
        assert targets["stop_loss"] is not None
        assert targets["stop_loss"] < current_price
        assert "support_level" in targets
        assert "resistance_level" in targets
        assert "volatility" in targets
    
    def test_calculate_sell_price_targets(self, sample_price_data):
        """Test price target calculation for sell signals."""
        current_price = 112.0
        
        targets = calculate_price_targets(
            current_price, Signal.SELL, 0.7, sample_price_data
        )
        
        assert targets["entry_price"] == current_price
        assert targets["target_price"] is not None
        assert targets["target_price"] < current_price
        assert targets["stop_loss"] is not None
        assert targets["stop_loss"] > current_price
    
    def test_calculate_hold_price_targets(self, sample_price_data):
        """Test price target calculation for hold signals."""
        current_price = 112.0
        
        targets = calculate_price_targets(
            current_price, Signal.HOLD, 0.5, sample_price_data
        )
        
        assert targets["entry_price"] == current_price
        # HOLD signals don't set targets
        assert targets["target_price"] is None
        assert targets["stop_loss"] is None
    
    def test_calculate_targets_insufficient_data(self):
        """Test price target calculation with insufficient data."""
        short_data = [
            PriceData(date="2024-01-01", open=100.0, high=105.0, low=98.0, close=102.0, volume=1000000)
        ]
        
        targets = calculate_price_targets(102.0, Signal.BUY, 0.8, short_data)
        
        assert targets["entry_price"] == 102.0
        assert targets["target_price"] is None
        assert targets["stop_loss"] is None


class TestTechnicalAnalysisIntegration:
    """Test technical analysis integration functionality."""
    
    @pytest.fixture
    def mock_price_data(self):
        """Create mock price data."""
        return StockPrice(
            ticker="TEST",
            data=[
                PriceData(date="2024-01-01", open=100.0, high=105.0, low=98.0, close=102.0, volume=1000000),
                PriceData(date="2024-01-02", open=102.0, high=108.0, low=101.0, close=106.0, volume=1200000),
                *[PriceData(date=f"2024-01-{i:02d}", open=110.0, high=115.0, low=108.0, close=112.0, volume=1000000) 
                  for i in range(3, 25)]
            ]
        )
    
    @pytest.fixture
    def mock_indicator_results(self):
        """Create mock indicator results."""
        return [
            {
                "indicator": "RSI",
                "signal": "BUY",
                "confidence": 0.8,
                "signal_reason": "RSI oversold",
                "values": [25.0]
            },
            {
                "indicator": "SMA",
                "signal": "BUY",
                "confidence": 0.7,
                "signal_reason": "Price above SMA",
                "values": [110.0]
            }
        ]
    
    @pytest.mark.asyncio
    async def test_perform_technical_analysis_internal_success(self, mock_price_data, mock_indicator_results):
        """Test successful technical analysis."""
        with patch('MCP_A2A.agents.technical_analyst_agent.fetch_price_data') as mock_fetch, \
             patch('MCP_A2A.agents.technical_analyst_agent.calculate_technical_indicator') as mock_calc:
            
            mock_fetch.return_value = mock_price_data
            mock_calc.return_value = mock_indicator_results[0]  # Return first indicator result
            
            result = await perform_technical_analysis_internal("TEST", ["RSI"], 30)
            
            assert result is not None
            assert result.ticker == "TEST"
            assert result.signal in [Signal.BUY, Signal.SELL, Signal.HOLD]
            assert 0.0 <= result.confidence <= 1.0
            assert result.rationale is not None
    
    @pytest.mark.asyncio
    async def test_perform_technical_analysis_internal_no_data(self):
        """Test technical analysis with no price data."""
        with patch('MCP_A2A.agents.technical_analyst_agent.fetch_price_data') as mock_fetch:
            mock_fetch.return_value = None
            
            result = await perform_technical_analysis_internal("NODATA", ["RSI"], 30)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_perform_technical_analysis_internal_no_indicators(self, mock_price_data):
        """Test technical analysis with no valid indicators."""
        with patch('MCP_A2A.agents.technical_analyst_agent.fetch_price_data') as mock_fetch, \
             patch('MCP_A2A.agents.technical_analyst_agent.calculate_technical_indicator') as mock_calc:
            
            mock_fetch.return_value = mock_price_data
            mock_calc.return_value = None  # No valid indicator results
            
            result = await perform_technical_analysis_internal("TEST", ["RSI"], 30)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_perform_technical_analysis_a2a_method(self):
        """Test A2A method for technical analysis."""
        mock_analysis = MagicMock()
        mock_analysis.ticker = "AAPL"
        mock_analysis.signal = Signal.BUY
        mock_analysis.confidence = 0.8
        mock_analysis.rationale = "Strong buy signals"
        mock_analysis.indicators = {"RSI": [25.0]}
        mock_analysis.entry_price = 150.0
        mock_analysis.target_price = 160.0
        mock_analysis.stop_loss = 145.0
        
        with patch('MCP_A2A.agents.technical_analyst_agent.perform_technical_analysis_internal') as mock_internal:
            mock_internal.return_value = mock_analysis
            
            result = await perform_technical_analysis("AAPL", ["RSI", "SMA"])
            
            assert result["ticker"] == "AAPL"
            assert result["signal"] == "BUY"
            assert result["confidence"] == 0.8
            assert "price_targets" in result
            assert result["price_targets"]["entry_price"] == 150.0
    
    @pytest.mark.asyncio
    async def test_perform_technical_analysis_failure(self):
        """Test A2A method with analysis failure."""
        with patch('MCP_A2A.agents.technical_analyst_agent.perform_technical_analysis_internal') as mock_internal:
            mock_internal.return_value = None
            
            result = await perform_technical_analysis("FAILED", ["RSI"])
            
            assert result["ticker"] == "FAILED"
            assert result["signal"] == "HOLD"
            assert result["confidence"] == 0.0
            assert "insufficient data" in result["rationale"].lower()


class TestIndicatorParameterHandling:
    """Test indicator parameter handling."""
    
    @pytest.mark.asyncio
    async def test_default_indicator_parameters(self):
        """Test that default parameters are set for indicators."""
        mock_price_data = StockPrice(
            ticker="TEST",
            data=[PriceData(date="2024-01-01", open=100.0, high=105.0, low=98.0, close=102.0, volume=1000000)]
        )
        
        with patch('MCP_A2A.agents.technical_analyst_agent.fetch_price_data') as mock_fetch, \
             patch('MCP_A2A.agents.technical_analyst_agent.calculate_technical_indicator') as mock_calc:
            
            mock_fetch.return_value = mock_price_data
            mock_calc.return_value = {
                "indicator": "RSI",
                "signal": "HOLD",
                "confidence": 0.5,
                "values": [50.0]
            }
            
            await perform_technical_analysis_internal("TEST", ["RSI", "SMA", "MACD", "BB"], 30)
            
            # Verify that calculate_technical_indicator was called with correct parameters
            calls = mock_calc.call_args_list
            assert len(calls) == 4  # Four indicators
            
            # Check RSI parameters
            rsi_call = calls[0]
            assert rsi_call[0][2] == {"period": 14}  # RSI default period
            
            # Check SMA parameters
            sma_call = calls[1]
            assert sma_call[0][2] == {"period": 20}  # SMA default period
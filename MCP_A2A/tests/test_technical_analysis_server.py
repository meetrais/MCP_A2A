"""
Unit tests for TechnicalAnalysis MCP Server.
"""

import pytest
from fastapi.testclient import TestClient

from ..mcp_servers.technical_analysis_server import (
    app, calculate_sma, calculate_ema, calculate_rsi, 
    calculate_macd, calculate_bollinger_bands, generate_signal
)


class TestTechnicalAnalysisServer:
    """Test TechnicalAnalysis MCP Server functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_price_data(self):
        """Sample price data for testing."""
        return [
            {"close": 100.0},
            {"close": 102.0},
            {"close": 101.0},
            {"close": 103.0},
            {"close": 105.0},
            {"close": 104.0},
            {"close": 106.0},
            {"close": 108.0},
            {"close": 107.0},
            {"close": 109.0},
            {"close": 111.0},
            {"close": 110.0},
            {"close": 112.0},
            {"close": 114.0},
            {"close": 113.0},
            {"close": 115.0},
            {"close": 117.0},
            {"close": 116.0},
            {"close": 118.0},
            {"close": 120.0}
        ]
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "TechnicalAnalysis MCP Server"
        assert data["status"] == "running"
    
    def test_get_supported_indicators(self, client):
        """Test supported indicators endpoint."""
        response = client.get("/mcp/supported_indicators")
        assert response.status_code == 200
        data = response.json()
        assert "indicators" in data
        assert "SMA" in data["indicators"]
        assert "EMA" in data["indicators"]
        assert "RSI" in data["indicators"]
        assert "MACD" in data["indicators"]
        assert "BB" in data["indicators"]
    
    def test_calculate_sma_indicator(self, client, sample_price_data):
        """Test SMA indicator calculation."""
        response = client.post(
            "/mcp/calculate_indicator",
            json={
                "price_data": sample_price_data,
                "indicator_name": "SMA",
                "params": {"period": 5}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["indicator"] == "SMA"
        assert "values" in data
        assert "signal" in data
        assert "confidence" in data
        assert len(data["values"]) == len(sample_price_data) - 4  # 20 - 5 + 1 = 16
    
    def test_calculate_ema_indicator(self, client, sample_price_data):
        """Test EMA indicator calculation."""
        response = client.post(
            "/mcp/calculate_indicator",
            json={
                "price_data": sample_price_data,
                "indicator_name": "EMA",
                "params": {"period": 10}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["indicator"] == "EMA"
        assert "values" in data
        assert len(data["values"]) == len(sample_price_data) - 9  # 20 - 10 = 10
    
    def test_calculate_rsi_indicator(self, client, sample_price_data):
        """Test RSI indicator calculation."""
        response = client.post(
            "/mcp/calculate_indicator",
            json={
                "price_data": sample_price_data,
                "indicator_name": "RSI",
                "params": {"period": 14}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["indicator"] == "RSI"
        assert "values" in data
        assert len(data["values"]) == len(sample_price_data) - 14  # 20 - 14 = 6
        
        # RSI should be between 0 and 100
        for value in data["values"]:
            assert 0 <= value <= 100
    
    def test_calculate_macd_indicator(self, client, sample_price_data):
        """Test MACD indicator calculation."""
        response = client.post(
            "/mcp/calculate_indicator",
            json={
                "price_data": sample_price_data,
                "indicator_name": "MACD",
                "params": {"fast_period": 5, "slow_period": 10, "signal_period": 3}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["indicator"] == "MACD"
        assert "components" in data
        assert "macd" in data["components"]
        assert "signal" in data["components"]
        assert "histogram" in data["components"]
    
    def test_calculate_bollinger_bands(self, client, sample_price_data):
        """Test Bollinger Bands calculation."""
        response = client.post(
            "/mcp/calculate_indicator",
            json={
                "price_data": sample_price_data,
                "indicator_name": "BB",
                "params": {"period": 10, "std_dev": 2.0}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["indicator"] == "BB"
        assert "components" in data
        assert "upper" in data["components"]
        assert "middle" in data["components"]
        assert "lower" in data["components"]
        
        # Upper band should be higher than lower band
        upper = data["components"]["upper"]
        lower = data["components"]["lower"]
        for i in range(len(upper)):
            assert upper[i] > lower[i]
    
    def test_unsupported_indicator(self, client, sample_price_data):
        """Test unsupported indicator error."""
        response = client.post(
            "/mcp/calculate_indicator",
            json={
                "price_data": sample_price_data,
                "indicator_name": "UNKNOWN",
                "params": {}
            }
        )
        assert response.status_code == 400
    
    def test_insufficient_data(self, client):
        """Test insufficient data error."""
        short_data = [{"close": 100.0}, {"close": 101.0}]
        response = client.post(
            "/mcp/calculate_indicator",
            json={
                "price_data": short_data,
                "indicator_name": "SMA",
                "params": {"period": 20}
            }
        )
        assert response.status_code == 200  # Should return empty values, not error
        data = response.json()
        assert len(data["values"]) == 0


class TestIndicatorCalculations:
    """Test individual indicator calculation functions."""
    
    @pytest.fixture
    def sample_prices(self):
        """Sample price data for testing."""
        return [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112, 114, 113, 115, 117, 116, 118, 120]
    
    def test_calculate_sma(self, sample_prices):
        """Test SMA calculation."""
        sma_5 = calculate_sma(sample_prices, 5)
        assert len(sma_5) == len(sample_prices) - 4
        
        # First SMA value should be average of first 5 prices
        expected_first = sum(sample_prices[:5]) / 5
        assert abs(sma_5[0] - expected_first) < 0.001
    
    def test_calculate_ema(self, sample_prices):
        """Test EMA calculation."""
        ema_5 = calculate_ema(sample_prices, 5)
        assert len(ema_5) == len(sample_prices) - 4
        
        # EMA values should be different from SMA
        sma_5 = calculate_sma(sample_prices, 5)
        assert ema_5 != sma_5
    
    def test_calculate_rsi(self, sample_prices):
        """Test RSI calculation."""
        rsi = calculate_rsi(sample_prices, 14)
        assert len(rsi) == len(sample_prices) - 14
        
        # All RSI values should be between 0 and 100
        for value in rsi:
            assert 0 <= value <= 100
    
    def test_calculate_macd(self, sample_prices):
        """Test MACD calculation."""
        macd_result = calculate_macd(sample_prices, 5, 10, 3)
        
        assert "macd" in macd_result
        assert "signal" in macd_result
        assert "histogram" in macd_result
        
        # MACD line should exist
        assert len(macd_result["macd"]) > 0
        
        # Signal line should be shorter than MACD line
        assert len(macd_result["signal"]) <= len(macd_result["macd"])
        
        # Histogram should match signal line length
        assert len(macd_result["histogram"]) == len(macd_result["signal"])
    
    def test_calculate_bollinger_bands(self, sample_prices):
        """Test Bollinger Bands calculation."""
        bb_result = calculate_bollinger_bands(sample_prices, 10, 2.0)
        
        assert "upper" in bb_result
        assert "middle" in bb_result
        assert "lower" in bb_result
        
        # All bands should have same length
        assert len(bb_result["upper"]) == len(bb_result["middle"])
        assert len(bb_result["middle"]) == len(bb_result["lower"])
        
        # Upper > Middle > Lower
        for i in range(len(bb_result["upper"])):
            assert bb_result["upper"][i] > bb_result["middle"][i]
            assert bb_result["middle"][i] > bb_result["lower"][i]
    
    def test_sma_with_insufficient_data(self):
        """Test SMA with insufficient data."""
        short_prices = [100, 101, 102]
        sma = calculate_sma(short_prices, 5)
        assert len(sma) == 0
    
    def test_ema_with_insufficient_data(self):
        """Test EMA with insufficient data."""
        short_prices = [100, 101, 102]
        ema = calculate_ema(short_prices, 5)
        assert len(ema) == 0
    
    def test_rsi_with_insufficient_data(self):
        """Test RSI with insufficient data."""
        short_prices = [100, 101, 102]
        rsi = calculate_rsi(short_prices, 14)
        assert len(rsi) == 0


class TestSignalGeneration:
    """Test signal generation functionality."""
    
    def test_rsi_overbought_signal(self):
        """Test RSI overbought signal generation."""
        signal_info = generate_signal("RSI", [75.0], [120.0], {})
        assert signal_info["signal"] == "SELL"
        assert signal_info["confidence"] > 0
        assert "overbought" in signal_info["reason"]
    
    def test_rsi_oversold_signal(self):
        """Test RSI oversold signal generation."""
        signal_info = generate_signal("RSI", [25.0], [100.0], {})
        assert signal_info["signal"] == "BUY"
        assert signal_info["confidence"] > 0
        assert "oversold" in signal_info["reason"]
    
    def test_rsi_neutral_signal(self):
        """Test RSI neutral signal generation."""
        signal_info = generate_signal("RSI", [50.0], [110.0], {})
        assert signal_info["signal"] == "HOLD"
        assert signal_info["confidence"] == 0.0
        assert "neutral" in signal_info["reason"]
    
    def test_sma_bullish_signal(self):
        """Test SMA bullish signal generation."""
        signal_info = generate_signal("SMA", [100.0], [105.0], {})
        assert signal_info["signal"] == "BUY"
        assert signal_info["confidence"] > 0
        assert "above SMA" in signal_info["reason"]
    
    def test_sma_bearish_signal(self):
        """Test SMA bearish signal generation."""
        signal_info = generate_signal("SMA", [100.0], [95.0], {})
        assert signal_info["signal"] == "SELL"
        assert signal_info["confidence"] > 0
        assert "below SMA" in signal_info["reason"]
    
    def test_macd_bullish_crossover(self):
        """Test MACD bullish crossover signal."""
        macd_data = {"histogram": [-0.1, 0.1]}
        signal_info = generate_signal("MACD", macd_data, [120.0], {})
        assert signal_info["signal"] == "BUY"
        assert signal_info["confidence"] > 0
        assert "crossed above zero" in signal_info["reason"]
    
    def test_macd_bearish_crossover(self):
        """Test MACD bearish crossover signal."""
        macd_data = {"histogram": [0.1, -0.1]}
        signal_info = generate_signal("MACD", macd_data, [120.0], {})
        assert signal_info["signal"] == "SELL"
        assert signal_info["confidence"] > 0
        assert "crossed below zero" in signal_info["reason"]
    
    def test_bollinger_bands_upper_touch(self):
        """Test Bollinger Bands upper band signal."""
        bb_data = {"upper": [125.0], "lower": [115.0]}
        signal_info = generate_signal("BB", bb_data, [125.0], {})
        assert signal_info["signal"] == "SELL"
        assert signal_info["confidence"] > 0
        assert "upper Bollinger Band" in signal_info["reason"]
    
    def test_bollinger_bands_lower_touch(self):
        """Test Bollinger Bands lower band signal."""
        bb_data = {"upper": [125.0], "lower": [115.0]}
        signal_info = generate_signal("BB", bb_data, [115.0], {})
        assert signal_info["signal"] == "BUY"
        assert signal_info["confidence"] > 0
        assert "lower Bollinger Band" in signal_info["reason"]
    
    def test_insufficient_data_signal(self):
        """Test signal generation with insufficient data."""
        signal_info = generate_signal("RSI", [], [120.0], {})
        assert signal_info["signal"] == "HOLD"
        assert signal_info["confidence"] == 0.0
        assert "Insufficient data" in signal_info["reason"]
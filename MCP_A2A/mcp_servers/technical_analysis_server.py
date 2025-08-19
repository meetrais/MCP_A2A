"""
TechnicalAnalysisMCP Server - Provides technical indicator calculations and signal generation.
"""

from typing import Dict, List, Optional
import math
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..models.market_data import TechnicalIndicator
from ..utils.logging_config import setup_logging, get_logger
from ..config import PORTS

# Initialize logging
setup_logging("technical_analysis_mcp")
logger = get_logger(__name__)

app = FastAPI(
    title="TechnicalAnalysis MCP Server",
    description="Provides technical indicator calculations and signal generation",
    version="1.0.0"
)

# Request models
class PricePoint(BaseModel):
    """Single price data point."""
    close: float = Field(..., gt=0, description="Closing price")
    high: Optional[float] = Field(None, gt=0, description="High price")
    low: Optional[float] = Field(None, gt=0, description="Low price")
    volume: Optional[int] = Field(None, ge=0, description="Trading volume")

class IndicatorRequest(BaseModel):
    """Request for technical indicator calculation."""
    price_data: List[PricePoint] = Field(..., min_items=1, description="Historical price data")
    indicator_name: str = Field(..., description="Indicator name (RSI, SMA, EMA, MACD, BB)")
    params: Dict = Field(default_factory=dict, description="Indicator parameters")


def calculate_sma(prices: List[float], period: int) -> List[float]:
    """Calculate Simple Moving Average."""
    if len(prices) < period:
        return []
    
    sma_values = []
    for i in range(period - 1, len(prices)):
        avg = sum(prices[i - period + 1:i + 1]) / period
        sma_values.append(round(avg, 4))
    
    return sma_values


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """Calculate Exponential Moving Average."""
    if len(prices) < period:
        return []
    
    ema_values = []
    multiplier = 2 / (period + 1)
    
    # Start with SMA for first value
    sma = sum(prices[:period]) / period
    ema_values.append(round(sma, 4))
    
    # Calculate EMA for remaining values
    for i in range(period, len(prices)):
        ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
        ema_values.append(round(ema, 4))
    
    return ema_values


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return []
    
    # Calculate price changes
    changes = []
    for i in range(1, len(prices)):
        changes.append(prices[i] - prices[i-1])
    
    # Separate gains and losses
    gains = [max(change, 0) for change in changes]
    losses = [abs(min(change, 0)) for change in changes]
    
    rsi_values = []
    
    # Calculate initial average gain and loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Calculate first RSI value
    if avg_loss == 0:
        rsi_values.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi_values.append(round(rsi, 2))
    
    # Calculate remaining RSI values using smoothed averages
    for i in range(period, len(changes)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period
        
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            rsi_values.append(round(rsi, 2))
    
    return rsi_values


def calculate_macd(prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict:
    """Calculate MACD (Moving Average Convergence Divergence)."""
    if len(prices) < slow_period:
        return {"macd": [], "signal": [], "histogram": []}
    
    # Calculate EMAs
    ema_fast = calculate_ema(prices, fast_period)
    ema_slow = calculate_ema(prices, slow_period)
    
    # Align EMAs (slow EMA starts later)
    start_index = slow_period - fast_period
    ema_fast_aligned = ema_fast[start_index:]
    
    # Calculate MACD line
    macd_line = []
    for i in range(len(ema_slow)):
        macd_value = ema_fast_aligned[i] - ema_slow[i]
        macd_line.append(round(macd_value, 4))
    
    # Calculate signal line (EMA of MACD)
    signal_line = calculate_ema(macd_line, signal_period)
    
    # Calculate histogram (MACD - Signal)
    histogram = []
    signal_start = len(macd_line) - len(signal_line)
    for i in range(len(signal_line)):
        hist_value = macd_line[signal_start + i] - signal_line[i]
        histogram.append(round(hist_value, 4))
    
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram
    }


def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Dict:
    """Calculate Bollinger Bands."""
    if len(prices) < period:
        return {"upper": [], "middle": [], "lower": []}
    
    middle_band = calculate_sma(prices, period)
    upper_band = []
    lower_band = []
    
    for i in range(period - 1, len(prices)):
        # Calculate standard deviation for the period
        price_slice = prices[i - period + 1:i + 1]
        mean = sum(price_slice) / period
        variance = sum((p - mean) ** 2 for p in price_slice) / period
        std = math.sqrt(variance)
        
        # Calculate bands
        middle = middle_band[i - period + 1]
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        upper_band.append(round(upper, 4))
        lower_band.append(round(lower, 4))
    
    return {
        "upper": upper_band,
        "middle": middle_band,
        "lower": lower_band
    }


def generate_signal(indicator_name: str, values: List[float], prices: List[float], params: Dict) -> Dict:
    """Generate trading signals based on indicator values."""
    if not values or len(values) == 0:
        return {"signal": "HOLD", "confidence": 0.0, "reason": "Insufficient data"}
    
    latest_value = values[-1]
    signal = "HOLD"
    confidence = 0.0
    reason = ""
    
    if indicator_name.upper() == "RSI":
        if latest_value > 70:
            signal = "SELL"
            confidence = min((latest_value - 70) / 20, 1.0)  # Scale 70-90 to 0-1
            reason = f"RSI overbought at {latest_value}"
        elif latest_value < 30:
            signal = "BUY"
            confidence = min((30 - latest_value) / 20, 1.0)  # Scale 30-10 to 0-1
            reason = f"RSI oversold at {latest_value}"
        else:
            reason = f"RSI neutral at {latest_value}"
    
    elif indicator_name.upper() == "SMA":
        if len(prices) >= len(values):
            current_price = prices[-1]
            sma_value = latest_value
            
            if current_price > sma_value * 1.02:  # 2% above SMA
                signal = "BUY"
                confidence = min((current_price - sma_value) / sma_value / 0.05, 1.0)  # Scale to 5% max
                reason = f"Price {current_price} above SMA {sma_value}"
            elif current_price < sma_value * 0.98:  # 2% below SMA
                signal = "SELL"
                confidence = min((sma_value - current_price) / sma_value / 0.05, 1.0)
                reason = f"Price {current_price} below SMA {sma_value}"
            else:
                reason = f"Price {current_price} near SMA {sma_value}"
    
    elif indicator_name.upper() == "EMA":
        if len(prices) >= len(values):
            current_price = prices[-1]
            ema_value = latest_value
            
            if current_price > ema_value * 1.015:  # 1.5% above EMA
                signal = "BUY"
                confidence = min((current_price - ema_value) / ema_value / 0.03, 1.0)
                reason = f"Price {current_price} above EMA {ema_value}"
            elif current_price < ema_value * 0.985:  # 1.5% below EMA
                signal = "SELL"
                confidence = min((ema_value - current_price) / ema_value / 0.03, 1.0)
                reason = f"Price {current_price} below EMA {ema_value}"
            else:
                reason = f"Price {current_price} near EMA {ema_value}"
    
    elif indicator_name.upper() == "MACD":
        if isinstance(values, dict) and "histogram" in values:
            histogram = values["histogram"]
            if len(histogram) >= 2:
                current_hist = histogram[-1]
                prev_hist = histogram[-2]
                
                if current_hist > 0 and prev_hist <= 0:
                    signal = "BUY"
                    confidence = min(abs(current_hist) / 0.5, 1.0)  # Scale based on histogram value
                    reason = "MACD histogram crossed above zero"
                elif current_hist < 0 and prev_hist >= 0:
                    signal = "SELL"
                    confidence = min(abs(current_hist) / 0.5, 1.0)
                    reason = "MACD histogram crossed below zero"
                else:
                    reason = f"MACD histogram at {current_hist}"
    
    elif indicator_name.upper() == "BB":
        if isinstance(values, dict) and len(prices) > 0:
            upper = values.get("upper", [])
            lower = values.get("lower", [])
            
            if upper and lower:
                current_price = prices[-1]
                upper_band = upper[-1]
                lower_band = lower[-1]
                
                if current_price >= upper_band:
                    signal = "SELL"
                    confidence = min((current_price - upper_band) / upper_band / 0.02, 1.0)
                    reason = f"Price {current_price} at upper Bollinger Band {upper_band}"
                elif current_price <= lower_band:
                    signal = "BUY"
                    confidence = min((lower_band - current_price) / lower_band / 0.02, 1.0)
                    reason = f"Price {current_price} at lower Bollinger Band {lower_band}"
                else:
                    reason = f"Price {current_price} within Bollinger Bands"
    
    return {
        "signal": signal,
        "confidence": round(confidence, 3),
        "reason": reason
    }


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "TechnicalAnalysis MCP Server", "status": "running", "version": "1.0.0"}


@app.post("/mcp/calculate_indicator")
async def calculate_indicator(request: IndicatorRequest) -> Dict:
    """
    Calculate technical indicator and generate trading signal.
    
    Args:
        request: Indicator calculation request
        
    Returns:
        Dictionary containing indicator values and trading signal
    """
    try:
        indicator_name = request.indicator_name.upper()
        prices = [point.close for point in request.price_data]
        
        logger.info(f"Calculating {indicator_name} for {len(prices)} price points")
        
        # Calculate indicator based on type
        if indicator_name == "SMA":
            period = request.params.get("period", 20)
            values = calculate_sma(prices, period)
            
        elif indicator_name == "EMA":
            period = request.params.get("period", 20)
            values = calculate_ema(prices, period)
            
        elif indicator_name == "RSI":
            period = request.params.get("period", 14)
            values = calculate_rsi(prices, period)
            
        elif indicator_name == "MACD":
            fast_period = request.params.get("fast_period", 12)
            slow_period = request.params.get("slow_period", 26)
            signal_period = request.params.get("signal_period", 9)
            values = calculate_macd(prices, fast_period, slow_period, signal_period)
            
        elif indicator_name == "BB":
            period = request.params.get("period", 20)
            std_dev = request.params.get("std_dev", 2.0)
            values = calculate_bollinger_bands(prices, period, std_dev)
            
        else:
            raise ValueError(f"Unsupported indicator: {indicator_name}")
        
        # Generate trading signal
        signal_info = generate_signal(indicator_name, values, prices, request.params)
        
        result = TechnicalIndicator(
            indicator=indicator_name,
            values=values if isinstance(values, list) else [values],
            signal=signal_info["signal"],
            confidence=signal_info["confidence"],
            parameters=request.params
        )
        
        # Add signal reason to result
        result_dict = result.dict()
        result_dict["signal_reason"] = signal_info["reason"]
        
        # For complex indicators, include all components
        if isinstance(values, dict):
            result_dict["components"] = values
            result_dict["values"] = []  # Clear simple values for complex indicators
        
        logger.info(f"Generated {indicator_name} signal: {signal_info['signal']} (confidence: {signal_info['confidence']})")
        
        return result_dict
        
    except ValueError as e:
        logger.error(f"Invalid indicator request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating indicator: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/mcp/supported_indicators")
async def get_supported_indicators() -> Dict:
    """
    Get list of supported technical indicators.
    
    Returns:
        Dictionary containing supported indicators and their parameters
    """
    logger.info("Fetching supported indicators")
    
    return {
        "indicators": {
            "SMA": {
                "name": "Simple Moving Average",
                "parameters": {
                    "period": {"type": "int", "default": 20, "description": "Period for moving average"}
                }
            },
            "EMA": {
                "name": "Exponential Moving Average", 
                "parameters": {
                    "period": {"type": "int", "default": 20, "description": "Period for moving average"}
                }
            },
            "RSI": {
                "name": "Relative Strength Index",
                "parameters": {
                    "period": {"type": "int", "default": 14, "description": "Period for RSI calculation"}
                }
            },
            "MACD": {
                "name": "Moving Average Convergence Divergence",
                "parameters": {
                    "fast_period": {"type": "int", "default": 12, "description": "Fast EMA period"},
                    "slow_period": {"type": "int", "default": 26, "description": "Slow EMA period"},
                    "signal_period": {"type": "int", "default": 9, "description": "Signal line EMA period"}
                }
            },
            "BB": {
                "name": "Bollinger Bands",
                "parameters": {
                    "period": {"type": "int", "default": 20, "description": "Period for moving average"},
                    "std_dev": {"type": "float", "default": 2.0, "description": "Standard deviation multiplier"}
                }
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    port = PORTS["technical_analysis_mcp"]
    logger.info(f"Starting TechnicalAnalysis MCP Server on port {port}")
    
    uvicorn.run(
        "technical_analysis_server:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
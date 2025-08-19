"""
TechnicalAnalystAgent - Focuses on price action and market timing analysis.
"""

from typing import Dict, List, Optional
import asyncio
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from ..models.trading_models import TechnicalAnalysis, Signal
from ..models.market_data import StockPrice, PriceData
from ..utils.logging_config import setup_logging, get_logger
from ..utils.a2a_server import A2AServer, create_a2a_endpoint
from ..utils.http_client import HTTPClient
from ..config import PORTS, SERVICE_URLS

# Initialize logging
setup_logging("technical_analyst_agent")
logger = get_logger(__name__)

app = FastAPI(
    title="TechnicalAnalyst Agent",
    description="Provides technical analysis and market timing signals",
    version="1.0.0"
)

# Initialize A2A server and HTTP client
a2a_server = A2AServer()
http_client = HTTPClient()

# Request models
class TechnicalAnalysisRequest(BaseModel):
    """Request for technical analysis."""
    ticker: str = Field(..., description="Stock ticker symbol")
    indicators: List[str] = Field(default=["RSI", "SMA", "EMA"], description="Technical indicators to calculate")
    timeframe: str = Field(default="daily", description="Analysis timeframe")
    lookback_days: int = Field(default=50, description="Number of days of historical data")


async def fetch_price_data(ticker: str, days: int = 50) -> Optional[StockPrice]:
    """
    Fetch historical price data from MarketDataMCP.
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days of historical data
        
    Returns:
        Stock price data or None if failed
    """
    try:
        market_data_url = SERVICE_URLS["market_data_mcp"]
        response = await http_client.post(
            f"{market_data_url}/mcp/get_stock_price",
            json_data={"ticker": ticker, "days": days}
        )
        
        if response.status_code == 200:
            data = response.json()
            return StockPrice(**data)
        else:
            logger.warning(f"Failed to fetch price data for {ticker}: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching price data for {ticker}: {e}")
        return None


async def calculate_technical_indicator(
    price_data: List[PriceData],
    indicator_name: str,
    params: Dict = None
) -> Optional[Dict]:
    """
    Calculate technical indicator using TechnicalAnalysisMCP.
    
    Args:
        price_data: Historical price data
        indicator_name: Name of the indicator
        params: Indicator parameters
        
    Returns:
        Indicator calculation result or None if failed
    """
    try:
        if params is None:
            params = {}
        
        # Convert price data to format expected by MCP server
        price_points = []
        for point in price_data:
            price_points.append({
                "close": point.close,
                "high": point.high,
                "low": point.low,
                "volume": point.volume
            })
        
        technical_analysis_url = SERVICE_URLS["technical_analysis_mcp"]
        response = await http_client.post(
            f"{technical_analysis_url}/mcp/calculate_indicator",
            json_data={
                "price_data": price_points,
                "indicator_name": indicator_name,
                "params": params
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to calculate {indicator_name}: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error calculating {indicator_name}: {e}")
        return None


def combine_indicator_signals(indicator_results: List[Dict]) -> Dict:
    """
    Combine multiple indicator signals into a unified trading signal.
    
    Args:
        indicator_results: List of indicator calculation results
        
    Returns:
        Combined signal analysis
    """
    if not indicator_results:
        return {
            "signal": Signal.HOLD,
            "confidence": 0.0,
            "rationale": "No indicator data available"
        }
    
    # Collect all signals and confidences
    signals = []
    confidences = []
    signal_details = []
    
    for result in indicator_results:
        if result and "signal" in result:
            signal = result["signal"]
            confidence = result.get("confidence", 0.0)
            indicator = result.get("indicator", "Unknown")
            reason = result.get("signal_reason", "")
            
            signals.append(signal)
            confidences.append(confidence)
            signal_details.append({
                "indicator": indicator,
                "signal": signal,
                "confidence": confidence,
                "reason": reason
            })
    
    if not signals:
        return {
            "signal": Signal.HOLD,
            "confidence": 0.0,
            "rationale": "No valid signals generated"
        }
    
    # Count signal types
    buy_signals = sum(1 for s in signals if s == "BUY")
    sell_signals = sum(1 for s in signals if s == "SELL")
    hold_signals = sum(1 for s in signals if s == "HOLD")
    
    total_signals = len(signals)
    
    # Calculate weighted signal strength
    buy_weight = sum(conf for i, conf in enumerate(confidences) if signals[i] == "BUY")
    sell_weight = sum(conf for i, conf in enumerate(confidences) if signals[i] == "SELL")
    hold_weight = sum(conf for i, conf in enumerate(confidences) if signals[i] == "HOLD")
    
    total_weight = buy_weight + sell_weight + hold_weight
    
    # Determine overall signal
    if total_weight == 0:
        final_signal = Signal.HOLD
        final_confidence = 0.0
    elif buy_weight > sell_weight and buy_weight > hold_weight:
        final_signal = Signal.BUY
        final_confidence = min(buy_weight / total_weight, 1.0)
    elif sell_weight > buy_weight and sell_weight > hold_weight:
        final_signal = Signal.SELL
        final_confidence = min(sell_weight / total_weight, 1.0)
    else:
        final_signal = Signal.HOLD
        final_confidence = max(hold_weight / total_weight if total_weight > 0 else 0.0, 0.3)
    
    # Generate rationale
    if final_signal == Signal.BUY:
        rationale = f"Bullish consensus: {buy_signals}/{total_signals} indicators signal BUY"
    elif final_signal == Signal.SELL:
        rationale = f"Bearish consensus: {sell_signals}/{total_signals} indicators signal SELL"
    else:
        rationale = f"Mixed signals: {buy_signals} BUY, {sell_signals} SELL, {hold_signals} HOLD"
    
    # Add signal strength description
    if final_confidence >= 0.8:
        strength = "Very Strong"
    elif final_confidence >= 0.6:
        strength = "Strong"
    elif final_confidence >= 0.4:
        strength = "Moderate"
    elif final_confidence >= 0.2:
        strength = "Weak"
    else:
        strength = "Very Weak"
    
    return {
        "signal": final_signal,
        "confidence": round(final_confidence, 3),
        "rationale": f"{strength} {final_signal.value} signal. {rationale}",
        "signal_breakdown": {
            "buy_count": buy_signals,
            "sell_count": sell_signals,
            "hold_count": hold_signals,
            "total_indicators": total_signals
        },
        "indicator_details": signal_details
    }


def calculate_price_targets(
    current_price: float,
    signal: Signal,
    confidence: float,
    price_data: List[PriceData]
) -> Dict:
    """
    Calculate price targets and stop loss levels.
    
    Args:
        current_price: Current stock price
        signal: Trading signal
        confidence: Signal confidence
        price_data: Historical price data
        
    Returns:
        Dictionary with price targets and stop loss
    """
    if len(price_data) < 20:
        return {
            "entry_price": current_price,
            "target_price": None,
            "stop_loss": None
        }
    
    # Calculate recent volatility (20-day)
    recent_prices = [p.close for p in price_data[-20:]]
    avg_price = sum(recent_prices) / len(recent_prices)
    volatility = sum(abs(p - avg_price) for p in recent_prices) / len(recent_prices) / avg_price
    
    # Calculate support and resistance levels
    highs = [p.high for p in price_data[-20:]]
    lows = [p.low for p in price_data[-20:]]
    
    resistance = max(highs)
    support = min(lows)
    
    entry_price = current_price
    target_price = None
    stop_loss = None
    
    if signal == Signal.BUY:
        # For buy signals, target is resistance level or volatility-based
        volatility_target = current_price * (1 + volatility * confidence * 2)
        resistance_target = resistance * 1.02  # 2% above resistance
        target_price = min(volatility_target, resistance_target)
        
        # Stop loss below recent support
        stop_loss = max(support * 0.98, current_price * (1 - volatility * 1.5))
        
    elif signal == Signal.SELL:
        # For sell signals, target is support level or volatility-based
        volatility_target = current_price * (1 - volatility * confidence * 2)
        support_target = support * 0.98  # 2% below support
        target_price = max(volatility_target, support_target)
        
        # Stop loss above recent resistance
        stop_loss = min(resistance * 1.02, current_price * (1 + volatility * 1.5))
    
    return {
        "entry_price": round(entry_price, 2),
        "target_price": round(target_price, 2) if target_price else None,
        "stop_loss": round(stop_loss, 2) if stop_loss else None,
        "support_level": round(support, 2),
        "resistance_level": round(resistance, 2),
        "volatility": round(volatility * 100, 2)  # As percentage
    }


async def perform_technical_analysis_internal(
    ticker: str,
    indicators: List[str],
    lookback_days: int
) -> Optional[TechnicalAnalysis]:
    """
    Perform comprehensive technical analysis on a stock.
    
    Args:
        ticker: Stock ticker symbol
        indicators: List of technical indicators to calculate
        lookback_days: Number of days of historical data
        
    Returns:
        Technical analysis result or None if failed
    """
    logger.info(f"Starting technical analysis for {ticker}")
    
    try:
        # Fetch price data
        price_data = await fetch_price_data(ticker, lookback_days)
        if not price_data or not price_data.data:
            logger.warning(f"No price data available for {ticker}")
            return None
        
        # Calculate indicators concurrently
        indicator_tasks = []
        for indicator in indicators:
            # Set default parameters for each indicator
            params = {}
            if indicator == "RSI":
                params = {"period": 14}
            elif indicator in ["SMA", "EMA"]:
                params = {"period": 20}
            elif indicator == "MACD":
                params = {"fast_period": 12, "slow_period": 26, "signal_period": 9}
            elif indicator == "BB":
                params = {"period": 20, "std_dev": 2.0}
            
            task = calculate_technical_indicator(price_data.data, indicator, params)
            indicator_tasks.append(task)
        
        indicator_results = await asyncio.gather(*indicator_tasks, return_exceptions=True)
        
        # Filter successful results
        valid_results = []
        indicator_values = {}
        
        for i, result in enumerate(indicator_results):
            if isinstance(result, dict) and result:
                valid_results.append(result)
                indicator_name = indicators[i]
                
                # Store indicator values
                if "values" in result:
                    indicator_values[indicator_name] = result["values"]
                elif "components" in result:
                    indicator_values[indicator_name] = result["components"]
            elif isinstance(result, Exception):
                logger.warning(f"Indicator calculation failed: {result}")
        
        if not valid_results:
            logger.warning(f"No valid indicator results for {ticker}")
            return None
        
        # Combine signals
        combined_signal = combine_indicator_signals(valid_results)
        
        # Calculate price targets
        current_price = price_data.data[-1].close
        price_targets = calculate_price_targets(
            current_price,
            Signal(combined_signal["signal"]),
            combined_signal["confidence"],
            price_data.data
        )
        
        # Create technical analysis result
        analysis = TechnicalAnalysis(
            ticker=ticker,
            signal=Signal(combined_signal["signal"]),
            confidence=combined_signal["confidence"],
            indicators=indicator_values,
            entry_price=price_targets["entry_price"],
            stop_loss=price_targets["stop_loss"],
            target_price=price_targets["target_price"],
            rationale=combined_signal["rationale"]
        )
        
        logger.info(f"Technical analysis complete for {ticker}: {combined_signal['signal']} (confidence: {combined_signal['confidence']:.3f})")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error in technical analysis for {ticker}: {e}")
        return None


# A2A method handlers
async def perform_technical_analysis(
    ticker: str,
    indicators: List[str] = None,
    timeframe: str = "daily",
    lookback_days: int = 50
) -> Dict:
    """
    Perform technical analysis on a specific stock.
    
    Args:
        ticker: Stock ticker symbol
        indicators: List of technical indicators to use
        timeframe: Analysis timeframe (not implemented in simulation)
        lookback_days: Number of days of historical data
        
    Returns:
        Dictionary with technical analysis results
    """
    if indicators is None:
        indicators = ["RSI", "SMA", "EMA", "MACD"]
    
    logger.info(f"Performing technical analysis for {ticker} with indicators: {indicators}")
    
    try:
        analysis = await perform_technical_analysis_internal(ticker, indicators, lookback_days)
        
        if not analysis:
            return {
                "ticker": ticker,
                "signal": Signal.HOLD.value,
                "confidence": 0.0,
                "rationale": "Unable to perform technical analysis - insufficient data",
                "indicators": {},
                "price_targets": {}
            }
        
        # Prepare response
        result = {
            "ticker": analysis.ticker,
            "signal": analysis.signal.value,
            "confidence": analysis.confidence,
            "rationale": analysis.rationale,
            "indicators": analysis.indicators,
            "price_targets": {
                "entry_price": analysis.entry_price,
                "target_price": analysis.target_price,
                "stop_loss": analysis.stop_loss
            },
            "analysis_parameters": {
                "indicators_used": indicators,
                "lookback_days": lookback_days,
                "timeframe": timeframe
            }
        }
        
        logger.info(f"Technical analysis result: {analysis.signal.value} signal for {ticker}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in technical analysis: {e}")
        raise


# Register A2A methods
a2a_server.register_method("perform_technical_analysis", perform_technical_analysis)

# FastAPI endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "TechnicalAnalyst Agent", "status": "running", "version": "1.0.0"}


@app.post("/a2a")
async def a2a_endpoint(request: Request):
    """A2A protocol endpoint."""
    return await create_a2a_endpoint(a2a_server)(request)


@app.post("/analyze")
async def analyze_endpoint(request: TechnicalAnalysisRequest) -> Dict:
    """
    Direct analysis endpoint for testing.
    
    Args:
        request: Technical analysis request
        
    Returns:
        Technical analysis results
    """
    return await perform_technical_analysis(
        ticker=request.ticker,
        indicators=request.indicators,
        timeframe=request.timeframe,
        lookback_days=request.lookback_days
    )


if __name__ == "__main__":
    import uvicorn
    
    port = PORTS["technical_analyst"]
    logger.info(f"Starting TechnicalAnalyst Agent on port {port}")
    
    uvicorn.run(
        "technical_analyst_agent:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
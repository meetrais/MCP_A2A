# MCP A2A Trading System - API Documentation

This document provides comprehensive API documentation for all services in the MCP A2A Trading System.

## 📋 Table of Contents

- [Agent Services](#agent-services)
  - [Portfolio Manager Agent](#portfolio-manager-agent)
  - [Fundamental Analyst Agent](#fundamental-analyst-agent)
  - [Technical Analyst Agent](#technical-analyst-agent)
  - [Risk Manager Agent](#risk-manager-agent)
  - [Trade Executor Agent](#trade-executor-agent)
- [MCP Servers](#mcp-servers)
  - [Market Data MCP](#market-data-mcp)
  - [Technical Analysis MCP](#technical-analysis-mcp)
  - [Trading Execution MCP](#trading-execution-mcp)
- [Common Data Models](#common-data-models)
- [Error Handling](#error-handling)
- [Authentication](#authentication)

## 🤖 Agent Services

All agent services communicate using the A2A protocol (JSON-RPC 2.0 over HTTP) and provide health check endpoints.

### Portfolio Manager Agent

**Base URL**: `http://localhost:8000`

#### Endpoints

##### POST /start_strategy
Initiates a new trading strategy workflow.

**Request Body**:
```json
{
  "goal": "Find undervalued tech stocks with growth potential",
  "sector_preference": "technology",
  "risk_tolerance": "medium",
  "max_investment": 25000.0,
  "time_horizon": "medium"
}
```

**Parameters**:
- `goal` (string, required): Investment objective description
- `sector_preference` (string, optional): Preferred sector ("technology", "healthcare", "finance", etc.)
- `risk_tolerance` (string, required): Risk level ("low", "medium", "high")
- `max_investment` (number, required): Maximum investment amount in USD
- `time_horizon` (string, required): Investment timeframe ("short", "medium", "long")

**Response**:
```json
{
  "workflow_id": "wf_20241218_001",
  "status": "completed",
  "trade_result": {
    "ticker": "AAPL",
    "action": "BUY",
    "quantity": 100,
    "price": 150.25,
    "total_value": 15025.00,
    "status": "EXECUTED",
    "trade_id": "trade_001"
  },
  "fundamental_analysis": {
    "recommended_stocks": ["AAPL", "MSFT", "GOOGL"],
    "analysis_summary": "Strong fundamentals in tech sector"
  },
  "technical_analysis": {
    "signal": "BUY",
    "confidence": 0.78,
    "entry_price": 150.25,
    "target_price": 165.00,
    "stop_loss": 142.00
  },
  "risk_evaluation": {
    "decision": "APPROVE",
    "reasoning": "Trade within risk limits",
    "position_size": 0.15
  },
  "audit_trail": [
    {
      "step": "fundamental_analysis",
      "timestamp": "2024-12-18T10:30:00Z",
      "result": "Strong fundamentals, score: 85/100",
      "duration": 2.3
    }
  ]
}
```

**Status Codes**:
- `200`: Workflow completed successfully
- `400`: Invalid request parameters
- `500`: Internal server error

##### POST /a2a
Handles A2A protocol communications from other agents.

**Request Body** (JSON-RPC 2.0):
```json
{
  "jsonrpc": "2.0",
  "method": "workflow_status",
  "params": {
    "workflow_id": "wf_20241218_001"
  },
  "id": "req_001"
}
```

##### GET /health
Returns service health status.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-12-18T10:30:00Z",
  "version": "1.0.0",
  "uptime": 3600.5
}
```

### Fundamental Analyst Agent

**Base URL**: `http://localhost:8001`

#### A2A Methods

##### analyze_companies
Analyzes companies based on fundamental criteria.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "analyze_companies",
  "params": {
    "sector": "technology",
    "criteria": "growth",
    "max_companies": 5
  },
  "id": "req_001"
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "recommended_stocks": [
      {
        "ticker": "AAPL",
        "score": 85,
        "strengths": ["Strong revenue growth", "Solid balance sheet"],
        "weaknesses": ["High valuation"],
        "recommendation": "BUY"
      }
    ],
    "analysis_summary": "Strong fundamentals in tech sector",
    "total_analyzed": 20
  },
  "id": "req_001"
}
```

### Technical Analyst Agent

**Base URL**: `http://localhost:8002`

#### A2A Methods

##### analyze_ticker
Performs technical analysis on a specific stock ticker.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "analyze_ticker",
  "params": {
    "ticker": "AAPL",
    "timeframe": "1d",
    "indicators": ["RSI", "SMA", "MACD"]
  },
  "id": "req_002"
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "ticker": "AAPL",
    "signal": "BUY",
    "confidence": 0.78,
    "indicators": {
      "RSI": 45.2,
      "SMA_20": 148.5,
      "SMA_50": 145.2,
      "MACD": {
        "macd": 1.2,
        "signal": 0.8,
        "histogram": 0.4
      }
    },
    "entry_price": 150.25,
    "target_price": 165.00,
    "stop_loss": 142.00,
    "analysis_summary": "Bullish momentum with RSI in healthy range"
  },
  "id": "req_002"
}
```

### Risk Manager Agent

**Base URL**: `http://localhost:8003`

#### A2A Methods

##### evaluate_trade
Evaluates a trade proposal against risk management rules.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "evaluate_trade",
  "params": {
    "ticker": "AAPL",
    "action": "BUY",
    "quantity": 100,
    "price": 150.25,
    "rationale": "Strong fundamentals and technical signals"
  },
  "id": "req_003"
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "decision": "APPROVE",
    "reasoning": "Trade within risk limits. Position size: 15% of portfolio",
    "risk_metrics": {
      "position_size_percent": 15.0,
      "portfolio_concentration": 0.25,
      "cash_reserve_after": 0.35,
      "max_loss_potential": 1500.0
    },
    "approved_quantity": 100,
    "risk_level": "MEDIUM"
  },
  "id": "req_003"
}
```

### Trade Executor Agent

**Base URL**: `http://localhost:8004`

#### A2A Methods

##### execute_trade
Executes an approved trade order.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "execute_trade",
  "params": {
    "ticker": "AAPL",
    "action": "BUY",
    "quantity": 100,
    "order_type": "MARKET",
    "risk_approval": "approved"
  },
  "id": "req_004"
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "trade_id": "trade_001",
    "ticker": "AAPL",
    "action": "BUY",
    "quantity": 100,
    "price": 150.25,
    "total_value": 15025.00,
    "status": "EXECUTED",
    "timestamp": "2024-12-18T10:30:05Z",
    "confirmation": "Trade executed successfully"
  },
  "id": "req_004"
}
```

## 🗄️ MCP Servers

MCP servers provide standardized data access through function calls.

### Market Data MCP

**Base URL**: `http://localhost:9000`

#### Endpoint

##### POST /mcp
Executes MCP functions for market data access.

#### Functions

##### get_stock_price
Retrieves historical stock price data.

**Request**:
```json
{
  "function": "get_stock_price",
  "arguments": {
    "ticker": "AAPL",
    "period": "1mo",
    "interval": "1d"
  }
}
```

**Response**:
```json
{
  "ticker": "AAPL",
  "data": [
    {
      "date": "2024-12-17",
      "open": 149.50,
      "high": 151.20,
      "low": 148.80,
      "close": 150.25,
      "volume": 45678900
    }
  ],
  "metadata": {
    "period": "1mo",
    "interval": "1d",
    "currency": "USD"
  }
}
```

##### get_market_news
Retrieves market news and sentiment data.

**Request**:
```json
{
  "function": "get_market_news",
  "arguments": {
    "ticker": "AAPL",
    "limit": 10
  }
}
```

**Response**:
```json
[
  {
    "headline": "Apple Reports Strong Q4 Earnings",
    "summary": "Apple exceeded expectations with revenue growth of 8%",
    "sentiment": "positive",
    "date": "2024-12-17",
    "source": "Financial News",
    "relevance_score": 0.95
  }
]
```

##### get_financial_statements
Retrieves company financial statement data.

**Request**:
```json
{
  "function": "get_financial_statements",
  "arguments": {
    "ticker": "AAPL",
    "statement_type": "income"
  }
}
```

**Response**:
```json
{
  "ticker": "AAPL",
  "revenue": 394328000000,
  "net_income": 99803000000,
  "total_assets": 352755000000,
  "total_debt": 123930000000,
  "cash": 29965000000,
  "period": "2024-Q4",
  "currency": "USD"
}
```

### Technical Analysis MCP

**Base URL**: `http://localhost:9001`

#### Functions

##### calculate_indicator
Calculates technical indicators from price data.

**Request**:
```json
{
  "function": "calculate_indicator",
  "arguments": {
    "price_data": [
      {"close": 150.25, "volume": 1000000},
      {"close": 151.30, "volume": 1100000},
      {"close": 149.80, "volume": 950000}
    ],
    "indicator_name": "RSI",
    "params": {
      "period": 14
    }
  }
}
```

**Response**:
```json
{
  "indicator": "RSI",
  "values": [45.2, 47.8, 44.1],
  "signal": "NEUTRAL",
  "confidence": 0.65,
  "interpretation": "RSI in neutral range, no strong signal",
  "parameters": {
    "period": 14
  }
}
```

**Supported Indicators**:
- `RSI`: Relative Strength Index
- `SMA`: Simple Moving Average
- `EMA`: Exponential Moving Average
- `MACD`: Moving Average Convergence Divergence
- `BOLLINGER`: Bollinger Bands
- `STOCHASTIC`: Stochastic Oscillator

### Trading Execution MCP

**Base URL**: `http://localhost:9002`

#### Functions

##### execute_mock_trade
Simulates trade execution in paper trading environment.

**Request**:
```json
{
  "function": "execute_mock_trade",
  "arguments": {
    "ticker": "AAPL",
    "action": "BUY",
    "quantity": 100,
    "trade_type": "MARKET"
  }
}
```

**Response**:
```json
{
  "trade_id": "trade_001",
  "ticker": "AAPL",
  "action": "BUY",
  "quantity": 100,
  "price": 150.25,
  "total_value": 15025.00,
  "status": "EXECUTED",
  "timestamp": "2024-12-18T10:30:05Z",
  "fees": 1.00
}
```

##### get_portfolio_status
Retrieves current portfolio status and positions.

**Request**:
```json
{
  "function": "get_portfolio_status",
  "arguments": {}
}
```

**Response**:
```json
{
  "cash_balance": 84975.00,
  "positions": [
    {
      "ticker": "AAPL",
      "quantity": 100,
      "avg_cost": 150.25,
      "current_price": 151.30,
      "current_value": 15130.00,
      "unrealized_pnl": 105.00,
      "unrealized_pnl_percent": 0.70
    }
  ],
  "total_value": 100105.00,
  "total_pnl": 105.00,
  "total_pnl_percent": 0.11
}
```

##### reset_portfolio
Resets portfolio to initial state (for testing).

**Request**:
```json
{
  "function": "reset_portfolio",
  "arguments": {
    "initial_cash": 100000.0
  }
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Portfolio reset to initial state",
  "cash_balance": 100000.0,
  "positions": []
}
```

## 📊 Common Data Models

### Investment Strategy
```json
{
  "goal": "string",
  "sector_preference": "string (optional)",
  "risk_tolerance": "low|medium|high",
  "max_investment": "number",
  "time_horizon": "short|medium|long"
}
```

### Trade Proposal
```json
{
  "ticker": "string",
  "action": "BUY|SELL",
  "quantity": "number",
  "rationale": "string",
  "expected_return": "number",
  "risk_level": "LOW|MEDIUM|HIGH"
}
```

### A2A Request
```json
{
  "jsonrpc": "2.0",
  "method": "string",
  "params": "object",
  "id": "string"
}
```

### A2A Response
```json
{
  "jsonrpc": "2.0",
  "result": "object (on success)",
  "error": "object (on error)",
  "id": "string"
}
```

### Health Status
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "ISO 8601 datetime",
  "version": "string",
  "uptime": "number (seconds)"
}
```

## ❌ Error Handling

### HTTP Status Codes

- `200`: Success
- `400`: Bad Request - Invalid parameters
- `401`: Unauthorized - Authentication required
- `404`: Not Found - Endpoint not found
- `422`: Unprocessable Entity - Validation error
- `500`: Internal Server Error
- `503`: Service Unavailable - Service temporarily down

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_TICKER",
    "message": "Invalid ticker symbol provided",
    "details": {
      "ticker": "INVALID",
      "valid_examples": ["AAPL", "MSFT", "GOOGL"]
    },
    "timestamp": "2024-12-18T10:30:00Z"
  }
}
```

### A2A Error Response

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "missing_params": ["ticker"],
      "provided_params": ["action", "quantity"]
    }
  },
  "id": "req_001"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `INVALID_TICKER` | Invalid stock ticker symbol |
| `INSUFFICIENT_FUNDS` | Not enough cash for trade |
| `RISK_LIMIT_EXCEEDED` | Trade exceeds risk limits |
| `SERVICE_UNAVAILABLE` | Required service is down |
| `TIMEOUT_ERROR` | Request timed out |
| `VALIDATION_ERROR` | Input validation failed |
| `ANALYSIS_FAILED` | Analysis could not be completed |
| `TRADE_REJECTED` | Trade was rejected by risk management |

## 🔐 Authentication

### Development Environment

The development environment runs without authentication for simplicity. All endpoints are publicly accessible on localhost.

### Production Considerations

For production deployment, implement:

1. **API Key Authentication**
   ```http
   Authorization: Bearer your-api-key-here
   ```

2. **JWT Tokens**
   ```http
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

3. **Rate Limiting**
   - Implement rate limiting per API key
   - Different limits for different endpoints

4. **HTTPS Only**
   - All communication must use HTTPS
   - Implement certificate validation

## 📝 Usage Examples

### Complete Trading Workflow

```python
import httpx
import asyncio

async def execute_trading_strategy():
    async with httpx.AsyncClient() as client:
        # 1. Start trading strategy
        strategy = {
            "goal": "Find undervalued tech stocks",
            "sector_preference": "technology",
            "risk_tolerance": "medium",
            "max_investment": 25000.0,
            "time_horizon": "medium"
        }
        
        response = await client.post(
            "http://localhost:8000/start_strategy",
            json=strategy
        )
        
        result = response.json()
        print(f"Workflow Status: {result['status']}")
        
        if result['status'] == 'completed':
            trade = result['trade_result']
            print(f"Executed: {trade['action']} {trade['quantity']} {trade['ticker']} @ ${trade['price']}")

# Run the example
asyncio.run(execute_trading_strategy())
```

### Direct MCP Server Access

```python
import httpx
import asyncio

async def get_market_data():
    async with httpx.AsyncClient() as client:
        # Get stock price data
        response = await client.post(
            "http://localhost:9000/mcp",
            json={
                "function": "get_stock_price",
                "arguments": {"ticker": "AAPL"}
            }
        )
        
        data = response.json()
        latest_price = data['data'][-1]['close']
        print(f"AAPL latest price: ${latest_price}")

asyncio.run(get_market_data())
```

### Health Check All Services

```python
import httpx
import asyncio
from MCP_A2A.config import SERVICE_URLS

async def health_check_all():
    async with httpx.AsyncClient() as client:
        for name, url in SERVICE_URLS.items():
            try:
                response = await client.get(f"{url}/health", timeout=5.0)
                status = "✓" if response.status_code == 200 else "✗"
                print(f"{status} {name}: {url}")
            except Exception as e:
                print(f"✗ {name}: {e}")

asyncio.run(health_check_all())
```

## 🔧 Interactive API Testing

### Using curl

```bash
# Start a trading strategy
curl -X POST http://localhost:8000/start_strategy \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Find growth stocks",
    "risk_tolerance": "medium",
    "max_investment": 10000.0,
    "time_horizon": "short"
  }'

# Get portfolio status
curl -X POST http://localhost:9002/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "function": "get_portfolio_status",
    "arguments": {}
  }'

# Health check
curl http://localhost:8000/health
```

### Using FastAPI Interactive Docs

When services are running, visit:
- Portfolio Manager: http://localhost:8000/docs
- Market Data MCP: http://localhost:9000/docs
- Technical Analysis MCP: http://localhost:9001/docs
- Trading Execution MCP: http://localhost:9002/docs

These provide interactive Swagger UI documentation where you can test endpoints directly.

---

This API documentation provides comprehensive coverage of all endpoints, data models, and usage patterns in the MCP A2A Trading System. For additional examples and troubleshooting, refer to the main README.md file.
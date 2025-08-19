# MCP A2A Trading System

A sophisticated multi-agent financial trading system that combines Model Context Protocol (MCP) servers with Agent-to-Agent (A2A) communication for automated market analysis and trade execution.

## 🏗️ Architecture Overview

The system follows a microservices architecture with specialized agents communicating via Google's A2A protocol (JSON-RPC 2.0 over HTTP) and accessing financial data through standardized MCP servers.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User/Client   │───▶│ PortfolioManager │───▶│ Trading Results │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │ Fundamental  │ │  Technical   │ │     Risk     │
            │   Analyst    │ │   Analyst    │ │   Manager    │
            └──────────────┘ └──────────────┘ └──────────────┘
                    │           │           │
                    └───────────┼───────────┘
                                ▼
                        ┌──────────────┐
                        │    Trade     │
                        │   Executor   │
                        └──────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │  MarketData  │ │ Technical    │ │   Trading    │
            │     MCP      │ │ Analysis MCP │ │Execution MCP │
            └──────────────┘ └──────────────┘ └──────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** with pip
- **Available Ports**: 8000-8004 (agents) and 9000-9002 (MCP servers)
- **Operating System**: Windows, macOS, or Linux

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MCP_A2A
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**
   ```bash
   python -c "import fastapi, httpx, numpy; print('✓ All dependencies installed')"
   ```

### Running the System

#### Option 1: Automated Startup (Recommended)

```bash
# Start all services and run a sample workflow
python main.py
```

This will:
- Start all 8 services (3 MCP servers + 5 agents)
- Perform health checks
- Execute a sample trading strategy
- Display results and shut down gracefully

#### Option 2: Manual Service Management

Start each service in separate terminals:

```bash
# Terminal 1-3: MCP Servers
python -m MCP_A2A.mcp_servers.market_data_server
python -m MCP_A2A.mcp_servers.technical_analysis_server
python -m MCP_A2A.mcp_servers.trading_execution_server

# Terminal 4-8: Agent Services
python -m MCP_A2A.agents.fundamental_analyst_agent
python -m MCP_A2A.agents.technical_analyst_agent
python -m MCP_A2A.agents.risk_manager_agent
python -m MCP_A2A.agents.trade_executor_agent
python -m MCP_A2A.agents.portfolio_manager_agent
```

Then execute a trading strategy:

```bash
curl -X POST http://localhost:8000/start_strategy \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Find undervalued tech stocks with growth potential",
    "sector_preference": "technology",
    "risk_tolerance": "medium",
    "max_investment": 25000.0,
    "time_horizon": "medium"
  }'
```

## 📋 System Components

### MCP Servers (Data Layer)

| Service | Port | Purpose | Key Functions |
|---------|------|---------|---------------|
| **MarketDataMCP** | 9000 | Financial market data | `get_stock_price`, `get_market_news`, `get_financial_statements` |
| **TechnicalAnalysisMCP** | 9001 | Technical indicators | `calculate_indicator` (RSI, SMA, EMA, MACD) |
| **TradingExecutionMCP** | 9002 | Trade execution & portfolio | `execute_mock_trade`, `get_portfolio_status` |

### Agent Services (Intelligence Layer)

| Agent | Port | Role | Responsibilities |
|-------|------|------|------------------|
| **PortfolioManagerAgent** | 8000 | Orchestrator | Strategy parsing, workflow coordination |
| **FundamentalAnalystAgent** | 8001 | Company Analysis | Financial health assessment, company ranking |
| **TechnicalAnalystAgent** | 8002 | Market Timing | Price action analysis, entry/exit signals |
| **RiskManagerAgent** | 8003 | Risk Control | Trade approval, portfolio risk management |
| **TradeExecutorAgent** | 8004 | Execution | Trade execution, confirmation handling |

## 🔄 Trading Workflow

1. **Strategy Input**: User submits investment strategy via REST API
2. **Fundamental Analysis**: Evaluate company financial health and news sentiment
3. **Technical Analysis**: Analyze price action and market timing signals
4. **Risk Evaluation**: Apply risk management rules and position sizing
5. **Trade Execution**: Execute approved trades and update portfolio
6. **Results & Audit**: Return results with complete audit trail

### Sample Workflow Response

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
    "status": "EXECUTED"
  },
  "audit_trail": [
    {
      "step": "fundamental_analysis",
      "timestamp": "2024-12-18T10:30:00Z",
      "result": "Strong fundamentals, score: 85/100",
      "duration": 2.3
    },
    {
      "step": "technical_analysis", 
      "timestamp": "2024-12-18T10:30:02Z",
      "result": "BUY signal, confidence: 0.78",
      "duration": 1.8
    },
    {
      "step": "risk_evaluation",
      "timestamp": "2024-12-18T10:30:04Z", 
      "result": "APPROVED - within risk limits",
      "duration": 0.5
    },
    {
      "step": "trade_execution",
      "timestamp": "2024-12-18T10:30:05Z",
      "result": "Trade executed successfully",
      "duration": 1.2
    }
  ]
}
```

## 🧪 Testing

### Quick Validation

```bash
# Run smoke tests (2-3 minutes)
python -m pytest MCP_A2A/tests/test_smoke.py -v

# Check system health
python -c "
import asyncio
import httpx
from MCP_A2A.config import SERVICE_URLS

async def health_check():
    async with httpx.AsyncClient() as client:
        for name, url in SERVICE_URLS.items():
            try:
                response = await client.get(f'{url}/health', timeout=5.0)
                status = '✓' if response.status_code == 200 else '✗'
                print(f'{status} {name}: {url}')
            except Exception as e:
                print(f'✗ {name}: {e}')

asyncio.run(health_check())
"
```

### Comprehensive Testing

```bash
# Run all integration tests with automatic service management
python MCP_A2A/tests/run_integration_tests.py

# Run specific test categories
python -m pytest MCP_A2A/tests/test_integration_workflows.py::TestCompleteWorkflows -v
python -m pytest MCP_A2A/tests/test_integration_workflows.py::TestPerformanceAndThroughput -v
```

### Test Coverage

```bash
# Generate coverage report
python -m pytest MCP_A2A/tests/ --cov=MCP_A2A --cov-report=html
# Open htmlcov/index.html in browser
```

## 📊 Monitoring and Observability

### Health Monitoring

All services provide health endpoints:

```bash
# Check individual service health
curl http://localhost:8000/health  # Portfolio Manager
curl http://localhost:9000/health  # Market Data MCP

# System-wide health check
python -c "
from MCP_A2A.utils.health_check import HealthChecker
import asyncio

async def check():
    checker = HealthChecker()
    status = await checker.get_system_health()
    print(f'System Health: {status[\"overall_status\"]}')
    for service, health in status['services'].items():
        print(f'  {service}: {health[\"status\"]}')

asyncio.run(check())
"
```

### Performance Metrics

```bash
# View performance metrics
python -c "
from MCP_A2A.utils.monitoring import MetricsCollector
import asyncio

async def metrics():
    collector = MetricsCollector()
    summary = await collector.get_performance_summary()
    print('Performance Summary:')
    for metric, value in summary.items():
        print(f'  {metric}: {value}')

asyncio.run(metrics())
"
```

### Audit Logging

```bash
# View recent audit events
python -c "
from MCP_A2A.utils.audit_logger import AuditLogger
import asyncio

async def audit():
    logger = AuditLogger()
    events = await logger.get_recent_events(limit=10)
    for event in events:
        print(f'{event[\"timestamp\"]} - {event[\"event_type\"]}: {event[\"description\"]}')

asyncio.run(audit())
"
```

## ⚙️ Configuration

### Environment Variables

```bash
# Service Configuration
export PORTFOLIO_MANAGER_PORT=8000
export FUNDAMENTAL_ANALYST_PORT=8001
export TECHNICAL_ANALYST_PORT=8002
export RISK_MANAGER_PORT=8003
export TRADE_EXECUTOR_PORT=8004
export MARKET_DATA_MCP_PORT=9000
export TECHNICAL_ANALYSIS_MCP_PORT=9001
export TRADING_EXECUTION_MCP_PORT=9002

# Logging Configuration
export LOG_LEVEL=INFO
export LOG_FORMAT=json

# Trading Configuration
export INITIAL_PORTFOLIO_VALUE=100000.0
export MAX_POSITION_SIZE=0.10
export MIN_CASH_RESERVE=0.20
```

### Configuration Files

Create `.env` file in project root:

```env
# MCP A2A Trading System Configuration

# Service Ports
PORTFOLIO_MANAGER_PORT=8000
FUNDAMENTAL_ANALYST_PORT=8001
TECHNICAL_ANALYST_PORT=8002
RISK_MANAGER_PORT=8003
TRADE_EXECUTOR_PORT=8004
MARKET_DATA_MCP_PORT=9000
TECHNICAL_ANALYSIS_MCP_PORT=9001
TRADING_EXECUTION_MCP_PORT=9002

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=structured

# Trading Parameters
INITIAL_PORTFOLIO_VALUE=100000.0
MAX_POSITION_SIZE=0.10
MIN_CASH_RESERVE=0.20
MAX_TRADE_VALUE=10000.0

# Performance
REQUEST_TIMEOUT=30
WORKFLOW_TIMEOUT=120
MAX_RETRIES=3
```

## 🔧 Development

### Project Structure

```
MCP_A2A/
├── agents/                 # Agent services
│   ├── portfolio_manager_agent.py
│   ├── fundamental_analyst_agent.py
│   ├── technical_analyst_agent.py
│   ├── risk_manager_agent.py
│   └── trade_executor_agent.py
├── mcp_servers/           # MCP server implementations
│   ├── market_data_server.py
│   ├── technical_analysis_server.py
│   └── trading_execution_server.py
├── models/                # Data models
│   ├── trading_models.py
│   └── market_data.py
├── utils/                 # Shared utilities
│   ├── a2a_client.py
│   ├── a2a_server.py
│   ├── http_client.py
│   ├── logging_config.py
│   ├── monitoring.py
│   ├── audit_logger.py
│   ├── health_check.py
│   ├── error_recovery.py
│   ├── retry_handler.py
│   └── circuit_breaker.py
├── tests/                 # Test suite
│   ├── test_integration_workflows.py
│   ├── test_smoke.py
│   ├── run_integration_tests.py
│   └── test_config.py
├── config.py             # Configuration management
├── main.py               # Main orchestration script
└── requirements.txt      # Python dependencies
```

### Code Style

```bash
# Format code
black MCP_A2A/
isort MCP_A2A/

# Lint code
flake8 MCP_A2A/
mypy MCP_A2A/

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

### Adding New Features

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-agent
   ```

2. **Implement Agent/MCP Server**
   ```python
   # Follow existing patterns in agents/ or mcp_servers/
   from fastapi import FastAPI
   from MCP_A2A.utils.a2a_server import A2AServer
   
   app = FastAPI(title="New Agent")
   a2a_server = A2AServer()
   
   @app.post("/a2a")
   async def handle_a2a(request: dict):
       return await a2a_server.handle_request(request)
   ```

3. **Add Tests**
   ```python
   # tests/test_new_agent.py
   import pytest
   from MCP_A2A.agents.new_agent import NewAgent
   
   @pytest.mark.asyncio
   async def test_new_agent_functionality():
       agent = NewAgent()
       result = await agent.process_request({})
       assert result["status"] == "success"
   ```

4. **Update Configuration**
   ```python
   # config.py
   SERVICE_URLS["new_agent"] = "http://localhost:8005"
   ```

## 🚨 Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # macOS/Linux

# Kill process
taskkill /PID <PID> /F        # Windows
kill -9 <PID>                 # macOS/Linux
```

#### Service Not Starting

```bash
# Check logs
python -m MCP_A2A.agents.portfolio_manager_agent

# Verify dependencies
pip install -r requirements.txt

# Check Python version
python --version  # Should be 3.8+
```

#### Tests Failing

```bash
# Run with verbose output
python -m pytest MCP_A2A/tests/ -v -s

# Check service health first
python MCP_A2A/tests/run_integration_tests.py --health-check-only

# Reset test environment
python -c "
import httpx
import asyncio

async def reset():
    async with httpx.AsyncClient() as client:
        await client.post('http://localhost:9002/mcp', 
                         json={'function': 'reset_portfolio', 'arguments': {}})
    print('Portfolio reset')

asyncio.run(reset())
"
```

#### Performance Issues

```bash
# Monitor system resources
python -c "
import psutil
print(f'CPU: {psutil.cpu_percent()}%')
print(f'Memory: {psutil.virtual_memory().percent}%')
print(f'Disk: {psutil.disk_usage(\"/\").percent}%')
"

# Check service response times
python -c "
import time
import httpx
import asyncio

async def benchmark():
    async with httpx.AsyncClient() as client:
        start = time.time()
        response = await client.get('http://localhost:8000/health')
        duration = time.time() - start
        print(f'Portfolio Manager response time: {duration:.3f}s')

asyncio.run(benchmark())
"
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export LOG_LEVEL=DEBUG
python main.py
```

### Getting Help

1. **Check Documentation**: Review this README and `/tests/README.md`
2. **Run Diagnostics**: Use the health check and monitoring utilities
3. **Check Logs**: Enable debug logging to see detailed execution flow
4. **Test Components**: Run individual component tests to isolate issues

## 📈 Performance Characteristics

### Expected Performance

- **Workflow Completion**: 15-60 seconds per complete trading workflow
- **System Throughput**: 0.1-0.5 requests per second sustained
- **Service Startup**: 10-30 seconds for all services
- **Memory Usage**: ~200-500MB total for all services
- **Concurrent Workflows**: 3-5 simultaneous workflows supported

### Optimization Tips

1. **Increase Concurrency**: Adjust `MAX_CONCURRENT_REQUESTS` in configuration
2. **Optimize Timeouts**: Tune timeout values based on your environment
3. **Cache Data**: Enable caching for frequently accessed market data
4. **Resource Limits**: Monitor and adjust memory/CPU limits as needed

## 🔒 Security Considerations

### Development Environment

- **No Real Trading**: System uses simulated data and paper trading only
- **Local Network**: All services run on localhost by default
- **No Authentication**: Development setup has no authentication (add for production)
- **Logging**: Sensitive data is not logged (portfolio values are simulated)

### Production Considerations

- **HTTPS**: Use HTTPS for all inter-service communication
- **Authentication**: Implement API key or OAuth authentication
- **Rate Limiting**: Add rate limiting to prevent abuse
- **Input Validation**: All inputs are validated, but add additional security layers
- **Network Security**: Use VPNs or private networks for service communication

## 📄 License

This project is for educational and demonstration purposes. See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📞 Support

For issues and questions:

1. Check the troubleshooting section above
2. Review the test documentation in `/tests/README.md`
3. Run the diagnostic utilities provided
4. Create an issue with detailed error information and system configuration

---

**Happy Trading! 📊🚀**
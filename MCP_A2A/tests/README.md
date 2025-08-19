# MCP A2A Trading System - Integration Tests

This directory contains comprehensive integration tests for the MCP A2A Trading System. The tests validate complete workflows, system performance, error handling, and data consistency.

## Test Structure

### Test Files

- **`test_integration_workflows.py`** - Complete end-to-end workflow tests
- **`test_smoke.py`** - Quick validation and smoke tests
- **`run_integration_tests.py`** - Test runner with service management
- **`test_config.py`** - Test configuration and settings
- **`README.md`** - This documentation file

### Test Categories

#### 1. Complete Workflow Tests (`TestCompleteWorkflows`)

Tests the entire trading workflow from strategy initiation to trade execution:

- **Successful Trading Workflow**: Complete happy path from strategy to executed trade
- **Fundamental Analysis Rejection**: Workflow stops when no suitable candidates found
- **Technical Analysis Hold Signal**: Workflow stops when technical analysis suggests waiting
- **Risk Management Denial**: Trade denied due to risk management rules
- **Trade Execution Failure**: Handling of trade execution failures

#### 2. Performance and Throughput Tests (`TestPerformanceAndThroughput`)

Validates system performance characteristics:

- **Concurrent Strategy Execution**: Multiple simultaneous strategy requests
- **System Throughput Measurement**: Sequential request processing speed
- **Response Time Validation**: Ensures reasonable response times

#### 3. Error Recovery and Resilience Tests (`TestErrorRecoveryAndResilience`)

Tests system behavior under failure conditions:

- **Service Unavailable Recovery**: Handling temporary service outages
- **Partial System Failure**: Graceful degradation when some services fail
- **Network Error Handling**: Timeout and connection error recovery

#### 4. Data Consistency and Integrity Tests (`TestDataConsistencyAndIntegrity`)

Validates data consistency across the system:

- **Portfolio State Consistency**: Portfolio updates match trade executions
- **Audit Trail Completeness**: Complete and chronological audit logging
- **Cross-Service Data Integrity**: Data consistency between services

#### 5. Smoke Tests (`TestSmokeTests`)

Quick validation tests for basic functionality:

- **Service Health Checks**: All services respond to health endpoints
- **Basic Endpoint Functionality**: Core endpoints accept requests
- **MCP Server Functionality**: Basic MCP server operations
- **A2A Protocol Communication**: Basic inter-agent communication
- **Configuration Validity**: System configuration is valid

## Running Tests

### Prerequisites

1. **Python Environment**: Python 3.8+ with required dependencies
2. **Service Dependencies**: All MCP servers and agents must be available
3. **Network Ports**: Ports 8000-8004 and 9000-9002 must be available

### Quick Start

```bash
# Run all integration tests with automatic service management
python MCP_A2A/tests/run_integration_tests.py

# Run only smoke tests for quick validation
python -m pytest MCP_A2A/tests/test_smoke.py -v

# Run specific test category
python -m pytest MCP_A2A/tests/test_integration_workflows.py::TestCompleteWorkflows -v
```

### Manual Service Management

If you prefer to manage services manually:

```bash
# Start all services first (in separate terminals or background)
python -m MCP_A2A.mcp_servers.market_data_server &
python -m MCP_A2A.mcp_servers.technical_analysis_server &
python -m MCP_A2A.mcp_servers.trading_execution_server &
python -m MCP_A2A.agents.fundamental_analyst_agent &
python -m MCP_A2A.agents.technical_analyst_agent &
python -m MCP_A2A.agents.risk_manager_agent &
python -m MCP_A2A.agents.trade_executor_agent &
python -m MCP_A2A.agents.portfolio_manager_agent &

# Then run tests
python -m pytest MCP_A2A/tests/test_integration_workflows.py -v
```

### Test Options

```bash
# Run with verbose output
python -m pytest MCP_A2A/tests/ -v

# Run with detailed failure information
python -m pytest MCP_A2A/tests/ -v --tb=long

# Stop on first failure
python -m pytest MCP_A2A/tests/ -x

# Run specific test method
python -m pytest MCP_A2A/tests/test_integration_workflows.py::TestCompleteWorkflows::test_successful_trading_workflow -v

# Run with coverage reporting
python -m pytest MCP_A2A/tests/ --cov=MCP_A2A --cov-report=html
```

## Test Configuration

### Environment Variables

- **`TEST_ENV`**: Set to `ci` for CI environment, `local` for local development
- **`LOG_LEVEL`**: Set logging level (DEBUG, INFO, WARNING, ERROR)
- **`TEST_TIMEOUT`**: Override default test timeouts

### Configuration File

The `test_config.py` file contains:

- **Timeout Settings**: Service startup, request, and workflow timeouts
- **Retry Configuration**: Retry attempts and backoff strategies
- **Portfolio Settings**: Initial cash, position limits, risk parameters
- **Test Strategies**: Predefined strategies for different test scenarios
- **Performance Thresholds**: Expected performance benchmarks

### Test Strategies

Predefined test strategies for different scenarios:

- **`successful_tech_strategy`**: Designed to complete successfully
- **`conservative_strategy`**: Low-risk, stable investment approach
- **`aggressive_strategy`**: High-risk, high-reward approach
- **`failing_strategy`**: Designed to trigger rejection scenarios

## Expected Test Results

### Successful Test Run

```
MCP A2A Trading System - Integration Test Runner
============================================================
Starting all services for integration testing...
✓ MarketDataMCP started successfully
✓ TechnicalAnalysisMCP started successfully
✓ TradingExecutionMCP started successfully
✓ FundamentalAnalyst started successfully
✓ TechnicalAnalyst started successfully
✓ RiskManager started successfully
✓ TradeExecutor started successfully
✓ PortfolioManager started successfully
✓ All 8 services started successfully

Performing health check on all services...
✓ PortfolioManager is healthy
✓ FundamentalAnalyst is healthy
✓ TechnicalAnalyst is healthy
✓ RiskManager is healthy
✓ TradeExecutor is healthy
✓ MarketDataMCP is healthy
✓ TechnicalAnalysisMCP is healthy
✓ TradingExecutionMCP is healthy

============================================================
Running Integration Tests
============================================================

test_integration_workflows.py::TestCompleteWorkflows::test_successful_trading_workflow PASSED
test_integration_workflows.py::TestCompleteWorkflows::test_fundamental_analysis_rejection_workflow PASSED
test_integration_workflows.py::TestCompleteWorkflows::test_technical_analysis_hold_signal_workflow PASSED
test_integration_workflows.py::TestCompleteWorkflows::test_risk_management_trade_denial_workflow PASSED
test_integration_workflows.py::TestCompleteWorkflows::test_trade_execution_failure_workflow PASSED
test_integration_workflows.py::TestPerformanceAndThroughput::test_concurrent_strategy_execution PASSED
test_integration_workflows.py::TestPerformanceAndThroughput::test_system_throughput_measurement PASSED
test_integration_workflows.py::TestErrorRecoveryAndResilience::test_service_unavailable_recovery PASSED
test_integration_workflows.py::TestErrorRecoveryAndResilience::test_partial_system_failure_handling PASSED
test_integration_workflows.py::TestDataConsistencyAndIntegrity::test_portfolio_state_consistency PASSED
test_integration_workflows.py::TestDataConsistencyAndIntegrity::test_audit_trail_completeness PASSED

============================================================
Integration Tests Completed
============================================================
✓ All integration tests passed!
```

### Performance Benchmarks

Expected performance characteristics:

- **Workflow Completion**: < 60 seconds per complete workflow
- **System Throughput**: > 0.1 requests per second
- **Service Startup**: < 30 seconds for all services
- **Health Check Response**: < 5 seconds per service
- **Concurrent Requests**: Support for 3-5 simultaneous workflows

## Troubleshooting

### Common Issues

#### Services Not Starting

```bash
# Check if ports are already in use
netstat -an | grep :8000
netstat -an | grep :9000

# Kill existing processes if needed
pkill -f "portfolio_manager_agent"
pkill -f "market_data_server"
```

#### Test Timeouts

```bash
# Increase timeout values in test_config.py
TEST_CONFIG["timeout"]["workflow_timeout"] = 180

# Or set environment variable
export TEST_TIMEOUT=180
```

#### Service Health Check Failures

```bash
# Check service logs
python -m MCP_A2A.agents.portfolio_manager_agent

# Verify service configuration
python -c "from MCP_A2A.config import SERVICE_URLS; print(SERVICE_URLS)"
```

#### Port Conflicts

```bash
# Use different ports if needed
export PORTFOLIO_MANAGER_PORT=8100
export MARKET_DATA_PORT=9100
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export LOG_LEVEL=DEBUG
python MCP_A2A/tests/run_integration_tests.py
```

### Test Data Reset

Reset test environment between runs:

```bash
# Reset portfolio state
curl -X POST http://localhost:9002/mcp -d '{"function": "reset_portfolio", "arguments": {}}'

# Clear any cached data
rm -rf /tmp/mcp_a2a_cache/
```

## Continuous Integration

### CI Configuration

For automated testing in CI environments:

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests
on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run integration tests
        env:
          TEST_ENV: ci
        run: python MCP_A2A/tests/run_integration_tests.py
```

### Test Reporting

Generate test reports for CI:

```bash
# Generate JUnit XML report
python -m pytest MCP_A2A/tests/ --junitxml=test-results.xml

# Generate HTML coverage report
python -m pytest MCP_A2A/tests/ --cov=MCP_A2A --cov-report=html --cov-report=xml
```

## Contributing

When adding new tests:

1. **Follow Naming Conventions**: Use descriptive test method names
2. **Add Documentation**: Include docstrings explaining test purpose
3. **Use Fixtures**: Leverage pytest fixtures for setup/teardown
4. **Handle Cleanup**: Ensure tests clean up after themselves
5. **Add Configuration**: Add new test parameters to `test_config.py`
6. **Update Documentation**: Update this README with new test information

### Test Template

```python
async def test_new_functionality(self, integration_helper):
    """
    Test description explaining what this test validates.
    
    This test verifies that [specific functionality] works correctly
    under [specific conditions].
    """
    # Arrange
    test_data = {...}
    
    # Act
    result = await integration_helper.client.post(...)
    
    # Assert
    assert result.status_code == 200
    assert "expected_field" in result.json()
    
    # Verify side effects
    portfolio = await integration_helper.get_portfolio_status()
    assert portfolio["cash_balance"] >= 0
```
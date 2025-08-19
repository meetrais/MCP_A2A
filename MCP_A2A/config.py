"""
Configuration management for the MCP A2A Trading System.
Manages service URLs, ports, and system-wide settings.
"""

# Service URLs and Ports
SERVICE_URLS = {
    "portfolio_manager": "http://localhost:8000",
    "fundamental_analyst": "http://localhost:8001",
    "technical_analyst": "http://localhost:8002",
    "risk_manager": "http://localhost:8003",
    "trade_executor": "http://localhost:8004",
    "market_data_mcp": "http://localhost:9000",
    "technical_analysis_mcp": "http://localhost:9001",
    "trading_execution_mcp": "http://localhost:9002"
}

# Port assignments
PORTS = {
    "portfolio_manager": 8000,
    "fundamental_analyst": 8001,
    "technical_analyst": 8002,
    "risk_manager": 8003,
    "trade_executor": 8004,
    "market_data_mcp": 9000,
    "technical_analysis_mcp": 9001,
    "trading_execution_mcp": 9002
}

# System settings
SYSTEM_CONFIG = {
    "request_timeout": 30.0,
    "retry_attempts": 3,
    "retry_delay": 1.0,
    "log_level": "INFO",
    "correlation_id_header": "X-Correlation-ID"
}

# Trading simulation settings
TRADING_CONFIG = {
    "initial_cash": 100000.0,
    "max_position_size_pct": 10.0,
    "max_sector_concentration_pct": 30.0,
    "min_cash_reserve_pct": 20.0,
    "max_single_trade_value": 10000.0
}
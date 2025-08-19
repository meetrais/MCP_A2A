"""
Configuration for integration tests.
"""

import os
from typing import Dict, Any

# Test configuration
TEST_CONFIG = {
    "timeout": {
        "service_startup": 30,  # seconds to wait for service startup
        "request_timeout": 30,  # seconds for individual requests
        "workflow_timeout": 120  # seconds for complete workflow
    },
    
    "retry": {
        "max_retries": 3,
        "backoff_factor": 1.5,
        "initial_delay": 1.0
    },
    
    "portfolio": {
        "initial_cash": 100000.0,
        "max_position_size": 0.1,  # 10% of portfolio
        "min_cash_reserve": 0.2    # 20% cash reserve
    },
    
    "test_strategies": {
        "successful_tech_strategy": {
            "goal": "Find undervalued tech stocks with strong growth potential",
            "sector_preference": "technology",
            "risk_tolerance": "medium",
            "max_investment": 25000.0,
            "time_horizon": "medium"
        },
        
        "conservative_strategy": {
            "goal": "Find stable dividend-paying stocks",
            "sector_preference": "utilities",
            "risk_tolerance": "low",
            "max_investment": 10000.0,
            "time_horizon": "long"
        },
        
        "aggressive_strategy": {
            "goal": "Find high-growth momentum stocks",
            "sector_preference": "technology",
            "risk_tolerance": "high",
            "max_investment": 50000.0,
            "time_horizon": "short"
        },
        
        "failing_strategy": {
            "goal": "Find profitable companies in declining industries",
            "sector_preference": "retail",
            "risk_tolerance": "low",
            "max_investment": 5000.0,
            "time_horizon": "short"
        }
    },
    
    "expected_responses": {
        "workflow_fields": [
            "workflow_id",
            "status",
            "audit_trail"
        ],
        
        "successful_trade_fields": [
            "trade_result",
            "ticker",
            "quantity",
            "total_value"
        ],
        
        "audit_trail_steps": [
            "fundamental_analysis",
            "technical_analysis", 
            "risk_evaluation",
            "trade_execution"
        ]
    },
    
    "performance_thresholds": {
        "max_workflow_time": 60.0,  # seconds
        "min_throughput": 0.1,      # requests per second
        "max_concurrent_requests": 5
    }
}

# Environment-specific overrides
if os.getenv("TEST_ENV") == "ci":
    # CI environment adjustments
    TEST_CONFIG["timeout"]["service_startup"] = 60
    TEST_CONFIG["timeout"]["workflow_timeout"] = 180
    TEST_CONFIG["performance_thresholds"]["max_workflow_time"] = 120.0

if os.getenv("TEST_ENV") == "local":
    # Local development adjustments
    TEST_CONFIG["timeout"]["service_startup"] = 20
    TEST_CONFIG["performance_thresholds"]["max_concurrent_requests"] = 3


def get_test_config() -> Dict[str, Any]:
    """Get the current test configuration."""
    return TEST_CONFIG


def get_test_strategy(strategy_name: str) -> Dict[str, Any]:
    """Get a specific test strategy by name."""
    return TEST_CONFIG["test_strategies"].get(strategy_name, {})


def get_performance_threshold(threshold_name: str) -> float:
    """Get a specific performance threshold."""
    return TEST_CONFIG["performance_thresholds"].get(threshold_name, 0.0)
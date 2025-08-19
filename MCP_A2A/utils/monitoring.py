"""
Monitoring and metrics collection for the MCP A2A Trading System.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import json

from .logging_config import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """A single metric value with timestamp."""
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for a service or operation."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def average_response_time(self) -> float:
        """Calculate average response time."""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time / self.total_requests
    
    @property
    def p95_response_time(self) -> float:
        """Calculate 95th percentile response time."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[min(index, len(sorted_times) - 1)]
    
    def record_request(self, response_time: float, success: bool):
        """Record a request with its response time and success status."""
        self.total_requests += 1
        self.total_response_time += response_time
        self.response_times.append(response_time)
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.min_response_time = min(self.min_response_time, response_time)
        self.max_response_time = max(self.max_response_time, response_time)


class MetricsCollector:
    """Collects and manages metrics for the trading system."""
    
    def __init__(self):
        self.metrics: Dict[str, List[MetricValue]] = defaultdict(list)
        self.performance_metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self.start_time = datetime.now()
        self._lock = asyncio.Lock()
    
    async def record_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Record a counter metric."""
        async with self._lock:
            metric = MetricValue(value, datetime.now(), labels or {})
            self.metrics[f"counter_{name}"].append(metric)
            
            # Keep only last 10000 metrics to prevent memory issues
            if len(self.metrics[f"counter_{name}"]) > 10000:
                self.metrics[f"counter_{name}"] = self.metrics[f"counter_{name}"][-5000:]
    
    async def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a gauge metric (current value)."""
        async with self._lock:
            metric = MetricValue(value, datetime.now(), labels or {})
            # For gauges, we only keep the latest value per label combination
            key = f"gauge_{name}"
            label_key = json.dumps(labels or {}, sort_keys=True)
            
            # Remove old values with same labels
            self.metrics[key] = [m for m in self.metrics[key] 
                               if json.dumps(m.labels, sort_keys=True) != label_key]
            self.metrics[key].append(metric)
    
    async def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram metric."""
        async with self._lock:
            metric = MetricValue(value, datetime.now(), labels or {})
            self.metrics[f"histogram_{name}"].append(metric)
            
            # Keep only last 10000 metrics
            if len(self.metrics[f"histogram_{name}"]) > 10000:
                self.metrics[f"histogram_{name}"] = self.metrics[f"histogram_{name}"][-5000:]
    
    async def record_performance(self, service_name: str, operation: str, response_time: float, success: bool):
        """Record performance metrics for a service operation."""
        async with self._lock:
            key = f"{service_name}_{operation}"
            self.performance_metrics[key].record_request(response_time, success)
    
    def get_counter_value(self, name: str, labels: Dict[str, str] = None, since: datetime = None) -> float:
        """Get total counter value, optionally filtered by labels and time."""
        key = f"counter_{name}"
        if key not in self.metrics:
            return 0.0
        
        total = 0.0
        label_filter = json.dumps(labels or {}, sort_keys=True) if labels else None
        
        for metric in self.metrics[key]:
            if since and metric.timestamp < since:
                continue
            if label_filter and json.dumps(metric.labels, sort_keys=True) != label_filter:
                continue
            total += metric.value
        
        return total
    
    def get_gauge_value(self, name: str, labels: Dict[str, str] = None) -> Optional[float]:
        """Get current gauge value."""
        key = f"gauge_{name}"
        if key not in self.metrics:
            return None
        
        label_filter = json.dumps(labels or {}, sort_keys=True) if labels else None
        
        # Find the most recent metric with matching labels
        latest_metric = None
        for metric in reversed(self.metrics[key]):
            if label_filter and json.dumps(metric.labels, sort_keys=True) != label_filter:
                continue
            latest_metric = metric
            break
        
        return latest_metric.value if latest_metric else None
    
    def get_histogram_stats(self, name: str, labels: Dict[str, str] = None, since: datetime = None) -> Dict[str, float]:
        """Get histogram statistics."""
        key = f"histogram_{name}"
        if key not in self.metrics:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}
        
        values = []
        label_filter = json.dumps(labels or {}, sort_keys=True) if labels else None
        
        for metric in self.metrics[key]:
            if since and metric.timestamp < since:
                continue
            if label_filter and json.dumps(metric.labels, sort_keys=True) != label_filter:
                continue
            values.append(metric.value)
        
        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}
        
        values.sort()
        count = len(values)
        total = sum(values)
        
        def percentile(p):
            index = int(count * p / 100)
            return values[min(index, count - 1)]
        
        return {
            "count": count,
            "sum": total,
            "avg": total / count,
            "min": values[0],
            "max": values[-1],
            "p50": percentile(50),
            "p95": percentile(95),
            "p99": percentile(99)
        }
    
    def get_performance_metrics(self, service_name: str = None) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for services."""
        if service_name:
            # Return metrics for specific service
            result = {}
            for key, metrics in self.performance_metrics.items():
                if key.startswith(f"{service_name}_"):
                    operation = key[len(f"{service_name}_"):]
                    result[operation] = {
                        "total_requests": metrics.total_requests,
                        "successful_requests": metrics.successful_requests,
                        "failed_requests": metrics.failed_requests,
                        "success_rate": metrics.success_rate,
                        "average_response_time": metrics.average_response_time,
                        "min_response_time": metrics.min_response_time if metrics.min_response_time != float('inf') else 0,
                        "max_response_time": metrics.max_response_time,
                        "p95_response_time": metrics.p95_response_time
                    }
            return result
        else:
            # Return all performance metrics
            result = {}
            for key, metrics in self.performance_metrics.items():
                result[key] = {
                    "total_requests": metrics.total_requests,
                    "successful_requests": metrics.successful_requests,
                    "failed_requests": metrics.failed_requests,
                    "success_rate": metrics.success_rate,
                    "average_response_time": metrics.average_response_time,
                    "min_response_time": metrics.min_response_time if metrics.min_response_time != float('inf') else 0,
                    "max_response_time": metrics.max_response_time,
                    "p95_response_time": metrics.p95_response_time
                }
            return result
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get overall system metrics."""
        uptime = datetime.now() - self.start_time
        
        # Calculate total requests across all services
        total_requests = sum(metrics.total_requests for metrics in self.performance_metrics.values())
        total_successful = sum(metrics.successful_requests for metrics in self.performance_metrics.values())
        total_failed = sum(metrics.failed_requests for metrics in self.performance_metrics.values())
        
        overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": str(uptime),
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "failed_requests": total_failed,
            "overall_success_rate": overall_success_rate,
            "services_count": len(set(key.split('_')[0] for key in self.performance_metrics.keys())),
            "operations_count": len(self.performance_metrics),
            "metrics_collected": sum(len(values) for values in self.metrics.values())
        }
    
    async def cleanup_old_metrics(self, older_than: timedelta = timedelta(hours=24)):
        """Clean up metrics older than specified time."""
        async with self._lock:
            cutoff_time = datetime.now() - older_than
            
            for metric_name in list(self.metrics.keys()):
                self.metrics[metric_name] = [
                    metric for metric in self.metrics[metric_name]
                    if metric.timestamp >= cutoff_time
                ]
                
                # Remove empty metric lists
                if not self.metrics[metric_name]:
                    del self.metrics[metric_name]
            
            logger.info(f"Cleaned up metrics older than {older_than}")


class PerformanceTimer:
    """Context manager for timing operations and recording metrics."""
    
    def __init__(self, metrics_collector: MetricsCollector, service_name: str, operation: str):
        self.metrics_collector = metrics_collector
        self.service_name = service_name
        self.operation = operation
        self.start_time = None
        self.success = True
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            response_time = time.time() - self.start_time
            self.success = exc_type is None
            
            await self.metrics_collector.record_performance(
                self.service_name,
                self.operation,
                response_time,
                self.success
            )
            
            # Also record as histogram
            await self.metrics_collector.record_histogram(
                f"{self.service_name}_response_time",
                response_time,
                {"operation": self.operation, "success": str(self.success)}
            )
    
    def mark_failure(self):
        """Mark this operation as failed."""
        self.success = False


class TradingSystemMonitor:
    """High-level monitoring for the trading system."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.trading_metrics = {
            "trades_executed": 0,
            "trades_failed": 0,
            "total_trade_value": 0.0,
            "portfolio_value": 0.0,
            "active_positions": 0
        }
    
    async def record_trade_execution(self, success: bool, trade_value: float = 0.0):
        """Record trade execution metrics."""
        if success:
            self.trading_metrics["trades_executed"] += 1
            self.trading_metrics["total_trade_value"] += trade_value
            await self.metrics.record_counter("trades_executed", 1.0, {"status": "success"})
        else:
            self.trading_metrics["trades_failed"] += 1
            await self.metrics.record_counter("trades_executed", 1.0, {"status": "failed"})
        
        await self.metrics.record_gauge("total_trade_value", self.trading_metrics["total_trade_value"])
    
    async def record_portfolio_update(self, portfolio_value: float, active_positions: int):
        """Record portfolio metrics."""
        self.trading_metrics["portfolio_value"] = portfolio_value
        self.trading_metrics["active_positions"] = active_positions
        
        await self.metrics.record_gauge("portfolio_value", portfolio_value)
        await self.metrics.record_gauge("active_positions", active_positions)
    
    async def record_analysis_result(self, analysis_type: str, success: bool, confidence: float = None):
        """Record analysis metrics."""
        labels = {"type": analysis_type, "success": str(success)}
        await self.metrics.record_counter("analysis_requests", 1.0, labels)
        
        if confidence is not None:
            await self.metrics.record_histogram("analysis_confidence", confidence, {"type": analysis_type})
    
    async def record_risk_decision(self, decision: str):
        """Record risk management decisions."""
        await self.metrics.record_counter("risk_decisions", 1.0, {"decision": decision})
    
    def get_trading_summary(self) -> Dict[str, Any]:
        """Get trading system summary metrics."""
        total_trades = self.trading_metrics["trades_executed"] + self.trading_metrics["trades_failed"]
        success_rate = (self.trading_metrics["trades_executed"] / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "total_trades": total_trades,
            "successful_trades": self.trading_metrics["trades_executed"],
            "failed_trades": self.trading_metrics["trades_failed"],
            "trade_success_rate": success_rate,
            "total_trade_value": self.trading_metrics["total_trade_value"],
            "current_portfolio_value": self.trading_metrics["portfolio_value"],
            "active_positions": self.trading_metrics["active_positions"]
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()
trading_monitor = TradingSystemMonitor(metrics_collector)


def performance_timer(service_name: str, operation: str) -> PerformanceTimer:
    """Create a performance timer for an operation."""
    return PerformanceTimer(metrics_collector, service_name, operation)


async def record_request_metrics(service_name: str, operation: str, response_time: float, success: bool):
    """Convenience function to record request metrics."""
    await metrics_collector.record_performance(service_name, operation, response_time, success)


async def record_counter(name: str, value: float = 1.0, labels: Dict[str, str] = None):
    """Convenience function to record counter metrics."""
    await metrics_collector.record_counter(name, value, labels)


async def record_gauge(name: str, value: float, labels: Dict[str, str] = None):
    """Convenience function to record gauge metrics."""
    await metrics_collector.record_gauge(name, value, labels)


async def record_histogram(name: str, value: float, labels: Dict[str, str] = None):
    """Convenience function to record histogram metrics."""
    await metrics_collector.record_histogram(name, value, labels)
"""
Audit logging for the MCP A2A Trading System.
Provides comprehensive audit trails for all trading decisions and operations.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

from .logging_config import get_logger
from .correlation_id import get_correlation_id

logger = get_logger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    TECHNICAL_ANALYSIS = "technical_analysis"
    RISK_EVALUATION = "risk_evaluation"
    TRADE_EXECUTION = "trade_execution"
    
    TRADE_PROPOSAL = "trade_proposal"
    TRADE_APPROVED = "trade_approved"
    TRADE_DENIED = "trade_denied"
    TRADE_EXECUTED = "trade_executed"
    TRADE_FAILED = "trade_failed"
    
    PORTFOLIO_UPDATE = "portfolio_update"
    RISK_VIOLATION = "risk_violation"
    SERVICE_ERROR = "service_error"
    FALLBACK_USED = "fallback_used"
    
    A2A_REQUEST = "a2a_request"
    A2A_RESPONSE = "a2a_response"
    MCP_REQUEST = "mcp_request"
    MCP_RESPONSE = "mcp_response"


@dataclass
class AuditEvent:
    """Represents a single audit event."""
    event_type: AuditEventType
    timestamp: datetime
    correlation_id: Optional[str]
    service_name: str
    operation: str
    details: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary for logging."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "service_name": self.service_name,
            "operation": self.operation,
            "details": self.details,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "success": self.success,
            "error_message": self.error_message
        }


class AuditLogger:
    """Handles audit logging for the trading system."""
    
    def __init__(self):
        self.audit_events: List[AuditEvent] = []
        self.max_events = 10000  # Keep last 10k events in memory
    
    def log_event(
        self,
        event_type: AuditEventType,
        service_name: str,
        operation: str,
        details: Dict[str, Any] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log an audit event."""
        event = AuditEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            correlation_id=get_correlation_id(),
            service_name=service_name,
            operation=operation,
            details=details or {},
            user_id=user_id,
            session_id=session_id,
            success=success,
            error_message=error_message
        )
        
        # Add to in-memory storage
        self.audit_events.append(event)
        
        # Trim old events if necessary
        if len(self.audit_events) > self.max_events:
            self.audit_events = self.audit_events[-self.max_events//2:]
        
        # Log to structured logger
        logger.info(
            f"AUDIT: {event_type.value}",
            extra={
                "audit_event": event.to_dict(),
                "event_type": event_type.value,
                "service_name": service_name,
                "operation": operation,
                "success": success
            }
        )
    
    def log_workflow_started(
        self,
        workflow_id: str,
        strategy: Dict[str, Any],
        service_name: str = "portfolio_manager"
    ):
        """Log workflow start event."""
        self.log_event(
            AuditEventType.WORKFLOW_STARTED,
            service_name,
            "start_workflow",
            {
                "workflow_id": workflow_id,
                "strategy": strategy
            }
        )
    
    def log_workflow_completed(
        self,
        workflow_id: str,
        result: Dict[str, Any],
        service_name: str = "portfolio_manager"
    ):
        """Log workflow completion event."""
        self.log_event(
            AuditEventType.WORKFLOW_COMPLETED,
            service_name,
            "complete_workflow",
            {
                "workflow_id": workflow_id,
                "result": result
            }
        )
    
    def log_workflow_failed(
        self,
        workflow_id: str,
        error: str,
        stage: str,
        service_name: str = "portfolio_manager"
    ):
        """Log workflow failure event."""
        self.log_event(
            AuditEventType.WORKFLOW_FAILED,
            service_name,
            "fail_workflow",
            {
                "workflow_id": workflow_id,
                "failed_stage": stage
            },
            success=False,
            error_message=error
        )
    
    def log_fundamental_analysis(
        self,
        ticker: str,
        result: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None
    ):
        """Log fundamental analysis event."""
        self.log_event(
            AuditEventType.FUNDAMENTAL_ANALYSIS,
            "fundamental_analyst",
            "analyze_company",
            {
                "ticker": ticker,
                "score": result.get("score"),
                "recommendation": result.get("recommendation"),
                "confidence": result.get("confidence")
            },
            success=success,
            error_message=error
        )
    
    def log_technical_analysis(
        self,
        ticker: str,
        result: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None
    ):
        """Log technical analysis event."""
        self.log_event(
            AuditEventType.TECHNICAL_ANALYSIS,
            "technical_analyst",
            "analyze_ticker",
            {
                "ticker": ticker,
                "signal": result.get("signal"),
                "confidence": result.get("confidence"),
                "indicators": list(result.get("indicators", {}).keys())
            },
            success=success,
            error_message=error
        )
    
    def log_trade_proposal(
        self,
        proposal: Dict[str, Any],
        service_name: str = "portfolio_manager"
    ):
        """Log trade proposal creation."""
        self.log_event(
            AuditEventType.TRADE_PROPOSAL,
            service_name,
            "create_trade_proposal",
            {
                "ticker": proposal.get("ticker"),
                "action": proposal.get("action"),
                "quantity": proposal.get("quantity"),
                "estimated_price": proposal.get("estimated_price"),
                "rationale": proposal.get("rationale"),
                "risk_level": proposal.get("risk_level")
            }
        )
    
    def log_risk_evaluation(
        self,
        proposal: Dict[str, Any],
        decision: str,
        violations: List[str] = None,
        warnings: List[str] = None
    ):
        """Log risk evaluation event."""
        self.log_event(
            AuditEventType.RISK_EVALUATION,
            "risk_manager",
            "evaluate_trade",
            {
                "ticker": proposal.get("ticker"),
                "action": proposal.get("action"),
                "quantity": proposal.get("quantity"),
                "decision": decision,
                "violations": violations or [],
                "warnings": warnings or []
            },
            success=decision in ["APPROVE", "CONDITIONAL_APPROVE"]
        )
        
        # Log specific approval/denial events
        if decision == "APPROVE":
            self.log_trade_approved(proposal)
        elif decision == "CONDITIONAL_APPROVE":
            self.log_trade_approved(proposal, conditional=True, warnings=warnings)
        else:
            self.log_trade_denied(proposal, violations or [])
    
    def log_trade_approved(
        self,
        proposal: Dict[str, Any],
        conditional: bool = False,
        warnings: List[str] = None
    ):
        """Log trade approval event."""
        self.log_event(
            AuditEventType.TRADE_APPROVED,
            "risk_manager",
            "approve_trade",
            {
                "ticker": proposal.get("ticker"),
                "action": proposal.get("action"),
                "quantity": proposal.get("quantity"),
                "conditional": conditional,
                "warnings": warnings or []
            }
        )
    
    def log_trade_denied(self, proposal: Dict[str, Any], violations: List[str]):
        """Log trade denial event."""
        self.log_event(
            AuditEventType.TRADE_DENIED,
            "risk_manager",
            "deny_trade",
            {
                "ticker": proposal.get("ticker"),
                "action": proposal.get("action"),
                "quantity": proposal.get("quantity"),
                "violations": violations
            },
            success=False
        )
    
    def log_trade_execution(
        self,
        proposal: Dict[str, Any],
        result: Dict[str, Any],
        success: bool = True
    ):
        """Log trade execution event."""
        event_type = AuditEventType.TRADE_EXECUTED if success else AuditEventType.TRADE_FAILED
        
        self.log_event(
            event_type,
            "trade_executor",
            "execute_trade",
            {
                "ticker": proposal.get("ticker"),
                "action": proposal.get("action"),
                "quantity": proposal.get("quantity"),
                "estimated_price": proposal.get("estimated_price"),
                "executed_price": result.get("executed_price"),
                "executed_quantity": result.get("executed_quantity"),
                "trade_id": result.get("trade_id"),
                "total_value": result.get("total_value"),
                "slippage": result.get("slippage"),
                "execution_status": result.get("execution_status")
            },
            success=success,
            error_message=result.get("message") if not success else None
        )
    
    def log_portfolio_update(
        self,
        portfolio_status: Dict[str, Any],
        service_name: str = "trading_execution_mcp"
    ):
        """Log portfolio update event."""
        self.log_event(
            AuditEventType.PORTFOLIO_UPDATE,
            service_name,
            "update_portfolio",
            {
                "total_value": portfolio_status.get("total_portfolio_value"),
                "cash_balance": portfolio_status.get("cash_balance"),
                "positions_count": portfolio_status.get("number_of_positions"),
                "equity_value": portfolio_status.get("total_equity_value")
            }
        )
    
    def log_risk_violation(
        self,
        violation_type: str,
        details: Dict[str, Any],
        service_name: str = "risk_manager"
    ):
        """Log risk violation event."""
        self.log_event(
            AuditEventType.RISK_VIOLATION,
            service_name,
            "risk_violation",
            {
                "violation_type": violation_type,
                **details
            },
            success=False
        )
    
    def log_service_error(
        self,
        service_name: str,
        operation: str,
        error: str,
        details: Dict[str, Any] = None
    ):
        """Log service error event."""
        self.log_event(
            AuditEventType.SERVICE_ERROR,
            service_name,
            operation,
            details or {},
            success=False,
            error_message=error
        )
    
    def log_fallback_used(
        self,
        service_name: str,
        operation: str,
        fallback_type: str,
        original_error: str
    ):
        """Log fallback usage event."""
        self.log_event(
            AuditEventType.FALLBACK_USED,
            service_name,
            operation,
            {
                "fallback_type": fallback_type,
                "original_error": original_error
            }
        )
    
    def log_a2a_request(
        self,
        source_service: str,
        target_service: str,
        method: str,
        params: Dict[str, Any] = None
    ):
        """Log A2A request event."""
        self.log_event(
            AuditEventType.A2A_REQUEST,
            source_service,
            f"a2a_call_{method}",
            {
                "target_service": target_service,
                "method": method,
                "params_keys": list(params.keys()) if params else []
            }
        )
    
    def log_a2a_response(
        self,
        source_service: str,
        target_service: str,
        method: str,
        success: bool,
        response_time: float,
        error: Optional[str] = None
    ):
        """Log A2A response event."""
        self.log_event(
            AuditEventType.A2A_RESPONSE,
            target_service,
            f"a2a_response_{method}",
            {
                "source_service": source_service,
                "method": method,
                "response_time": response_time
            },
            success=success,
            error_message=error
        )
    
    def log_mcp_request(
        self,
        service_name: str,
        endpoint: str,
        params: Dict[str, Any] = None
    ):
        """Log MCP request event."""
        self.log_event(
            AuditEventType.MCP_REQUEST,
            service_name,
            f"mcp_call_{endpoint}",
            {
                "endpoint": endpoint,
                "params_keys": list(params.keys()) if params else []
            }
        )
    
    def log_mcp_response(
        self,
        service_name: str,
        endpoint: str,
        success: bool,
        response_time: float,
        error: Optional[str] = None
    ):
        """Log MCP response event."""
        self.log_event(
            AuditEventType.MCP_RESPONSE,
            service_name,
            f"mcp_response_{endpoint}",
            {
                "endpoint": endpoint,
                "response_time": response_time
            },
            success=success,
            error_message=error
        )
    
    def get_audit_trail(
        self,
        correlation_id: Optional[str] = None,
        service_name: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        since: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get audit trail with optional filtering."""
        events = self.audit_events
        
        # Apply filters
        if correlation_id:
            events = [e for e in events if e.correlation_id == correlation_id]
        
        if service_name:
            events = [e for e in events if e.service_name == service_name]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        # Sort by timestamp (newest first) and limit
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]
        
        return [event.to_dict() for event in events]
    
    def get_workflow_audit_trail(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get complete audit trail for a specific workflow."""
        # Find the correlation ID for this workflow
        workflow_events = [
            e for e in self.audit_events
            if e.event_type == AuditEventType.WORKFLOW_STARTED
            and e.details.get("workflow_id") == workflow_id
        ]
        
        if not workflow_events:
            return []
        
        correlation_id = workflow_events[0].correlation_id
        return self.get_audit_trail(correlation_id=correlation_id)
    
    def get_trading_audit_summary(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Get trading audit summary."""
        events = self.audit_events
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        # Count events by type
        event_counts = {}
        for event in events:
            event_counts[event.event_type.value] = event_counts.get(event.event_type.value, 0) + 1
        
        # Trading-specific metrics
        trades_executed = len([e for e in events if e.event_type == AuditEventType.TRADE_EXECUTED])
        trades_failed = len([e for e in events if e.event_type == AuditEventType.TRADE_FAILED])
        trades_approved = len([e for e in events if e.event_type == AuditEventType.TRADE_APPROVED])
        trades_denied = len([e for e in events if e.event_type == AuditEventType.TRADE_DENIED])
        
        workflows_started = len([e for e in events if e.event_type == AuditEventType.WORKFLOW_STARTED])
        workflows_completed = len([e for e in events if e.event_type == AuditEventType.WORKFLOW_COMPLETED])
        workflows_failed = len([e for e in events if e.event_type == AuditEventType.WORKFLOW_FAILED])
        
        return {
            "total_events": len(events),
            "event_counts": event_counts,
            "trading_metrics": {
                "trades_executed": trades_executed,
                "trades_failed": trades_failed,
                "trades_approved": trades_approved,
                "trades_denied": trades_denied,
                "trade_success_rate": (trades_executed / (trades_executed + trades_failed) * 100) if (trades_executed + trades_failed) > 0 else 0
            },
            "workflow_metrics": {
                "workflows_started": workflows_started,
                "workflows_completed": workflows_completed,
                "workflows_failed": workflows_failed,
                "workflow_success_rate": (workflows_completed / workflows_started * 100) if workflows_started > 0 else 0
            }
        }


# Global audit logger instance
audit_logger = AuditLogger()
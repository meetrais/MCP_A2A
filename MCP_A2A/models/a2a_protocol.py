"""
A2A (Agent-to-Agent) Protocol data models.
Implements JSON-RPC 2.0 over HTTP for inter-agent communication.
"""

from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field
import uuid


class A2ARequest(BaseModel):
    """A2A protocol request message following JSON-RPC 2.0 specification."""
    
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name to call")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method parameters")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Request ID")


class A2AError(BaseModel):
    """A2A protocol error object."""
    
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional error data")


class A2AResponse(BaseModel):
    """A2A protocol response message following JSON-RPC 2.0 specification."""
    
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Method result")
    error: Optional[A2AError] = Field(default=None, description="Error object if method failed")
    id: str = Field(..., description="Request ID this response corresponds to")
    
    def is_success(self) -> bool:
        """Check if the response indicates success."""
        return self.error is None
    
    def is_error(self) -> bool:
        """Check if the response indicates an error."""
        return self.error is not None


# Common A2A error codes
class A2AErrorCodes:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # Custom application error codes
    ANALYSIS_FAILED = -32001
    INSUFFICIENT_DATA = -32002
    RISK_VIOLATION = -32003
    TRADE_EXECUTION_FAILED = -32004
    SERVICE_UNAVAILABLE = -32005
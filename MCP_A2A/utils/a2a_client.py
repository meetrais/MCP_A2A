"""
A2A (Agent-to-Agent) protocol client for sending JSON-RPC requests between agents.
"""

import asyncio
from typing import Any, Dict, Optional
import httpx
from ..models.a2a_protocol import A2ARequest, A2AResponse, A2AError, A2AErrorCodes
from ..config import SYSTEM_CONFIG
from .logging_config import get_logger
from .correlation_id import get_correlation_id
from .error_recovery import error_recovery_manager

logger = get_logger(__name__)


class A2AClient:
    """Client for sending A2A protocol requests to other agents."""
    
    def __init__(self, timeout: float = None):
        """
        Initialize A2A client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout or SYSTEM_CONFIG["request_timeout"]
        self.retry_attempts = SYSTEM_CONFIG["retry_attempts"]
        self.retry_delay = SYSTEM_CONFIG["retry_delay"]
    
    async def send_request(
        self,
        target_url: str,
        method: str,
        params: Dict[str, Any] = None,
        request_id: str = None
    ) -> A2AResponse:
        """
        Send an A2A request to another agent with error recovery.
        
        Args:
            target_url: Target agent URL
            method: Method name to call
            params: Method parameters
            request_id: Optional request ID
            
        Returns:
            A2A response from the target agent
            
        Raises:
            A2AClientError: If the request fails after all retries
        """
        if params is None:
            params = {}
        
        request = A2ARequest(
            method=method,
            params=params,
            id=request_id
        )
        
        correlation_id = get_correlation_id()
        headers = {}
        if correlation_id:
            headers[SYSTEM_CONFIG["correlation_id_header"]] = correlation_id
        
        logger.info(
            f"Sending A2A request to {target_url}",
            extra={
                "method": method,
                "target_url": target_url,
                "request_id": request.id,
                "params_keys": list(params.keys())
            }
        )
        
        # Extract service name from URL for error recovery
        service_name = self._extract_service_name(target_url)
        
        async def make_request():
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{target_url}/a2a",
                    json=request.dict(),
                    headers=headers
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    a2a_response = A2AResponse(**response_data)
                    
                    logger.info(
                        f"Received A2A response from {target_url}",
                        extra={
                            "request_id": request.id,
                            "success": a2a_response.is_success(),
                            "has_error": a2a_response.is_error()
                        }
                    )
                    
                    return a2a_response
                else:
                    raise httpx.HTTPStatusError(
                        f"HTTP {response.status_code}",
                        request=response.request,
                        response=response
                    )
        
        try:
            # Use error recovery manager for resilient execution
            return await error_recovery_manager.execute_with_recovery(
                service_name,
                make_request,
                method=method
            )
            
        except Exception as e:
            logger.error(
                f"A2A request failed after all recovery attempts",
                extra={
                    "target_url": target_url,
                    "method": method,
                    "request_id": request.id,
                    "error": str(e)
                }
            )
            
            # Return error response
            return A2AResponse(
                id=request.id,
                error=A2AError(
                    code=A2AErrorCodes.SERVICE_UNAVAILABLE,
                    message=f"Failed to reach {target_url}: {str(e)}"
                )
            )
    
    def _extract_service_name(self, url: str) -> str:
        """Extract service name from URL for error recovery."""
        # Extract service name from URL (e.g., http://localhost:8001 -> fundamental_analyst)
        port_mapping = {
            "8000": "portfolio_manager",
            "8001": "fundamental_analyst", 
            "8002": "technical_analyst",
            "8003": "risk_manager",
            "8004": "trade_executor",
            "9000": "market_data_mcp",
            "9001": "technical_analysis_mcp",
            "9002": "trading_execution_mcp"
        }
        
        for port, service in port_mapping.items():
            if f":{port}" in url:
                return service
        
        return "unknown_service"
    
    async def call_agent(
        self,
        target_url: str,
        method: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Convenience method to call an agent and return the result directly.
        
        Args:
            target_url: Target agent URL
            method: Method name to call
            **kwargs: Method parameters
            
        Returns:
            Method result dictionary
            
        Raises:
            A2AClientError: If the request fails or returns an error
        """
        response = await self.send_request(target_url, method, kwargs)
        
        if response.is_error():
            raise A2AClientError(
                f"A2A call failed: {response.error.message}",
                error_code=response.error.code,
                error_data=response.error.data
            )
        
        return response.result or {}


class A2AClientError(Exception):
    """Exception raised by A2A client operations."""
    
    def __init__(self, message: str, error_code: int = None, error_data: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.error_data = error_data
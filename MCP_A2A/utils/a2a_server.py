"""
A2A (Agent-to-Agent) protocol server endpoint handler for receiving agent communications.
"""

from typing import Any, Callable, Dict, Optional
from fastapi import Request, HTTPException
from ..models.a2a_protocol import A2ARequest, A2AResponse, A2AError, A2AErrorCodes
from .logging_config import get_logger
from .correlation_id import set_correlation_id, generate_correlation_id
from ..config import SYSTEM_CONFIG

logger = get_logger(__name__)


class A2AServer:
    """Server for handling incoming A2A protocol requests."""
    
    def __init__(self):
        """Initialize A2A server."""
        self.methods: Dict[str, Callable] = {}
    
    def register_method(self, method_name: str, handler: Callable):
        """
        Register a method handler for A2A calls.
        
        Args:
            method_name: Name of the method
            handler: Async function to handle the method call
        """
        self.methods[method_name] = handler
        logger.info(f"Registered A2A method: {method_name}")
    
    async def handle_request(self, request: Request) -> A2AResponse:
        """
        Handle incoming A2A request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            A2A response
        """
        # Extract correlation ID from headers
        correlation_id = request.headers.get(SYSTEM_CONFIG["correlation_id_header"])
        if not correlation_id:
            correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)
        
        try:
            # Parse request body
            request_data = await request.json()
            a2a_request = A2ARequest(**request_data)
            
            logger.info(
                f"Received A2A request",
                extra={
                    "method": a2a_request.method,
                    "request_id": a2a_request.id,
                    "params_keys": list(a2a_request.params.keys()) if a2a_request.params else []
                }
            )
            
            # Check if method is registered
            if a2a_request.method not in self.methods:
                error = A2AError(
                    code=A2AErrorCodes.METHOD_NOT_FOUND,
                    message=f"Method '{a2a_request.method}' not found"
                )
                logger.warning(
                    f"Method not found: {a2a_request.method}",
                    extra={"request_id": a2a_request.id}
                )
                return A2AResponse(id=a2a_request.id, error=error)
            
            # Call method handler
            try:
                handler = self.methods[a2a_request.method]
                result = await handler(**a2a_request.params)
                
                logger.info(
                    f"A2A method executed successfully",
                    extra={
                        "method": a2a_request.method,
                        "request_id": a2a_request.id
                    }
                )
                
                return A2AResponse(id=a2a_request.id, result=result)
                
            except TypeError as e:
                # Invalid parameters
                error = A2AError(
                    code=A2AErrorCodes.INVALID_PARAMS,
                    message=f"Invalid parameters for method '{a2a_request.method}': {str(e)}"
                )
                logger.warning(
                    f"Invalid parameters for method {a2a_request.method}",
                    extra={"request_id": a2a_request.id, "error": str(e)}
                )
                return A2AResponse(id=a2a_request.id, error=error)
                
            except Exception as e:
                # Internal error
                error = A2AError(
                    code=A2AErrorCodes.INTERNAL_ERROR,
                    message=f"Internal error executing method '{a2a_request.method}': {str(e)}"
                )
                logger.error(
                    f"Internal error executing method {a2a_request.method}",
                    extra={"request_id": a2a_request.id, "error": str(e)},
                    exc_info=True
                )
                return A2AResponse(id=a2a_request.id, error=error)
        
        except ValueError as e:
            # JSON parsing error
            error = A2AError(
                code=A2AErrorCodes.PARSE_ERROR,
                message=f"Failed to parse request: {str(e)}"
            )
            logger.error(f"Failed to parse A2A request", extra={"error": str(e)})
            return A2AResponse(id="unknown", error=error)
        
        except Exception as e:
            # Unexpected error
            error = A2AError(
                code=A2AErrorCodes.INTERNAL_ERROR,
                message=f"Unexpected error: {str(e)}"
            )
            logger.error(f"Unexpected error handling A2A request", extra={"error": str(e)}, exc_info=True)
            return A2AResponse(id="unknown", error=error)


def create_a2a_endpoint(a2a_server: A2AServer):
    """
    Create FastAPI endpoint for A2A protocol.
    
    Args:
        a2a_server: A2A server instance
        
    Returns:
        FastAPI endpoint function
    """
    async def a2a_endpoint(request: Request):
        """A2A protocol endpoint."""
        response = await a2a_server.handle_request(request)
        return response.dict()
    
    return a2a_endpoint
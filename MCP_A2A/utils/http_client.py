"""
HTTP client utilities with retry logic and error handling.
"""

import asyncio
from typing import Any, Dict, Optional
import httpx
from .logging_config import get_logger
from .correlation_id import get_correlation_id
from ..config import SYSTEM_CONFIG

logger = get_logger(__name__)


class HTTPClient:
    """HTTP client with retry logic and correlation ID support."""
    
    def __init__(self, timeout: float = None):
        """
        Initialize HTTP client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout or SYSTEM_CONFIG["request_timeout"]
        self.retry_attempts = SYSTEM_CONFIG["retry_attempts"]
        self.retry_delay = SYSTEM_CONFIG["retry_delay"]
    
    async def post(
        self,
        url: str,
        json_data: Dict[str, Any] = None,
        headers: Dict[str, str] = None
    ) -> httpx.Response:
        """
        Send POST request with retry logic.
        
        Args:
            url: Target URL
            json_data: JSON data to send
            headers: Additional headers
            
        Returns:
            HTTP response
            
        Raises:
            HTTPClientError: If request fails after all retries
        """
        if headers is None:
            headers = {}
        
        # Add correlation ID header
        correlation_id = get_correlation_id()
        if correlation_id:
            headers[SYSTEM_CONFIG["correlation_id_header"]] = correlation_id
        
        logger.debug(f"Sending POST request to {url}")
        
        for attempt in range(self.retry_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=json_data, headers=headers)
                    
                    logger.debug(
                        f"Received response from {url}",
                        extra={"status_code": response.status_code}
                    )
                    
                    return response
                    
            except httpx.TimeoutException:
                logger.warning(
                    f"Timeout calling {url}",
                    extra={"attempt": attempt + 1, "timeout": self.timeout}
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"Request error calling {url}: {e}",
                    extra={"attempt": attempt + 1, "error": str(e)}
                )
            
            # Wait before retry (except on last attempt)
            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
        
        # All retries failed
        raise HTTPClientError(f"Failed to reach {url} after {self.retry_attempts} attempts")
    
    async def get(
        self,
        url: str,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None
    ) -> httpx.Response:
        """
        Send GET request with retry logic.
        
        Args:
            url: Target URL
            params: Query parameters
            headers: Additional headers
            
        Returns:
            HTTP response
            
        Raises:
            HTTPClientError: If request fails after all retries
        """
        if headers is None:
            headers = {}
        
        # Add correlation ID header
        correlation_id = get_correlation_id()
        if correlation_id:
            headers[SYSTEM_CONFIG["correlation_id_header"]] = correlation_id
        
        logger.debug(f"Sending GET request to {url}")
        
        for attempt in range(self.retry_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params, headers=headers)
                    
                    logger.debug(
                        f"Received response from {url}",
                        extra={"status_code": response.status_code}
                    )
                    
                    return response
                    
            except httpx.TimeoutException:
                logger.warning(
                    f"Timeout calling {url}",
                    extra={"attempt": attempt + 1, "timeout": self.timeout}
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"Request error calling {url}: {e}",
                    extra={"attempt": attempt + 1, "error": str(e)}
                )
            
            # Wait before retry (except on last attempt)
            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
        
        # All retries failed
        raise HTTPClientError(f"Failed to reach {url} after {self.retry_attempts} attempts")


class HTTPClientError(Exception):
    """Exception raised by HTTP client operations."""
    pass
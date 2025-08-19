"""
Unit tests for A2A protocol implementation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import Request
import httpx

from ..models.a2a_protocol import A2ARequest, A2AResponse, A2AError, A2AErrorCodes
from ..utils.a2a_client import A2AClient, A2AClientError
from ..utils.a2a_server import A2AServer


class TestA2AProtocolModels:
    """Test A2A protocol data models."""
    
    def test_a2a_request_creation(self):
        """Test A2A request creation."""
        request = A2ARequest(
            method="test_method",
            params={"param1": "value1"}
        )
        
        assert request.jsonrpc == "2.0"
        assert request.method == "test_method"
        assert request.params == {"param1": "value1"}
        assert request.id is not None
    
    def test_a2a_response_success(self):
        """Test successful A2A response."""
        response = A2AResponse(
            id="test-id",
            result={"status": "success"}
        )
        
        assert response.jsonrpc == "2.0"
        assert response.result == {"status": "success"}
        assert response.error is None
        assert response.is_success()
        assert not response.is_error()
    
    def test_a2a_response_error(self):
        """Test error A2A response."""
        error = A2AError(
            code=A2AErrorCodes.INTERNAL_ERROR,
            message="Test error"
        )
        response = A2AResponse(
            id="test-id",
            error=error
        )
        
        assert response.jsonrpc == "2.0"
        assert response.result is None
        assert response.error is not None
        assert not response.is_success()
        assert response.is_error()


class TestA2AClient:
    """Test A2A client functionality."""
    
    @pytest.fixture
    def client(self):
        """Create A2A client for testing."""
        return A2AClient(timeout=5.0)
    
    @pytest.mark.asyncio
    async def test_successful_request(self, client):
        """Test successful A2A request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {"status": "success"}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            response = await client.send_request(
                "http://localhost:8001",
                "test_method",
                {"param1": "value1"}
            )
            
            assert response.is_success()
            assert response.result == {"status": "success"}
    
    @pytest.mark.asyncio
    async def test_error_response(self, client):
        """Test A2A request with error response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "error": {
                "code": A2AErrorCodes.METHOD_NOT_FOUND,
                "message": "Method not found"
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            response = await client.send_request(
                "http://localhost:8001",
                "unknown_method"
            )
            
            assert response.is_error()
            assert response.error.code == A2AErrorCodes.METHOD_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_timeout_retry(self, client):
        """Test timeout and retry logic."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )
            
            response = await client.send_request(
                "http://localhost:8001",
                "test_method"
            )
            
            assert response.is_error()
            assert response.error.code == A2AErrorCodes.SERVICE_UNAVAILABLE
    
    @pytest.mark.asyncio
    async def test_call_agent_success(self, client):
        """Test call_agent convenience method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {"data": "test_data"}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await client.call_agent(
                "http://localhost:8001",
                "get_data",
                param1="value1"
            )
            
            assert result == {"data": "test_data"}
    
    @pytest.mark.asyncio
    async def test_call_agent_error(self, client):
        """Test call_agent with error response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "error": {
                "code": A2AErrorCodes.INTERNAL_ERROR,
                "message": "Internal error"
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            with pytest.raises(A2AClientError):
                await client.call_agent(
                    "http://localhost:8001",
                    "failing_method"
                )


class TestA2AServer:
    """Test A2A server functionality."""
    
    @pytest.fixture
    def server(self):
        """Create A2A server for testing."""
        return A2AServer()
    
    @pytest.mark.asyncio
    async def test_method_registration(self, server):
        """Test method registration."""
        async def test_handler(param1: str):
            return {"result": f"processed_{param1}"}
        
        server.register_method("test_method", test_handler)
        assert "test_method" in server.methods
    
    @pytest.mark.asyncio
    async def test_successful_method_call(self, server):
        """Test successful method call handling."""
        async def test_handler(param1: str):
            return {"result": f"processed_{param1}"}
        
        server.register_method("test_method", test_handler)
        
        # Mock request
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "test-correlation-id"
        mock_request.json = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "method": "test_method",
            "params": {"param1": "test_value"},
            "id": "test-id"
        })
        
        response = await server.handle_request(mock_request)
        
        assert response.is_success()
        assert response.result == {"result": "processed_test_value"}
        assert response.id == "test-id"
    
    @pytest.mark.asyncio
    async def test_method_not_found(self, server):
        """Test method not found error."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "test-correlation-id"
        mock_request.json = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "method": "unknown_method",
            "params": {},
            "id": "test-id"
        })
        
        response = await server.handle_request(mock_request)
        
        assert response.is_error()
        assert response.error.code == A2AErrorCodes.METHOD_NOT_FOUND
        assert response.id == "test-id"
    
    @pytest.mark.asyncio
    async def test_invalid_parameters(self, server):
        """Test invalid parameters error."""
        async def test_handler(required_param: str):
            return {"result": "success"}
        
        server.register_method("test_method", test_handler)
        
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "test-correlation-id"
        mock_request.json = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "method": "test_method",
            "params": {"wrong_param": "value"},
            "id": "test-id"
        })
        
        response = await server.handle_request(mock_request)
        
        assert response.is_error()
        assert response.error.code == A2AErrorCodes.INVALID_PARAMS
    
    @pytest.mark.asyncio
    async def test_internal_error(self, server):
        """Test internal error handling."""
        async def failing_handler():
            raise Exception("Test exception")
        
        server.register_method("failing_method", failing_handler)
        
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "test-correlation-id"
        mock_request.json = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "method": "failing_method",
            "params": {},
            "id": "test-id"
        })
        
        response = await server.handle_request(mock_request)
        
        assert response.is_error()
        assert response.error.code == A2AErrorCodes.INTERNAL_ERROR
    
    @pytest.mark.asyncio
    async def test_parse_error(self, server):
        """Test JSON parse error handling."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "test-correlation-id"
        mock_request.json = AsyncMock(side_effect=ValueError("Invalid JSON"))
        
        response = await server.handle_request(mock_request)
        
        assert response.is_error()
        assert response.error.code == A2AErrorCodes.PARSE_ERROR
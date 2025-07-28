"""
Tests for OPAClient.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from a2a_opa.client import OPAClient, PolicyDecision
from a2a_opa.exceptions import PolicyEvaluationError, OPAConnectionError


class TestOPAClient:
    """Test cases for OPAClient."""
    
    @pytest.fixture
    async def client(self):
        """Create test OPA client."""
        client = OPAClient("http://localhost:8181")
        yield client
        await client.close()
        
    @pytest.fixture
    def mock_response(self):
        """Create mock HTTP response."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 200
        response.json.return_value = {
            "result": {
                "allow": True,
                "violations": []
            }
        }
        return response
        
    async def test_health_check_success(self, client):
        """Test successful health check."""
        with patch.object(client._client, 'get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = await client.health_check()
            assert result is True
            
    async def test_health_check_failure(self, client):
        """Test failed health check."""
        with patch.object(client._client, 'get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")
            
            result = await client.health_check()
            assert result is False
            
    async def test_evaluate_policy_success(self, client, mock_response):
        """Test successful policy evaluation."""
        with patch.object(client._client, 'request', return_value=mock_response):
            decision = await client.evaluate_policy(
                "a2a/test_policy",
                {"requester": {"agent_id": "test_agent"}}
            )
            
            assert isinstance(decision, PolicyDecision)
            assert decision.allow is True
            assert decision.violations == []
            
    async def test_evaluate_policy_denied(self, client):
        """Test policy evaluation that denies access."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "allow": False,
                "violations": ["Access denied"]
            }
        }
        
        with patch.object(client._client, 'request', return_value=mock_response):
            decision = await client.evaluate_policy(
                "a2a/test_policy",
                {"requester": {"agent_id": "unauthorized_agent"}}
            )
            
            assert decision.allow is False
            assert decision.violations == ["Access denied"]
            
    async def test_evaluate_policy_error(self, client):
        """Test policy evaluation error."""
        with patch.object(client._client, 'request') as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError(
                "Policy error",
                request=AsyncMock(),
                response=AsyncMock(status_code=400)
            )
            
            with pytest.raises(PolicyEvaluationError):
                await client.evaluate_policy(
                    "a2a/invalid_policy",
                    {"invalid": "input"}
                )
                
    async def test_upload_policy_success(self, client):
        """Test successful policy upload."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        
        with patch.object(client._client, 'request', return_value=mock_response):
            result = await client.upload_policy(
                "test_policy",
                "package test\ndefault allow = false"
            )
            
            assert result is True
            
    async def test_upload_policy_failure(self, client):
        """Test failed policy upload."""
        with patch.object(client._client, 'request') as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError(
                "Upload failed",
                request=AsyncMock(),
                response=AsyncMock(status_code=500)
            )
            
            result = await client.upload_policy(
                "test_policy", 
                "invalid policy content"
            )
            
            assert result is False
            
    async def test_batch_evaluate(self, client, mock_response):
        """Test batch policy evaluation."""
        with patch.object(client._client, 'request', return_value=mock_response):
            evaluations = [
                {"policy_path": "a2a/policy1", "input_data": {"test": 1}},
                {"policy_path": "a2a/policy2", "input_data": {"test": 2}}
            ]
            
            results = await client.batch_evaluate(evaluations)
            
            assert len(results) == 2
            assert all(isinstance(r, PolicyDecision) for r in results)
            
    async def test_connection_retry(self, client):
        """Test connection retry logic."""
        with patch.object(client._client, 'request') as mock_request:
            # First two attempts fail, third succeeds
            mock_request.side_effect = [
                httpx.ConnectError("Connection failed"),
                httpx.ConnectError("Connection failed"),
                AsyncMock(status_code=200, json=lambda: {"result": {"allow": True}})
            ]
            
            # Should eventually succeed after retries
            decision = await client.evaluate_policy("test", {})
            assert decision.allow is True
            
            # Should have made 3 attempts
            assert mock_request.call_count == 3
            
    async def test_connection_exhausted_retries(self, client):
        """Test connection failure after exhausting retries."""
        with patch.object(client._client, 'request') as mock_request:
            mock_request.side_effect = httpx.ConnectError("Connection failed")
            
            with pytest.raises(OPAConnectionError):
                await client.evaluate_policy("test", {})
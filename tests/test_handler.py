"""
Tests for OPARequestHandler.
"""

import pytest
from unittest.mock import AsyncMock, Mock

from a2a.server.context import ServerCallContext
from a2a.server.request_handlers.request_handler import RequestHandler
from a2a.types import Message, TextPart, MessageSendParams, Task, TaskIdParams

from a2a_opa.handler import OPARequestHandler
from a2a_opa.client import OPAClient, PolicyDecision
from a2a_opa.context import ContextExtractor, A2AContext, RequestInfo, AgentInfo
from a2a_opa.policies import PolicyManager
from a2a_opa.exceptions import PolicyViolationError


class TestOPARequestHandler:
    """Test cases for OPARequestHandler."""
    
    @pytest.fixture
    def mock_wrapped_handler(self):
        """Create mock wrapped handler."""
        handler = Mock(spec=RequestHandler)
        handler.on_message_send = AsyncMock()
        handler.on_get_task = AsyncMock()
        handler.on_cancel_task = AsyncMock()
        return handler
        
    @pytest.fixture
    def mock_opa_client(self):
        """Create mock OPA client."""
        client = Mock(spec=OPAClient)
        client.evaluate_policy = AsyncMock()
        return client
        
    @pytest.fixture
    def mock_context_extractor(self):
        """Create mock context extractor."""
        extractor = Mock(spec=ContextExtractor)
        extractor.extract_context = AsyncMock()
        return extractor
        
    @pytest.fixture
    def policy_manager(self):
        """Create policy manager."""
        return PolicyManager()
        
    @pytest.fixture
    def opa_handler(self, mock_wrapped_handler, mock_opa_client, mock_context_extractor, policy_manager):
        """Create OPA request handler."""
        return OPARequestHandler(
            wrapped_handler=mock_wrapped_handler,
            opa_client=mock_opa_client,
            context_extractor=mock_context_extractor,
            policy_manager=policy_manager
        )
        
    @pytest.fixture
    def sample_context(self):
        """Create sample A2A context."""
        return A2AContext(
            requester=AgentInfo(agent_id="test_agent"),
            target=AgentInfo(agent_id="target_agent"),
            request=RequestInfo(method="message/send"),
            operation="message/send"
        )
        
    async def test_message_send_authorized(
        self, 
        opa_handler, 
        mock_wrapped_handler,
        mock_opa_client,
        mock_context_extractor,
        sample_context
    ):
        """Test authorized message send."""
        # Setup mocks
        mock_context_extractor.extract_context.return_value = sample_context
        mock_opa_client.evaluate_policy.return_value = PolicyDecision(allow=True)
        
        expected_response = Message(messageId="test", role="agent", parts=[TextPart(text="Hello")])
        mock_wrapped_handler.on_message_send.return_value = expected_response
        
        # Create test parameters
        params = MessageSendParams(
            message=Message(messageId="test", role="user", parts=[TextPart(text="Hello")])
        )
        
        # Execute
        result = await opa_handler.on_message_send(params, None)
        
        # Verify
        assert result == expected_response
        mock_opa_client.evaluate_policy.assert_called_once()
        mock_wrapped_handler.on_message_send.assert_called_once()
        
    async def test_message_send_denied(
        self,
        opa_handler,
        mock_wrapped_handler,
        mock_opa_client, 
        mock_context_extractor,
        sample_context
    ):
        """Test denied message send."""
        # Setup mocks
        mock_context_extractor.extract_context.return_value = sample_context
        mock_opa_client.evaluate_policy.return_value = PolicyDecision(
            allow=False,
            violations=["Access denied"]
        )
        
        # Create test parameters
        params = MessageSendParams(
            message=Message(messageId="test", role="user", parts=[TextPart(text="Hello")])
        )
        
        # Execute and verify exception
        with pytest.raises(PolicyViolationError) as exc_info:
            await opa_handler.on_message_send(params, None)
            
        assert "Access denied" in str(exc_info.value)
        mock_wrapped_handler.on_message_send.assert_not_called()
        
    async def test_task_get_authorized(
        self,
        opa_handler,
        mock_wrapped_handler,
        mock_opa_client,
        mock_context_extractor,
        sample_context
    ):
        """Test authorized task get."""
        # Setup mocks
        mock_context_extractor.extract_context.return_value = sample_context
        mock_opa_client.evaluate_policy.return_value = PolicyDecision(allow=True)
        
        expected_task = Task(id="task123", status="running")
        mock_wrapped_handler.on_get_task.return_value = expected_task
        
        # Create test parameters
        params = TaskIdParams(task_id="task123")
        
        # Execute
        result = await opa_handler.on_get_task(params, None)
        
        # Verify
        assert result == expected_task
        mock_opa_client.evaluate_policy.assert_called_once()
        mock_wrapped_handler.on_get_task.assert_called_once()
        
    async def test_task_cancel_denied(
        self,
        opa_handler,
        mock_wrapped_handler,
        mock_opa_client,
        mock_context_extractor,
        sample_context
    ):
        """Test denied task cancel."""
        # Setup mocks
        mock_context_extractor.extract_context.return_value = sample_context
        mock_opa_client.evaluate_policy.return_value = PolicyDecision(
            allow=False,
            violations=["Cannot cancel this task"]
        )
        
        # Create test parameters
        params = TaskIdParams(task_id="task123")
        
        # Execute and verify exception
        with pytest.raises(PolicyViolationError) as exc_info:
            await opa_handler.on_cancel_task(params, None)
            
        assert "Cannot cancel this task" in str(exc_info.value)
        mock_wrapped_handler.on_cancel_task.assert_not_called()
        
    async def test_fail_open_mode(
        self,
        mock_wrapped_handler,
        mock_opa_client,
        mock_context_extractor,
        policy_manager
    ):
        """Test fail open mode when OPA is unavailable."""
        # Create handler with fail_open=True
        opa_handler = OPARequestHandler(
            wrapped_handler=mock_wrapped_handler,
            opa_client=mock_opa_client,
            context_extractor=mock_context_extractor,
            policy_manager=policy_manager,
            fail_open=True
        )
        
        # Setup mocks to simulate OPA failure
        sample_context = A2AContext(
            requester=AgentInfo(agent_id="test_agent"),
            request=RequestInfo(method="message/send"),
            operation="message/send"
        )
        mock_context_extractor.extract_context.return_value = sample_context
        mock_opa_client.evaluate_policy.side_effect = Exception("OPA unavailable")
        
        expected_response = Message(messageId="test", role="agent", parts=[TextPart(text="Hello")])
        mock_wrapped_handler.on_message_send.return_value = expected_response
        
        # Create test parameters
        params = MessageSendParams(
            message=Message(messageId="test", role="user", parts=[TextPart(text="Hello")])
        )
        
        # Execute - should succeed despite OPA failure
        result = await opa_handler.on_message_send(params, None)
        
        # Verify
        assert result == expected_response
        mock_wrapped_handler.on_message_send.assert_called_once()
        
    async def test_fail_closed_mode(
        self,
        opa_handler,
        mock_wrapped_handler,
        mock_opa_client,
        mock_context_extractor
    ):
        """Test fail closed mode when OPA is unavailable."""
        # Setup mocks to simulate OPA failure
        sample_context = A2AContext(
            requester=AgentInfo(agent_id="test_agent"),
            request=RequestInfo(method="message/send"),
            operation="message/send"
        )
        mock_context_extractor.extract_context.return_value = sample_context
        mock_opa_client.evaluate_policy.side_effect = Exception("OPA unavailable")
        
        # Create test parameters
        params = MessageSendParams(
            message=Message(messageId="test", role="user", parts=[TextPart(text="Hello")])
        )
        
        # Execute - should fail when OPA is unavailable
        with pytest.raises(PolicyViolationError):
            await opa_handler.on_message_send(params, None)
            
        mock_wrapped_handler.on_message_send.assert_not_called()
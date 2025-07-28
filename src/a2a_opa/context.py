"""
Context extraction for A2A requests.
"""

import logging
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from a2a.server.context import ServerCallContext
from a2a.types import (
    Message,
    MessageSendParams,
    Task,
    TaskIdParams,
    TaskQueryParams,
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentInfo(BaseModel):
    """Information about an agent."""

    agent_id: str | None = None
    name: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    role: str | None = None
    clearance_level: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageInfo(BaseModel):
    """Information about a message."""

    message_id: str | None = None
    content: str | None = None
    message_type: str = "text"
    parts: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    contains_sensitive_data: bool = False
    data_classification: str = "public"


class TaskInfo(BaseModel):
    """Information about a task."""

    task_id: str | None = None
    status: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RequestInfo(BaseModel):
    """Information about the request."""

    method: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    remote_addr: str | None = None
    user_agent: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class A2AContext(BaseModel):
    """
    Complete context for A2A policy evaluation.

    This contains all the information extracted from an A2A request
    that can be used in policy evaluation.
    """

    requester: AgentInfo = Field(default_factory=AgentInfo)
    target: AgentInfo = Field(default_factory=AgentInfo)
    message: MessageInfo | None = None
    task: TaskInfo | None = None
    request: RequestInfo
    operation: str
    resource: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, Any] = Field(default_factory=dict)

    def to_opa_input(self) -> dict[str, Any]:
        """
        Convert context to OPA input format.

        Returns:
            Dictionary suitable for OPA policy evaluation
        """
        return {
            "requester": self.requester.model_dump(),
            "target": self.target.model_dump(),
            "message": self.message.model_dump() if self.message else None,
            "task": self.task.model_dump() if self.task else None,
            "request": self.request.model_dump(),
            "operation": self.operation,
            "resource": self.resource,
            "data": self.data,
            "environment": self.environment,
        }


@runtime_checkable
class ContextExtractorProtocol(Protocol):
    """Protocol for context extractors."""

    async def extract_agent_info(
        self,
        context: ServerCallContext | None
    ) -> AgentInfo:
        """Extract agent information from server context."""
        ...

    async def classify_message(self, message: Message) -> MessageInfo:
        """Extract and classify message information."""
        ...

    async def extract_request_info(
        self,
        method: str,
        context: ServerCallContext | None
    ) -> RequestInfo:
        """Extract request information."""
        ...


class DefaultContextExtractor:
    """
    Default context extractor for A2A requests.

    This extractor provides basic context extraction. Organizations can
    extend this class to add custom context extraction logic.
    """

    def __init__(
        self,
        agent_registry: dict[str, AgentInfo] | None = None,
        sensitive_patterns: list[str] | None = None
    ):
        """
        Initialize context extractor.

        Args:
            agent_registry: Registry of known agents and their info
            sensitive_patterns: List of patterns to detect sensitive data
        """
        self.agent_registry = agent_registry or {}
        self.sensitive_patterns = sensitive_patterns or [
            "SECRET", "CONFIDENTIAL", "PASSWORD", "TOKEN", "API_KEY",
            "PRIVATE_KEY", "SSN", "CREDIT_CARD"
        ]

    async def extract_agent_info(
        self,
        context: ServerCallContext | None
    ) -> AgentInfo:
        """
        Extract agent information from server context.

        Args:
            context: A2A server call context

        Returns:
            AgentInfo with extracted information
        """
        if not context:
            return AgentInfo()

        # Try to extract agent ID from various sources
        agent_id = None

        # Check if agent ID is in headers
        if hasattr(context, 'headers'):
            agent_id = context.headers.get('X-Agent-ID')

        # Check if it's in metadata
        if not agent_id and hasattr(context, 'metadata'):
            agent_id = context.metadata.get('agent_id')

        # Look up agent in registry
        if agent_id and agent_id in self.agent_registry:
            return self.agent_registry[agent_id]

        # Return basic info if found
        if agent_id:
            return AgentInfo(agent_id=agent_id)

        return AgentInfo()

    async def classify_message(self, message: Message) -> MessageInfo:
        """
        Extract and classify message information.

        Args:
            message: A2A message object

        Returns:
            MessageInfo with classification
        """
        info = MessageInfo()

        # Extract basic message info
        if hasattr(message, 'id'):
            info.message_id = message.id

        # Extract content from parts
        content_parts = []
        parts_info = []

        for part in message.parts:
            part_type = type(part).__name__.lower().replace('part', '')
            part_dict = {"type": part_type}

            if part_type == "text" and hasattr(part, 'text'):
                content_parts.append(part.text)
                part_dict["content"] = part.text

            elif part_type == "file" and hasattr(part, 'name'):
                part_dict["filename"] = part.name
                if hasattr(part, 'mime_type'):
                    part_dict["mime_type"] = part.mime_type

            elif part_type == "data" and hasattr(part, 'data'):
                part_dict["data"] = "<binary_data>"
                if hasattr(part, 'mime_type'):
                    part_dict["mime_type"] = part.mime_type

            parts_info.append(part_dict)

        # Combine text content
        info.content = " ".join(content_parts) if content_parts else None
        info.parts = parts_info

        # Classify data sensitivity
        if info.content:
            info.contains_sensitive_data = self._contains_sensitive_data(info.content)
            info.data_classification = self._classify_data(info.content)

        return info

    def _contains_sensitive_data(self, content: str) -> bool:
        """Check if content contains sensitive data patterns."""
        content_upper = content.upper()
        return any(pattern in content_upper for pattern in self.sensitive_patterns)

    def _classify_data(self, content: str) -> str:
        """Classify data based on content."""
        if self._contains_sensitive_data(content):
            return "confidential"
        elif any(word in content.upper() for word in ["INTERNAL", "PRIVATE"]):
            return "internal"
        else:
            return "public"

    async def extract_task_info(self, task: Task | None) -> TaskInfo | None:
        """
        Extract task information.

        Args:
            task: A2A task object

        Returns:
            TaskInfo if task provided, None otherwise
        """
        if not task:
            return None

        info = TaskInfo()

        if hasattr(task, 'id'):
            info.task_id = task.id
        if hasattr(task, 'status'):
            info.status = str(task.status) if task.status else None
        if hasattr(task, 'created_at'):
            info.created_at = task.created_at
        if hasattr(task, 'updated_at'):
            info.updated_at = task.updated_at

        return info

    async def extract_request_info(
        self,
        method: str,
        context: ServerCallContext | None
    ) -> RequestInfo:
        """
        Extract request information.

        Args:
            method: A2A method name
            context: Server call context

        Returns:
            RequestInfo with request details
        """
        info = RequestInfo(method=method)

        if context:
            # Extract request details from context
            if hasattr(context, 'remote_addr'):
                info.remote_addr = context.remote_addr
            if hasattr(context, 'headers'):
                info.headers = dict(context.headers)
                info.user_agent = context.headers.get('User-Agent')

        return info


class ContextExtractor:
    """
    Main context extractor that orchestrates extraction of different context components.
    """

    def __init__(
        self,
        extractor: ContextExtractorProtocol | None = None,
        environment_data: dict[str, Any] | None = None
    ):
        """
        Initialize context extractor.

        Args:
            extractor: Custom context extractor implementation
            environment_data: Static environment data for policies
        """
        self.extractor = extractor or DefaultContextExtractor()
        self.environment_data = environment_data or {}

    async def extract_context(
        self,
        method: str,
        params: Any,
        context: ServerCallContext | None = None,
        additional_data: dict[str, Any] | None = None
    ) -> A2AContext:
        """
        Extract complete context for policy evaluation.

        Args:
            method: A2A method being called
            params: Method parameters
            context: Server call context
            additional_data: Additional context data

        Returns:
            Complete A2AContext for policy evaluation
        """
        # Extract requester info
        requester = await self.extractor.extract_agent_info(context)

        # Extract target info (for now, same as requester)
        target = AgentInfo()  # TODO: Extract target agent info

        # Extract request info
        request_info = await self.extractor.extract_request_info(method, context)

        # Initialize context
        a2a_context = A2AContext(
            requester=requester,
            target=target,
            request=request_info,
            operation=method,
            environment=self.environment_data
        )

        # Add additional data
        if additional_data:
            a2a_context.data.update(additional_data)

        # Extract method-specific context
        await self._extract_method_context(method, params, a2a_context)

        return a2a_context

    async def _extract_method_context(
        self,
        method: str,
        params: Any,
        context: A2AContext
    ) -> None:
        """Extract method-specific context information."""

        if method in ["message/send", "message/stream"]:
            if isinstance(params, MessageSendParams):
                context.message = await self.extractor.classify_message(params.message)
                context.resource = "message"

                # Extract task info if continuing a task
                if hasattr(params, 'task_id') and params.task_id:
                    context.task = TaskInfo(task_id=params.task_id)

        elif method == "tasks/get":
            if isinstance(params, TaskQueryParams):
                context.task = TaskInfo(task_id=params.task_id)
                context.resource = "task"

        elif method == "tasks/cancel":
            if isinstance(params, TaskIdParams):
                context.task = TaskInfo(task_id=params.task_id)
                context.resource = "task"
                context.operation = "task_cancel"

        elif method.startswith("tasks/pushNotificationConfig"):
            context.resource = "push_notification"
            if hasattr(params, 'task_id'):
                context.task = TaskInfo(task_id=params.task_id)

        logger.debug(f"Extracted context for {method}: resource={context.resource}")

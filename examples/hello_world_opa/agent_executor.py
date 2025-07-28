"""
Enhanced HelloWorld agent executor with OPA integration support.
"""

import asyncio
from collections.abc import AsyncGenerator

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.events.event_queue import Event
from a2a.types import Message, TextPart, Task, TaskStatus, TaskStatusUpdateEvent


class EnhancedHelloWorldAgentExecutor(AgentExecutor):
    """
    Enhanced HelloWorld agent executor that demonstrates OPA integration.

    This executor extends the basic HelloWorld functionality with features
    that showcase different policy scenarios.
    """

    async def execute_task(self, message: Message, task: Task) -> AsyncGenerator[Event]:
        """
        Execute task with enhanced capabilities.

        Args:
            message: Input message
            task: Task to execute

        Yields:
            Events during task execution
        """
        # Extract message content
        content = self._extract_text_content(message)

        # Update task status
        task.status = TaskStatus.RUNNING
        yield TaskStatusUpdateEvent(task=task)

        # Simulate processing time
        await asyncio.sleep(0.5)

        # Generate response based on content
        response_content = await self._generate_response(content, task)

        # Create response message
        response_message = Message(
            parts=[TextPart(content=response_content)]
        )

        # Yield response message
        yield response_message

        # Complete task
        task.status = TaskStatus.COMPLETED
        yield TaskStatusUpdateEvent(task=task)

    def _extract_text_content(self, message: Message) -> str:
        """Extract text content from message parts."""
        text_parts = []
        for part in message.parts:
            if hasattr(part, 'content'):
                text_parts.append(part.content)
        return " ".join(text_parts)

    async def _generate_response(self, content: str, task: Task) -> str:
        """
        Generate response based on input content.

        This method demonstrates different response types that can trigger
        various policy scenarios.
        """
        content_lower = content.lower()

        # Basic hello world responses
        if "hello" in content_lower or "hi" in content_lower:
            return "Hello! I'm your friendly A2A agent with OPA security!"

        # Super greeting (requires special permission)
        if "super" in content_lower:
            return "🎉 SUPER HELLO WORLD! 🎉 You have special access!"

        # Administrative information (requires admin role)
        if "admin" in content_lower or "status" in content_lower:
            return (
                f"Admin Info: Task {task.id} running with OPA policies active. "
                "System status: operational."
            )

        # Sensitive data response (will be filtered by policies)
        if "secret" in content_lower or "confidential" in content_lower:
            return (
                "CONFIDENTIAL: This is sensitive information that should be filtered "
                "by OPA policies."
            )

        # Large response (tests message size policies)
        if "large" in content_lower or "big" in content_lower:
            return "Large Response: " + "This is a very long message. " * 100

        # Data classification examples
        if "public" in content_lower:
            return "PUBLIC: This is public information available to all agents."
        if "internal" in content_lower:
            return "INTERNAL: This is internal information for authorized agents only."

        # Tool access simulation
        if "calculator" in content_lower:
            return "Calculator Tool: 2 + 2 = 4 (This demonstrates tool access control)"
        if "database" in content_lower:
            return (
                "Database Query: SELECT * FROM agents WHERE authorized=true "
                "(Database access required)"
            )

        # Error simulation
        if "error" in content_lower:
            return "ERROR: This simulates an error condition for testing policy handling."

        # Default response
        return f"Hello! You said: '{content}'. I'm an OPA-enhanced A2A agent ready to help!"

    async def cancel_task(self, task: Task) -> Task:
        """
        Cancel a running task.

        Args:
            task: Task to cancel

        Returns:
            Updated task with cancelled status
        """
        task.status = TaskStatus.CANCELLED
        return task

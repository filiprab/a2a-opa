"""
OPA-enhanced request handler for A2A protocol.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from a2a.server.context import ServerCallContext
from a2a.server.events.event_queue import Event
from a2a.server.request_handlers.request_handler import RequestHandler
from a2a.types import (
    DeleteTaskPushNotificationConfigParams,
    GetTaskPushNotificationConfigParams,
    ListTaskPushNotificationConfigParams,
    Message,
    MessageSendParams,
    Task,
    TaskIdParams,
    TaskPushNotificationConfig,
    TaskQueryParams,
)

from .client import OPAClient
from .context import A2AContext, ContextExtractor
from .exceptions import PolicyEvaluationError, PolicyViolationError
from .policies import PolicyManager

logger = logging.getLogger(__name__)


class OPARequestHandler(RequestHandler):
    """
    OPA-enhanced A2A request handler.

    This handler wraps an existing A2A RequestHandler and adds OPA policy
    enforcement at all interaction points. It follows the decorator pattern
    to provide non-invasive integration.
    """

    def __init__(
        self,
        wrapped_handler: RequestHandler,
        opa_client: OPAClient,
        context_extractor: ContextExtractor | None = None,
        policy_manager: PolicyManager | None = None,
        default_deny: bool = True,
        audit_decisions: bool = True,
        fail_open: bool = False
    ):
        """
        Initialize OPA request handler.

        Args:
            wrapped_handler: Original A2A request handler to wrap
            opa_client: OPA client for policy evaluation
            context_extractor: Context extractor for building policy input
            policy_manager: Policy manager for handling policy mappings
            default_deny: Whether to deny by default when policy is unclear
            audit_decisions: Whether to log all policy decisions
            fail_open: Whether to allow requests when OPA is unavailable
        """
        self.wrapped_handler = wrapped_handler
        self.opa_client = opa_client
        self.context_extractor = context_extractor or ContextExtractor()
        self.policy_manager = policy_manager or PolicyManager()
        self.default_deny = default_deny
        self.audit_decisions = audit_decisions
        self.fail_open = fail_open

    async def on_get_task(
        self,
        params: TaskQueryParams,
        context: ServerCallContext | None = None,
    ) -> Task | None:
        """Handles the 'tasks/get' method with OPA authorization."""

        # Extract context and evaluate policy
        await self._authorize_request("tasks/get", params, context)

        # Execute original handler
        result = await self.wrapped_handler.on_get_task(params, context)

        # Filter result based on policies
        return await self._filter_task_response(result, context)

    async def on_cancel_task(
        self,
        params: TaskIdParams,
        context: ServerCallContext | None = None,
    ) -> Task | None:
        """Handles the 'tasks/cancel' method with OPA authorization."""

        # Check authorization
        await self._authorize_request("tasks/cancel", params, context)

        # Execute original handler
        return await self.wrapped_handler.on_cancel_task(params, context)

    async def on_message_send(
        self,
        params: MessageSendParams,
        context: ServerCallContext | None = None,
    ) -> Task | Message:
        """Handles the 'message/send' method with OPA authorization."""

        # Authorize message sending
        await self._authorize_request("message/send", params, context)

        # Additional message content filtering
        filtered_params = await self._filter_message_params(params, context)

        # Execute original handler
        result = await self.wrapped_handler.on_message_send(filtered_params, context)

        # Filter response
        return await self._filter_response("message/send", result, context)

    async def on_message_send_stream(
        self,
        params: MessageSendParams,
        context: ServerCallContext | None = None,
    ) -> AsyncGenerator[Event]:
        """Handles the 'message/stream' method with OPA authorization."""

        # Authorize streaming message
        await self._authorize_request("message/stream", params, context)

        # Filter message parameters
        filtered_params = await self._filter_message_params(params, context)

        # Stream events with filtering
        async for event in self.wrapped_handler.on_message_send_stream(filtered_params, context):
            # Filter each event
            filtered_event = await self._filter_stream_event(event, context)
            if filtered_event:
                yield filtered_event

    async def on_set_task_push_notification_config(
        self,
        params: TaskPushNotificationConfig,
        context: ServerCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        """Handles push notification config setting with OPA authorization."""

        await self._authorize_request("tasks/pushNotificationConfig/set", params, context)
        return await self.wrapped_handler.on_set_task_push_notification_config(params, context)

    async def on_get_task_push_notification_config(
        self,
        params: TaskIdParams | GetTaskPushNotificationConfigParams,
        context: ServerCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        """Handles push notification config retrieval with OPA authorization."""

        await self._authorize_request("tasks/pushNotificationConfig/get", params, context)
        return await self.wrapped_handler.on_get_task_push_notification_config(params, context)

    async def on_resubscribe_to_task(
        self,
        params: TaskIdParams,
        context: ServerCallContext | None = None,
    ) -> AsyncGenerator[Event]:
        """Handles task resubscription with OPA authorization."""

        await self._authorize_request("tasks/resubscribe", params, context)

        async for event in self.wrapped_handler.on_resubscribe_to_task(params, context):
            filtered_event = await self._filter_stream_event(event, context)
            if filtered_event:
                yield filtered_event

    async def on_list_task_push_notification_config(
        self,
        params: ListTaskPushNotificationConfigParams,
        context: ServerCallContext | None = None,
    ) -> list[TaskPushNotificationConfig]:
        """Handles push notification config listing with OPA authorization."""

        await self._authorize_request("tasks/pushNotificationConfig/list", params, context)
        return await self.wrapped_handler.on_list_task_push_notification_config(params, context)

    async def on_delete_task_push_notification_config(
        self,
        params: DeleteTaskPushNotificationConfigParams,
        context: ServerCallContext | None = None,
    ) -> None:
        """Handles push notification config deletion with OPA authorization."""

        await self._authorize_request("tasks/pushNotificationConfig/delete", params, context)
        return await self.wrapped_handler.on_delete_task_push_notification_config(params, context)

    async def _authorize_request(
        self,
        method: str,
        params: Any,
        context: ServerCallContext | None,
        additional_data: dict[str, Any] | None = None
    ) -> A2AContext:
        """
        Authorize a request using OPA policies.

        Args:
            method: A2A method name
            params: Method parameters
            context: Server call context
            additional_data: Additional context data

        Returns:
            Extracted A2A context

        Raises:
            PolicyViolationError: If authorization fails
        """
        try:
            # Extract context
            a2a_context = await self.context_extractor.extract_context(
                method, params, context, additional_data
            )

            # Get policy path for this method
            policy_path = self.policy_manager.get_policy_path(method)

            # Evaluate policy
            decision = await self.opa_client.evaluate_policy(
                policy_path,
                a2a_context.to_opa_input()
            )

            # Log decision if auditing enabled
            if self.audit_decisions:
                logger.info(
                    f"Policy decision: {method} -> {decision.allow} "
                    f"(policy: {policy_path}, agent: {a2a_context.requester.agent_id})"
                )

            # Check if request is allowed
            if not decision.allow:
                violations = decision.violations or ["Request denied by policy"]
                raise PolicyViolationError(
                    f"Request {method} denied: {', '.join(violations)}",
                    policy_path=policy_path,
                    decision=decision.result,
                    context=a2a_context.model_dump()
                )

            return a2a_context

        except PolicyEvaluationError as e:
            logger.error(f"Policy evaluation failed for {method}: {e}")

            if self.fail_open:
                logger.warning(f"Failing open for {method} due to policy evaluation error")
                return await self.context_extractor.extract_context(method, params, context)
            else:
                raise PolicyViolationError(
                    f"Policy evaluation failed for {method}",
                    policy_path=self.policy_manager.get_policy_path(method),
                    decision={},
                    context={}
                ) from e

        except Exception as e:
            logger.error(f"Authorization error for {method}: {e}")

            if self.fail_open:
                logger.warning(f"Failing open for {method} due to authorization error")
                return await self.context_extractor.extract_context(method, params, context)
            else:
                raise

    async def _filter_message_params(
        self,
        params: MessageSendParams,
        context: ServerCallContext | None
    ) -> MessageSendParams:
        """
        Filter message parameters based on content policies.

        Args:
            params: Original message parameters
            context: Server call context

        Returns:
            Filtered message parameters
        """
        # For now, return params as-is
        # TODO: Implement content filtering based on policies
        return params

    async def _filter_response(
        self,
        method: str,
        response: Task | Message,
        context: ServerCallContext | None
    ) -> Task | Message:
        """
        Filter response data based on policies.

        Args:
            method: A2A method name
            response: Original response
            context: Server call context

        Returns:
            Filtered response
        """
        # For now, return response as-is
        # TODO: Implement response filtering based on policies
        return response

    async def _filter_task_response(
        self,
        task: Task | None,
        context: ServerCallContext | None
    ) -> Task | None:
        """
        Filter task response based on policies.

        Args:
            task: Original task
            context: Server call context

        Returns:
            Filtered task or None if access denied
        """
        if not task:
            return None

        # TODO: Implement task-specific filtering
        return task

    async def _filter_stream_event(
        self,
        event: Event,
        context: ServerCallContext | None
    ) -> Event | None:
        """
        Filter streaming event based on policies.

        Args:
            event: Original event
            context: Server call context

        Returns:
            Filtered event or None if should be filtered out
        """
        # For now, return event as-is
        # TODO: Implement event filtering based on policies
        return event

"""
OPA client-side interceptor for A2A Agent Card discovery enforcement.
"""

import logging
from typing import Any

from a2a.client.middleware import ClientCallContext, ClientCallInterceptor
from a2a.types import AgentCard
from opa_client.opa_async import AsyncOpaClient

from ..exceptions import PolicyEvaluationError, PolicyViolationError
from .context import AgentCardDiscoveryContext
from .opa_client import evaluate_agent_card_policy

logger = logging.getLogger(__name__)


class OPAClientInterceptor(ClientCallInterceptor):
    """
    Client-side OPA interceptor for Agent Card discovery enforcement.

    This interceptor evaluates OPA policies before A2A requests are sent,
    ensuring that the client is authorized to discover and interact with
    the target agent based on Agent Card level policies.
    """

    def __init__(
        self,
        opa_client: AsyncOpaClient,
        client_identity: str,
        package_path: str,
        rule_name: str,
        fail_closed: bool = True,
        log_decisions: bool = True,
    ):
        """
        Initialize the OPA client interceptor.

        Args:
            opa_client: AsyncOpaClient instance from opa-python-client
            client_identity: Identity of this client for policy evaluation
            package_path: OPA package path for Agent Card policies
            rule_name: OPA rule name for Agent Card discovery
            fail_closed: If True, deny access when policy evaluation fails
            log_decisions: If True, log policy decisions for audit
        """
        self.opa_client = opa_client
        self.client_identity = client_identity
        self.package_path = package_path
        self.rule_name = rule_name
        self.fail_closed = fail_closed
        self.log_decisions = log_decisions

    async def intercept(
        self,
        method_name: str,
        request_payload: dict[str, Any],
        http_kwargs: dict[str, Any],
        agent_card: AgentCard | None,
        context: ClientCallContext | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Intercept A2A client calls to enforce Agent Card discovery policies.

        Args:
            method_name: The A2A method name (e.g., 'message/send')
            request_payload: The JSON RPC request payload
            http_kwargs: HTTP keyword arguments
            agent_card: The target agent's AgentCard (if available)
            context: Client call context

        Returns:
            Tuple of (request_payload, http_kwargs) - potentially modified

        Raises:
            PolicyViolationError: If OPA policy denies access
            PolicyEvaluationError: If policy evaluation fails
        """
        # Extract target agent URL from AgentCard or context
        target_agent_url = self._extract_target_url(agent_card, context, http_kwargs)

        if not target_agent_url:
            logger.warning("No target agent URL found - skipping OPA evaluation")
            return request_payload, http_kwargs

        # Build policy evaluation context
        discovery_context = AgentCardDiscoveryContext.from_client_call(
            client_identity=self.client_identity,
            target_agent_url=target_agent_url,
            method_name=method_name,
            client_metadata=self._extract_client_metadata(context),
            request_headers=http_kwargs.get("headers", {}),
            request_metadata=self._extract_request_metadata(request_payload),
        )

        # Evaluate OPA policy
        try:
            is_allowed = await evaluate_agent_card_policy(
                opa_client=self.opa_client,
                input_data=discovery_context.to_opa_input(),
                package_path=self.package_path,
                rule_name=self.rule_name,
            )

            if self.log_decisions:
                logger.info(
                    "OPA policy decision: client=%s, target=%s, method=%s, allowed=%s",
                    self.client_identity,
                    target_agent_url,
                    method_name,
                    is_allowed,
                )

            if not is_allowed:
                raise PolicyViolationError(
                    f"Agent Card discovery denied by policy for {target_agent_url}",
                    policy_path=f"{self.package_path}.{self.rule_name}",
                    decision={"allowed": False},
                    context=discovery_context.model_dump(),
                )

        except PolicyViolationError:
            # Re-raise policy violations
            raise

        except PolicyEvaluationError as e:
            if self.fail_closed:
                logger.error("Policy evaluation failed, denying access: %s", e)
                raise
            else:
                logger.warning("Policy evaluation failed, allowing access: %s", e)

        # Add policy context to request if available
        if context:
            context.state["opa_policy_evaluated"] = True
            context.state["opa_discovery_context"] = discovery_context.model_dump()

        return request_payload, http_kwargs

    def _extract_target_url(
        self,
        agent_card: AgentCard | None,
        context: ClientCallContext | None,
        http_kwargs: dict[str, Any],
    ) -> str | None:
        """Extract target agent URL from available sources."""
        # Try AgentCard first
        if agent_card and hasattr(agent_card, "url"):
            return str(agent_card.url)

        # Try context state
        if context and "target_agent_url" in context.state:
            url = context.state["target_agent_url"]
            return str(url) if url is not None else None

        # Try to infer from http_kwargs (less reliable)
        # This might not work in all cases depending on A2A client implementation
        return None

    def _extract_client_metadata(
        self,
        context: ClientCallContext | None,
    ) -> dict[str, Any]:
        """Extract client metadata from context."""
        if not context:
            return {}

        metadata = {}

        # Extract common client metadata
        for key in ["client_version", "client_type", "environment"]:
            if key in context.state:
                metadata[key] = context.state[key]

        return metadata

    def _extract_request_metadata(
        self,
        request_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract relevant metadata from request payload."""
        metadata = {}

        # Extract request ID if present
        if "id" in request_payload:
            metadata["request_id"] = request_payload["id"]

        # Extract method-specific metadata
        if "params" in request_payload:
            params = request_payload["params"]

            # For message requests
            if isinstance(params, dict):
                for key in ["priority", "timeout", "streaming"]:
                    if key in params:
                        metadata[key] = params[key]

        return metadata

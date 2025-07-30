"""
A2A-specific utilities for opa-python-client.
"""

import logging
from typing import Any

from opa_client.opa_async import AsyncOpaClient

from ..exceptions import PolicyEvaluationError

logger = logging.getLogger(__name__)


async def evaluate_agent_card_policy(
    opa_client: AsyncOpaClient,
    input_data: dict[str, Any],
    package_path: str = "a2a.client",
    rule_name: str = "agent_card_discovery_allow",
) -> bool:
    """
    Evaluate Agent Card discovery policy using OPA client.

    Args:
        opa_client: AsyncOpaClient instance from opa-python-client
        input_data: Policy evaluation input data
        package_path: OPA package path
        rule_name: Rule name to evaluate

    Returns:
        True if policy allows access, False otherwise

    Raises:
        PolicyEvaluationError: If policy evaluation fails
    """
    try:
        logger.debug(
            "[-] Evaluating Agent Card policy: package=%s, rule=%s, input=%s",
            package_path,
            rule_name,
            input_data,
        )

        result = await opa_client.query_rule(
            input_data=input_data,
            package_path=package_path,
            rule_name=rule_name,
        )

        logger.debug("[+] Policy evaluation result: %s", result)

        # Extract boolean result from OPA response
        if isinstance(result, dict) and "result" in result:
            return bool(result["result"])

        # Fallback: treat any truthy value as allowed
        return bool(result)

    except Exception as e:
        raise PolicyEvaluationError(
            f"Failed to evaluate policy {package_path}.{rule_name}: {e}",
            policy_path=f"{package_path}.{rule_name}",
            input_data=input_data,
            opa_error=str(e),
        ) from e

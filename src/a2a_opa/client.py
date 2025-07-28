"""
OPA client for policy evaluation.
"""

import asyncio
import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

from .exceptions import OPAConnectionError, PolicyEvaluationError

logger = logging.getLogger(__name__)


class PolicyDecision(BaseModel):
    """Represents a policy decision from OPA."""

    allow: bool = Field(description="Whether the request is allowed")
    decision_id: str | None = Field(default=None, description="Unique identifier for this decision")
    result: dict[str, Any] = Field(default_factory=dict, description="Full OPA result")
    violations: list[str] = Field(default_factory=list, description="Policy violations if any")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class OPAClient:
    """
    Client for communicating with OPA (Open Policy Agent) server.

    Provides methods for policy evaluation, bundle management, and health checks.
    """

    def __init__(
        self,
        url: str,
        timeout: float = 10.0,
        max_retries: int = 3,
        auth_token: str | None = None,
        verify_ssl: bool = True
    ):
        """
        Initialize OPA client.

        Args:
            url: OPA server URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            auth_token: Optional authentication token
            verify_ssl: Whether to verify SSL certificates
        """
        self.url = url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl

        # Setup HTTP client
        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            verify=verify_ssl
        )

    async def __aenter__(self) -> 'OPAClient':
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def health_check(self) -> bool:
        """
        Check if OPA server is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self._client.get(f"{self.url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"OPA health check failed: {e}")
            return False

    async def evaluate_policy(
        self,
        policy_path: str,
        input_data: dict[str, Any],
        include_metrics: bool = False,
        include_trace: bool = False
    ) -> PolicyDecision:
        """
        Evaluate a policy with given input data.

        Args:
            policy_path: Policy path (e.g., "a2a/message_authorization")
            input_data: Input data for policy evaluation
            include_metrics: Whether to include performance metrics
            include_trace: Whether to include execution trace

        Returns:
            PolicyDecision with evaluation result

        Raises:
            PolicyEvaluationError: If evaluation fails
            OPAConnectionError: If connection to OPA fails
        """
        url = f"{self.url}/v1/data/{policy_path.replace('.', '/')}"

        # Build request payload
        payload = {"input": input_data}

        # Add optional parameters
        params = {}
        if include_metrics:
            params["metrics"] = "true"
        if include_trace:
            params["explain"] = "full"

        try:
            response = await self._make_request("POST", url, json=payload, params=params)
            result = response.json()

            # Extract decision
            decision_result = result.get("result", {})
            allow = decision_result.get("allow", False)

            # Extract violations if present
            violations = decision_result.get("violations", [])
            if isinstance(violations, str):
                violations = [violations]
            elif not isinstance(violations, list):
                violations = []

            # Build decision object
            decision = PolicyDecision(
                allow=allow,
                result=result,
                violations=violations,
                metadata={
                    "policy_path": policy_path,
                    "metrics": result.get("metrics", {}),
                    "trace": result.get("explanation", [])
                }
            )

            logger.debug(f"Policy evaluation result: {policy_path} -> {allow}")
            return decision

        except httpx.HTTPStatusError as e:
            error_msg = f"Policy evaluation failed: {e.response.status_code}"
            try:
                error_details = e.response.json()
                error_msg += f" - {error_details.get('message', '')}"
            except Exception:
                pass

            raise PolicyEvaluationError(
                error_msg,
                policy_path=policy_path,
                input_data=input_data,
                opa_error=str(e)
            ) from e

        except Exception as e:
            raise PolicyEvaluationError(
                f"Policy evaluation failed: {str(e)}",
                policy_path=policy_path,
                input_data=input_data,
                opa_error=str(e)
            ) from e

    async def batch_evaluate(
        self,
        evaluations: list[dict[str, Any]]
    ) -> list[PolicyDecision]:
        """
        Evaluate multiple policies in a single request.

        Args:
            evaluations: List of dicts with 'policy_path' and 'input_data' keys

        Returns:
            List of PolicyDecision objects
        """
        tasks = []
        for evaluation in evaluations:
            task = self.evaluate_policy(
                evaluation["policy_path"],
                evaluation["input_data"]
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Filter out exceptions and return only successful PolicyDecision objects
        policy_decisions = []
        for result in results:
            if isinstance(result, PolicyDecision):
                policy_decisions.append(result)
            elif isinstance(result, Exception):
                # Log the exception and create a deny decision
                logger.error(f"Batch evaluation failed: {result}")
                policy_decisions.append(PolicyDecision(allow=False, violations=[str(result)]))
        return policy_decisions

    async def upload_policy(
        self,
        policy_path: str,
        policy_content: str
    ) -> bool:
        """
        Upload a Rego policy to OPA.

        Args:
            policy_path: Policy path (e.g., "a2a/message_authorization")
            policy_content: Rego policy content

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.url}/v1/policies/{policy_path}"

        try:
            response = await self._make_request(
                "PUT",
                url,
                content=policy_content,
                headers={"Content-Type": "text/plain"}
            )
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to upload policy {policy_path}: {e}")
            return False

    async def delete_policy(self, policy_path: str) -> bool:
        """
        Delete a policy from OPA.

        Args:
            policy_path: Policy path to delete

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.url}/v1/policies/{policy_path}"

        try:
            response = await self._make_request("DELETE", url)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to delete policy {policy_path}: {e}")
            return False

    async def get_policies(self) -> list[str]:
        """
        Get list of all policies loaded in OPA.

        Returns:
            List of policy paths
        """
        url = f"{self.url}/v1/policies"

        try:
            response = await self._make_request("GET", url)
            result = response.json()
            return list(result.get("result", {}).keys())

        except Exception as e:
            logger.error(f"Failed to get policies: {e}")
            return []

    async def upload_data(
        self,
        data_path: str,
        data: dict[str, Any]
    ) -> bool:
        """
        Upload data to OPA for use in policies.

        Args:
            data_path: Data path (e.g., "trusted_agents")
            data: Data to upload

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.url}/v1/data/{data_path}"

        try:
            response = await self._make_request("PUT", url, json=data)
            return response.status_code == 204

        except Exception as e:
            logger.error(f"Failed to upload data to {data_path}: {e}")
            return False

    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs: Any
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request arguments

        Returns:
            HTTP response

        Raises:
            OPAConnectionError: If all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(method, url, **kwargs)
                response.raise_for_status()
                return response

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"OPA request failed (attempt {attempt + 1}), retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                    continue

            except httpx.HTTPStatusError as e:
                # Don't retry on HTTP errors (4xx, 5xx)
                raise e

        # All retries exhausted
        raise OPAConnectionError(
            f"Failed to connect to OPA after {self.max_retries + 1} attempts: {last_exception}",
            url=url
        )

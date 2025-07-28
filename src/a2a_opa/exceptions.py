"""
Exception classes for A2A-OPA integration.
"""

from typing import Any


class OPAError(Exception):
    """Base exception for OPA-related errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class PolicyEvaluationError(OPAError):
    """Raised when policy evaluation fails."""

    def __init__(
        self,
        message: str,
        policy_path: str | None = None,
        input_data: dict[str, Any] | None = None,
        opa_error: str | None = None
    ):
        super().__init__(message)
        self.policy_path = policy_path
        self.input_data = input_data
        self.opa_error = opa_error


class PolicyViolationError(OPAError):
    """Raised when a policy denies access."""

    def __init__(
        self,
        message: str,
        policy_path: str,
        decision: dict[str, Any],
        context: dict[str, Any] | None = None
    ):
        super().__init__(message)
        self.policy_path = policy_path
        self.decision = decision
        self.context = context or {}


class PolicyLoadError(OPAError):
    """Raised when policy loading fails."""

    def __init__(self, message: str, policy_path: str | None = None):
        super().__init__(message)
        self.policy_path = policy_path


class OPAConnectionError(OPAError):
    """Raised when connection to OPA server fails."""

    def __init__(self, message: str, url: str | None = None):
        super().__init__(message)
        self.url = url

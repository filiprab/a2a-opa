"""
A2A-OPA Integration Library

This library provides OPA (Open Policy Agent) integration for A2A (Agent-to-Agent) protocol,
enabling policy-based authorization and access control for agent communications.
"""

from .client import OPAClient, PolicyDecision
from .context import A2AContext, ContextExtractor
from .exceptions import OPAError, PolicyEvaluationError, PolicyViolationError
from .handler import OPARequestHandler
from .policies import PolicyManager

__version__ = "0.1.0"
__all__ = [
    "OPAClient",
    "OPARequestHandler",
    "ContextExtractor",
    "A2AContext",
    "PolicyManager",
    "PolicyDecision",
    "OPAError",
    "PolicyViolationError",
    "PolicyEvaluationError",
]

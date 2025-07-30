"""
A2A-OPA Integration Library

This library provides OPA (Open Policy Agent) integration for A2A (Agent-to-Agent) protocol,
enabling policy-based authorization and access control for agent communications.
"""

from .client import AgentCardDiscoveryContext, OPAClientInterceptor, evaluate_agent_card_policy
from .exceptions import OPAError, PolicyEvaluationError, PolicyViolationError

__version__ = "0.1.0"
__all__ = [
    # Client-side components
    "OPAClientInterceptor",
    "AgentCardDiscoveryContext",
    "evaluate_agent_card_policy",
    # Server-side components
    # TODO
    # Exceptions
    "OPAError",
    "PolicyViolationError",
    "PolicyEvaluationError",
]

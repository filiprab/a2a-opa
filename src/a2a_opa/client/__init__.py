"""
Client-side OPA integration for A2A protocol.

This module provides OPA policy enforcement at the Agent Card discovery level,
ensuring that clients can only discover and interact with agents that are
permitted by OPA policies.
"""

from .context import AgentCardDiscoveryContext
from .interceptor import OPAClientInterceptor
from .opa_client import evaluate_agent_card_policy

__all__ = [
    "AgentCardDiscoveryContext",
    "OPAClientInterceptor",
    "evaluate_agent_card_policy",
]

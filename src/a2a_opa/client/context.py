"""
Context extraction for Agent Card discovery OPA policy evaluation.
"""

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from a2a.client.middleware import ClientCallContext
from pydantic import Field


class AgentCardDiscoveryContext(ClientCallContext):
    """
    Context model for OPA policy evaluation during Agent Card discovery.

    This context is used to evaluate whether a client should be allowed to
    discover and interact with a target agent before the AgentCard is fetched.
    """

    # Client information
    client_identity: str = Field(description="Identity of the requesting client")
    client_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional client metadata"
    )

    # Target agent information
    target_agent_url: str = Field(description="URL of the target agent")
    target_agent_domain: str = Field(description="Domain of the target agent")
    target_agent_path: str = Field(description="Path component of target agent URL")

    # Request information
    operation_type: str = Field(
        description="Type of operation being requested (message, task, etc.)"
    )
    method_name: str = Field(description="A2A method name (e.g., 'message/send')")

    # Discovery metadata
    discovery_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When discovery was attempted"
    )
    discovery_source: str = Field(default="client", description="Source of the discovery request")

    # Request context
    request_headers: dict[str, str] = Field(
        default_factory=dict, description="HTTP headers from the request"
    )
    request_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional request metadata"
    )

    @classmethod
    def from_client_call(
        cls,
        client_identity: str,
        target_agent_url: str,
        method_name: str,
        operation_type: str | None = None,
        client_metadata: dict[str, Any] | None = None,
        request_headers: dict[str, str] | None = None,
        request_metadata: dict[str, Any] | None = None,
    ) -> "AgentCardDiscoveryContext":
        """
        Create context from A2A client call information.

        Args:
            client_identity: Identity of the requesting client
            target_agent_url: URL of the target agent
            method_name: A2A method name (e.g., 'message/send')
            operation_type: Type of operation, defaults to method prefix
            client_metadata: Additional client metadata
            request_headers: HTTP headers from the request
            request_metadata: Additional request metadata

        Returns:
            AgentCardDiscoveryContext instance
        """
        # Parse target URL
        parsed_url = urlparse(target_agent_url)
        target_domain = parsed_url.netloc
        target_path = parsed_url.path

        # Infer operation type from method name if not provided
        if operation_type is None:
            operation_type = method_name.split("/")[0] if "/" in method_name else method_name

        return cls(
            client_identity=client_identity,
            client_metadata=client_metadata or {},
            target_agent_url=target_agent_url,
            target_agent_domain=target_domain,
            target_agent_path=target_path,
            operation_type=operation_type,
            method_name=method_name,
            request_headers=request_headers or {},
            request_metadata=request_metadata or {},
        )

    def to_opa_input(self) -> dict[str, Any]:
        """
        Convert context to OPA policy input format.

        Returns:
            Dictionary suitable for OPA policy evaluation
        """
        return {
            "client": {
                "identity": self.client_identity,
                "metadata": self.client_metadata,
            },
            "target_agent": {
                "url": self.target_agent_url,
                "domain": self.target_agent_domain,
                "path": self.target_agent_path,
            },
            "request": {
                "operation_type": self.operation_type,
                "method_name": self.method_name,
                "headers": self.request_headers,
                "metadata": self.request_metadata,
            },
            "discovery": {
                "timestamp": self.discovery_timestamp.isoformat(),
                "source": self.discovery_source,
            },
        }

"""
Example usage of OPA client-side interceptor for A2A Agent Card discovery enforcement.

This example demonstrates how to use the OPAClientInterceptor to enforce
policies at the Agent Card discovery level before making A2A requests.
"""

import asyncio
import logging

import httpx
from a2a.client.client import A2AClient
from a2a.types import SendMessageRequest
from opa_client import create_opa_client

from a2a_opa import OPAClientInterceptor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate OPA client-side enforcement."""

    # Initialize OPA client using opa-python-client factory
    opa_client = create_opa_client(async_mode=True, host="localhost", port=8181)

    async with opa_client:

        # Check OPA connection
        if not await opa_client.check_connection():
            logger.error("Failed to connect to OPA server")
            return

        logger.info("Connected to OPA server")

        # Create OPA interceptor
        opa_interceptor = OPAClientInterceptor(
            opa_client=opa_client,
            client_identity="example-client-agent",
            package_path="a2a.client",
            rule_name="agent_card_discovery_allow",
            fail_closed=True,  # Deny access when policy evaluation fails
            log_decisions=True,  # Log policy decisions for audit
        )

        # Create A2A client with OPA interceptor
        async with httpx.AsyncClient() as http_client:

            # Target agent details
            target_agent_url = "https://example-agent.com/a2a"

            try:
                # Create A2A client - this will trigger Agent Card discovery
                # which will be intercepted by OPA policy evaluation
                a2a_client = A2AClient(
                    httpx_client=http_client,
                    url=target_agent_url,  # Direct URL approach
                    interceptors=[opa_interceptor],
                )

                # Send a message - OPA will evaluate policy before request
                message_request = SendMessageRequest(
                    message={
                        "role": "user",
                        "content": "Hello, can you help me with a task?"
                    }
                )

                logger.info("Sending message to agent...")
                response = await a2a_client.send_message(message_request)

                logger.info("Message sent successfully: %s", response.id)

            except Exception as e:
                logger.error("Failed to interact with agent: %s", e)
                if "policy" in str(e).lower():
                    logger.error("This appears to be a policy violation - check OPA policies")


async def setup_example_policy():
    """Set up example OPA policy for testing."""

    policy_content = '''
package a2a.client

# Default deny
default agent_card_discovery_allow = false

# Allow discovery for trusted clients and domains
agent_card_discovery_allow {
    # Check client identity
    input.client.identity == "example-client-agent"

    # Check target agent domain is in allowlist
    allowed_domains := ["example-agent.com", "trusted-agent.org"]
    input.target_agent.domain in allowed_domains

    # Check operation type is allowed
    allowed_operations := ["message", "task"]
    input.request.operation_type in allowed_operations
}

# Special rule for admin clients
agent_card_discovery_allow {
    input.client.identity == "admin-client"
}
'''

    opa_client = create_opa_client(async_mode=True, host="localhost", port=8181)
    async with opa_client:
        try:
            # Load policy using opa-python-client
            await opa_client.update_policy_from_string(policy_content, "client-policy")
            logger.info("Successfully loaded example policy")

        except Exception as e:
            logger.error("Failed to set up policy: %s", e)
            logger.info("Policy content:\n%s", policy_content)


if __name__ == "__main__":
    print("OPA Client Interceptor Example")
    print("=" * 40)
    print()
    print("This example demonstrates how to use OPAClientInterceptor")
    print("to enforce Agent Card discovery policies.")
    print()
    print("Prerequisites:")
    print("1. OPA server running on localhost:8181")
    print("2. Policy loaded (see setup_example_policy)")
    print("3. Target agent available for testing")
    print()
    
    # Set up example policy first
    print("Setting up example policy...")
    asyncio.run(setup_example_policy())
    print()
    
    # Run the main example
    print("Running client example...")
    asyncio.run(main())
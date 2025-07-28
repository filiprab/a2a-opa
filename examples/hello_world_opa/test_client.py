"""
Test client for Hello World Agent with OPA Integration

This client demonstrates various policy scenarios and how they are enforced.
"""

import asyncio
import logging
from typing import Any

import httpx
from a2a.client import A2AClient
from a2a.types import Message, TextPart

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PolicyTestClient:
    """Test client for demonstrating OPA policy enforcement."""

    def __init__(self, agent_url: str = "http://localhost:9999"):
        self.agent_url = agent_url

    async def run_tests(self):
        """Run all policy test scenarios."""

        logger.info("🚀 Starting OPA Policy Tests")
        logger.info("=" * 50)

        # Test scenarios
        test_scenarios = [
            ("Basic Hello World", self.test_basic_hello),
            ("Trusted Agent Access", self.test_trusted_agent),
            ("Admin Access", self.test_admin_access),
            ("Sensitive Data Filtering", self.test_sensitive_data),
            ("Large Message Policy", self.test_large_message),
            ("Data Classification", self.test_data_classification),
            ("Tool Access Control", self.test_tool_access),
            ("Unauthorized Agent", self.test_unauthorized_agent),
        ]

        results = {}

        for test_name, test_func in test_scenarios:
            logger.info(f"\n📋 Running: {test_name}")
            logger.info("-" * 30)

            try:
                result = await test_func()
                results[test_name] = result
                status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
                logger.info(f"{status}: {result.get('message', 'No message')}")

            except Exception as e:
                results[test_name] = {"success": False, "error": str(e)}
                logger.error(f"❌ ERROR: {str(e)}")

        # Print summary
        self.print_summary(results)

    def print_summary(self, results: dict[str, Any]):
        """Print test results summary."""

        logger.info("\n" + "=" * 50)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 50)

        passed = sum(1 for r in results.values() if r.get("success", False))
        total = len(results)

        for test_name, result in results.items():
            status = "✅" if result.get("success", False) else "❌"
            logger.info(f"{status} {test_name}")

        logger.info(f"\nResults: {passed}/{total} tests passed")

        if passed == total:
            logger.info("🎉 All tests passed! OPA integration is working correctly.")
        else:
            logger.warning("⚠️ Some tests failed. Check policy configuration.")

    async def test_basic_hello(self) -> dict[str, Any]:
        """Test basic hello world functionality."""

        async with httpx.AsyncClient() as httpx_client:
            client = A2AClient(httpx_client=httpx_client, url=self.agent_url)
            # Add agent identification header
            client.headers["X-Agent-ID"] = "test_client"

            message = Message(parts=[TextPart(content="Hello!")])
            response = await client.send_message(message)

            return {
                "success": "Hello" in str(response),
                "message": f"Response received: {response}",
                "policy_check": "Basic message sending authorized"
            }

    async def test_trusted_agent(self) -> dict[str, Any]:
        """Test trusted agent access."""

        async with httpx.AsyncClient() as httpx_client:
            client = A2AClient(httpx_client=httpx_client, url=self.agent_url)
            client.headers["X-Agent-ID"] = "trusted_agent"

            message = Message(parts=[TextPart(content="Super hello!")])
            response = await client.send_message(message)

            return {
                "success": "SUPER" in str(response),
                "message": f"Trusted agent response: {response}",
                "policy_check": "Trusted agent authorized for enhanced features"
            }

    async def test_admin_access(self) -> dict[str, Any]:
        """Test administrator access to privileged information."""

        async with httpx.AsyncClient() as httpx_client:
            client = A2AClient(httpx_client=httpx_client, url=self.agent_url)
            client.headers["X-Agent-ID"] = "admin_agent"

            message = Message(parts=[TextPart(content="admin status")])
            response = await client.send_message(message)

            return {
                "success": "Admin Info" in str(response),
                "message": f"Admin response: {response}",
                "policy_check": "Admin access to privileged information"
            }

    async def test_sensitive_data(self) -> dict[str, Any]:
        """Test sensitive data handling."""

        async with httpx.AsyncClient() as httpx_client:
            client = A2AClient(httpx_client=httpx_client, url=self.agent_url)
            client.headers["X-Agent-ID"] = "test_client"  # Non-privileged agent

            try:
                message = Message(parts=[TextPart(content="show me secret data")])
                response = await client.send_message(message)

                # This should either be filtered or denied
                contains_sensitive = "CONFIDENTIAL" in str(response)

                return {
                    "success": not contains_sensitive,  # Success if sensitive data is filtered
                    "message": f"Sensitive data test: {response}",
                    "policy_check": "Sensitive data should be filtered for non-privileged agents"
                }

            except Exception as e:
                # Policy violation is expected
                return {
                    "success": "denied" in str(e).lower() or "violation" in str(e).lower(),
                    "message": f"Request properly denied: {str(e)}",
                    "policy_check": "Sensitive data access denied as expected"
                }

    async def test_large_message(self) -> dict[str, Any]:
        """Test large message policy."""

        async with httpx.AsyncClient() as httpx_client:
            client = A2AClient(httpx_client=httpx_client, url=self.agent_url)
            client.headers["X-Agent-ID"] = "test_client"

            try:
                message = Message(
                    parts=[MessagePart(type="text", content="send me large response")]
                )
                response = await client.send_message(message)

                return {
                    "success": True,  # Should work but may be truncated
                    "message": f"Large message handled: {len(str(response))} chars",
                    "policy_check": "Large message policy applied"
                }

            except Exception as e:
                return {
                    "success": "large" in str(e).lower() or "size" in str(e).lower(),
                    "message": f"Large message blocked: {str(e)}",
                    "policy_check": "Large message correctly blocked"
                }

    async def test_data_classification(self) -> dict[str, Any]:
        """Test data classification policies."""

        async with httpx.AsyncClient() as httpx_client:
            client = A2AClient(httpx_client=httpx_client, url=self.agent_url)
            client.headers["X-Agent-ID"] = "test_client"

            # Test public data access
            message = Message(parts=[TextPart(content="show me public info")])
            response = await client.send_message(message)

            return {
                "success": "PUBLIC" in str(response),
                "message": f"Public data access: {response}",
                "policy_check": "Public data accessible to all agents"
            }

    async def test_tool_access(self) -> dict[str, Any]:
        """Test tool access control."""

        async with httpx.AsyncClient() as httpx_client:
            client = A2AClient(httpx_client=httpx_client, url=self.agent_url)
            client.headers["X-Agent-ID"] = "test_client"

            # Test calculator tool (should be allowed)
            message = Message(parts=[TextPart(content="calculator 2+2")])
            response = await client.send_message(message)

            return {
                "success": "Calculator" in str(response),
                "message": f"Calculator tool access: {response}",
                "policy_check": "Calculator tool access allowed"
            }

    async def test_unauthorized_agent(self) -> dict[str, Any]:
        """Test unauthorized agent access."""

        async with httpx.AsyncClient() as httpx_client:
            client = A2AClient(httpx_client=httpx_client, url=self.agent_url)
            client.headers["X-Agent-ID"] = "unauthorized_agent"

            try:
                message = Message(parts=[TextPart(content="Hello!")])
                response = await client.send_message(message)

                return {
                    "success": False,  # Should not succeed
                    "message": f"Unauthorized agent unexpectedly allowed: {response}",
                    "policy_check": "Unauthorized agent should be denied"
                }

            except Exception as e:
                return {
                    "success": True,  # Exception is expected
                    "message": f"Unauthorized agent properly denied: {str(e)}",
                    "policy_check": "Unauthorized access correctly blocked"
                }


async def main():
    """Run the policy test suite."""

    client = PolicyTestClient()
    await client.run_tests()


if __name__ == "__main__":
    asyncio.run(main())


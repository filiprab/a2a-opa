"""
Hello World Agent with OPA Integration

This example demonstrates how to integrate OPA policy enforcement
with an A2A agent using the a2a-opa library.
"""

import asyncio
import logging
from pathlib import Path

import uvicorn
import yaml
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent_executor import EnhancedHelloWorldAgentExecutor

# Import OPA integration components
from a2a_opa import ContextExtractor, OPAClient, OPARequestHandler
from a2a_opa.context import AgentInfo, DefaultContextExtractor
from a2a_opa.policies import PolicyManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def load_config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {}


async def setup_agent_registry():
    """Setup agent registry with known agents and their permissions."""
    return {
        "hello_agent": AgentInfo(
            agent_id="hello_agent",
            name="Hello World Agent",
            capabilities=["greeting", "basic_chat"],
            permissions=["send_messages", "view_tasks"],
            role="agent",
            clearance_level=1
        ),
        "admin_agent": AgentInfo(
            agent_id="admin_agent",
            name="Administrator Agent",
            capabilities=["all"],
            permissions=["admin", "manage_all_tasks", "handle_sensitive_data"],
            role="admin",
            clearance_level=5
        ),
        "trusted_agent": AgentInfo(
            agent_id="trusted_agent",
            name="Trusted Agent",
            capabilities=["secure_messaging", "data_processing"],
            permissions=["send_messages", "view_tasks", "handle_sensitive_data"],
            role="trusted",
            clearance_level=3
        ),
        "test_client": AgentInfo(
            agent_id="test_client",
            name="Test Client",
            capabilities=["testing"],
            permissions=["send_messages"],
            role="client",
            clearance_level=1
        )
    }


async def setup_opa_integration(config: dict):
    """Setup OPA integration components."""

    # Setup OPA client
    opa_url = config.get("opa", {}).get("url", "http://localhost:8181")
    opa_client = OPAClient(
        url=opa_url,
        timeout=config.get("opa", {}).get("timeout", 10.0)
    )

    # Test OPA connection
    if not await opa_client.health_check():
        logger.warning(f"OPA server at {opa_url} is not healthy. Policies may not work correctly.")
    else:
        logger.info(f"Connected to OPA server at {opa_url}")

    # Setup agent registry and context extractor
    agent_registry = await setup_agent_registry()
    context_extractor = ContextExtractor(
        extractor=DefaultContextExtractor(
            agent_registry=agent_registry,
            sensitive_patterns=config.get("security", {}).get("sensitive_patterns", [])
        ),
        environment_data=config.get("environment", {})
    )

    # Setup policy manager
    policy_manager = PolicyManager()

    return opa_client, context_extractor, policy_manager


async def upload_sample_policies(opa_client: OPAClient, policy_manager: PolicyManager):
    """Upload sample policies to OPA."""
    try:
        logger.info("Uploading sample policies to OPA...")

        templates = policy_manager.get_policy_templates()

        for policy_name, policy_content in templates.items():
            success = await opa_client.upload_policy(policy_name, policy_content)
            if success:
                logger.info(f"Uploaded policy: {policy_name}")
            else:
                logger.error(f"Failed to upload policy: {policy_name}")

        # Upload sample data
        sample_data = {
            "trusted_agents": ["hello_agent", "admin_agent", "trusted_agent", "test_client"],
            "public_agents": ["hello_agent"],
            "authorized_agents": ["hello_agent", "admin_agent", "trusted_agent", "test_client"],
            "agent_organizations": {
                "hello_agent": "demo_org",
                "admin_agent": "demo_org",
                "trusted_agent": "demo_org",
                "test_client": "demo_org"
            },
            "task_owners": {},  # Will be populated as tasks are created
            "public_tasks": [],
            "public_capabilities": ["greeting", "basic_chat"],
            "capability_permissions": {
                "secure_messaging": "handle_sensitive_data",
                "admin_functions": "admin"
            },
            "capability_clearance": {
                "sensitive_data": 3,
                "admin_data": 5
            },
            "allowed_operations": {
                "hello_agent": ["message/send", "message/stream", "tasks/get"],
                "admin_agent": ["message/send", "message/stream", "tasks/get", "tasks/cancel"],
                "trusted_agent": ["message/send", "message/stream", "tasks/get"],
                "test_client": ["message/send", "tasks/get"]
            },
            "system": {
                "maintenance_mode": False
            }
        }

        # Upload data for each policy
        for key, value in sample_data.items():
            success = await opa_client.upload_data(key, value)
            if success:
                logger.info(f"Uploaded data: {key}")
            else:
                logger.error(f"Failed to upload data: {key}")

    except Exception as e:
        logger.error(f"Error uploading policies: {e}")


async def main():
    """Main application setup and startup."""

    # Load configuration
    config = await load_config()

    # Setup OPA integration
    opa_client, context_extractor, policy_manager = await setup_opa_integration(config)

    # Upload sample policies
    await upload_sample_policies(opa_client, policy_manager)

    # Define agent skills
    basic_skill = AgentSkill(
        id='hello_world',
        name='Basic Hello World',
        description='Returns a friendly greeting',
        tags=['greeting', 'basic'],
        examples=['hi', 'hello', 'hello world'],
    )

    enhanced_skill = AgentSkill(
        id='enhanced_greeting',
        name='Enhanced Greeting',
        description='Enhanced greeting with policy demonstrations',
        tags=['greeting', 'enhanced', 'demo'],
        examples=['super hello', 'admin status', 'show me public info'],
    )

    # Create agent card
    agent_card = AgentCard(
        name='Hello World Agent with OPA',
        description='A demonstration agent showing OPA policy integration',
        url='http://localhost:9999/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[basic_skill, enhanced_skill],
        supports_authenticated_extended_card=False,
    )

    # Create original request handler
    original_handler = DefaultRequestHandler(
        agent_executor=EnhancedHelloWorldAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    # Create OPA-enhanced request handler
    opa_handler = OPARequestHandler(
        wrapped_handler=original_handler,
        opa_client=opa_client,
        context_extractor=context_extractor,
        policy_manager=policy_manager,
        default_deny=config.get("security", {}).get("default_deny", True),
        audit_decisions=config.get("security", {}).get("audit_decisions", True),
        fail_open=config.get("security", {}).get("fail_open", False)
    )

    # Create A2A server with OPA integration
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=opa_handler,
    )

    # Get server configuration
    host = config.get("server", {}).get("host", "0.0.0.0")
    port = config.get("server", {}).get("port", 9999)

    logger.info(f"Starting Hello World Agent with OPA at http://{host}:{port}")
    logger.info("Policy enforcement is active for all operations")

    # Start server
    uvicorn.run(
        server.build(),
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == '__main__':
    asyncio.run(main())

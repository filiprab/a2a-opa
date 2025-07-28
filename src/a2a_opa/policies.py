"""
Policy management for A2A-OPA integration.
"""

import logging
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PolicyMapping(BaseModel):
    """Mapping between A2A methods and OPA policy paths."""

    method: str
    policy_path: str
    description: str | None = None
    required: bool = True


class PolicyManager:
    """
    Manages policy mappings and configurations for A2A operations.

    This class handles the mapping between A2A methods and corresponding
    OPA policy paths, and provides utilities for policy management.
    """

    def __init__(self, policy_mappings: dict[str, str] | None = None):
        """
        Initialize policy manager.

        Args:
            policy_mappings: Custom mapping of A2A methods to policy paths
        """
        self.policy_mappings = policy_mappings or self._get_default_mappings()

    def _get_default_mappings(self) -> dict[str, str]:
        """Get default policy mappings for A2A methods."""
        return {
            # Message operations
            "message/send": "a2a.message_authorization",
            "message/stream": "a2a.message_authorization",

            # Task operations
            "tasks/get": "a2a.task_access",
            "tasks/cancel": "a2a.task_modification",
            "tasks/resubscribe": "a2a.task_access",

            # Push notification operations
            "tasks/pushNotificationConfig/set": "a2a.notification_management",
            "tasks/pushNotificationConfig/get": "a2a.notification_access",
            "tasks/pushNotificationConfig/list": "a2a.notification_access",
            "tasks/pushNotificationConfig/delete": "a2a.notification_management",

            # Agent card access (for future use)
            "agent/card": "a2a.agent_discovery",
            "agent/capabilities": "a2a.capability_access",
        }

    def get_policy_path(self, method: str) -> str:
        """
        Get the OPA policy path for an A2A method.

        Args:
            method: A2A method name

        Returns:
            OPA policy path
        """
        return self.policy_mappings.get(method, "a2a.default_authorization")

    def add_policy_mapping(self, method: str, policy_path: str) -> None:
        """
        Add or update a policy mapping.

        Args:
            method: A2A method name
            policy_path: OPA policy path
        """
        self.policy_mappings[method] = policy_path
        logger.info(f"Added policy mapping: {method} -> {policy_path}")

    def remove_policy_mapping(self, method: str) -> None:
        """
        Remove a policy mapping.

        Args:
            method: A2A method name to remove
        """
        if method in self.policy_mappings:
            del self.policy_mappings[method]
            logger.info(f"Removed policy mapping for: {method}")

    def get_all_mappings(self) -> dict[str, str]:
        """Get all current policy mappings."""
        return self.policy_mappings.copy()

    def get_policy_templates(self) -> dict[str, str]:
        """
        Get Rego policy templates for common A2A scenarios.

        Returns:
            Dictionary of policy name to Rego content
        """
        return {
            "message_authorization": self._get_message_authorization_template(),
            "task_access": self._get_task_access_template(),
            "task_modification": self._get_task_modification_template(),
            "agent_discovery": self._get_agent_discovery_template(),
            "capability_access": self._get_capability_access_template(),
            "notification_management": self._get_notification_management_template(),
            "notification_access": self._get_notification_access_template(),
            "default_authorization": self._get_default_authorization_template(),
        }

    def _get_message_authorization_template(self) -> str:
        """Get message authorization policy template."""
        return '''
package a2a.message_authorization

import rego.v1

# Default deny
default allow := false

# Default violations list
default violations := []

# Allow messages between trusted agents
allow if {
    input.requester.agent_id in data.trusted_agents
    input.target.agent_id in data.trusted_agents
}

# Allow public messages from authenticated agents
allow if {
    input.requester.agent_id != ""
    input.message.data_classification == "public"
}

# Allow internal messages with proper clearance
allow if {
    input.requester.clearance_level >= 2
    input.message.data_classification in ["public", "internal"]
}

# Block messages containing sensitive data unless authorized
violations contains "Message contains sensitive data" if {
    input.message.contains_sensitive_data
    not input.requester.permissions[_] == "handle_sensitive_data"
}

# Block large messages unless authorized
violations contains "Message too large" if {
    count(input.message.content) > 10000
    not input.requester.permissions[_] == "send_large_messages"
}

# Block messages during maintenance windows
violations contains "System in maintenance mode" if {
    data.system.maintenance_mode == true
    not input.requester.role == "admin"
}
'''.strip()

    def _get_task_access_template(self) -> str:
        """Get task access policy template."""
        return '''
package a2a.task_access

import rego.v1

default allow := false

# Allow access to own tasks
allow if {
    input.task.task_id != ""
    input.requester.agent_id == data.task_owners[input.task.task_id]
}

# Allow administrators to access all tasks
allow if {
    input.requester.role == "admin"
}

# Allow access to public tasks
allow if {
    input.task.task_id in data.public_tasks
}

# Allow agents with task_viewer permission
allow if {
    input.requester.permissions[_] == "view_all_tasks"
}
'''.strip()

    def _get_task_modification_template(self) -> str:
        """Get task modification policy template."""
        return '''
package a2a.task_modification

import rego.v1

default allow := false

# Allow modification of own tasks
allow if {
    input.task.task_id != ""
    input.requester.agent_id == data.task_owners[input.task.task_id]
}

# Allow administrators to modify all tasks
allow if {
    input.requester.role == "admin"
}

# Allow agents with task modification permission
allow if {
    input.requester.permissions[_] == "modify_all_tasks"
}

# Block modification of completed tasks unless admin
allow if {
    input.task.status != "completed"
    input.requester.agent_id == data.task_owners[input.task.task_id]
}
'''.strip()

    def _get_agent_discovery_template(self) -> str:
        """Get agent discovery policy template."""
        return '''
package a2a.agent_discovery

import rego.v1

default allow := false

# Allow authenticated agents to discover public agents
allow if {
    input.requester.agent_id != ""
    input.target.agent_id in data.public_agents
}

# Allow discovery within same organization
allow if {
    input.requester.agent_id != ""
    requester_org := data.agent_organizations[input.requester.agent_id]
    target_org := data.agent_organizations[input.target.agent_id]
    requester_org == target_org
}

# Allow administrators to discover all agents
allow if {
    input.requester.role == "admin"
}
'''.strip()

    def _get_capability_access_template(self) -> str:
        """Get capability access policy template."""
        return '''
package a2a.capability_access

import rego.v1

default allow := false

# Allow access to public capabilities
allow if {
    input.resource in data.public_capabilities
}

# Allow access based on agent permissions
allow if {
    required_permission := data.capability_permissions[input.resource]
    input.requester.permissions[_] == required_permission
}

# Allow access based on clearance level
allow if {
    required_clearance := data.capability_clearance[input.resource]
    input.requester.clearance_level >= required_clearance
}
'''.strip()

    def _get_notification_management_template(self) -> str:
        """Get notification management policy template."""
        return '''
package a2a.notification_management

import rego.v1

default allow := false

# Allow managing notifications for own tasks
allow if {
    input.task.task_id != ""
    input.requester.agent_id == data.task_owners[input.task.task_id]
}

# Allow administrators to manage all notifications
allow if {
    input.requester.role == "admin"
}

# Allow agents with notification management permission
allow if {
    input.requester.permissions[_] == "manage_notifications"
}
'''.strip()

    def _get_notification_access_template(self) -> str:
        """Get notification access policy template."""
        return '''
package a2a.notification_access

import rego.v1

default allow := false

# Allow viewing notifications for own tasks
allow if {
    input.task.task_id != ""
    input.requester.agent_id == data.task_owners[input.task.task_id]
}

# Allow administrators to view all notifications
allow if {
    input.requester.role == "admin"
}

# Allow agents with notification viewing permission
allow if {
    input.requester.permissions[_] == "view_notifications"
}
'''.strip()

    def _get_default_authorization_template(self) -> str:
        """Get default authorization policy template."""
        return '''
package a2a.default_authorization

import rego.v1

# Default deny - be explicit about authorization
default allow := false

# Only allow if explicitly authorized
allow if {
    input.requester.agent_id in data.authorized_agents
    input.operation in data.allowed_operations[input.requester.agent_id]
}

# Allow administrators for all operations
allow if {
    input.requester.role == "admin"
}
'''.strip()

    async def generate_policy_bundle(
        self,
        output_dir: Path,
        include_data: bool = True
    ) -> None:
        """
        Generate a complete policy bundle for OPA.

        Args:
            output_dir: Directory to write policy files
            include_data: Whether to include sample data files
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write policy templates
        templates = self.get_policy_templates()
        for name, content in templates.items():
            policy_file = output_dir / f"{name}.rego"
            policy_file.write_text(content)
            logger.info(f"Generated policy: {policy_file}")

        # Write sample data if requested
        if include_data:
            await self._generate_sample_data(output_dir)

    async def _generate_sample_data(self, output_dir: Path) -> None:
        """Generate sample data files for policies."""

        # Sample agent data
        agent_data = {
            "trusted_agents": ["agent1", "agent2", "admin_agent"],
            "public_agents": ["public_agent", "info_agent"],
            "authorized_agents": ["agent1", "agent2", "admin_agent"],
            "agent_organizations": {
                "agent1": "org1",
                "agent2": "org1",
                "external_agent": "org2"
            },
            "task_owners": {
                "task123": "agent1",
                "task456": "agent2"
            },
            "public_tasks": ["public_task1"],
            "public_capabilities": ["calculator", "weather"],
            "capability_permissions": {
                "file_access": "read_files",
                "database_access": "db_read"
            },
            "capability_clearance": {
                "sensitive_data": 3,
                "classified_info": 5
            },
            "allowed_operations": {
                "agent1": ["message/send", "tasks/get"],
                "agent2": ["message/send", "message/stream", "tasks/get"]
            },
            "system": {
                "maintenance_mode": False
            }
        }

        data_file = output_dir / "data.json"

        import json

        data_file.write_text(json.dumps(agent_data, indent=2))
        logger.info(f"Generated sample data: {data_file}")

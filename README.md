# A2A-OPA Integration

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

OPA (Open Policy Agent) integration for A2A (Agent-to-Agent) protocol, enabling policy-based authorization and access control for agent communications.

## Overview

!!! Be aware that this is currently not production ready. Current state of this project is a rough draft

This library provides a middleware layer that integrates OPA policy enforcement with the A2A Python SDK, allowing developers to:

- Enforce authorization policies on agent-to-agent communications
- Control access to agent capabilities and tools
- Implement fine-grained data access controls
- Audit and log all policy decisions
- Hot-reload policies without service restart

## Features

- 🔒 **Policy-based Authorization**: Use Rego policies to control agent interactions
- 🚀 **Non-invasive Integration**: Works with existing A2A agents via middleware pattern
- 🔄 **Real-time Policy Updates**: Hot-reload policies without downtime
- 📊 **Comprehensive Auditing**: Log all authorization decisions for compliance
- 🛠️ **Extensible Context**: Custom context extractors for domain-specific policies
- 🧪 **Policy Testing**: Built-in tools for testing and validating policies

## Quick Start

### Installation

```bash
uv add a2a-opa
```

### Development Setup

If you want to contribute or modify the library:

```bash
git clone https://github.com/your-org/a2a-opa.git
cd a2a-opa
uv sync --dev
```

### Basic Usage

```python
from a2a_opa import OPARequestHandler, OPAClient
from a2a.server.request_handlers import DefaultRequestHandler

# Wrap your existing A2A request handler
original_handler = DefaultRequestHandler(...)
opa_handler = OPARequestHandler(
    wrapped_handler=original_handler,
    opa_client=OPAClient("http://localhost:8181"),
    policy_bundle="a2a_policies"
)

# Use the OPA-enhanced handler in your A2A server
server = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=opa_handler
)
```

### Policy Example

```rego
package a2a.message_authorization

default allow = false

# Allow messages between trusted agents
allow {
    input.requester.agent_id in data.trusted_agents
    input.target.agent_id in data.trusted_agents
}

# Block messages containing sensitive data
allow {
    not contains(input.message.content, "SECRET")
    not contains(input.message.content, "CONFIDENTIAL")
}
```

## Documentation

- [Installation Guide](docs/installation.md)
- [Policy Writing Tutorial](docs/policies.md)
- [Integration Examples](docs/examples.md)
- [API Reference](docs/api.md)

## Examples

See the [examples](examples/) directory for complete working examples:

- [Hello World with OPA](examples/hello_world_opa/)
- [Multi-Agent Authorization](examples/multi_agent_auth/)
- [Data Classification Policies](examples/data_classification/)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
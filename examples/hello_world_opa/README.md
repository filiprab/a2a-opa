# Hello World Agent with OPA Integration

This example demonstrates how to integrate OPA (Open Policy Agent) with an A2A agent using the `a2a-opa` library.

## Overview

This example extends the basic Hello World agent from the A2A samples to include:

- Policy-based authorization for all agent interactions
- Content filtering based on data classification
- Agent-specific permissions and capabilities
- Audit logging of all policy decisions

## Files

- `agent_executor.py` - Enhanced HelloWorld agent executor
- `main.py` - Main server with OPA integration
- `policies/` - Rego policy files
- `config.yaml` - Configuration file
- `docker-compose.yml` - Complete setup with OPA server

## Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- A2A Python SDK

### Installation

1. Install with uv (recommended):
```bash
cd ../../
uv sync --dev
cd examples/hello_world_opa
uv add a2a-python uvicorn pyyaml httpx
```

2. Or install with pip:
```bash
pip install -e ../../
pip install -r requirements.txt
```

### Running the Example

1. Start OPA server and load policies:
```bash
docker-compose up -d opa
```

2. Run the enhanced Hello World agent:
```bash
uv run python main.py
```

3. Test the agent (in another terminal):
```bash
uv run python test_client.py
```

## Policy Configuration

The example includes several policies:

### Message Authorization (`policies/message_authorization.rego`)
- Controls who can send messages
- Filters messages based on content classification
- Blocks sensitive data unless authorized

### Agent Discovery (`policies/agent_discovery.rego`)
- Controls which agents can discover each other
- Implements organization-based access control

### Task Access (`policies/task_access.rego`)
- Controls access to task information
- Implements task ownership and permissions

## Testing Different Scenarios

The test client demonstrates various scenarios:

1. **Authorized Request**: Normal hello world request from trusted agent
2. **Unauthorized Agent**: Request from non-trusted agent (should be denied)
3. **Sensitive Content**: Message containing sensitive data (should be filtered)
4. **Administrator Access**: Admin user accessing restricted resources

## Customization

You can customize the policies by:

1. Editing the Rego files in the `policies/` directory
2. Modifying the data in `policies/data.json`
3. Updating the agent configuration in `config.yaml`
4. Extending the context extractor for custom data extraction

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   A2A Client    │───▶│ OPARequestHandler│───▶│OriginalHandler │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   OPA Server    │
                       │  (Policies)     │
                       └─────────────────┘
```

The OPA integration is completely transparent to both the client and the original agent implementation. All policy enforcement happens in the middleware layer.
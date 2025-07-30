# OPA Client Interceptor Example

This example demonstrates how to use the `OPAClientInterceptor` to enforce policies at the Agent Card discovery level for A2A client communications.

## Overview

The `OPAClientInterceptor` intercepts A2A client requests and evaluates OPA policies **before** Agent Card discovery, ensuring that clients can only interact with agents that are permitted by policy.

## Key Features

- **Agent Card Level Enforcement**: Policies are evaluated before Agent Card discovery
- **Rich Context**: Provides client identity, target agent info, and request metadata to policies
- **Fail Safe**: Configurable fail-open/fail-closed behavior
- **Audit Logging**: Optional logging of policy decisions
- **Async Compatible**: Uses `opa-python-client` for efficient async operations

## Prerequisites

1. **OPA Server**: Running on `localhost:8181`
2. **Python Dependencies**: `a2a-sdk`, `opa-python-client`, `httpx`
3. **Target Agent**: An A2A agent to test against (or mock)

## Setup

### 1. Start OPA Server

```bash
docker run -d -p 8181:8181 --name opa-client-example openpolicyagent/opa:latest run --server --addr=0.0.0.0:8181
```

### 2. Load Policy

```bash
# Load the example policy
curl -X PUT localhost:8181/v1/policies/client-policy \
  --data-binary @policy.rego \
  --header "Content-Type: text/plain"
```

### 3. Run Example

```bash
cd examples/client_opa_example
uv run python main.py
```

## Policy Structure

The example policy (`policy.rego`) demonstrates several access control patterns:

### Basic Trust-Based Access

```rego
agent_card_discovery_allow {
    # Trusted client identities
    input.client.identity in ["example-client-agent", "trusted-client-001"]
    
    # Allowed target domains  
    input.target_agent.domain in ["example-agent.com", "trusted-agent.org"]
    
    # Permitted operations
    input.request.operation_type in ["message", "task"]
}
```

### Admin Access

```rego
agent_card_discovery_allow {
    input.client.identity == "admin-client"
    # Admin gets broader access to operation types
}
```

### Time-Based Access

```rego
agent_card_discovery_allow {
    input.client.identity == "scheduled-client"
    
    # Only during business hours (9 AM - 5 PM UTC)
    hour := time.clock([time.parse_rfc3339_ns(input.discovery.timestamp), "UTC"])[0]
    hour >= 9
    hour < 17
}
```

### Environment-Based Access

```rego
agent_card_discovery_allow {
    # More permissive for development
    input.client.metadata.environment == "development"
    input.target_agent.domain in ["localhost", "dev.example.com"]
}
```

## Policy Input Format

The interceptor provides the following context to OPA policies:

```json
{
  "client": {
    "identity": "example-client-agent",
    "metadata": {
      "environment": "development",
      "client_version": "1.0.0"
    }
  },
  "target_agent": {
    "url": "https://example-agent.com/a2a",
    "domain": "example-agent.com", 
    "path": "/a2a"
  },
  "request": {
    "operation_type": "message",
    "method_name": "message/send",
    "headers": {},
    "metadata": {
      "request_id": "abc-123"
    }
  },
  "discovery": {
    "timestamp": "2024-01-01T12:00:00.000Z",
    "source": "client"
  }
}
```

## Usage Patterns

### Basic Usage

```python
from opa_client import create_opa_client
from a2a_opa import OPAClientInterceptor

# Use opa-python-client directly
opa_client = create_opa_client(async_mode=True, host="localhost", port=8181)

async with opa_client:
    interceptor = OPAClientInterceptor(
        opa_client=opa_client,
        client_identity="my-client-agent",
        package_path="a2a.client",
        rule_name="agent_card_discovery_allow"
    )
    
    client = A2AClient(
        httpx_client=http_client,
        url=target_url,
        interceptors=[interceptor]
    )
```

### Advanced Configuration

```python
interceptor = OPAClientInterceptor(
    opa_client=opa_client,
    client_identity="production-client",
    package_path="a2a.production.client",
    rule_name="discovery_allow",
    fail_closed=True,      # Deny on policy evaluation errors
    log_decisions=True,    # Log all policy decisions
)
```

## Testing

Test the policy with different client identities and target domains:

1. **Allowed Access**: `example-client-agent` → `example-agent.com`
2. **Denied Access**: `unknown-client` → `example-agent.com`  
3. **Admin Access**: `admin-client` → any domain
4. **Time-based**: `scheduled-client` during business hours

## Error Handling

The interceptor raises specific exceptions:

- `PolicyViolationError`: When policy explicitly denies access
- `PolicyEvaluationError`: When policy evaluation fails
- Standard A2A client errors for other failures

## Security Considerations

- Use `fail_closed=True` in production for security
- Regularly audit policy decisions via logs
- Keep OPA policies and client identities secure
- Consider rate limiting and other DoS protections
# Policy Writing Guide

This guide covers how to write Rego policies for A2A-OPA integration.

## Policy Structure

A2A-OPA policies follow standard Rego syntax with specific input data structure:

```rego
package a2a.example_policy

import rego.v1

# Default deny
default allow := false

# Allow rule
allow if {
    # Your authorization logic here
}

# Optional violations
violations contains "Reason for denial" if {
    # Condition that triggers violation
}
```

## Input Data Structure

Policies receive the following input structure:

```json
{
  "requester": {
    "agent_id": "string",
    "name": "string", 
    "capabilities": ["string"],
    "permissions": ["string"],
    "role": "string",
    "clearance_level": 0,
    "metadata": {}
  },
  "target": {
    "agent_id": "string",
    // ... same structure as requester
  },
  "message": {
    "message_id": "string",
    "content": "string",
    "message_type": "text",
    "parts": [{}],
    "contains_sensitive_data": false,
    "data_classification": "public"
  },
  "task": {
    "task_id": "string",
    "status": "string",
    "created_at": "2023-01-01T00:00:00Z",
    "metadata": {}
  },
  "request": {
    "method": "message/send",
    "timestamp": "2023-01-01T00:00:00Z",
    "remote_addr": "127.0.0.1",
    "headers": {}
  },
  "operation": "message/send",
  "resource": "message",
  "data": {},
  "environment": {}
}
```

## Common Policy Patterns

### 1. Agent Authorization

```rego
package a2a.agent_authorization

import rego.v1

# Allow trusted agents
allow if {
    input.requester.agent_id in data.trusted_agents
}

# Allow based on role
allow if {
    input.requester.role in ["admin", "trusted"]
}
```

### 2. Content Filtering

```rego
package a2a.content_filter

import rego.v1

default allow := false

# Block sensitive content
allow if {
    not input.message.contains_sensitive_data
}

# Allow sensitive content for authorized agents
allow if {
    input.message.contains_sensitive_data
    input.requester.permissions[_] == "handle_sensitive_data"
}
```

### 3. Time-Based Access

```rego
package a2a.time_based_access

import rego.v1

# Only allow during business hours
allow if {
    hour := time.hour(time.now_ns())
    hour >= 9
    hour <= 17
}

# Allow 24/7 for admins
allow if {
    input.requester.role == "admin"
}
```

### 4. Resource-Based Access Control

```rego
package a2a.resource_access

import rego.v1

# Allow access to public resources
allow if {
    input.resource in data.public_resources
}

# Allow access based on clearance level
allow if {
    required_clearance := data.resource_clearance[input.resource]
    input.requester.clearance_level >= required_clearance
}
```

## Data Management

### Static Data

Define static data in JSON files:

```json
{
  "trusted_agents": ["agent1", "agent2"],
  "admin_agents": ["admin"],
  "public_resources": ["greeting", "status"]
}
```

### Dynamic Data

Update data through OPA API:

```python
await opa_client.upload_data("trusted_agents", ["agent1", "agent2", "agent3"])
```

## Policy Testing

### Unit Testing

```rego
package a2a.example_policy

test_allow_trusted_agent if {
    allow with input as {
        "requester": {"agent_id": "trusted_agent"},
        "operation": "message/send"
    } with data as {
        "trusted_agents": ["trusted_agent"]
    }
}

test_deny_untrusted_agent if {
    not allow with input as {
        "requester": {"agent_id": "unknown_agent"},
        "operation": "message/send"
    } with data as {
        "trusted_agents": ["trusted_agent"]
    }
}
```

Run tests:
```bash
opa test policies/
```

## Best Practices

### 1. Default Deny
Always use explicit deny as default:
```rego
default allow := false
```

### 2. Explicit Rules
Make authorization rules explicit and readable:
```rego
# Good
allow if {
    input.requester.role == "admin"
    input.operation == "message/send"
}

# Less clear
allow if {
    input.requester.role == "admin"; input.operation == "message/send"
}
```

### 3. Use Violations
Provide clear violation messages:
```rego
violations contains "Agent not authorized for this operation" if {
    not input.requester.agent_id in data.authorized_agents
}
```

### 4. Performance Considerations
- Use indexed data structures when possible
- Avoid complex loops in hot paths
- Cache policy decisions when appropriate

## Advanced Topics

### 1. Partial Evaluation
Use partial evaluation for complex policies:
```rego
partial_allow[{"agent_id": agent_id}] if {
    agent_id := data.trusted_agents[_]
    # Additional conditions
}
```

### 2. External Data Sources
Integrate with external systems:
```rego
allow if {
    agent_info := http.send({
        "method": "GET",
        "url": sprintf("http://auth-service/agents/%s", [input.requester.agent_id])
    })
    agent_info.body.authorized == true
}
```

### 3. Policy Composition
Combine multiple policies:
```rego
package a2a.combined_policy

import data.a2a.agent_auth
import data.a2a.content_filter
import data.a2a.time_based

allow if {
    agent_auth.allow
    content_filter.allow  
    time_based.allow
}
```
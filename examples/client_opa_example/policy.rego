package a2a.client

# Default deny - be explicit about access control
default agent_card_discovery_allow = false

# Allow discovery for trusted clients and domains
agent_card_discovery_allow {
    # Verify client identity is in trusted list
    trusted_clients := [
        "example-client-agent",
        "trusted-client-001",
        "development-client"
    ]
    input.client.identity in trusted_clients
    
    # Verify target agent domain is in allowlist
    allowed_domains := [
        "example-agent.com",
        "trusted-agent.org", 
        "internal-agent.local",
        "localhost"
    ]
    input.target_agent.domain in allowed_domains
    
    # Verify operation type is permitted
    allowed_operations := ["message", "task", "notification"]
    input.request.operation_type in allowed_operations
}

# Special rule for admin clients - broader access
agent_card_discovery_allow {
    input.client.identity == "admin-client"
    
    # Admin clients can access any operation type
    input.request.operation_type in ["message", "task", "notification", "admin"]
}

# Time-based access control example
agent_card_discovery_allow {
    input.client.identity == "scheduled-client"
    
    # Parse discovery timestamp
    discovery_time := time.parse_rfc3339_ns(input.discovery.timestamp)
    now := time.now_ns()
    
    # Allow access during business hours (9 AM - 5 PM UTC)
    hour := time.clock([discovery_time, "UTC"])[0]
    hour >= 9
    hour < 17
    
    # Must be a message operation
    input.request.operation_type == "message"
}

# Development environment - more permissive
agent_card_discovery_allow {
    # Check if this is a development environment
    input.client.metadata.environment == "development"
    
    # Allow localhost and development domains
    dev_domains := ["localhost", "dev.example.com", "test.example.com"]
    input.target_agent.domain in dev_domains
    
    # Standard operations only
    input.request.operation_type in ["message", "task"]
}
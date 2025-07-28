# Installation Guide

## Prerequisites

- Python 3.11 or higher
- uv (recommended) or pip
- Docker (for OPA server)
- A2A Python SDK

## Installation Methods

### 1. Install with uv (Recommended)

```bash
uv add a2a-opa
```

### 2. Install from PyPI with pip

```bash
pip install a2a-opa
```

### 3. Install from Source with uv

```bash
git clone https://github.com/your-org/a2a-opa.git
cd a2a-opa
uv sync
```

### 4. Development Installation

```bash
git clone https://github.com/your-org/a2a-opa.git
cd a2a-opa
uv sync --dev
```

## OPA Setup

### Using Docker (Recommended)

1. Start OPA server:
```bash
docker run -d -p 8181:8181 --name opa openpolicyagent/opa:latest run --server --addr=0.0.0.0:8181
```

2. Verify OPA is running:
```bash
curl http://localhost:8181/health
```

### Using Binary

1. Download OPA binary from [releases](https://github.com/open-policy-agent/opa/releases)

2. Start OPA server:
```bash
./opa run --server --addr=0.0.0.0:8181
```

## Verification

Test your installation:

```python
import asyncio
from a2a_opa import OPAClient

async def test_installation():
    async with OPAClient("http://localhost:8181") as client:
        healthy = await client.health_check()
        print(f"OPA connection: {'✅ OK' if healthy else '❌ Failed'}")

asyncio.run(test_installation())
```

## Next Steps

- [Quick Start Guide](../README.md#quick-start)
- [Policy Writing Tutorial](policies.md)
- [Integration Examples](examples.md)
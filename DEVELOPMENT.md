# Development Guide

## Getting Started

### Prerequisites
- Python 3.11 or higher
- uv package manager (recommended) or pip
- Docker (for OPA server)
- Git

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/a2a-opa.git
   cd a2a-opa
   ```

2. **Install dependencies with uv (recommended):**
   ```bash
   uv sync --dev
   ```
   
   This will:
   - Create a virtual environment automatically
   - Install all project dependencies
   - Install development dependencies (pytest, mypy, ruff, etc.)
   - Generate a `uv.lock` file

3. **Alternative: Install with pip:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```

### Development Workflow

#### Running Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/a2a_opa --cov-report=html

# Run specific test file
uv run pytest tests/test_client.py
```

#### Code Quality
```bash
# Format code
uv run ruff format .

# Check for issues
uv run ruff check .

# Type checking
uv run mypy src/
```

#### Running the Example
```bash
# Start OPA server
docker run -d -p 8181:8181 --name opa-dev openpolicyagent/opa:latest run --server --addr=0.0.0.0:8181

# Run the Hello World example
cd examples/hello_world_opa
uv run python main.py

# Test the example (in another terminal)
uv run python test_client.py
```

### Project Structure

```
a2a-opa/
├── src/a2a_opa/          # Main package
│   ├── __init__.py       # Package exports
│   ├── client.py         # OPA client
│   ├── handler.py        # Request handler
│   ├── context.py        # Context extraction
│   ├── policies.py       # Policy management
│   └── exceptions.py     # Custom exceptions
├── tests/                # Test suite
├── examples/             # Usage examples
├── docs/                 # Documentation
└── pyproject.toml        # Project configuration
```

### Adding Dependencies

```bash
# Add a new dependency
uv add httpx

# Add a development dependency
uv add --dev pytest-mock

# Remove a dependency
uv remove httpx
```

### Common Issues

1. **Missing uv.lock file**: Just run `uv sync --dev` to generate it
2. **Python version conflicts**: Make sure you have Python 3.11+ installed
3. **OPA connection errors**: Ensure OPA server is running on port 8181

### Testing Policy Changes

1. **Edit policies in** `src/a2a_opa/policies.py`
2. **Test policies with OPA CLI:**
   ```bash
   # Test a specific policy
   opa test examples/hello_world_opa/policies/
   ```
3. **Run integration tests:**
   ```bash
   uv run pytest tests/test_handler.py
   ```

### Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run full test suite: `uv run pytest`
4. Build package: `uv build`
5. Publish: `uv publish` (requires PyPI credentials)

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.
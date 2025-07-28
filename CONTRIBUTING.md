# Contributing to A2A-OPA Integration

We welcome contributions to the A2A-OPA integration project! This document provides guidelines for contributing.

## Development Setup

### Prerequisites

- Python 3.11+
- uv (recommended) or pip
- Docker
- Git

### Setup

1. Fork and clone the repository:
```bash
git clone https://github.com/your-username/a2a-opa.git
cd a2a-opa
```

2. Install with uv (recommended):
```bash
uv sync --dev
```

Or with pip:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

**Note**: The first time you run `uv sync --dev`, uv will create a `uv.lock` file and virtual environment automatically.

4. Start OPA server for testing:
```bash
docker run -d -p 8181:8181 --name opa-dev openpolicyagent/opa:latest run --server --addr=0.0.0.0:8181
```

## Development Workflow

### Code Style

We use Ruff for linting and formatting:

```bash
# Format code
ruff format .

# Check for issues
ruff check .
```

### Type Checking

We use MyPy for type checking:

```bash
mypy src/
```

### Testing

Run tests with pytest:

```bash
# Run all tests with uv
uv run pytest

# Run with coverage
uv run pytest --cov=src/a2a_opa --cov-report=html

# Run specific test file
uv run pytest tests/test_client.py
```

### Policy Testing

Test Rego policies:

```bash
# Test all policies
opa test examples/hello_world_opa/policies/

# Test specific policy
opa test examples/hello_world_opa/policies/message_authorization.rego
```

## Contribution Guidelines

### Pull Request Process

1. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes following the code style guidelines

3. Add tests for new functionality

4. Update documentation if needed

5. Commit your changes:
```bash
git commit -m "feat: add new feature description"
```

6. Push to your fork and create a pull request

### Commit Message Format

Use conventional commits format:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

### Code Requirements

- All code must have type hints
- New features must include tests
- Public APIs must have docstrings
- Breaking changes must be documented

### Policy Contributions

When contributing Rego policies:

1. Include comprehensive tests
2. Add documentation explaining the policy logic
3. Follow the established package naming convention
4. Include example data for testing

## Documentation

### Adding Documentation

- API documentation is auto-generated from docstrings
- Update relevant `.md` files in the `docs/` directory
- Include examples in documentation

### Building Documentation

```bash
# Install documentation dependencies (if docs extra is defined)
uv sync --extra docs

# Build documentation
cd docs
make html
```

## Issue Reporting

### Bug Reports

Include:
- Python version
- A2A SDK version
- OPA version
- Minimal reproduction case
- Error messages and stack traces

### Feature Requests

Include:
- Clear description of the feature
- Use case and motivation
- Proposed API changes (if applicable)

## Community

### Getting Help

- Open an issue for questions
- Check existing issues and documentation first
- Be respectful and constructive

### Code Review

- All contributions require code review
- Address reviewer feedback promptly
- Be open to suggestions and improvements

## Security

### Reporting Security Issues

- Do not open public issues for security vulnerabilities
- Email security@your-org.com with details
- Allow time for investigation and fixes

### Security Guidelines

- Never commit secrets, keys, or credentials
- Follow security best practices in policy design
- Consider security implications of new features

## Release Process

### Versioning

We follow semantic versioning (SemVer):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

### Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update `CHANGELOG.md`
- [ ] Create release notes
- [ ] Tag release
- [ ] Publish to PyPI

Thank you for contributing to A2A-OPA integration!
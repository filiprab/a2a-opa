"""
Pytest configuration and fixtures.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_server_context():
    """Create mock server call context."""
    context = AsyncMock()
    context.headers = {"X-Agent-ID": "test_agent"}
    context.remote_addr = "127.0.0.1"
    context.metadata = {}
    return context
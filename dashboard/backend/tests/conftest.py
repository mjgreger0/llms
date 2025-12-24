"""Pytest configuration and fixtures for Phase 5 tests."""

import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default event loop policy."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


# Note: For integration tests that need database access,
# fixtures should be added here to create test database sessions.

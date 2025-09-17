"""
Pytest configuration for async tests
"""

import asyncio
import pytest
import pytest_asyncio


# Set event loop policy to avoid Windows-specific issues
if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# Configure pytest-asyncio
pytest_asyncio.asyncio_default_fixture_loop_scope = "function"

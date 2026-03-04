"""
Comprehensive test suite for Rustlette — Starlette 0.50.0 drop-in replacement.

Tests verify API compatibility, behavior correctness, and FastAPI integration.
"""

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"

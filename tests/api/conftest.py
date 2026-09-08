"""
Pytest fixtures scoped to the tests/api/ subsystem:
- client: TestClient configured with FastAPI application lifespan context
"""

from typing import Generator
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Yields a TestClient instance wrapped with lifespan management
    so graph initialization runs on startup.
    """
    with TestClient(app) as test_client:
        yield test_client


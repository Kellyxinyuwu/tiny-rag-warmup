"""
Pytest fixtures for tiny_rag tests.
"""
import pytest
from fastapi.testclient import TestClient

from tiny_rag.api import app


@pytest.fixture
def client():
    """FastAPI TestClient."""
    return TestClient(app)

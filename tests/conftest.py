from collections.abc import Generator

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """
    Shared FastAPI test client.

    Runs the application's lifespan events
    (startup and shutdown) just like production.
    """
    with TestClient(app) as client:
        yield client

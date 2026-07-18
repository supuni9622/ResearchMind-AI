"""
Unit tests for get_langsmith_client.

Covers:
- Returns None when langsmith_api_key isn't configured
- Returns the constructed Client when configured
- Returns None (not raising) when Client construction fails
"""

from __future__ import annotations

import langsmith
import pytest
from app.ai.observability.providers.langsmith.client import get_langsmith_client
from app.core.settings import settings


@pytest.fixture(autouse=True)
def _clear_cache():
    get_langsmith_client.cache_clear()
    yield
    get_langsmith_client.cache_clear()


async def test_returns_none_when_api_key_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "langsmith_api_key", None)

    assert get_langsmith_client() is None


async def test_returns_client_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "langsmith_api_key", "test-key")
    monkeypatch.setattr(langsmith, "Client", lambda **kwargs: "fake-client")

    assert get_langsmith_client() == "fake-client"


async def test_returns_none_when_client_construction_fails(monkeypatch) -> None:
    monkeypatch.setattr(settings, "langsmith_api_key", "test-key")

    def _raise(**kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(langsmith, "Client", _raise)

    assert get_langsmith_client() is None

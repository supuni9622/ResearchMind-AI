"""
Unit tests for RetrievalRegistry.

Covers:
- get returns the provider registered under its own provider identifier
- get raises RetrievalProviderNotFoundError for an unregistered provider
- has reflects registration state
- providers lists every registered provider identifier
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.ai.knowledge.retrieval.enums import RetrievalProvider
from app.ai.knowledge.retrieval.exceptions import RetrievalProviderNotFoundError
from app.ai.knowledge.retrieval.registry import RetrievalRegistry


def _make_provider(provider: RetrievalProvider) -> MagicMock:
    mock_provider = MagicMock()
    mock_provider.provider = provider
    return mock_provider


def test_get_returns_the_provider_registered_under_its_identifier() -> None:
    provider = _make_provider(RetrievalProvider.QDRANT)
    registry = RetrievalRegistry([provider])

    assert registry.get(RetrievalProvider.QDRANT) is provider


def test_get_raises_not_found_for_an_unregistered_provider() -> None:
    registry = RetrievalRegistry([])

    with pytest.raises(RetrievalProviderNotFoundError):
        registry.get(RetrievalProvider.QDRANT)


def test_has_reflects_registration_state() -> None:
    provider = _make_provider(RetrievalProvider.QDRANT)
    registry = RetrievalRegistry([provider])

    assert registry.has(RetrievalProvider.QDRANT) is True
    assert registry.has(RetrievalProvider.QDRANT) is True  # idempotent, no mutation


def test_has_returns_false_for_an_unregistered_provider() -> None:
    registry = RetrievalRegistry([])

    assert registry.has(RetrievalProvider.QDRANT) is False


def test_providers_lists_every_registered_provider_identifier() -> None:
    provider = _make_provider(RetrievalProvider.QDRANT)
    registry = RetrievalRegistry([provider])

    assert registry.providers == [RetrievalProvider.QDRANT]

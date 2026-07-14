"""
Unit tests for RerankingRegistry.

Covers:
- get returns the provider registered under its own provider identifier
- get raises RerankingProviderNotFoundError for an unregistered provider
- has reflects registration state, without mutating it
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.ai.knowledge.reranking.enums import RerankingProvider
from app.ai.knowledge.reranking.exceptions import RerankingProviderNotFoundError
from app.ai.knowledge.reranking.registry import RerankingRegistry


def _make_provider(provider: RerankingProvider) -> MagicMock:
    mock_provider = MagicMock()
    mock_provider.provider = provider
    return mock_provider


def test_get_returns_the_provider_registered_under_its_identifier() -> None:
    provider = _make_provider(RerankingProvider.CROSS_ENCODER)
    registry = RerankingRegistry([provider])

    assert registry.get(RerankingProvider.CROSS_ENCODER) is provider


def test_get_raises_not_found_for_an_unregistered_provider() -> None:
    registry = RerankingRegistry([])

    with pytest.raises(RerankingProviderNotFoundError):
        registry.get(RerankingProvider.CROSS_ENCODER)


def test_has_reflects_registration_state() -> None:
    provider = _make_provider(RerankingProvider.VOYAGE_AI)
    registry = RerankingRegistry([provider])

    assert registry.has(RerankingProvider.VOYAGE_AI) is True
    assert registry.has(RerankingProvider.VOYAGE_AI) is True  # idempotent, no mutation


def test_has_returns_false_for_an_unregistered_provider() -> None:
    registry = RerankingRegistry([])

    assert registry.has(RerankingProvider.VOYAGE_AI) is False

"""
Unit tests for EmbeddingRegistry.

Covers:
- Registering and resolving providers
- Duplicate registration raises ValueError
- Unknown provider lookup raises EmbeddingProviderNotFoundError
- exists/unregister/clear behavior
- providers property returns a defensive copy
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.exceptions import EmbeddingProviderNotFoundError
from app.ai.knowledge.embeddings.interfaces import (
    EmbeddingProvider as EmbeddingProviderInterface,
)
from app.ai.knowledge.embeddings.registry import EmbeddingRegistry


def _make_provider(provider: EmbeddingProvider) -> MagicMock:
    fake = MagicMock(spec=EmbeddingProviderInterface)
    fake.provider = provider
    return fake


def test_register_then_get_returns_same_provider() -> None:
    registry = EmbeddingRegistry()
    provider = _make_provider(EmbeddingProvider.SENTENCE_TRANSFORMERS)

    registry.register(provider)

    assert registry.get(EmbeddingProvider.SENTENCE_TRANSFORMERS) is provider


def test_register_duplicate_provider_raises_value_error() -> None:
    registry = EmbeddingRegistry()
    registry.register(_make_provider(EmbeddingProvider.SENTENCE_TRANSFORMERS))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_make_provider(EmbeddingProvider.SENTENCE_TRANSFORMERS))


def test_get_unknown_provider_raises_not_found_error() -> None:
    registry = EmbeddingRegistry()

    with pytest.raises(EmbeddingProviderNotFoundError):
        registry.get(EmbeddingProvider.VOYAGE_AI)


def test_exists_reflects_registration_state() -> None:
    registry = EmbeddingRegistry()

    assert registry.exists(EmbeddingProvider.SENTENCE_TRANSFORMERS) is False

    registry.register(_make_provider(EmbeddingProvider.SENTENCE_TRANSFORMERS))

    assert registry.exists(EmbeddingProvider.SENTENCE_TRANSFORMERS) is True


def test_unregister_removes_provider() -> None:
    registry = EmbeddingRegistry()
    registry.register(_make_provider(EmbeddingProvider.SENTENCE_TRANSFORMERS))

    registry.unregister(EmbeddingProvider.SENTENCE_TRANSFORMERS)

    assert registry.exists(EmbeddingProvider.SENTENCE_TRANSFORMERS) is False


def test_unregister_missing_provider_is_a_no_op() -> None:
    registry = EmbeddingRegistry()

    registry.unregister(EmbeddingProvider.SENTENCE_TRANSFORMERS)

    assert registry.exists(EmbeddingProvider.SENTENCE_TRANSFORMERS) is False


def test_clear_removes_all_providers() -> None:
    registry = EmbeddingRegistry()
    registry.register(_make_provider(EmbeddingProvider.SENTENCE_TRANSFORMERS))
    registry.register(_make_provider(EmbeddingProvider.VOYAGE_AI))

    registry.clear()

    assert registry.supported_providers == []


def test_providers_property_returns_defensive_copy() -> None:
    registry = EmbeddingRegistry()
    registry.register(_make_provider(EmbeddingProvider.SENTENCE_TRANSFORMERS))

    snapshot = registry.providers
    snapshot[EmbeddingProvider.VOYAGE_AI] = _make_provider(EmbeddingProvider.VOYAGE_AI)

    assert registry.exists(EmbeddingProvider.VOYAGE_AI) is False


def test_supported_providers_lists_registered_providers() -> None:
    registry = EmbeddingRegistry()
    registry.register(_make_provider(EmbeddingProvider.SENTENCE_TRANSFORMERS))
    registry.register(_make_provider(EmbeddingProvider.VOYAGE_AI))

    assert set(registry.supported_providers) == {
        EmbeddingProvider.SENTENCE_TRANSFORMERS,
        EmbeddingProvider.VOYAGE_AI,
    }

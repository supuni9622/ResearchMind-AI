"""
Unit tests for VectorStoreRegistry.

Covers:
- Registering and resolving providers
- Duplicate registration raises ValueError
- Unknown provider lookup raises VectorStoreProviderNotFoundError
- exists/unregister behavior
- providers property returns a defensive copy
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.ai.knowledge.vectorstores.enums import VectorStoreProvider
from app.ai.knowledge.vectorstores.exceptions import VectorStoreProviderNotFoundError
from app.ai.knowledge.vectorstores.interfaces import VectorStoreProviderInterface
from app.ai.knowledge.vectorstores.registry import VectorStoreRegistry


def _make_provider(provider: VectorStoreProvider) -> MagicMock:
    fake = MagicMock(spec=VectorStoreProviderInterface)
    fake.provider = provider
    return fake


def test_register_then_get_returns_same_provider() -> None:
    registry = VectorStoreRegistry()
    provider = _make_provider(VectorStoreProvider.QDRANT)

    registry.register(provider)

    assert registry.get(VectorStoreProvider.QDRANT) is provider


def test_register_duplicate_provider_raises_value_error() -> None:
    registry = VectorStoreRegistry()
    registry.register(_make_provider(VectorStoreProvider.QDRANT))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_make_provider(VectorStoreProvider.QDRANT))


def test_get_unknown_provider_raises_not_found_error() -> None:
    registry = VectorStoreRegistry()

    with pytest.raises(VectorStoreProviderNotFoundError):
        registry.get(VectorStoreProvider.QDRANT)


def test_exists_reflects_registration_state() -> None:
    registry = VectorStoreRegistry()

    assert registry.exists(VectorStoreProvider.QDRANT) is False

    registry.register(_make_provider(VectorStoreProvider.QDRANT))

    assert registry.exists(VectorStoreProvider.QDRANT) is True


def test_unregister_removes_provider() -> None:
    registry = VectorStoreRegistry()
    registry.register(_make_provider(VectorStoreProvider.QDRANT))

    registry.unregister(VectorStoreProvider.QDRANT)

    assert registry.exists(VectorStoreProvider.QDRANT) is False


def test_providers_property_returns_defensive_copy() -> None:
    registry = VectorStoreRegistry()
    registry.register(_make_provider(VectorStoreProvider.QDRANT))

    snapshot = registry.providers
    snapshot[VectorStoreProvider.CHROMADB] = _make_provider(VectorStoreProvider.CHROMADB)

    assert registry.exists(VectorStoreProvider.CHROMADB) is False

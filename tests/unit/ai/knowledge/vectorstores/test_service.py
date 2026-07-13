"""
Unit tests for VectorStoreService.

Covers:
- Successful delegation to the resolved provider for every operation
- upsert validation: empty record list and records with an empty vector
  both raise VectorStoreValidationError before the provider is called
- Unknown provider propagates VectorStoreProviderNotFoundError from the
  registry
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.vectorstores.enums import (
    VectorDistanceMetric,
    VectorStoreProvider,
)
from app.ai.knowledge.vectorstores.exceptions import (
    VectorStoreProviderNotFoundError,
    VectorStoreValidationError,
)
from app.ai.knowledge.vectorstores.models import (
    CollectionDefinition,
    VectorPayload,
    VectorStoreRecord,
)
from app.ai.knowledge.vectorstores.registry import VectorStoreRegistry
from app.ai.knowledge.vectorstores.service import VectorStoreService

_DOCUMENT_ID = uuid.uuid4()


def _make_collection_definition() -> CollectionDefinition:
    return CollectionDefinition(
        name="researchmind_knowledge",
        provider=VectorStoreProvider.QDRANT,
        dimensions=512,
        distance_metric=VectorDistanceMetric.DOT,
    )


def _make_record(*, vector: list[float] | None = None) -> VectorStoreRecord:
    return VectorStoreRecord(
        id=uuid.uuid4(),
        vector=[0.1, 0.2] if vector is None else vector,
        payload=VectorPayload(
            document_id=_DOCUMENT_ID,
            chunk_id=uuid.uuid4(),
            filename="test.pdf",
            content="test chunk content",
            owner_id="owner-1",
            chunk_index=0,
        ),
    )


def _make_registry_with_provider() -> tuple[VectorStoreRegistry, AsyncMock]:
    provider = AsyncMock()
    provider.provider = VectorStoreProvider.QDRANT

    registry = VectorStoreRegistry()
    registry.register(provider)
    return registry, provider


async def test_create_collection_delegates_to_resolved_provider() -> None:
    registry, provider = _make_registry_with_provider()
    service = VectorStoreService(registry=registry)
    definition = _make_collection_definition()

    await service.create_collection(provider=VectorStoreProvider.QDRANT, definition=definition)

    provider.create_collection.assert_awaited_once_with(definition)


async def test_collection_exists_delegates_to_resolved_provider() -> None:
    registry, provider = _make_registry_with_provider()
    provider.collection_exists = AsyncMock(return_value=True)
    service = VectorStoreService(registry=registry)

    result = await service.collection_exists(
        provider=VectorStoreProvider.QDRANT,
        collection_name="researchmind_knowledge",
    )

    assert result is True
    provider.collection_exists.assert_awaited_once_with("researchmind_knowledge")


async def test_upsert_delegates_valid_records_to_resolved_provider() -> None:
    registry, provider = _make_registry_with_provider()
    service = VectorStoreService(registry=registry)
    records = [_make_record()]

    await service.upsert(
        provider=VectorStoreProvider.QDRANT,
        collection_name="researchmind_knowledge",
        records=records,
    )

    provider.upsert.assert_awaited_once_with(
        collection_name="researchmind_knowledge",
        records=records,
    )


async def test_upsert_raises_on_empty_record_list() -> None:
    registry, provider = _make_registry_with_provider()
    service = VectorStoreService(registry=registry)

    with pytest.raises(VectorStoreValidationError, match="No vector records"):
        await service.upsert(
            provider=VectorStoreProvider.QDRANT,
            collection_name="researchmind_knowledge",
            records=[],
        )

    provider.upsert.assert_not_awaited()


async def test_upsert_raises_when_a_record_has_no_vector_values() -> None:
    registry, provider = _make_registry_with_provider()
    service = VectorStoreService(registry=registry)

    with pytest.raises(VectorStoreValidationError, match="contains no values"):
        await service.upsert(
            provider=VectorStoreProvider.QDRANT,
            collection_name="researchmind_knowledge",
            records=[_make_record(vector=[])],
        )

    provider.upsert.assert_not_awaited()


async def test_delete_document_delegates_to_resolved_provider() -> None:
    registry, provider = _make_registry_with_provider()
    service = VectorStoreService(registry=registry)

    await service.delete_document(
        provider=VectorStoreProvider.QDRANT,
        collection_name="researchmind_knowledge",
        document_id=str(_DOCUMENT_ID),
    )

    provider.delete_document.assert_awaited_once_with(
        collection_name="researchmind_knowledge",
        document_id=str(_DOCUMENT_ID),
    )


async def test_count_delegates_to_resolved_provider() -> None:
    registry, provider = _make_registry_with_provider()
    provider.count = AsyncMock(return_value=7)
    service = VectorStoreService(registry=registry)

    result = await service.count(
        provider=VectorStoreProvider.QDRANT,
        collection_name="researchmind_knowledge",
    )

    assert result == 7
    provider.count.assert_awaited_once_with("researchmind_knowledge")


async def test_operations_raise_when_provider_not_registered() -> None:
    service = VectorStoreService(registry=VectorStoreRegistry())

    with pytest.raises(VectorStoreProviderNotFoundError):
        await service.collection_exists(
            provider=VectorStoreProvider.QDRANT,
            collection_name="researchmind_knowledge",
        )

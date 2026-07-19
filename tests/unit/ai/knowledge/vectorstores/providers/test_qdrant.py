"""
Unit tests for QdrantVectorStoreProvider.

Covers the ADR-019 hybrid retrieval schema specifically:
- create_collection configures named `dense` + `sparse` vectors (not a
  single unnamed vector), and refuses to recreate an existing collection
- upsert converts records into points carrying a named dense vector,
  attaching a named sparse vector only when the record has one
- delete_document filters by the `document_id` payload field
- collection_info reads dimensions/distance back from the named `dense`
  vector config, and raises a clear error for a pre-hybrid (unnamed
  vector) collection instead of misreading it
- SDK failures are translated into canonical VectorStoreError subclasses
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.vectorstores.config import QdrantVectorStoreConfig
from app.ai.knowledge.vectorstores.enums import VectorDistanceMetric, VectorStoreProvider
from app.ai.knowledge.vectorstores.exceptions import (
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
    CollectionOperationError,
    VectorDeletionError,
    VectorIndexingError,
)
from app.ai.knowledge.vectorstores.models import (
    CollectionDefinition,
    SparseVector,
    VectorPayload,
    VectorStoreRecord,
)
from app.ai.knowledge.vectorstores.providers.qdrant import (
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    QdrantVectorStoreProvider,
)
from qdrant_client.http import models as qdrant

_DOCUMENT_ID = uuid.uuid4()


def _make_collection_definition(**overrides: object) -> CollectionDefinition:
    defaults: dict[str, object] = {
        "name": "researchmind_knowledge",
        "provider": VectorStoreProvider.QDRANT,
        "dimensions": 512,
        "distance_metric": VectorDistanceMetric.DOT,
    }
    defaults.update(overrides)
    return CollectionDefinition(**defaults)


def _make_record(*, sparse: SparseVector | None = None, chunk_index: int = 0) -> VectorStoreRecord:
    return VectorStoreRecord(
        id=uuid.uuid4(),
        vector=[0.1, 0.2, 0.3],
        sparse_vector=sparse,
        payload=VectorPayload(
            document_id=_DOCUMENT_ID,
            chunk_id=uuid.uuid4(),
            filename="test.pdf",
            content="test chunk content",
            owner_id="owner-1",
            chunk_index=chunk_index,
        ),
    )


def _make_provider(
    *,
    client: AsyncMock | None = None,
    config: QdrantVectorStoreConfig | None = None,
) -> tuple[QdrantVectorStoreProvider, AsyncMock]:
    client = client or AsyncMock()
    provider = QdrantVectorStoreProvider(
        config=config or QdrantVectorStoreConfig(),
        client=client,
    )
    return provider, client


# ---------------------------------------------------------------------------
# create_collection
# ---------------------------------------------------------------------------


async def test_create_collection_configures_named_dense_and_sparse_vectors() -> None:
    provider, client = _make_provider()
    client.collection_exists = AsyncMock(return_value=False)
    definition = _make_collection_definition(
        dimensions=512, distance_metric=VectorDistanceMetric.DOT
    )

    await provider.create_collection(definition)

    call_kwargs = client.create_collection.await_args.kwargs
    assert call_kwargs["collection_name"] == "researchmind_knowledge"
    assert call_kwargs["vectors_config"] == {
        DENSE_VECTOR_NAME: qdrant.VectorParams(size=512, distance=qdrant.Distance.DOT),
    }
    assert call_kwargs["sparse_vectors_config"] == {
        SPARSE_VECTOR_NAME: qdrant.SparseVectorParams(
            index=qdrant.SparseIndexParams(on_disk=False),
        ),
    }


async def test_create_collection_raises_when_collection_already_exists() -> None:
    provider, client = _make_provider()
    client.collection_exists = AsyncMock(return_value=True)

    with pytest.raises(CollectionAlreadyExistsError):
        await provider.create_collection(_make_collection_definition())

    client.create_collection.assert_not_awaited()


# ---------------------------------------------------------------------------
# upsert
# ---------------------------------------------------------------------------


async def test_upsert_attaches_named_sparse_vector_when_present() -> None:
    provider, client = _make_provider()
    record = _make_record(sparse=SparseVector(indices=[1, 5], values=[0.9, 0.4]))

    await provider.upsert(collection_name="researchmind_knowledge", records=[record])

    points = client.upsert.await_args.kwargs["points"]
    assert len(points) == 1
    point_vector = points[0].vector
    assert point_vector[DENSE_VECTOR_NAME] == record.vector
    assert point_vector[SPARSE_VECTOR_NAME] == qdrant.SparseVector(
        indices=[1, 5], values=[0.9, 0.4]
    )


async def test_upsert_omits_sparse_vector_when_record_has_none() -> None:
    provider, client = _make_provider()
    record = _make_record(sparse=None)

    await provider.upsert(collection_name="researchmind_knowledge", records=[record])

    point_vector = client.upsert.await_args.kwargs["points"][0].vector
    assert point_vector == {DENSE_VECTOR_NAME: record.vector}


async def test_upsert_batches_records_according_to_configured_batch_size() -> None:
    provider, client = _make_provider(config=QdrantVectorStoreConfig(batch_size=1))
    records = [_make_record(), _make_record()]

    await provider.upsert(collection_name="researchmind_knowledge", records=records)

    assert client.upsert.await_count == 2


async def test_upsert_wraps_client_failures_in_vector_indexing_error() -> None:
    provider, client = _make_provider()
    client.upsert = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(VectorIndexingError):
        await provider.upsert(collection_name="researchmind_knowledge", records=[_make_record()])


# ---------------------------------------------------------------------------
# delete_document
# ---------------------------------------------------------------------------


async def test_delete_document_filters_by_document_id_payload_field() -> None:
    provider, client = _make_provider()

    await provider.delete_document(
        collection_name="researchmind_knowledge",
        document_id=str(_DOCUMENT_ID),
    )

    call_kwargs = client.delete.await_args.kwargs
    condition = call_kwargs["points_selector"].filter.must[0]
    assert condition.key == "document_id"
    assert condition.match.value == str(_DOCUMENT_ID)


async def test_delete_document_wraps_client_failures_in_vector_deletion_error() -> None:
    provider, client = _make_provider()
    client.delete = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(VectorDeletionError):
        await provider.delete_document(
            collection_name="researchmind_knowledge",
            document_id=str(_DOCUMENT_ID),
        )


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


async def test_count_returns_client_reported_count() -> None:
    provider, client = _make_provider()
    client.count = AsyncMock(return_value=SimpleNamespace(count=42))

    result = await provider.count("researchmind_knowledge")

    assert result == 42


async def test_count_filters_vectors_by_owner_when_requested() -> None:
    provider, client = _make_provider()
    client.count = AsyncMock(return_value=SimpleNamespace(count=12))

    result = await provider.count("researchmind_knowledge", owner_id="owner-1")

    assert result == 12
    count_filter = client.count.await_args.kwargs["count_filter"]
    assert count_filter.must[0].key == "owner_id"
    assert count_filter.must[0].match.value == "owner-1"


async def test_count_wraps_client_failures_in_collection_operation_error() -> None:
    provider, client = _make_provider()
    client.count = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(CollectionOperationError):
        await provider.count("researchmind_knowledge")


# ---------------------------------------------------------------------------
# collection_info
# ---------------------------------------------------------------------------


def _make_collection_info(*, vectors: object, points_count: int = 10) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(params=SimpleNamespace(vectors=vectors)),
        points_count=points_count,
    )


async def test_collection_info_reads_dimensions_from_named_dense_vector() -> None:
    provider, client = _make_provider()
    client.get_collection = AsyncMock(
        return_value=_make_collection_info(
            vectors={
                DENSE_VECTOR_NAME: qdrant.VectorParams(size=512, distance=qdrant.Distance.DOT)
            },
            points_count=7,
        )
    )

    metadata = await provider.collection_info("researchmind_knowledge")

    assert metadata.definition.dimensions == 512
    assert metadata.definition.distance_metric == VectorDistanceMetric.DOT
    assert metadata.vector_count == 7


async def test_collection_info_raises_for_pre_hybrid_unnamed_vector_schema() -> None:
    """
    A collection created before ADR-019 (single unnamed vector) must raise a
    clear error rather than being silently misread.
    """

    provider, client = _make_provider()
    client.get_collection = AsyncMock(
        return_value=_make_collection_info(
            vectors=qdrant.VectorParams(size=512, distance=qdrant.Distance.DOT),
        )
    )

    with pytest.raises(CollectionOperationError, match=DENSE_VECTOR_NAME):
        await provider.collection_info("researchmind_knowledge")


async def test_collection_info_wraps_client_failures_in_collection_not_found_error() -> None:
    provider, client = _make_provider()
    client.get_collection = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(CollectionNotFoundError):
        await provider.collection_info("researchmind_knowledge")

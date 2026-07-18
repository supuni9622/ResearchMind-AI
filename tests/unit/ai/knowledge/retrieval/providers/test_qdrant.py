"""
Unit tests for QdrantRetrievalProvider.

Covers:
- search queries the named `dense` vector (ADR-019 hybrid schema) with the
  configured collection/limit/payload options, and maps returned points
  into canonical RetrievedChunk objects
- Missing optional payload fields (filename, owner_id, chunk_index,
  content, additional_metadata) fall back to their documented defaults
- No matching points returns an empty chunk list rather than raising
- A point payload missing a required field (chunk_id/document_id) fails
  fast with a KeyError instead of silently producing a bad chunk
- search_metadata performs a filter-only `scroll()` (no vector) when
  filters are present, assigns matches a flat score since there is no
  similarity to rank by, and short-circuits to an empty result without
  calling Qdrant at all when there are no filters (an unfiltered scroll
  would ignore tenant scoping and return arbitrary points)
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.retrieval.config import QdrantRetrievalConfig
from app.ai.knowledge.retrieval.models import RetrievalQuery
from app.ai.knowledge.retrieval.providers.qdrant import QdrantRetrievalProvider
from app.ai.knowledge.vectorstores.providers.qdrant import DENSE_VECTOR_NAME

_DOCUMENT_ID = uuid.uuid4()
_CHUNK_ID = uuid.uuid4()


def _make_point(**payload_overrides: object) -> SimpleNamespace:
    payload: dict[str, object] = {
        "chunk_id": str(_CHUNK_ID),
        "document_id": str(_DOCUMENT_ID),
        "filename": "test.pdf",
        "owner_id": "owner-1",
        "chunk_index": 3,
        "content": "some chunk text",
        "additional_metadata": {"page": 2},
    }
    payload.update(payload_overrides)

    return SimpleNamespace(payload=payload, score=0.87)


def _make_provider(
    *,
    client: AsyncMock | None = None,
    config: QdrantRetrievalConfig | None = None,
) -> tuple[QdrantRetrievalProvider, AsyncMock]:
    client = client or AsyncMock()
    provider = QdrantRetrievalProvider(
        client=client,
        config=config or QdrantRetrievalConfig(),
    )
    return provider, client


async def test_search_queries_named_dense_vector_and_maps_points_to_chunks() -> None:
    provider, client = _make_provider(
        config=QdrantRetrievalConfig(collection_name="researchmind_knowledge"),
    )
    client.query_points = AsyncMock(return_value=SimpleNamespace(points=[_make_point()]))
    query = RetrievalQuery(query="what is rag?", top_k=5)

    result = await provider.search(query=query, query_vector=[0.1, 0.2, 0.3])

    call_kwargs = client.query_points.await_args.kwargs
    assert call_kwargs["collection_name"] == "researchmind_knowledge"
    assert call_kwargs["query"] == [0.1, 0.2, 0.3]
    assert call_kwargs["using"] == DENSE_VECTOR_NAME
    assert call_kwargs["limit"] == 5

    assert len(result.chunks) == 1
    chunk = result.chunks[0]
    assert chunk.chunk_id == _CHUNK_ID
    assert chunk.document_id == _DOCUMENT_ID
    assert chunk.filename == "test.pdf"
    assert chunk.owner_id == "owner-1"
    assert chunk.chunk_index == 3
    assert chunk.content == "some chunk text"
    assert chunk.score == pytest.approx(0.87)
    assert chunk.metadata == {"page": 2}
    assert result.query is query
    assert result.execution.completed_at is not None


async def test_search_defaults_missing_optional_payload_fields() -> None:
    provider, client = _make_provider()
    sparse_point = _make_point(
        filename=None,
        owner_id=None,
        chunk_index=None,
        content=None,
        additional_metadata=None,
    )
    # Simulate a payload that truly omits the optional keys rather than
    # setting them to None (payload.get(..., default) only kicks in when
    # the key is absent).
    for key in ("filename", "owner_id", "chunk_index", "content", "additional_metadata"):
        sparse_point.payload.pop(key)

    client.query_points = AsyncMock(return_value=SimpleNamespace(points=[sparse_point]))

    result = await provider.search(
        query=RetrievalQuery(query="rag"),
        query_vector=[0.1],
    )

    chunk = result.chunks[0]
    assert chunk.filename == ""
    assert chunk.owner_id == ""
    assert chunk.chunk_index == 0
    assert chunk.content == ""
    assert chunk.metadata == {}


async def test_search_returns_empty_chunks_when_no_points_found() -> None:
    provider, client = _make_provider()
    client.query_points = AsyncMock(return_value=SimpleNamespace(points=[]))

    result = await provider.search(
        query=RetrievalQuery(query="rag"),
        query_vector=[0.1],
    )

    assert result.chunks == []


async def test_search_raises_key_error_when_payload_missing_document_id() -> None:
    provider, client = _make_provider()
    point = _make_point()
    del point.payload["document_id"]
    client.query_points = AsyncMock(return_value=SimpleNamespace(points=[point]))

    with pytest.raises(KeyError):
        await provider.search(
            query=RetrievalQuery(query="rag"),
            query_vector=[0.1],
        )


async def test_search_metadata_scrolls_with_filter_and_assigns_flat_score() -> None:
    provider, client = _make_provider(
        config=QdrantRetrievalConfig(collection_name="researchmind_knowledge"),
    )
    # scroll() records carry no `.score` attribute -- unlike query_points
    # points, there is no vector similarity involved.
    record = SimpleNamespace(
        payload={
            "chunk_id": str(_CHUNK_ID),
            "document_id": str(_DOCUMENT_ID),
            "filename": "test.pdf",
            "owner_id": "owner-1",
            "chunk_index": 1,
            "content": "some chunk text",
            "additional_metadata": {},
        }
    )
    client.scroll = AsyncMock(return_value=([record], None))
    query = RetrievalQuery(query="rag", top_k=5, filters={"owner_id": "owner-1"})

    result = await provider.search_metadata(query=query)

    call_kwargs = client.scroll.await_args.kwargs
    assert call_kwargs["collection_name"] == "researchmind_knowledge"
    assert call_kwargs["limit"] == 5
    assert call_kwargs["scroll_filter"] is not None

    assert len(result.chunks) == 1
    assert result.chunks[0].chunk_id == _CHUNK_ID
    assert result.chunks[0].score == 1.0


async def test_search_metadata_short_circuits_without_filters() -> None:
    provider, client = _make_provider()
    client.scroll = AsyncMock()

    result = await provider.search_metadata(
        query=RetrievalQuery(query="rag"),
    )

    client.scroll.assert_not_awaited()
    assert result.chunks == []

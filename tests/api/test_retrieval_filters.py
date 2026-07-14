"""
Integration tests for owner_id filter enforcement across the retrieval API.

Covers:
- POST /retrieve, /retrieve/sparse, /retrieve/hybrid all forward
  `filters` from the request body into the RetrievalQuery handed to
  RetrievalService
- When an owner_id filter is supplied, only chunks belonging to that
  owner are returned
- With no filters, chunks from every owner are returned

RetrievedChunkResponse does not expose `owner_id` (see
app/schemas/retrieval.py), so ownership is asserted via each chunk's
`filename`, which is deterministically prefixed with its owner in the
fake chunk pool below.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.ai.knowledge.retrieval.enums import RetrievalProvider, RetrievalStrategy
from app.ai.knowledge.retrieval.models import (
    RetrievalExecution,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStatistics,
    RetrievedChunk,
)
from app.dependencies.retrieval import get_retrieval_service
from app.main import app
from fastapi.testclient import TestClient

_OWNER_1 = "owner-1"
_OWNER_2 = "owner-2"

_CHUNK_POOL = [
    RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        filename=f"{_OWNER_1}-report.pdf",
        owner_id=_OWNER_1,
        chunk_index=0,
        content="owner-1 chunk content",
        score=0.9,
    ),
    RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        filename=f"{_OWNER_2}-report.pdf",
        owner_id=_OWNER_2,
        chunk_index=0,
        content="owner-2 chunk content",
        score=0.8,
    ),
]


class _FakeRetrievalService:
    """
    Stands in for RetrievalService, applying the same owner_id filter
    semantics as QdrantRetrievalProvider._build_filter without needing a
    live Qdrant instance.
    """

    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self._chunks = chunks
        self.received_queries: list[RetrievalQuery] = []

    def _filtered_chunks(self, query: RetrievalQuery) -> list[RetrievedChunk]:
        owner_id = query.filters.get("owner_id")

        chunks = self._chunks
        if owner_id:
            chunks = [chunk for chunk in chunks if chunk.owner_id == owner_id]

        return chunks[: query.top_k]

    def _result_for(
        self,
        query: RetrievalQuery,
        strategy: RetrievalStrategy,
    ) -> RetrievalResult:
        self.received_queries.append(query)
        chunks = self._filtered_chunks(query)

        return RetrievalResult(
            query=query,
            execution=RetrievalExecution(completed_at=datetime.now(UTC)),
            statistics=RetrievalStatistics(
                provider=RetrievalProvider.QDRANT,
                strategy=strategy,
                duration_ms=0.0,
                returned_chunks=len(chunks),
            ),
            chunks=chunks,
        )

    async def search(
        self, *, provider: RetrievalProvider, query: RetrievalQuery
    ) -> RetrievalResult:
        return self._result_for(query, RetrievalStrategy.DENSE)

    async def search_sparse(
        self, *, provider: RetrievalProvider, query: RetrievalQuery
    ) -> RetrievalResult:
        return self._result_for(query, RetrievalStrategy.SPARSE)

    async def search_hybrid(
        self, *, provider: RetrievalProvider, query: RetrievalQuery
    ) -> RetrievalResult:
        return self._result_for(query, RetrievalStrategy.HYBRID)


@pytest.fixture
def fake_retrieval_service() -> Iterator[_FakeRetrievalService]:
    service = _FakeRetrievalService(list(_CHUNK_POOL))
    app.dependency_overrides[get_retrieval_service] = lambda: service

    yield service

    app.dependency_overrides.pop(get_retrieval_service, None)


@pytest.mark.parametrize(
    "endpoint",
    ["/retrieve", "/retrieve/sparse", "/retrieve/hybrid"],
)
def test_owner_filter_only_returns_chunks_for_that_owner(
    client: TestClient,
    fake_retrieval_service: _FakeRetrievalService,
    endpoint: str,
) -> None:
    response = client.post(
        f"/api/v1{endpoint}",
        json={
            "query": "what is rag?",
            "filters": {"owner_id": _OWNER_1},
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["total_chunks"] == 1
    for chunk in body["chunks"]:
        assert chunk["filename"].startswith(_OWNER_1)

    forwarded_query = fake_retrieval_service.received_queries[-1]
    assert forwarded_query.filters == {"owner_id": _OWNER_1}


@pytest.mark.parametrize(
    "endpoint",
    ["/retrieve", "/retrieve/sparse", "/retrieve/hybrid"],
)
def test_no_filters_returns_chunks_from_every_owner(
    client: TestClient,
    fake_retrieval_service: _FakeRetrievalService,
    endpoint: str,
) -> None:
    response = client.post(
        f"/api/v1{endpoint}",
        json={"query": "what is rag?"},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["total_chunks"] == len(_CHUNK_POOL)
    filenames = {chunk["filename"] for chunk in body["chunks"]}
    assert filenames == {chunk.filename for chunk in _CHUNK_POOL}

    forwarded_query = fake_retrieval_service.received_queries[-1]
    assert forwarded_query.filters == {}


@pytest.mark.parametrize(
    "endpoint",
    ["/retrieve", "/retrieve/sparse", "/retrieve/hybrid"],
)
def test_owner_filter_excludes_other_owners_chunk(
    client: TestClient,
    fake_retrieval_service: _FakeRetrievalService,
    endpoint: str,
) -> None:
    response = client.post(
        f"/api/v1{endpoint}",
        json={
            "query": "what is rag?",
            "filters": {"owner_id": _OWNER_2},
        },
    )

    assert response.status_code == 200
    body = response.json()

    filenames = {chunk["filename"] for chunk in body["chunks"]}
    assert f"{_OWNER_1}-report.pdf" not in filenames

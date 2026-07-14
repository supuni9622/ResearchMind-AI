"""
Integration tests for auth and owner_id scoping on the retrieval API.

Covers:
- POST /retrieve, /retrieve/sparse, /retrieve/hybrid all require
  authentication (401 without a bearer token)
- Retrieval is always scoped to the authenticated user: owner_id is
  derived from current_user.id, never from the request body
- A client-supplied owner_id in `filters` is ignored/overridden rather
  than trusted, closing the IDOR where a caller could otherwise read
  another user's documents by spoofing the filter

RetrievedChunkResponse does not expose `owner_id` (see
app/schemas/retrieval.py), so ownership is asserted via each chunk's
`filename`, which is deterministically prefixed with its owner in the
fake chunk pool below.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.ai.knowledge.retrieval.enums import RetrievalProvider, RetrievalStrategy
from app.ai.knowledge.retrieval.models import (
    RetrievalExecution,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStatistics,
    RetrievedChunk,
)
from app.auth.dependencies import get_current_user
from app.dependencies.retrieval import get_retrieval_service
from app.main import app
from app.models.user import User
from fastapi.testclient import TestClient

_OWNER_1_ID = str(uuid.uuid4())
_OWNER_2_ID = str(uuid.uuid4())

_CHUNK_POOL = [
    RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename="owner-1-report.pdf",
        owner_id=_OWNER_1_ID,
        chunk_index=0,
        content="owner-1 chunk content",
        score=0.9,
    ),
    RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename="owner-2-report.pdf",
        owner_id=_OWNER_2_ID,
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


def _fake_user(owner_id: str) -> User:
    return User(
        id=uuid.UUID(owner_id),
        auth_provider="test",
        provider_user_id=owner_id,
        email=f"{owner_id}@example.com",
    )


def _authenticate_as(owner_id: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: _fake_user(owner_id)


@pytest.fixture
def fake_retrieval_service() -> Iterator[_FakeRetrievalService]:
    service = _FakeRetrievalService(list(_CHUNK_POOL))
    app.dependency_overrides[get_retrieval_service] = lambda: service

    yield service

    app.dependency_overrides.pop(get_retrieval_service, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize(
    "endpoint",
    ["/retrieve", "/retrieve/sparse", "/retrieve/hybrid"],
)
def test_missing_authentication_returns_401(
    client: TestClient,
    fake_retrieval_service: _FakeRetrievalService,
    endpoint: str,
) -> None:
    response = client.post(
        f"/api/v1{endpoint}",
        json={"query": "what is rag?"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert fake_retrieval_service.received_queries == []


@pytest.mark.parametrize(
    "endpoint",
    ["/retrieve", "/retrieve/sparse", "/retrieve/hybrid"],
)
def test_retrieval_is_scoped_to_the_authenticated_user(
    client: TestClient,
    fake_retrieval_service: _FakeRetrievalService,
    endpoint: str,
) -> None:
    _authenticate_as(_OWNER_1_ID)

    response = client.post(
        f"/api/v1{endpoint}",
        json={"query": "what is rag?"},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["total_chunks"] == 1
    assert body["chunks"][0]["filename"] == "owner-1-report.pdf"

    forwarded_query = fake_retrieval_service.received_queries[-1]
    assert forwarded_query.filters == {"owner_id": _OWNER_1_ID}


@pytest.mark.parametrize(
    "endpoint",
    ["/retrieve", "/retrieve/sparse", "/retrieve/hybrid"],
)
def test_client_supplied_owner_id_filter_is_ignored(
    client: TestClient,
    fake_retrieval_service: _FakeRetrievalService,
    endpoint: str,
) -> None:
    # Authenticated as owner 1, but the request body tries to spoof
    # owner 2's filter. The server must override it with the
    # authenticated user's id rather than trusting the client.
    _authenticate_as(_OWNER_1_ID)

    response = client.post(
        f"/api/v1{endpoint}",
        json={
            "query": "what is rag?",
            "filters": {"owner_id": _OWNER_2_ID},
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["total_chunks"] == 1
    assert body["chunks"][0]["filename"] == "owner-1-report.pdf"

    forwarded_query = fake_retrieval_service.received_queries[-1]
    assert forwarded_query.filters == {"owner_id": _OWNER_1_ID}

"""
Unit tests for RetrievalService.

Covers:
- Successful search: normalized query and embedding are forwarded to the
  resolved provider, and runtime statistics/execution metadata are
  populated from the provider's result
- Query normalization collapses internal whitespace and trims
- Validation edge cases: empty query, whitespace-only query, over-length
  query, and non-positive top_k all raise before any provider is touched
- Provider resolution failure propagates from the registry
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.retrieval.enums import RetrievalProvider, RetrievalStrategy
from app.ai.knowledge.retrieval.exceptions import (
    RetrievalProviderNotFoundError,
    RetrievalValidationError,
)
from app.ai.knowledge.retrieval.models import (
    RetrievalExecution,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
)
from app.ai.knowledge.retrieval.registry import RetrievalRegistry
from app.ai.knowledge.retrieval.service import RetrievalService


def _make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename="test.pdf",
        owner_id="owner-1",
        chunk_index=0,
        content="some chunk text",
        score=0.9,
    )


def _make_provider(
    *,
    result: RetrievalResult | None = None,
    strategy: RetrievalStrategy = RetrievalStrategy.DENSE,
) -> AsyncMock:
    provider = AsyncMock()
    provider.provider = RetrievalProvider.QDRANT
    provider.config = SimpleNamespace(strategy=strategy)

    if result is not None:
        provider.search = AsyncMock(return_value=result)
    else:
        provider.search = AsyncMock(
            side_effect=lambda **kwargs: RetrievalResult(
                query=kwargs["query"],
                execution=RetrievalExecution(),
                chunks=[_make_chunk()],
            )
        )

    return provider


def _make_query_embedding_service(vector: list[float] | None = None) -> AsyncMock:
    service = AsyncMock()
    service.embed = AsyncMock(return_value=vector or [0.1, 0.2, 0.3])
    return service


def _make_service(
    *,
    registry: RetrievalRegistry,
    query_embedding_service: AsyncMock | None = None,
) -> RetrievalService:
    return RetrievalService(
        registry=registry,
        query_embedding_service=(query_embedding_service or _make_query_embedding_service()),
        sparse_query_embedding_service=AsyncMock(),
        fusion_service=AsyncMock(),
    )


async def test_search_returns_result_with_statistics_populated_from_provider() -> None:
    chunk = _make_chunk()
    provider = _make_provider(
        result=RetrievalResult(
            query=RetrievalQuery(query="rag"),
            execution=RetrievalExecution(),
            chunks=[chunk],
        ),
        strategy=RetrievalStrategy.HYBRID,
    )
    query_embedding_service = _make_query_embedding_service([0.4, 0.5])
    registry = RetrievalRegistry([provider])
    service = _make_service(
        registry=registry,
        query_embedding_service=query_embedding_service,
    )

    result = await service.search(
        provider=RetrievalProvider.QDRANT,
        query=RetrievalQuery(query="what is rag?", top_k=3),
    )

    query_embedding_service.embed.assert_awaited_once_with("what is rag?")
    provider.search.assert_awaited_once()
    assert provider.search.await_args.kwargs["query_vector"] == [0.4, 0.5]

    assert result.chunks == [chunk]
    assert result.execution.completed_at is not None
    assert result.statistics is not None
    assert result.statistics.provider == RetrievalProvider.QDRANT
    assert result.statistics.strategy == RetrievalStrategy.HYBRID
    assert result.statistics.duration_ms >= 0
    assert result.statistics.returned_chunks == 1


async def test_search_normalizes_whitespace_in_query() -> None:
    provider = _make_provider()
    query_embedding_service = _make_query_embedding_service()
    registry = RetrievalRegistry([provider])
    service = _make_service(
        registry=registry,
        query_embedding_service=query_embedding_service,
    )

    await service.search(
        provider=RetrievalProvider.QDRANT,
        query=RetrievalQuery(query="  what   is\n\nrag?  "),
    )

    query_embedding_service.embed.assert_awaited_once_with("what is rag?")
    sent_query = provider.search.await_args.kwargs["query"]
    assert sent_query.query == "what is rag?"


@pytest.mark.parametrize(
    "query_text",
    ["", "   ", "\n\t  "],
)
async def test_search_raises_on_empty_or_whitespace_only_query(query_text: str) -> None:
    provider = _make_provider()
    registry = RetrievalRegistry([provider])
    service = _make_service(registry=registry)

    # RetrievalQuery enforces min_length=1 at construction, so an empty
    # string is built via model_copy (which skips validation) to reach
    # the service's own validation instead of pydantic's.
    query = RetrievalQuery(query="x").model_copy(update={"query": query_text})

    with pytest.raises(RetrievalValidationError, match="cannot be empty"):
        await service.search(
            provider=RetrievalProvider.QDRANT,
            query=query,
        )

    provider.search.assert_not_awaited()


async def test_search_raises_when_query_exceeds_max_length() -> None:
    provider = _make_provider()
    registry = RetrievalRegistry([provider])
    service = _make_service(registry=registry)
    long_query = "a" * (RetrievalService.MAX_QUERY_LENGTH + 1)

    with pytest.raises(RetrievalValidationError, match="maximum length"):
        await service.search(
            provider=RetrievalProvider.QDRANT,
            query=RetrievalQuery(query=long_query),
        )

    provider.search.assert_not_awaited()


async def test_search_raises_when_top_k_is_not_positive() -> None:
    provider = _make_provider()
    registry = RetrievalRegistry([provider])
    service = _make_service(registry=registry)

    with pytest.raises(RetrievalValidationError, match="top_k"):
        await service.search(
            provider=RetrievalProvider.QDRANT,
            query=RetrievalQuery(query="rag", top_k=5).model_copy(update={"top_k": 0}),
        )

    provider.search.assert_not_awaited()


async def test_search_raises_when_provider_not_registered() -> None:
    service = _make_service(registry=RetrievalRegistry([]))

    with pytest.raises(RetrievalProviderNotFoundError):
        await service.search(
            provider=RetrievalProvider.QDRANT,
            query=RetrievalQuery(query="rag"),
        )

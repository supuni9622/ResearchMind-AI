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
- search_hybrid: dense, sparse, and metadata search all run (in
  parallel, via asyncio.gather) and are handed to the fusion service;
  reranking is applied by default and skipped when rerank=False, when
  no reranking service is configured, or when fusion produced no
  chunks -- these are regression tests for a bug where result.chunks
  was only ever reassigned from the reranked result unconditionally,
  so any of those three "don't rerank" paths crashed with an
  UnboundLocalError
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.reranking.enums import RerankingProvider
from app.ai.knowledge.reranking.models import RerankedChunk, RerankingResult
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
    sparse_result: RetrievalResult | None = None,
    metadata_result: RetrievalResult | None = None,
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

    if sparse_result is not None:
        provider.search_sparse = AsyncMock(return_value=sparse_result)
    else:
        provider.search_sparse = AsyncMock(
            side_effect=lambda **kwargs: RetrievalResult(
                query=kwargs["query"],
                execution=RetrievalExecution(),
                chunks=[_make_chunk()],
            )
        )

    if metadata_result is not None:
        provider.search_metadata = AsyncMock(return_value=metadata_result)
    else:
        # No metadata filters by default: an empty result, mirroring
        # QdrantRetrievalProvider.search_metadata's own short-circuit.
        provider.search_metadata = AsyncMock(
            side_effect=lambda **kwargs: RetrievalResult(
                query=kwargs["query"],
                execution=RetrievalExecution(),
                chunks=[],
            )
        )

    return provider


def _make_query_embedding_service(vector: list[float] | None = None) -> AsyncMock:
    service = AsyncMock()
    service.embed = AsyncMock(return_value=vector or [0.1, 0.2, 0.3])
    return service


def _make_sparse_query_embedding_service() -> AsyncMock:
    service = AsyncMock()
    service.embed = AsyncMock(return_value=SimpleNamespace(indices=[1, 2], values=[0.1, 0.2]))
    return service


def _make_fusion_service(fused: RetrievalResult | None = None) -> AsyncMock:
    service = AsyncMock()
    if fused is not None:
        service.fuse = AsyncMock(return_value=fused)
    else:
        service.fuse = AsyncMock(
            side_effect=lambda *, dense, sparse, top_k, metadata=None: RetrievalResult(
                query=dense.query,
                execution=RetrievalExecution(),
                chunks=(dense.chunks + sparse.chunks + (metadata.chunks if metadata else []))[
                    :top_k
                ],
            )
        )
    return service


def _make_service(
    *,
    registry: RetrievalRegistry,
    query_embedding_service: AsyncMock | None = None,
    sparse_query_embedding_service: AsyncMock | None = None,
    fusion_service: AsyncMock | None = None,
    reranking_service: AsyncMock | None = None,
) -> RetrievalService:
    return RetrievalService(
        registry=registry,
        query_embedding_service=(query_embedding_service or _make_query_embedding_service()),
        sparse_query_embedding_service=(sparse_query_embedding_service or AsyncMock()),
        fusion_service=(fusion_service or AsyncMock()),
        reranking_service=reranking_service,
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


def _make_reranking_service(reranked_order: list[RetrievedChunk]) -> AsyncMock:
    service = AsyncMock()
    service.rerank = AsyncMock(
        return_value=RerankingResult(
            chunks=[RerankedChunk(chunk=chunk, rerank_score=1.0) for chunk in reranked_order],
            duration_ms=1.0,
        )
    )
    return service


async def test_search_metadata_returns_result_with_statistics() -> None:
    chunk = _make_chunk()
    provider = _make_provider(
        metadata_result=RetrievalResult(
            query=RetrievalQuery(query="rag"),
            execution=RetrievalExecution(),
            chunks=[chunk],
        ),
    )
    registry = RetrievalRegistry([provider])
    service = _make_service(registry=registry)

    result = await service.search_metadata(
        provider=RetrievalProvider.QDRANT,
        query=RetrievalQuery(query="rag", top_k=5, filters={"owner_id": "owner-1"}),
    )

    provider.search_metadata.assert_awaited_once()
    assert result.chunks == [chunk]
    assert result.statistics is not None
    assert result.statistics.strategy == RetrievalStrategy.METADATA
    assert result.statistics.duration_ms >= 0
    assert result.statistics.returned_chunks == 1


async def test_search_hybrid_runs_dense_sparse_and_metadata_then_fuses() -> None:
    dense_chunk = _make_chunk()
    sparse_chunk = _make_chunk()
    metadata_chunk = _make_chunk()
    provider = _make_provider(
        result=RetrievalResult(
            query=RetrievalQuery(query="rag"),
            execution=RetrievalExecution(),
            chunks=[dense_chunk],
        ),
        sparse_result=RetrievalResult(
            query=RetrievalQuery(query="rag"),
            execution=RetrievalExecution(),
            chunks=[sparse_chunk],
        ),
        metadata_result=RetrievalResult(
            query=RetrievalQuery(query="rag"),
            execution=RetrievalExecution(),
            chunks=[metadata_chunk],
        ),
    )
    fusion_service = _make_fusion_service()
    registry = RetrievalRegistry([provider])
    service = _make_service(registry=registry, fusion_service=fusion_service)

    result = await service.search_hybrid(
        provider=RetrievalProvider.QDRANT,
        query=RetrievalQuery(query="rag", top_k=5),
    )

    provider.search.assert_awaited_once()
    provider.search_sparse.assert_awaited_once()
    provider.search_metadata.assert_awaited_once()
    fusion_service.fuse.assert_awaited_once()
    assert fusion_service.fuse.await_args.kwargs["metadata"].chunks == [metadata_chunk]
    assert result.chunks == [dense_chunk, sparse_chunk, metadata_chunk]
    assert result.statistics is not None
    assert result.statistics.strategy == RetrievalStrategy.HYBRID


async def test_search_hybrid_reranks_by_default_when_configured() -> None:
    fused_chunk = _make_chunk()
    reranked_chunk = _make_chunk()
    provider = _make_provider()
    fusion_service = _make_fusion_service(
        RetrievalResult(
            query=RetrievalQuery(query="rag"),
            execution=RetrievalExecution(),
            chunks=[fused_chunk],
        )
    )
    reranking_service = _make_reranking_service([reranked_chunk])
    registry = RetrievalRegistry([provider])
    service = _make_service(
        registry=registry,
        fusion_service=fusion_service,
        reranking_service=reranking_service,
    )

    result = await service.search_hybrid(
        provider=RetrievalProvider.QDRANT,
        query=RetrievalQuery(query="rag", top_k=5),
    )

    reranking_service.rerank.assert_awaited_once()
    assert reranking_service.rerank.await_args.kwargs["provider"] == RerankingProvider.VOYAGE_AI
    assert reranking_service.rerank.await_args.kwargs["request"].chunks == [fused_chunk]
    assert result.chunks == [reranked_chunk]


async def test_search_hybrid_skips_reranking_when_rerank_is_false() -> None:
    fused_chunk = _make_chunk()
    provider = _make_provider()
    fusion_service = _make_fusion_service(
        RetrievalResult(
            query=RetrievalQuery(query="rag"),
            execution=RetrievalExecution(),
            chunks=[fused_chunk],
        )
    )
    reranking_service = _make_reranking_service([_make_chunk()])
    registry = RetrievalRegistry([provider])
    service = _make_service(
        registry=registry,
        fusion_service=fusion_service,
        reranking_service=reranking_service,
    )

    result = await service.search_hybrid(
        provider=RetrievalProvider.QDRANT,
        query=RetrievalQuery(query="rag", top_k=5),
        rerank=False,
    )

    reranking_service.rerank.assert_not_awaited()
    assert result.chunks == [fused_chunk]


async def test_search_hybrid_skips_reranking_when_no_reranking_service_configured() -> None:
    fused_chunk = _make_chunk()
    provider = _make_provider()
    fusion_service = _make_fusion_service(
        RetrievalResult(
            query=RetrievalQuery(query="rag"),
            execution=RetrievalExecution(),
            chunks=[fused_chunk],
        )
    )
    registry = RetrievalRegistry([provider])
    service = _make_service(
        registry=registry,
        fusion_service=fusion_service,
        reranking_service=None,
    )

    result = await service.search_hybrid(
        provider=RetrievalProvider.QDRANT,
        query=RetrievalQuery(query="rag", top_k=5),
    )

    assert result.chunks == [fused_chunk]


async def test_search_hybrid_populates_component_latencies_from_component_results() -> None:
    provider = _make_provider()
    fusion_service = _make_fusion_service()
    registry = RetrievalRegistry([provider])
    service = _make_service(registry=registry, fusion_service=fusion_service)

    result = await service.search_hybrid(
        provider=RetrievalProvider.QDRANT,
        query=RetrievalQuery(query="rag", top_k=5),
        rerank=False,
    )

    assert result.statistics is not None
    assert result.statistics.dense_latency_ms is not None
    assert result.statistics.dense_latency_ms >= 0
    assert result.statistics.sparse_latency_ms is not None
    assert result.statistics.sparse_latency_ms >= 0
    assert result.statistics.metadata_latency_ms is not None
    assert result.statistics.metadata_latency_ms >= 0
    assert result.statistics.rerank_latency_ms is None
    assert result.statistics.reranker_provider is None


async def test_search_hybrid_populates_rerank_latency_and_provider_when_reranked() -> None:
    fused_chunk = _make_chunk()
    provider = _make_provider()
    fusion_service = _make_fusion_service(
        RetrievalResult(
            query=RetrievalQuery(query="rag"),
            execution=RetrievalExecution(),
            chunks=[fused_chunk],
        )
    )
    reranking_service = _make_reranking_service([_make_chunk()])
    registry = RetrievalRegistry([provider])
    service = _make_service(
        registry=registry,
        fusion_service=fusion_service,
        reranking_service=reranking_service,
    )

    result = await service.search_hybrid(
        provider=RetrievalProvider.QDRANT,
        query=RetrievalQuery(query="rag", top_k=5),
    )

    assert result.statistics is not None
    assert result.statistics.rerank_latency_ms is not None
    assert result.statistics.rerank_latency_ms >= 0
    assert result.statistics.reranker_provider == RerankingProvider.VOYAGE_AI.value


async def test_search_hybrid_skips_reranking_when_fusion_returns_no_chunks() -> None:
    provider = _make_provider()
    fusion_service = _make_fusion_service(
        RetrievalResult(
            query=RetrievalQuery(query="rag"),
            execution=RetrievalExecution(),
            chunks=[],
        )
    )
    reranking_service = _make_reranking_service([_make_chunk()])
    registry = RetrievalRegistry([provider])
    service = _make_service(
        registry=registry,
        fusion_service=fusion_service,
        reranking_service=reranking_service,
    )

    result = await service.search_hybrid(
        provider=RetrievalProvider.QDRANT,
        query=RetrievalQuery(query="rag", top_k=5),
    )

    reranking_service.rerank.assert_not_awaited()
    assert result.chunks == []

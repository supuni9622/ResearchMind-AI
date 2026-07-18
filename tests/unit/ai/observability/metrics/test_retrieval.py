"""
Unit tests for build_retrieval_metrics_snapshot.

Covers:
- Core fields (provider/strategy/retrieved_chunks) are read from the
  RetrievalResult's statistics
- Per-stage latency/reranker fields pass through from RetrievalStatistics
- Fields default to None when result.statistics is unset
- context_build_latency_ms/compressed_chunks/citations_count are only
  populated when a ContextResult is supplied
"""

from __future__ import annotations

import uuid

from app.ai.knowledge.context.citations.models import Citation
from app.ai.knowledge.context.models import (
    ContextResult,
    ContextStatistics,
    PromptContext,
)
from app.ai.knowledge.retrieval.enums import RetrievalProvider, RetrievalStrategy
from app.ai.knowledge.retrieval.models import (
    RetrievalExecution,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStatistics,
    RetrievedChunk,
)
from app.ai.observability.metrics.retrieval import build_retrieval_metrics_snapshot


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


def _make_result(*, statistics: RetrievalStatistics | None = None) -> RetrievalResult:
    return RetrievalResult(
        query=RetrievalQuery(query="rag"),
        execution=RetrievalExecution(),
        statistics=statistics,
        chunks=[_make_chunk()],
    )


async def test_core_fields_are_read_from_statistics() -> None:
    result = _make_result(
        statistics=RetrievalStatistics(
            provider=RetrievalProvider.QDRANT,
            strategy=RetrievalStrategy.HYBRID,
            duration_ms=42.0,
            returned_chunks=1,
        )
    )

    snapshot = build_retrieval_metrics_snapshot(result)

    assert snapshot.retrieval_id == result.retrieval_id
    assert snapshot.provider == RetrievalProvider.QDRANT
    assert snapshot.strategy == RetrievalStrategy.HYBRID
    assert snapshot.retrieved_chunks == 1


async def test_per_stage_latency_and_reranker_pass_through() -> None:
    result = _make_result(
        statistics=RetrievalStatistics(
            provider=RetrievalProvider.QDRANT,
            strategy=RetrievalStrategy.HYBRID,
            duration_ms=42.0,
            returned_chunks=1,
            dense_latency_ms=10.0,
            sparse_latency_ms=5.0,
            rerank_latency_ms=3.0,
            reranker_provider="voyage_ai",
        )
    )

    snapshot = build_retrieval_metrics_snapshot(result)

    assert snapshot.dense_latency_ms == 10.0
    assert snapshot.sparse_latency_ms == 5.0
    assert snapshot.rerank_latency_ms == 3.0
    assert snapshot.reranker_provider == "voyage_ai"


async def test_fields_default_to_none_without_statistics() -> None:
    result = _make_result(statistics=None)

    snapshot = build_retrieval_metrics_snapshot(result)

    assert snapshot.provider is None
    assert snapshot.strategy is None
    assert snapshot.dense_latency_ms is None
    assert snapshot.sparse_latency_ms is None
    assert snapshot.rerank_latency_ms is None
    assert snapshot.reranker_provider is None
    assert snapshot.context_build_latency_ms is None
    assert snapshot.compressed_chunks is None
    assert snapshot.citations_count is None


async def test_context_fields_populate_only_when_context_result_supplied() -> None:
    result = _make_result(
        statistics=RetrievalStatistics(
            provider=RetrievalProvider.QDRANT,
            strategy=RetrievalStrategy.HYBRID,
            duration_ms=42.0,
            returned_chunks=1,
        )
    )

    context = ContextResult(
        prompt_context=PromptContext(
            context="some context",
            chunks=[],
            citations=[
                Citation(citation_id="S1", filename="test.pdf", document_id=uuid.uuid4()),
            ],
        ),
        statistics=ContextStatistics(
            input_chunks=3,
            output_chunks=1,
            compressed_chunks=2,
            duration_ms=15.0,
        ),
    )

    snapshot = build_retrieval_metrics_snapshot(result, context=context)

    assert snapshot.context_build_latency_ms == 15.0
    assert snapshot.compressed_chunks == 2
    assert snapshot.citations_count == 1

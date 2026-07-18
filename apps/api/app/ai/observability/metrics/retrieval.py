"""
Canonical Retrieval Metrics Platform (AI Runtime Observability PRD §5.2).

Mirrors `runtime/generation/observability/models.py::
build_generation_metrics_snapshot` -- a pure derivation from an already
completed `RetrievalResult` (and optionally the `ContextResult` built on
top of it), never recomputing anything the Retrieval/Context platforms
already measured.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.knowledge.context.models import ContextResult
from app.ai.knowledge.retrieval.enums import RetrievalProvider, RetrievalStrategy
from app.ai.knowledge.retrieval.models import RetrievalResult


class RetrievalMetricsSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retrieval_id: UUID

    provider: RetrievalProvider | None = None

    strategy: RetrievalStrategy | None = None

    #
    # Performance
    #

    dense_latency_ms: float | None = None

    sparse_latency_ms: float | None = None

    rerank_latency_ms: float | None = None

    context_build_latency_ms: float | None = None

    #
    # Volume
    #

    retrieved_chunks: int

    expanded_chunks: int | None = None
    """
    Not tracked by `ContextBuilderService` today -- parent expansion
    enriches chunks in place rather than reporting a before/after delta.
    Left `None` rather than fabricated (Engineering Guidelines §13).
    """

    compressed_chunks: int | None = None

    citations_count: int | None = None

    #
    # Providers
    #

    reranker_provider: str | None = None

    compression_provider: str | None = None
    """
    Not carried on `ContextResult` -- `ContextBuilderService` always runs
    a fixed compression pipeline (embedding-redundancy -> optional
    LangChain contextual -> token-budget) rather than a single selectable
    provider, so there's no one result-level value to read here yet.
    """

    guardrail_provider: str | None = None
    """Same gap as `compression_provider` -- `ContextGuardrailService`'s
    strategy isn't recorded on `ContextResult`."""


def build_retrieval_metrics_snapshot(
    result: RetrievalResult,
    *,
    context: ContextResult | None = None,
) -> RetrievalMetricsSnapshot:
    """
    Pure derivation of a `RetrievalMetricsSnapshot` from a completed
    `RetrievalResult`, optionally enriched with the `ContextResult` built
    from it (context-build latency, compression/citation counts). No side
    effects, no recording -- shared by any future recorder/artifact
    builder the same way `build_generation_metrics_snapshot` is.
    """

    statistics = result.statistics

    context_statistics = context.statistics if context is not None else None

    return RetrievalMetricsSnapshot(
        retrieval_id=result.retrieval_id,
        provider=(statistics.provider if statistics else None),
        strategy=(statistics.strategy if statistics else None),
        dense_latency_ms=(statistics.dense_latency_ms if statistics else None),
        sparse_latency_ms=(statistics.sparse_latency_ms if statistics else None),
        rerank_latency_ms=(statistics.rerank_latency_ms if statistics else None),
        context_build_latency_ms=(context_statistics.duration_ms if context_statistics else None),
        retrieved_chunks=len(result.chunks),
        compressed_chunks=(context_statistics.compressed_chunks if context_statistics else None),
        citations_count=(len(context.prompt_context.citations) if context is not None else None),
        reranker_provider=(statistics.reranker_provider if statistics else None),
    )

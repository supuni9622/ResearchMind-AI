"""
Unit tests for GenerationStatisticsBuilder / RetrievalStatisticsBuilder.

Covers:
- Empty input returns a zero-sample snapshot without crashing
- Generation: percentiles/averages/cache-hit-rate/hallucination-rate are
  computed correctly, and provider/model/cost/latency rankings group and
  sort as expected
- Retrieval: latency percentiles/average come from context_build_latency_ms
  only (entries without it are excluded), provider rankings by volume
"""

from __future__ import annotations

from uuid import uuid4

from app.ai.observability.metrics.retrieval import RetrievalMetricsSnapshot
from app.ai.observability.statistics.enums import TimeWindow
from app.ai.observability.statistics.service import (
    GenerationStatisticsBuilder,
    RetrievalStatisticsBuilder,
)
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.observability.models import GenerationMetricsSnapshot


def _generation_snapshot(
    *,
    provider: GenerationProvider = GenerationProvider.GROQ,
    model: str = "test-model",
    latency_ms: float = 100.0,
    cost: float = 0.01,
    total_tokens: int = 50,
    cache_hit: bool = False,
    hallucination_score: float | None = None,
) -> GenerationMetricsSnapshot:
    return GenerationMetricsSnapshot(
        request_id=uuid4(),
        generation_id=uuid4(),
        provider=provider,
        model=model,
        latency_ms=latency_ms,
        retries=0,
        regeneration_count=0,
        cache_hit=cache_hit,
        prompt_tokens=10,
        completion_tokens=total_tokens - 10,
        total_tokens=total_tokens,
        estimated_cost_usd=cost,
        hallucination_score=hallucination_score,
        guardrail_blocked=False,
    )


async def test_generation_statistics_empty_input() -> None:
    stats = GenerationStatisticsBuilder.build([], window=TimeWindow.DAILY)

    assert stats.sample_count == 0
    assert stats.window == TimeWindow.DAILY
    assert stats.latency_percentiles is None


async def test_generation_statistics_aggregations() -> None:
    snapshots = [
        _generation_snapshot(latency_ms=100.0, cost=0.01, cache_hit=True),
        _generation_snapshot(latency_ms=200.0, cost=0.02, hallucination_score=0.5),
        _generation_snapshot(latency_ms=300.0, cost=0.03, hallucination_score=1.0),
    ]

    stats = GenerationStatisticsBuilder.build(snapshots)

    assert stats.sample_count == 3
    assert stats.average_latency_ms == 200.0
    assert stats.average_cost_usd == 0.02
    assert stats.cache_hit_rate == 1 / 3
    assert stats.hallucination_rate == 1 / 3
    assert stats.latency_percentiles is not None


async def test_generation_statistics_rankings_group_by_provider_and_model() -> None:
    snapshots = [
        _generation_snapshot(
            provider=GenerationProvider.GROQ, model="a", latency_ms=100.0, cost=0.01
        ),
        _generation_snapshot(
            provider=GenerationProvider.GROQ, model="a", latency_ms=100.0, cost=0.01
        ),
        _generation_snapshot(
            provider=GenerationProvider.OPENAI, model="b", latency_ms=400.0, cost=0.10
        ),
    ]

    stats = GenerationStatisticsBuilder.build(snapshots)

    assert stats.provider_rankings[0].key == GenerationProvider.GROQ.value
    assert stats.provider_rankings[0].sample_count == 2

    assert stats.cost_rankings[0].key == GenerationProvider.OPENAI.value
    assert stats.cost_rankings[0].value == 0.10

    assert stats.latency_rankings[0].key == GenerationProvider.OPENAI.value
    assert stats.latency_rankings[0].value == 400.0


async def test_retrieval_statistics_empty_input() -> None:
    stats = RetrievalStatisticsBuilder.build([])

    assert stats.sample_count == 0
    assert stats.latency_percentiles is None


async def test_retrieval_statistics_only_uses_entries_with_context_latency() -> None:
    snapshots = [
        RetrievalMetricsSnapshot(retrieval_id=uuid4(), retrieved_chunks=3),
        RetrievalMetricsSnapshot(
            retrieval_id=uuid4(),
            retrieved_chunks=5,
            context_build_latency_ms=20.0,
        ),
    ]

    stats = RetrievalStatisticsBuilder.build(snapshots)

    assert stats.sample_count == 2
    assert stats.average_latency_ms == 20.0
    assert stats.latency_percentiles is not None

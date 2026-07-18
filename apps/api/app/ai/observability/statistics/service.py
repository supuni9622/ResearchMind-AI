"""
Domain-specific Statistics Platform builders (AI Runtime Observability
PRD §6). Each builder turns a caller-supplied collection of one domain's
metrics snapshots into a `StatisticsSnapshot` -- pure aggregation, no I/O,
no recomputation of anything the snapshots don't already carry.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.ai.observability.metrics.retrieval import RetrievalMetricsSnapshot
from app.ai.observability.statistics.aggregator import (
    average,
    compute_percentiles,
    rank_by_average,
    rank_by_count,
    rate,
)
from app.ai.observability.statistics.enums import TimeWindow
from app.ai.observability.statistics.models import StatisticsSnapshot
from app.ai.runtime.generation.observability.models import GenerationMetricsSnapshot


class GenerationStatisticsBuilder:
    """Aggregates a batch of `GenerationMetricsSnapshot`s."""

    @staticmethod
    def build(
        snapshots: Sequence[GenerationMetricsSnapshot],
        *,
        window: TimeWindow | None = None,
    ) -> StatisticsSnapshot:

        sample_count = len(snapshots)

        if sample_count == 0:
            return StatisticsSnapshot(window=window, sample_count=0)

        latencies = [snapshot.latency_ms for snapshot in snapshots]
        costs = [snapshot.estimated_cost_usd for snapshot in snapshots]
        tokens = [float(snapshot.total_tokens) for snapshot in snapshots]

        cache_hits = sum(1 for snapshot in snapshots if snapshot.cache_hit)

        hallucinations = sum(
            1
            for snapshot in snapshots
            if snapshot.hallucination_score is not None and snapshot.hallucination_score < 1.0
        )

        provider_groups: dict[str, list[float]] = {}
        model_groups: dict[str, list[float]] = {}
        cost_by_provider: dict[str, list[float]] = {}
        latency_by_provider: dict[str, list[float]] = {}

        for snapshot in snapshots:
            provider_groups.setdefault(snapshot.provider.value, []).append(1.0)
            model_groups.setdefault(snapshot.model, []).append(1.0)
            cost_by_provider.setdefault(snapshot.provider.value, []).append(
                snapshot.estimated_cost_usd
            )
            latency_by_provider.setdefault(snapshot.provider.value, []).append(snapshot.latency_ms)

        return StatisticsSnapshot(
            window=window,
            sample_count=sample_count,
            latency_percentiles=compute_percentiles(latencies),
            average_latency_ms=average(latencies),
            average_cost_usd=average(costs),
            average_tokens=average(tokens),
            cache_hit_rate=rate(matching=cache_hits, total=sample_count),
            hallucination_rate=rate(matching=hallucinations, total=sample_count),
            provider_rankings=rank_by_count(provider_groups),
            model_rankings=rank_by_count(model_groups),
            cost_rankings=rank_by_average(cost_by_provider),
            latency_rankings=rank_by_average(latency_by_provider),
        )


class RetrievalStatisticsBuilder:
    """Aggregates a batch of `RetrievalMetricsSnapshot`s."""

    @staticmethod
    def build(
        snapshots: Sequence[RetrievalMetricsSnapshot],
        *,
        window: TimeWindow | None = None,
    ) -> StatisticsSnapshot:

        sample_count = len(snapshots)

        if sample_count == 0:
            return StatisticsSnapshot(window=window, sample_count=0)

        latencies = [
            snapshot.context_build_latency_ms
            for snapshot in snapshots
            if snapshot.context_build_latency_ms is not None
        ]

        provider_groups: dict[str, list[float]] = {}

        for snapshot in snapshots:
            if snapshot.provider is not None:
                provider_groups.setdefault(snapshot.provider.value, []).append(1.0)

        return StatisticsSnapshot(
            window=window,
            sample_count=sample_count,
            latency_percentiles=(compute_percentiles(latencies) if latencies else None),
            average_latency_ms=average(latencies),
            provider_rankings=rank_by_count(provider_groups),
        )

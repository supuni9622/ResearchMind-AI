"""
Canonical Statistics Platform models (AI Runtime Observability PRD §6, §9
`StatisticsSnapshot`).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.ai.observability.statistics.enums import TimeWindow


class PercentileStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p50: float
    p90: float
    p95: float
    p99: float


class RankingEntry(BaseModel):
    """One row of a provider/model/cost/latency ranking table."""

    model_config = ConfigDict(extra="forbid")

    key: str
    """Provider name, model name, etc. -- whatever the ranking groups by."""

    value: float
    """The ranked metric's value for this key (meaning depends on which
    ranking list this entry lives in -- see `StatisticsSnapshot` field
    docs)."""

    sample_count: int


class StatisticsSnapshot(BaseModel):
    """
    Aggregate runtime statistics computed over a caller-supplied collection
    of metrics snapshots (PRD §9). Deliberately has no persistence-backed
    "give me last week's stats" query -- this phase has no metrics store
    to query (Non-Goals §4 defers Prometheus/Grafana-style infrastructure);
    callers assemble the snapshot list themselves (e.g. from a batch of
    `GenerationArtifact.metrics` reads) and this model just shapes the
    aggregation.
    """

    model_config = ConfigDict(extra="forbid")

    window: TimeWindow | None = None

    sample_count: int

    #
    # Percentiles
    #

    latency_percentiles: PercentileStats | None = None

    #
    # Aggregations
    #

    average_latency_ms: float | None = None

    average_cost_usd: float | None = None

    average_tokens: float | None = None

    average_ttft_ms: float | None = None

    average_tps: float | None = None

    error_rate: float | None = None
    """
    `None` for Generation statistics today: `GenerationMetricsService.
    record()` only ever runs on a successful `GenerationResult` (failed
    `generate()` calls raise before reaching it), so a collection of
    `GenerationMetricsSnapshot`s structurally can't carry failures to
    compute a rate from. Left as a real field for whichever caller
    aggregates over a superset that does include failures.
    """

    cache_hit_rate: float | None = None

    hallucination_rate: float | None = None

    #
    # Provider Statistics
    #

    provider_rankings: list[RankingEntry] = []
    """Ranked by request volume, descending."""

    model_rankings: list[RankingEntry] = []
    """Ranked by request volume, descending."""

    cost_rankings: list[RankingEntry] = []
    """Ranked by average `estimated_cost_usd`, descending."""

    latency_rankings: list[RankingEntry] = []
    """Ranked by average `latency_ms`, descending."""

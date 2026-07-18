"""
Generic aggregation primitives shared by every domain-specific statistics
builder (`service.py`). Pure functions only -- no knowledge of Generation/
Retrieval/Streaming snapshot shapes.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import ceil, floor

from app.ai.observability.statistics.models import PercentileStats, RankingEntry


def percentile(values: Sequence[float], p: float) -> float:
    """
    Linear-interpolation percentile (same method as numpy's default
    `interpolation="linear"`), `p` in `[0, 100]`. Returns `0.0` for an
    empty sequence rather than raising -- callers already guard on
    `sample_count` before reading percentiles.
    """

    if not values:
        return 0.0

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    rank = (len(ordered) - 1) * (p / 100)

    lower = floor(rank)
    upper = ceil(rank)

    if lower == upper:
        return ordered[int(rank)]

    fraction = rank - lower

    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def compute_percentiles(values: Sequence[float]) -> PercentileStats:
    """Builds the PRD §6 `p50/p90/p95/p99` set from a value sequence."""

    return PercentileStats(
        p50=percentile(values, 50),
        p90=percentile(values, 90),
        p95=percentile(values, 95),
        p99=percentile(values, 99),
    )


def average(values: Sequence[float]) -> float | None:
    return (sum(values) / len(values)) if values else None


def rate(*, matching: int, total: int) -> float | None:
    return (matching / total) if total else None


def rank_by_count(groups: dict[str, list[float]]) -> list[RankingEntry]:
    """Ranks groups by member count, descending. `values` per group are
    unused for the ranking itself but carried as `sample_count`."""

    return sorted(
        (
            RankingEntry(key=key, value=float(len(values)), sample_count=len(values))
            for key, values in groups.items()
        ),
        key=lambda entry: entry.value,
        reverse=True,
    )


def rank_by_average(groups: dict[str, list[float]]) -> list[RankingEntry]:
    """Ranks groups by their average value, descending."""

    return sorted(
        (
            RankingEntry(
                key=key,
                value=(sum(values) / len(values)),
                sample_count=len(values),
            )
            for key, values in groups.items()
            if values
        ),
        key=lambda entry: entry.value,
        reverse=True,
    )

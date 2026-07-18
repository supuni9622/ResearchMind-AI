"""
Unit tests for the Statistics Platform's generic aggregation primitives.

Covers:
- percentile() on known distributions (p50 == median, p100 == max)
- percentile() returns 0.0 for an empty sequence
- compute_percentiles() builds all four PRD percentiles
- average()/rate() handle the empty-input case without dividing by zero
- rank_by_count()/rank_by_average() sort descending
"""

from __future__ import annotations

import pytest
from app.ai.observability.statistics.aggregator import (
    average,
    compute_percentiles,
    percentile,
    rank_by_average,
    rank_by_count,
    rate,
)


async def test_percentile_of_empty_sequence_is_zero() -> None:
    assert percentile([], 50) == 0.0


async def test_percentile_p50_is_the_median_for_odd_length() -> None:
    assert percentile([1.0, 2.0, 3.0], 50) == 2.0


async def test_percentile_p100_is_the_max() -> None:
    values = [1.0, 5.0, 9.0, 20.0]
    assert percentile(values, 100) == 20.0


async def test_percentile_p0_is_the_min() -> None:
    values = [1.0, 5.0, 9.0, 20.0]
    assert percentile(values, 0) == 1.0


async def test_compute_percentiles_builds_all_four_fields() -> None:
    values = [float(i) for i in range(1, 101)]

    stats = compute_percentiles(values)

    assert stats.p50 == pytest.approx(50.5)
    assert stats.p90 == pytest.approx(90.1)
    assert stats.p95 == pytest.approx(95.05)
    assert stats.p99 == pytest.approx(99.01)


async def test_average_of_empty_sequence_is_none() -> None:
    assert average([]) is None


async def test_average_computes_the_mean() -> None:
    assert average([1.0, 2.0, 3.0]) == 2.0


async def test_rate_of_zero_total_is_none() -> None:
    assert rate(matching=0, total=0) is None


async def test_rate_computes_the_fraction() -> None:
    assert rate(matching=1, total=4) == 0.25


async def test_rank_by_count_sorts_descending_by_group_size() -> None:
    groups = {"a": [1.0], "b": [1.0, 1.0, 1.0], "c": [1.0, 1.0]}

    rankings = rank_by_count(groups)

    assert [entry.key for entry in rankings] == ["b", "c", "a"]
    assert rankings[0].value == 3.0
    assert rankings[0].sample_count == 3


async def test_rank_by_average_sorts_descending_by_mean_value() -> None:
    groups = {"a": [1.0, 1.0], "b": [10.0, 10.0], "c": [5.0]}

    rankings = rank_by_average(groups)

    assert [entry.key for entry in rankings] == ["b", "c", "a"]
    assert rankings[0].value == 10.0

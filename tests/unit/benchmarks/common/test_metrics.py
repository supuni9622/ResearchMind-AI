"""
Unit tests for shared benchmark statistical helpers.

Covers:
- average() computes the arithmetic mean and returns 0.0 for empty input
- percentile() selects the nearest-rank value and returns 0.0 for empty
  input
"""

from __future__ import annotations

from benchmarks.common.metrics import average, percentile


def test_average_computes_arithmetic_mean() -> None:
    assert average([1.0, 2.0, 3.0]) == 2.0


def test_average_returns_zero_for_empty_input() -> None:
    assert average([]) == 0.0


def test_percentile_selects_nearest_rank_value() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0]

    assert percentile(values, 0.0) == 10.0
    assert percentile(values, 0.95) == 50.0


def test_percentile_returns_zero_for_empty_input() -> None:
    assert percentile([], 0.95) == 0.0

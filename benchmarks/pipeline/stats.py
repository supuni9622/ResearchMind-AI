"""
Descriptive statistics helpers for aggregating benchmark measurements.
"""

from __future__ import annotations

import statistics

from benchmarks.pipeline.models import StatSummary


def summarize(values: list[float]) -> StatSummary:
    """
    Compute average / minimum / maximum / median / P95 for a metric.
    """

    if not values:
        raise ValueError("Cannot summarize an empty list of values.")

    ordered = sorted(values)

    return StatSummary(
        average=statistics.fmean(ordered),
        minimum=ordered[0],
        maximum=ordered[-1],
        median=statistics.median(ordered),
        p95=_percentile(ordered, 95),
    )


def _percentile(ordered_values: list[float], percentile: float) -> float:
    """
    Linear-interpolation percentile over an already-sorted list.
    """

    if len(ordered_values) == 1:
        return ordered_values[0]

    rank = (percentile / 100) * (len(ordered_values) - 1)
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(ordered_values) - 1)
    fraction = rank - lower_index

    return (
        ordered_values[lower_index]
        + (ordered_values[upper_index] - ordered_values[lower_index]) * fraction
    )

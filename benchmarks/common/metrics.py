"""
Shared statistical helpers for benchmark candidates.

Framework-independent so they can be unit tested without a running
benchmark stack.
"""

from __future__ import annotations


def average(values: list[float]) -> float:
    """
    Arithmetic mean, rounded to 4 decimal places.

    Returns 0.0 for an empty list rather than raising.
    """

    if not values:
        return 0.0

    return round(sum(values) / len(values), 4)


def percentile(
    values: list[float],
    rank: float,
) -> float:
    """
    Nearest-rank percentile (e.g. rank=0.95 for P95).

    Returns 0.0 for an empty list rather than raising.
    """

    if not values:
        return 0.0

    ordered = sorted(values)
    index = min(
        int(len(ordered) * rank),
        len(ordered) - 1,
    )

    return ordered[index]

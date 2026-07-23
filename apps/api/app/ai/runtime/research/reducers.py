"""Deterministic reducers for later parallel Research Runtime nodes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def merge_by_stable_id(
    existing: Mapping[str, dict[str, Any]] | None,
    incoming: Mapping[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """Merge keyed results without duplicate append semantics.

    Retrying an identical task update is a no-op. A conflicting update is
    rejected instead of silently selecting an execution-order-dependent value.
    """

    merged = dict(existing or {})
    for key, value in (incoming or {}).items():
        if key in merged and merged[key] != value:
            raise ValueError(f"Conflicting update for stable id '{key}'.")
        merged[key] = value
    return merged


def merge_non_decreasing_usage(
    existing: Mapping[str, int | float] | None,
    incoming: Mapping[str, int | float] | None,
) -> dict[str, int | float]:
    """Merge monotonic budget counters while rejecting invalid decrements."""

    merged = dict(existing or {})
    for key, value in (incoming or {}).items():
        if value < merged.get(key, 0):
            raise ValueError(f"Budget usage for '{key}' cannot decrease.")
        merged[key] = value
    return merged

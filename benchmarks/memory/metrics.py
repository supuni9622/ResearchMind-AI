"""Pure M6 metrics for retrieval quality, selection harm, and isolation."""

from __future__ import annotations

from benchmarks.retrieval.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * percentile_value)))
    return ordered[index]


def selection_rate(selected: list[str], flagged: set[str]) -> float:
    if not selected:
        return 0.0
    return len(set(selected) & flagged) / len(selected)


__all__ = [
    "average",
    "ndcg_at_k",
    "percentile",
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank",
    "selection_rate",
]

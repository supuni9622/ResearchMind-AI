"""
Regression thresholds.

Per-metric rules for what counts as a regression (PRD §18 example
rules: MRR_DROP_THRESHOLD=0.05, FAITHFULNESS_THRESHOLD=0.03,
LATENCY_THRESHOLD=0.25). Expressed as a lookup table keyed by metric
name so new benchmarks/metrics can opt in without touching
`detector.py`; a metric absent from this table is simply never checked.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ThresholdDirection(StrEnum):
    """
    How a metric is allowed to move between runs before it counts as a
    regression.
    """

    MIN_DROP = "min_drop"
    """Higher is better. Regressed if current < previous - threshold."""

    MAX_INCREASE = "max_increase"
    """Lower is better, absolute scale (e.g. a 0-1 rate).

    Regressed if current > previous + threshold.
    """

    MAX_RELATIVE_INCREASE = "max_relative_increase"
    """Lower is better, unbounded scale (e.g. latency_ms).

    Regressed if current > previous * (1 + threshold).
    """


@dataclass(frozen=True)
class MetricThreshold:
    direction: ThresholdDirection
    threshold: float


_QUALITY_DROP = MetricThreshold(ThresholdDirection.MIN_DROP, 0.05)
_GENERATION_QUALITY_DROP = MetricThreshold(ThresholdDirection.MIN_DROP, 0.03)
_LATENCY_INCREASE = MetricThreshold(ThresholdDirection.MAX_RELATIVE_INCREASE, 0.25)

DEFAULT_METRIC_THRESHOLDS: dict[str, MetricThreshold] = {
    # Retrieval (PRD §14 / ADR-020).
    "recall_at_5": _QUALITY_DROP,
    "recall_at_10": _QUALITY_DROP,
    "recall_at_20": _QUALITY_DROP,
    "precision_at_5": _QUALITY_DROP,
    "precision_at_10": _QUALITY_DROP,
    "ndcg_at_5": _QUALITY_DROP,
    "ndcg_at_10": _QUALITY_DROP,
    "mrr": _QUALITY_DROP,
    # Generation (PRD §15).
    "faithfulness": _GENERATION_QUALITY_DROP,
    "groundedness": _GENERATION_QUALITY_DROP,
    "relevance": _GENERATION_QUALITY_DROP,
    "completeness": _GENERATION_QUALITY_DROP,
    "citation_accuracy": _GENERATION_QUALITY_DROP,
    "hallucination_rate": MetricThreshold(ThresholdDirection.MAX_INCREASE, 0.03),
    # Latency, any benchmark.
    "avg_latency_ms": _LATENCY_INCREASE,
    "p95_latency_ms": _LATENCY_INCREASE,
    "p99_latency_ms": _LATENCY_INCREASE,
}

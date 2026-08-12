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

    The first three directions are *relative* -- they compare the
    current run against the previous one, appropriate for fuzzy/
    LLM-judged metrics where there's no calibrated sense yet of what a
    good absolute score looks like (EVALUATION_PLAN.md §13). The last
    two are *absolute* -- they compare the current run against a fixed
    bound regardless of what the previous run scored, reserved for
    metrics where §13 explicitly decided a hard line is safe: deterministic
    checks with no LLM-judge noise to calibrate against (citation
    validity, schema validity, abstention pass rate).
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

    ABSOLUTE_MIN = "absolute_min"
    """Fixed floor, independent of the previous run's value.

    Regressed if current < threshold (`threshold` is the floor itself,
    not a delta -- e.g. abstention_pass_rate's floor is 0.95, so
    `MetricThreshold(ABSOLUTE_MIN, 0.95)`).
    """

    ABSOLUTE_MAX = "absolute_max"
    """Fixed ceiling, independent of the previous run's value.

    Regressed if current > threshold (`threshold` is the ceiling itself
    -- e.g. fabricated_citation_rate's ceiling is 0.0, so
    `MetricThreshold(ABSOLUTE_MAX, 0.0)`).
    """


@dataclass(frozen=True)
class MetricThreshold:
    direction: ThresholdDirection
    threshold: float


_QUALITY_DROP = MetricThreshold(ThresholdDirection.MIN_DROP, 0.05)
_GENERATION_QUALITY_DROP = MetricThreshold(ThresholdDirection.MIN_DROP, 0.03)
_UNBOUNDED_INCREASE = MetricThreshold(ThresholdDirection.MAX_RELATIVE_INCREASE, 0.25)
"""Shared 25% relative-increase threshold for any unbounded, lower-is-better
metric (latency, cost)."""

DEFAULT_METRIC_THRESHOLDS: dict[str, MetricThreshold] = {
    # Retrieval (PRD §14 / ADR-020).
    "recall_at_5": _QUALITY_DROP,
    "recall_at_10": _QUALITY_DROP,
    "recall_at_20": _QUALITY_DROP,
    "precision_at_5": _QUALITY_DROP,
    "precision_at_10": _QUALITY_DROP,
    "ndcg_at_5": _QUALITY_DROP,
    "ndcg_at_10": _QUALITY_DROP,
    "hit_rate_at_5": _QUALITY_DROP,
    "hit_rate_at_10": _QUALITY_DROP,
    "mrr": _QUALITY_DROP,
    # Generation (PRD §15).
    "faithfulness": _GENERATION_QUALITY_DROP,
    "groundedness": _GENERATION_QUALITY_DROP,
    "relevance": _GENERATION_QUALITY_DROP,
    "completeness": _GENERATION_QUALITY_DROP,
    "citation_accuracy": _GENERATION_QUALITY_DROP,
    "hallucination_rate": MetricThreshold(ThresholdDirection.MAX_INCREASE, 0.03),
    # E16's rubric-adherence judge -- same relative-drop treatment as the
    # other LLM-judged generation metrics above, not an absolute gate
    # (no calibrated sense yet of what a good absolute score looks like,
    # same §13 reasoning).
    "rubric_adherence": _GENERATION_QUALITY_DROP,
    # Ingestion fidelity (EVALUATION_PLAN.md §4).
    "parse_success_rate": _QUALITY_DROP,
    "heading_preservation_score": _QUALITY_DROP,
    "table_preservation_score": _QUALITY_DROP,
    # Latency, any benchmark.
    "avg_latency_ms": _UNBOUNDED_INCREASE,
    "p95_latency_ms": _UNBOUNDED_INCREASE,
    "p99_latency_ms": _UNBOUNDED_INCREASE,
    # Cost (Generation).
    "avg_cost_usd": _UNBOUNDED_INCREASE,
    "cost_per_query": _UNBOUNDED_INCREASE,
    "cost_per_1k_queries": _UNBOUNDED_INCREASE,
    # Absolute gates (EVALUATION_PLAN.md §13) -- deterministic checks with
    # no LLM-judge noise to calibrate against, so a hard line is safe
    # rather than a relative "no worse than last run" comparison.
    #
    # `fabricated_citation_rate` is produced today by
    # `check_citation_validity()`/`check_prompt_context_citation_validity()`
    # (app/ai/knowledge/context/citations/validity.py, EVALUATION_IMPLEMENTATION_TRACKER.md
    # E4) -- not yet emitted into a BenchmarkReport by any benchmark, since
    # that requires the golden dataset (E1) to run it against. Declaring
    # the gate now means E1/E5 only need to start emitting the metric
    # name, not also design its threshold.
    "fabricated_citation_rate": MetricThreshold(ThresholdDirection.ABSOLUTE_MAX, 0.0),
    # `schema_validity_rate` -- fraction of responses passing
    # SchemaValidator (generation/validation/output/schema_validator.py,
    # already live and blocking at generation time) -- not yet aggregated
    # into a rate anywhere; same "declare the gate, populate later" logic.
    "schema_validity_rate": MetricThreshold(ThresholdDirection.ABSOLUTE_MIN, 1.0),
    # `abstention_pass_rate` -- fraction of the golden set's unanswerable-
    # query subset correctly abstaining rather than answering with
    # unwarranted certainty. Needs E1's golden set to exist at all.
    "abstention_pass_rate": MetricThreshold(ThresholdDirection.ABSOLUTE_MIN, 0.95),
}

"""
Unit tests for `RegressionDetector` (EVALUATION_PLAN.md §13).

Covers all five `ThresholdDirection` variants:
- MIN_DROP / MAX_INCREASE / MAX_RELATIVE_INCREASE: the pre-existing
  relative gates, previously untested at the unit level
- ABSOLUTE_MIN / ABSOLUTE_MAX: the new fixed-bound gates added for §13's
  deterministic-check absolute gates (citation validity, schema
  validity, abstention pass rate)
- A candidate present only in one report is skipped, not flagged
- An absolute gate applies even on a metric's first-ever run (no
  baseline value to compare against), unlike a relative gate
"""

from __future__ import annotations

from benchmarks.models.report import BenchmarkCandidate, BenchmarkDataset, BenchmarkReport
from benchmarks.regression.detector import RegressionDetector
from benchmarks.regression.thresholds import MetricThreshold, ThresholdDirection


def _report(
    *,
    benchmark_name: str = "Test",
    candidate_name: str = "Candidate",
    metrics: dict[str, float],
) -> BenchmarkReport:
    return BenchmarkReport(
        benchmark_name=benchmark_name,
        dataset=BenchmarkDataset(name="test-dataset", document_count=1),
        candidates=[BenchmarkCandidate(name=candidate_name, metrics=metrics)],
    )


def test_min_drop_flags_a_metric_that_dropped_beyond_its_threshold() -> None:
    detector = RegressionDetector(
        thresholds={"recall_at_10": MetricThreshold(ThresholdDirection.MIN_DROP, 0.05)}
    )

    result = detector.compare(
        previous=_report(metrics={"recall_at_10": 0.80}),
        current=_report(metrics={"recall_at_10": 0.70}),
    )

    assert not result.passed
    assert result.regressions[0].metric == "recall_at_10"


def test_min_drop_tolerates_a_drop_within_the_threshold() -> None:
    detector = RegressionDetector(
        thresholds={"recall_at_10": MetricThreshold(ThresholdDirection.MIN_DROP, 0.05)}
    )

    result = detector.compare(
        previous=_report(metrics={"recall_at_10": 0.80}),
        current=_report(metrics={"recall_at_10": 0.76}),
    )

    assert result.passed


def test_max_increase_flags_a_metric_that_rose_beyond_its_threshold() -> None:
    detector = RegressionDetector(
        thresholds={"hallucination_rate": MetricThreshold(ThresholdDirection.MAX_INCREASE, 0.03)}
    )

    result = detector.compare(
        previous=_report(metrics={"hallucination_rate": 0.02}),
        current=_report(metrics={"hallucination_rate": 0.10}),
    )

    assert not result.passed


def test_max_relative_increase_flags_a_proportionally_large_jump() -> None:
    detector = RegressionDetector(
        thresholds={
            "p95_latency_ms": MetricThreshold(ThresholdDirection.MAX_RELATIVE_INCREASE, 0.25)
        }
    )

    result = detector.compare(
        previous=_report(metrics={"p95_latency_ms": 100.0}),
        current=_report(metrics={"p95_latency_ms": 200.0}),
    )

    assert not result.passed


def test_max_relative_increase_tolerates_a_small_proportional_jump() -> None:
    detector = RegressionDetector(
        thresholds={
            "p95_latency_ms": MetricThreshold(ThresholdDirection.MAX_RELATIVE_INCREASE, 0.25)
        }
    )

    result = detector.compare(
        previous=_report(metrics={"p95_latency_ms": 100.0}),
        current=_report(metrics={"p95_latency_ms": 110.0}),
    )

    assert result.passed


def test_absolute_max_flags_any_fabricated_citation_rate_above_zero() -> None:
    detector = RegressionDetector(
        thresholds={
            "fabricated_citation_rate": MetricThreshold(ThresholdDirection.ABSOLUTE_MAX, 0.0)
        }
    )

    result = detector.compare(
        previous=_report(metrics={"fabricated_citation_rate": 0.0}),
        current=_report(metrics={"fabricated_citation_rate": 0.02}),
    )

    assert not result.passed
    assert "ceiling" in result.regressions[0].message


def test_absolute_max_passes_at_exactly_the_ceiling() -> None:
    detector = RegressionDetector(
        thresholds={
            "fabricated_citation_rate": MetricThreshold(ThresholdDirection.ABSOLUTE_MAX, 0.0)
        }
    )

    result = detector.compare(
        previous=_report(metrics={"fabricated_citation_rate": 0.0}),
        current=_report(metrics={"fabricated_citation_rate": 0.0}),
    )

    assert result.passed


def test_absolute_min_flags_a_rate_below_the_required_floor() -> None:
    detector = RegressionDetector(
        thresholds={"abstention_pass_rate": MetricThreshold(ThresholdDirection.ABSOLUTE_MIN, 0.95)}
    )

    result = detector.compare(
        previous=_report(metrics={"abstention_pass_rate": 0.97}),
        current=_report(metrics={"abstention_pass_rate": 0.80}),
    )

    assert not result.passed
    assert "floor" in result.regressions[0].message


def test_absolute_gate_applies_even_with_no_baseline_value_to_compare_against() -> None:
    """
    A relative gate is silently skipped when the metric didn't exist in
    the previous run (nothing to compare against). An absolute gate must
    NOT be skipped in that situation -- the whole point is that it holds
    regardless of history, including a metric's first-ever appearance.
    """

    detector = RegressionDetector(
        thresholds={
            "fabricated_citation_rate": MetricThreshold(ThresholdDirection.ABSOLUTE_MAX, 0.0)
        }
    )

    result = detector.compare(
        previous=_report(metrics={}),  # metric didn't exist yet last run
        current=_report(metrics={"fabricated_citation_rate": 0.15}),
    )

    assert not result.passed


def test_relative_gate_is_skipped_with_no_baseline_value_to_compare_against() -> None:
    detector = RegressionDetector(
        thresholds={"recall_at_10": MetricThreshold(ThresholdDirection.MIN_DROP, 0.05)}
    )

    result = detector.compare(
        previous=_report(metrics={}),
        current=_report(metrics={"recall_at_10": 0.50}),
    )

    assert result.passed


def test_a_candidate_present_only_in_the_current_report_is_not_flagged() -> None:
    detector = RegressionDetector(
        thresholds={"recall_at_10": MetricThreshold(ThresholdDirection.MIN_DROP, 0.05)}
    )

    result = detector.compare(
        previous=_report(candidate_name="Old Candidate", metrics={"recall_at_10": 0.90}),
        current=_report(candidate_name="New Candidate", metrics={"recall_at_10": 0.10}),
    )

    assert result.passed

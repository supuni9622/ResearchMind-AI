"""
Regression detector.

Compares a fresh BenchmarkReport against a previously stored one and
flags any metric that crossed its configured threshold (PRD §18).

Candidates present only in one of the two reports are skipped rather
than treated as regressions -- a newly added candidate (e.g. a new
GenerationProvider becoming configured) has no baseline to compare
against.
"""

from __future__ import annotations

from benchmarks.models.report import BenchmarkReport
from benchmarks.regression.models import RegressionIssue, RegressionResult
from benchmarks.regression.thresholds import (
    DEFAULT_METRIC_THRESHOLDS,
    MetricThreshold,
    ThresholdDirection,
)


class RegressionDetector:
    """
    Detects regressions between two benchmark runs.
    """

    def __init__(
        self,
        thresholds: dict[str, MetricThreshold] | None = None,
    ) -> None:
        self._thresholds = thresholds or DEFAULT_METRIC_THRESHOLDS

    def compare(
        self,
        *,
        previous: BenchmarkReport,
        current: BenchmarkReport,
    ) -> RegressionResult:
        """
        Compare `current` against `previous` and report any regressions.
        """

        previous_by_name = {candidate.name: candidate for candidate in previous.candidates}

        issues: list[RegressionIssue] = []

        for candidate in current.candidates:
            previous_candidate = previous_by_name.get(candidate.name)

            if previous_candidate is None:
                continue

            for metric_name, threshold in self._thresholds.items():
                current_value = candidate.metrics.get(metric_name)
                previous_value = previous_candidate.metrics.get(metric_name)

                if not isinstance(current_value, (int, float)) or not isinstance(
                    previous_value, (int, float)
                ):
                    continue

                issue = self._check(
                    candidate_name=candidate.name,
                    metric_name=metric_name,
                    previous_value=float(previous_value),
                    current_value=float(current_value),
                    threshold=threshold,
                )

                if issue is not None:
                    issues.append(issue)

        return RegressionResult(
            benchmark_name=current.benchmark_name,
            previous_commit=previous.metadata.git_commit,
            current_commit=current.metadata.git_commit,
            previous_dataset_version=previous.metadata.dataset_version,
            current_dataset_version=current.metadata.dataset_version,
            passed=not issues,
            regressions=issues,
        )

    def _check(
        self,
        *,
        candidate_name: str,
        metric_name: str,
        previous_value: float,
        current_value: float,
        threshold: MetricThreshold,
    ) -> RegressionIssue | None:
        if threshold.direction == ThresholdDirection.MIN_DROP:
            if current_value < previous_value - threshold.threshold:
                return RegressionIssue(
                    candidate=candidate_name,
                    metric=metric_name,
                    previous_value=previous_value,
                    current_value=current_value,
                    threshold=threshold.threshold,
                    message=(
                        f"{metric_name} dropped from {previous_value:.4f} to "
                        f"{current_value:.4f} (allowed drop: {threshold.threshold:.4f})."
                    ),
                )

        elif threshold.direction == ThresholdDirection.MAX_INCREASE:
            if current_value > previous_value + threshold.threshold:
                return RegressionIssue(
                    candidate=candidate_name,
                    metric=metric_name,
                    previous_value=previous_value,
                    current_value=current_value,
                    threshold=threshold.threshold,
                    message=(
                        f"{metric_name} increased from {previous_value:.4f} to "
                        f"{current_value:.4f} (allowed increase: {threshold.threshold:.4f})."
                    ),
                )

        elif (
            threshold.direction == ThresholdDirection.MAX_RELATIVE_INCREASE
            and previous_value > 0
            and current_value > previous_value * (1 + threshold.threshold)
        ):
            return RegressionIssue(
                candidate=candidate_name,
                metric=metric_name,
                previous_value=previous_value,
                current_value=current_value,
                threshold=threshold.threshold,
                message=(
                    f"{metric_name} increased from {previous_value:.2f} to "
                    f"{current_value:.2f} (allowed relative increase: "
                    f"{threshold.threshold:.0%})."
                ),
            )

        return None

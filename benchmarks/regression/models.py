"""
Canonical regression detection models.

Mirrors `evaluation_platform_prd.md` §11.5's `RegressionResult`, but
compares two `benchmarks.models.report.BenchmarkReport` instances rather
than inventing a parallel canonical model -- report.py's
`BenchmarkReport`/`BenchmarkCandidate` are already the Engineering
Benchmark Platform's canonical result shape.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class RegressionIssue(BaseModel):
    """
    A single metric that regressed beyond its configured threshold.
    """

    model_config = ConfigDict(extra="forbid")

    candidate: str = Field(
        description="Benchmark candidate the regression was found on.",
    )

    metric: str = Field(
        description="Metric name that regressed.",
    )

    previous_value: float

    current_value: float

    threshold: float = Field(
        description="Configured threshold that was exceeded.",
    )

    message: str


class RegressionResult(BaseModel):
    """
    Canonical regression detection result (PRD §11.5).
    """

    model_config = ConfigDict(extra="forbid")

    benchmark_name: str

    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )

    previous_commit: str | None = Field(
        default=None,
        description="Git commit the previous (baseline) report was generated from.",
    )

    current_commit: str | None = Field(
        default=None,
        description="Git commit the current report was generated from.",
    )

    previous_dataset_version: str = Field(
        default="unknown",
    )

    current_dataset_version: str = Field(
        default="unknown",
    )

    passed: bool

    regressions: list[RegressionIssue] = Field(
        default_factory=list,
    )

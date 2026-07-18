"""
Canonical benchmark report models.

These models define the standard output produced by every engineering
benchmark within ResearchMind.

Benchmark reports are intentionally generic so they can represent
evaluations across multiple AI platforms, including:

- Chunking
- Embeddings
- Retrieval
- Reranking
- End-to-End AI Pipeline

Reports may be serialized to JSON for automation or Markdown for
human-readable engineering analysis.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from benchmarks.common.git_info import get_git_branch, get_git_commit

BENCHMARK_VERSION = "1.0.0"
"""
Version of the `benchmarks/` framework itself (report schema + runner
contract), independent of `pyproject.toml`'s application version. Bump
this when `BenchmarkReport`/`BenchmarkCandidate` or the runner's CLI
contract change in a way that could affect how old reports compare to
new ones.
"""

# ============================================================================
# Candidate
# ============================================================================


class BenchmarkCandidate(BaseModel):
    """
    Results for a single benchmark candidate.

    A candidate represents one implementation being evaluated, such as a
    chunking strategy, embedding provider, or retrieval algorithm.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Human-readable candidate name.",
    )

    version: str | None = Field(
        default=None,
        description="Implementation version.",
    )

    metrics: dict[str, float | int | str | bool] = Field(
        default_factory=dict,
        description="Measured benchmark metrics.",
    )

    notes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional benchmark metadata.",
    )


# ============================================================================
# Dataset
# ============================================================================


class BenchmarkDataset(BaseModel):
    """
    Dataset used during benchmark execution.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Dataset collection name.",
    )

    document_count: int = Field(
        ge=0,
        description="Number of benchmark documents.",
    )


# ============================================================================
# Metadata
# ============================================================================


class BenchmarkMetadata(BaseModel):
    """
    Provenance for a single benchmark run.

    Without this, a regression flagged by `benchmarks/regression/` can
    only say a metric moved -- not what changed between the two runs
    being compared. `git_commit`/`branch` are captured automatically at
    report-construction time; `dataset_version`/`model_versions` are
    populated by whichever benchmark has that information (both default
    to "unknown" rather than silently omitting the field).
    """

    model_config = ConfigDict(extra="forbid")

    git_commit: str | None = Field(
        default_factory=get_git_commit,
        description="Full SHA of the commit the benchmark ran against.",
    )

    branch: str | None = Field(
        default_factory=get_git_branch,
        description="Git branch the benchmark ran against.",
    )

    dataset_version: str = Field(
        default="unknown",
        description="Version of the benchmark query dataset used.",
    )

    model_versions: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Candidate name -> concrete model/implementation identifier actually exercised."
        ),
    )

    benchmark_version: str = Field(
        default=BENCHMARK_VERSION,
        description=("Version of the benchmarks/ framework (report schema + runner contract)."),
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when this metadata was captured.",
    )


# ============================================================================
# Benchmark Report
# ============================================================================


class BenchmarkReport(BaseModel):
    """
    Canonical benchmark report.

    Every engineering benchmark within ResearchMind should return this
    model.
    """

    model_config = ConfigDict(extra="forbid")

    benchmark_name: str = Field(
        description="Benchmark identifier.",
    )

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the benchmark completed.",
    )

    dataset: BenchmarkDataset

    metadata: BenchmarkMetadata = Field(
        default_factory=BenchmarkMetadata,
        description="Run provenance (git commit/branch, dataset/model/benchmark versions).",
    )

    candidates: list[BenchmarkCandidate] = Field(
        default_factory=list,
        description="Evaluated benchmark candidates.",
    )

    summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional benchmark summary.",
    )

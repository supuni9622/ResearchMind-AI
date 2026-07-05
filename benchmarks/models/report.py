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

    candidates: list[BenchmarkCandidate] = Field(
        default_factory=list,
        description="Evaluated benchmark candidates.",
    )

    summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional benchmark summary.",
    )

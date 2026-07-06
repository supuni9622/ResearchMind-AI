from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RuntimeStageMetric(BaseModel):
    """Runtime metrics collected for a single pipeline stage."""

    stage: str = Field(description="Pipeline stage name (e.g. Processing, Chunking, Embedding).")

    duration_ms: float = Field(
        ge=0,
        description="Execution duration in milliseconds.",
    )

    peak_memory_mb: float = Field(
        ge=0,
        description="Peak memory usage during the stage in megabytes.",
    )


class ArtifactMetric(BaseModel):
    """Size information for a generated artifact."""

    name: str = Field(description="Artifact name (e.g. chunks.json, embeddings.json).")

    size_bytes: int = Field(
        ge=0,
        description="Artifact size in bytes.",
    )


class PipelineRuntimeMetrics(BaseModel):
    """Canonical runtime metrics for an entire processing pipeline execution."""

    started_at: datetime = Field(description="Pipeline execution start time.")

    completed_at: datetime = Field(description="Pipeline execution completion time.")

    total_duration_ms: float = Field(
        ge=0,
        description="Total pipeline execution time in milliseconds.",
    )

    peak_memory_mb: float = Field(
        ge=0,
        description="Peak memory usage across the entire pipeline in megabytes.",
    )

    stages: list[RuntimeStageMetric] = Field(
        default_factory=list,
        description="Runtime metrics collected for each pipeline stage.",
    )

    artifacts: list[ArtifactMetric] = Field(
        default_factory=list,
        description="Metrics for artifacts generated during the pipeline.",
    )

from __future__ import annotations

from datetime import UTC, datetime

import psutil

from app.ai.observability.models import (
    ArtifactMetric,
    PipelineRuntimeMetrics,
    RuntimeStageMetric,
)
from app.ai.observability.timer import Timer


class RuntimeMetricsCollector:
    """Collects runtime metrics for a processing pipeline."""

    def __init__(self) -> None:
        self._pipeline_timer = Timer()
        self._stage_timer: Timer | None = None

        self._started_at: datetime | None = None
        self._completed_at: datetime | None = None

        self._stages: list[RuntimeStageMetric] = []
        self._artifacts: list[ArtifactMetric] = []

        self._peak_memory_mb: float = self._current_memory_mb()

    def start_pipeline(self) -> None:
        """Start collecting pipeline runtime metrics."""
        self._started_at = datetime.now(UTC)
        self._pipeline_timer.start()
        self._peak_memory_mb = self._current_memory_mb()

    def finish_pipeline(self) -> PipelineRuntimeMetrics:
        """Finish pipeline execution and return collected metrics."""
        if self._started_at is None:
            raise RuntimeError("Pipeline has not been started.")

        self._pipeline_timer.stop()
        self._completed_at = datetime.now(UTC)
        self._update_peak_memory()

        return PipelineRuntimeMetrics(
            started_at=self._started_at,
            completed_at=self._completed_at,
            total_duration_ms=self._pipeline_timer.elapsed_milliseconds,
            peak_memory_mb=self._peak_memory_mb,
            stages=self._stages,
            artifacts=self._artifacts,
        )

    def start_stage(self, stage: str) -> None:
        """Start measuring a pipeline stage."""
        self._stage_name = stage
        self._stage_timer = Timer()
        self._stage_timer.start()

    def finish_stage(self) -> None:
        """Finish measuring the current pipeline stage."""
        if self._stage_timer is None:
            raise RuntimeError("No stage is currently running.")

        self._stage_timer.stop()

        current_memory = self._current_memory_mb()
        self._peak_memory_mb = max(self._peak_memory_mb, current_memory)

        self._stages.append(
            RuntimeStageMetric(
                stage=self._stage_name,
                duration_ms=self._stage_timer.elapsed_milliseconds,
                peak_memory_mb=current_memory,
            )
        )

        self._stage_timer = None

    def add_artifact(self, name: str, size_bytes: int) -> None:
        """Record a generated artifact."""
        self._artifacts.append(
            ArtifactMetric(
                name=name,
                size_bytes=size_bytes,
            )
        )

    @staticmethod
    def _current_memory_mb() -> float:
        """Return the current process memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)

    def _update_peak_memory(self) -> None:
        """Update the pipeline peak memory usage."""
        self._peak_memory_mb = max(
            self._peak_memory_mb,
            self._current_memory_mb(),
        )

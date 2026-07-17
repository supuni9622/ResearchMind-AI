from __future__ import annotations

import structlog
from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.observability.models import (
    GenerationMetricsSnapshot,
    build_generation_metrics_snapshot,
)
from app.infrastructure.metrics.generation import (
    GENERATION_CACHE_HITS_TOTAL,
    GENERATION_HALLUCINATION_FLAGS_TOTAL,
    GENERATION_REGENERATIONS_TOTAL,
    GENERATION_REQUESTS_TOTAL,
    GENERATION_RETRIES_TOTAL,
    GENERATION_RUNTIME_VALIDATION_FAILURES_TOTAL,
    GENERATION_VALIDATION_FAILURES_TOTAL,
)
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.metrics.noop import NoOpMetricsRecorder

logger = structlog.get_logger()


class GenerationMetricsService:
    """
    Runtime Metrics Integration (PRD §3.5). Turns a completed
    `GenerationResult` into a `GenerationMetricsSnapshot`, forwards its
    counters/duration to a `MetricsRecorder` (the same Prometheus-ready,
    currently-`NoOpMetricsRecorder`-backed interface the Guardrails
    Platform uses -- see `infrastructure/metrics/guardrails.py`), and
    emits the full snapshot as a single structured log event.

    Token/cost figures are never recomputed here -- they already live on
    `GenerationResult.statistics` (populated per-provider, see
    `providers/base.py::build_statistics`) and
    `build_generation_metrics_snapshot` just reads them through.
    """

    def __init__(
        self,
        metrics: MetricsRecorder | None = None,
    ) -> None:
        self._metrics = metrics or NoOpMetricsRecorder()

    def record(
        self,
        result: GenerationResult,
        *,
        cumulative_session_cost_usd: float | None = None,
    ) -> GenerationMetricsSnapshot:

        snapshot = build_generation_metrics_snapshot(
            result,
            cumulative_session_cost_usd=cumulative_session_cost_usd,
        )

        self._metrics.increment(
            metric=GENERATION_REQUESTS_TOTAL,
        )

        self._metrics.record_duration(
            operation="generation",
            duration_ms=snapshot.latency_ms,
        )

        if snapshot.retries:
            self._metrics.increment(
                metric=GENERATION_RETRIES_TOTAL,
            )

        if snapshot.regeneration_count:
            self._metrics.increment(
                metric=GENERATION_REGENERATIONS_TOTAL,
            )

        if snapshot.cache_hit:
            self._metrics.increment(
                metric=GENERATION_CACHE_HITS_TOTAL,
            )

        if snapshot.validation_score is not None and snapshot.validation_score < 1.0:
            self._metrics.increment(
                metric=GENERATION_VALIDATION_FAILURES_TOTAL,
            )

        if snapshot.hallucination_score is not None and snapshot.hallucination_score < 1.0:
            self._metrics.increment(
                metric=GENERATION_HALLUCINATION_FLAGS_TOTAL,
            )

        if snapshot.runtime_score is not None and snapshot.runtime_score < 1.0:
            self._metrics.increment(
                metric=GENERATION_RUNTIME_VALIDATION_FAILURES_TOTAL,
            )

        logger.info(
            "generation.metrics.recorded",
            **snapshot.model_dump(
                mode="json",
            ),
        )

        return snapshot

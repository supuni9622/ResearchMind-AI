"""
Observability Platform composition service (AI Runtime Observability PRD
§8 "Artifact Platform"). Turns an already-built metrics snapshot into a
Markdown report and persists both as an `ObservabilityArtifact` --
best-effort, never blocking the runtime execution it observes (PRD §13).

`record_generation` covers both Generation-runtime entry points
(`GenerationService.generate()` and, via `StreamingService`,
`stream_generate()`). `record_processing` covers the Knowledge Processing
pipeline (parse/chunk/embed/index -- no LLM call, so no LangSmith trace),
reusing its pre-existing `PipelineRuntimeMetrics`/`RuntimeReportBuilder`
(`app/ai/observability/{models,report}.py` -- an older, unrelated module
that predates this PRD, see [[observability-platform]]) rather than
recomputing anything. Add `record_retrieval` alongside them the same way
once a caller needs it -- `app/ai/observability/metrics/retrieval.py`
already produces the snapshot, it's just not persisted end-to-end yet.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from app.ai.artifacts.enums import ArtifactCategory, ArtifactRuntime
from app.ai.artifacts.observability.builders import ObservabilityArtifactBuilder
from app.ai.artifacts.observability.writers import ObservabilityArtifactWriter
from app.ai.artifacts.policies.service import ArtifactPolicyService
from app.ai.observability.models import PipelineRuntimeMetrics
from app.ai.observability.report import RuntimeReportBuilder
from app.ai.observability.reports.generation import GenerationReportBuilder
from app.ai.runtime.generation.observability.models import GenerationMetricsSnapshot

logger = structlog.get_logger()


class ObservabilityService:
    def __init__(
        self,
        *,
        artifact_writer: ObservabilityArtifactWriter | None = None,
        artifact_policy_service: ArtifactPolicyService | None = None,
    ) -> None:
        self._artifact_writer = artifact_writer
        self._artifact_policy_service = artifact_policy_service

    async def record_generation(
        self,
        *,
        metrics: GenerationMetricsSnapshot,
        artifact_runtime: ArtifactRuntime,
        owner_id: UUID | None = None,
        session_id: UUID | None = None,
    ) -> None:
        """
        Builds a Generation Report from an already-computed
        `GenerationMetricsSnapshot` and persists it as an
        `ObservabilityArtifact`. No-op when no writer is wired; best
        effort otherwise -- a storage failure here must never fail the
        generation that already succeeded (mirrors
        `GenerationService._persist_generation_artifact`).
        """

        if self._artifact_writer is None:
            return

        if self._artifact_policy_service is not None and not (
            self._artifact_policy_service.should_persist(
                artifact_runtime,
                ArtifactCategory.OBSERVABILITY,
            )
        ):
            logger.debug(
                "artifacts.observability.skipped",
                generation_id=str(metrics.generation_id),
                runtime=artifact_runtime.value,
            )
            return

        try:
            report = GenerationReportBuilder.build(metrics)

            artifact = ObservabilityArtifactBuilder.build(
                execution_id=metrics.generation_id,
                runtime="generation",
                metrics=metrics,
                report=report,
                owner_id=owner_id,
                session_id=session_id,
            )

            await self._artifact_writer.write(artifact)
        except Exception as exc:
            logger.warning(
                "artifacts.observability.failed",
                generation_id=str(metrics.generation_id),
                reason="artifact_persistence_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )

    async def record_processing(
        self,
        *,
        metrics: PipelineRuntimeMetrics,
        document_id: UUID,
        owner_id: str | None = None,
    ) -> None:
        """
        Builds a Runtime Report from an already-computed
        `PipelineRuntimeMetrics` and persists it as an
        `ObservabilityArtifact` under `ArtifactRuntime.PROCESSING`. No-op
        when no writer is wired; best effort otherwise -- a storage
        failure here must never fail a document that already finished
        processing (mirrors `record_generation`).

        No `RuntimeTracer` involvement here -- document processing has no
        LLM call to trace, only pipeline stage timings, so LangSmith
        tracing (which this platform reserves for generation) doesn't
        apply.
        """

        if self._artifact_writer is None:
            return

        if self._artifact_policy_service is not None and not (
            self._artifact_policy_service.should_persist(
                ArtifactRuntime.PROCESSING,
                ArtifactCategory.OBSERVABILITY,
            )
        ):
            logger.debug(
                "artifacts.observability.skipped",
                document_id=str(document_id),
                runtime=ArtifactRuntime.PROCESSING.value,
            )
            return

        try:
            report = RuntimeReportBuilder.build(metrics)

            artifact = ObservabilityArtifactBuilder.build(
                execution_id=document_id,
                runtime="processing",
                metrics=metrics,
                report=report,
                owner_id=(UUID(owner_id) if owner_id else None),
            )

            await self._artifact_writer.write(artifact)
        except Exception as exc:
            logger.warning(
                "artifacts.observability.failed",
                document_id=str(document_id),
                reason="artifact_persistence_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )

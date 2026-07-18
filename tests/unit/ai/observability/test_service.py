"""
Unit tests for ObservabilityService.record_generation/record_processing.

Covers:
- No-op when no artifact writer is wired
- Skipped (no write) when the artifact policy service says not to persist
- Writes an ObservabilityArtifact built from the snapshot when wired and
  policy allows
- A writer failure is swallowed, never raised (best-effort persistence)
- record_processing mirrors record_generation's shape, using
  PipelineRuntimeMetrics/ArtifactRuntime.PROCESSING instead
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.ai.artifacts.enums import ArtifactCategory, ArtifactRuntime
from app.ai.observability.models import PipelineRuntimeMetrics
from app.ai.observability.service import ObservabilityService
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.observability.models import GenerationMetricsSnapshot


def _pipeline_metrics() -> PipelineRuntimeMetrics:
    now = datetime.now(UTC)
    return PipelineRuntimeMetrics(
        started_at=now,
        completed_at=now,
        total_duration_ms=100.0,
        peak_memory_mb=50.0,
    )


def _metrics() -> GenerationMetricsSnapshot:
    return GenerationMetricsSnapshot(
        request_id=uuid4(),
        generation_id=uuid4(),
        provider=GenerationProvider.GROQ,
        model="test-model",
        latency_ms=10.0,
        retries=0,
        regeneration_count=0,
        cache_hit=False,
        prompt_tokens=1,
        completion_tokens=1,
        total_tokens=2,
        estimated_cost_usd=0.0,
        guardrail_blocked=False,
    )


async def test_record_generation_is_a_noop_without_a_writer() -> None:
    service = ObservabilityService(artifact_writer=None)

    await service.record_generation(
        metrics=_metrics(),
        artifact_runtime=ArtifactRuntime.CHAT,
    )

    # No exception, nothing to assert on -- absence of a writer means
    # nothing could have been called.


async def test_record_generation_writes_an_artifact_when_policy_allows() -> None:
    writer = AsyncMock()
    policy_service = MagicMock()
    policy_service.should_persist.return_value = True

    service = ObservabilityService(
        artifact_writer=writer,
        artifact_policy_service=policy_service,
    )
    metrics = _metrics()

    await service.record_generation(
        metrics=metrics,
        artifact_runtime=ArtifactRuntime.CHAT,
    )

    policy_service.should_persist.assert_called_once_with(
        ArtifactRuntime.CHAT,
        ArtifactCategory.OBSERVABILITY,
    )
    writer.write.assert_awaited_once()
    written_artifact = writer.write.await_args.args[0]
    assert written_artifact.metadata.execution_id == metrics.generation_id


async def test_record_generation_skips_write_when_policy_denies() -> None:
    writer = AsyncMock()
    policy_service = MagicMock()
    policy_service.should_persist.return_value = False

    service = ObservabilityService(
        artifact_writer=writer,
        artifact_policy_service=policy_service,
    )

    await service.record_generation(
        metrics=_metrics(),
        artifact_runtime=ArtifactRuntime.CHAT,
    )

    writer.write.assert_not_awaited()


async def test_record_generation_swallows_writer_failures() -> None:
    writer = AsyncMock()
    writer.write = AsyncMock(side_effect=RuntimeError("storage down"))

    service = ObservabilityService(artifact_writer=writer)

    # Must not raise.
    await service.record_generation(
        metrics=_metrics(),
        artifact_runtime=ArtifactRuntime.CHAT,
    )


async def test_record_processing_is_a_noop_without_a_writer() -> None:
    service = ObservabilityService(artifact_writer=None)

    await service.record_processing(
        metrics=_pipeline_metrics(),
        document_id=uuid4(),
        owner_id=str(uuid4()),
    )

    # No exception, nothing to assert on -- absence of a writer means
    # nothing could have been called.


async def test_record_processing_writes_an_artifact_when_policy_allows() -> None:
    writer = AsyncMock()
    policy_service = MagicMock()
    policy_service.should_persist.return_value = True

    service = ObservabilityService(
        artifact_writer=writer,
        artifact_policy_service=policy_service,
    )
    document_id = uuid4()
    owner_id = uuid4()

    await service.record_processing(
        metrics=_pipeline_metrics(),
        document_id=document_id,
        owner_id=str(owner_id),
    )

    policy_service.should_persist.assert_called_once_with(
        ArtifactRuntime.PROCESSING,
        ArtifactCategory.OBSERVABILITY,
    )
    writer.write.assert_awaited_once()
    written_artifact = writer.write.await_args.args[0]
    assert written_artifact.metadata.execution_id == document_id
    assert written_artifact.metadata.runtime == "processing"
    assert written_artifact.metadata.owner_id == owner_id


async def test_record_processing_skips_write_when_policy_denies() -> None:
    writer = AsyncMock()
    policy_service = MagicMock()
    policy_service.should_persist.return_value = False

    service = ObservabilityService(
        artifact_writer=writer,
        artifact_policy_service=policy_service,
    )

    await service.record_processing(
        metrics=_pipeline_metrics(),
        document_id=uuid4(),
    )

    writer.write.assert_not_awaited()


async def test_record_processing_swallows_writer_failures() -> None:
    writer = AsyncMock()
    writer.write = AsyncMock(side_effect=RuntimeError("storage down"))

    service = ObservabilityService(artifact_writer=writer)

    # Must not raise.
    await service.record_processing(
        metrics=_pipeline_metrics(),
        document_id=uuid4(),
    )

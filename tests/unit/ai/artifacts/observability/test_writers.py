from __future__ import annotations

from uuid import uuid4

from app.ai.artifacts.observability.builders import ObservabilityArtifactBuilder
from app.ai.artifacts.observability.writers import ObservabilityArtifactWriter
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.observability.models import GenerationMetricsSnapshot

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage


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


async def test_write_persists_metadata_metrics_and_report(
    fake_storage: FakeDocumentStorage,
) -> None:
    writer = ObservabilityArtifactWriter(storage_provider=fake_storage)
    metrics = _metrics()

    artifact = ObservabilityArtifactBuilder.build(
        execution_id=metrics.generation_id,
        runtime="generation",
        metrics=metrics,
        report="# Generation Report",
    )

    await writer.write(artifact)

    base = f"observability/{metrics.generation_id}"

    assert set(fake_storage.uploads.keys()) == {
        f"{base}/metadata.json",
        f"{base}/metrics.json",
        f"{base}/report.md",
    }
    assert fake_storage.uploads[f"{base}/report.md"] == b"# Generation Report"


async def test_write_persists_statistics_when_present(
    fake_storage: FakeDocumentStorage,
) -> None:
    from app.ai.observability.statistics.models import StatisticsSnapshot

    writer = ObservabilityArtifactWriter(storage_provider=fake_storage)
    metrics = _metrics()

    artifact = ObservabilityArtifactBuilder.build(
        execution_id=metrics.generation_id,
        runtime="generation",
        metrics=metrics,
        statistics=StatisticsSnapshot(sample_count=1),
        report="# report",
    )

    await writer.write(artifact)

    base = f"observability/{metrics.generation_id}"

    assert f"{base}/statistics.json" in fake_storage.uploads

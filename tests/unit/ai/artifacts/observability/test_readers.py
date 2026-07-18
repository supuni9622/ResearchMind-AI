from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.artifacts.exceptions import ArtifactNotFoundError
from app.ai.artifacts.observability.builders import ObservabilityArtifactBuilder
from app.ai.artifacts.observability.readers import ObservabilityArtifactReader
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


async def test_read_roundtrips_a_written_artifact(fake_storage: FakeDocumentStorage) -> None:
    writer = ObservabilityArtifactWriter(storage_provider=fake_storage)
    reader = ObservabilityArtifactReader(storage_provider=fake_storage)
    metrics = _metrics()

    artifact = ObservabilityArtifactBuilder.build(
        execution_id=metrics.generation_id,
        runtime="generation",
        metrics=metrics,
        report="# report",
    )
    await writer.write(artifact)

    read_back = await reader.read(metrics.generation_id)

    assert read_back.metadata.execution_id == metrics.generation_id
    assert read_back.metrics["model"] == "test-model"
    assert read_back.statistics is None
    assert read_back.report == "# report"


async def test_read_raises_when_execution_id_unknown(
    fake_storage: FakeDocumentStorage,
) -> None:
    reader = ObservabilityArtifactReader(storage_provider=fake_storage)

    with pytest.raises(ArtifactNotFoundError):
        await reader.read(uuid4())

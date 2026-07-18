"""
Unit tests for ObservabilityArtifactBuilder.

Covers:
- metrics/statistics BaseModels are dumped to plain dicts on the artifact
- statistics is None when not supplied
"""

from __future__ import annotations

from uuid import uuid4

from app.ai.artifacts.observability.builders import ObservabilityArtifactBuilder
from app.ai.observability.statistics.models import StatisticsSnapshot
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.observability.models import GenerationMetricsSnapshot


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


async def test_build_dumps_metrics_to_a_dict() -> None:
    metrics = _metrics()

    artifact = ObservabilityArtifactBuilder.build(
        execution_id=metrics.generation_id,
        runtime="generation",
        metrics=metrics,
        report="# report",
    )

    assert artifact.metadata.execution_id == metrics.generation_id
    assert artifact.metadata.runtime == "generation"
    assert artifact.metrics["model"] == "test-model"
    assert artifact.statistics is None
    assert artifact.report == "# report"


async def test_build_dumps_statistics_when_supplied() -> None:
    metrics = _metrics()
    statistics = StatisticsSnapshot(sample_count=1, average_latency_ms=10.0)

    artifact = ObservabilityArtifactBuilder.build(
        execution_id=metrics.generation_id,
        runtime="generation",
        metrics=metrics,
        statistics=statistics,
        report="# report",
    )

    assert artifact.statistics is not None
    assert artifact.statistics["sample_count"] == 1

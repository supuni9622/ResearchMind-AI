from __future__ import annotations

from uuid import uuid4

from app.ai.artifacts.evaluation.builders import EvaluationArtifactBuilder
from app.ai.artifacts.evaluation.readers import EvaluationArtifactReader
from app.ai.artifacts.evaluation.writers import EvaluationArtifactWriter

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage


async def test_write_then_read_roundtrips_without_comparison(
    fake_storage: FakeDocumentStorage,
) -> None:
    writer = EvaluationArtifactWriter(storage_provider=fake_storage)
    reader = EvaluationArtifactReader(storage_provider=fake_storage)

    evaluation_id = uuid4()
    artifact = EvaluationArtifactBuilder().build(
        evaluation_id=evaluation_id,
        dataset={"examples": []},
        results={"scores": []},
        metrics={"accuracy": 0.8},
    )

    await writer.write(artifact)

    base = f"artifacts/evaluations/{evaluation_id}"
    assert set(fake_storage.uploads.keys()) == {
        f"{base}/dataset.json",
        f"{base}/results.json",
        f"{base}/metrics.json",
    }

    read_back = await reader.read(evaluation_id)
    assert read_back.metrics == artifact.metrics
    assert read_back.comparison is None

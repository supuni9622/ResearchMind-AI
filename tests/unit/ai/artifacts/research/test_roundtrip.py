from __future__ import annotations

from uuid import uuid4

from app.ai.artifacts.research.builders import ResearchArtifactBuilder
from app.ai.artifacts.research.readers import ResearchArtifactReader
from app.ai.artifacts.research.writers import ResearchArtifactWriter

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage


async def test_write_then_read_roundtrips_without_evaluation(
    fake_storage: FakeDocumentStorage,
) -> None:
    writer = ResearchArtifactWriter(storage_provider=fake_storage)
    reader = ResearchArtifactReader(storage_provider=fake_storage)

    research_id = uuid4()
    artifact = ResearchArtifactBuilder().build(
        research_id=research_id,
        plan={"steps": ["search", "synthesize"]},
        queries={"queries": ["what is x"]},
        retrievals={"results": []},
        citations={"citations": []},
        report={"summary": "done"},
    )

    await writer.write(artifact)

    base = f"artifacts/research/{research_id}"
    assert set(fake_storage.uploads.keys()) == {
        f"{base}/plan.json",
        f"{base}/queries.json",
        f"{base}/retrievals.json",
        f"{base}/citations.json",
        f"{base}/report.json",
    }

    read_back = await reader.read(research_id)
    assert read_back.plan == artifact.plan
    assert read_back.evaluation is None


async def test_write_then_read_roundtrips_with_evaluation(
    fake_storage: FakeDocumentStorage,
) -> None:
    writer = ResearchArtifactWriter(storage_provider=fake_storage)
    reader = ResearchArtifactReader(storage_provider=fake_storage)

    research_id = uuid4()
    artifact = ResearchArtifactBuilder().build(
        research_id=research_id,
        plan={},
        queries={},
        retrievals={},
        citations={},
        report={},
        evaluation={"score": 0.9},
    )

    await writer.write(artifact)
    read_back = await reader.read(research_id)

    assert read_back.evaluation == {"score": 0.9}

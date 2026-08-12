from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.artifacts.exceptions import ArtifactNotFoundError
from app.ai.artifacts.replay.research import ResearchReplayService
from app.ai.artifacts.research.builders import ResearchArtifactBuilder
from app.ai.artifacts.research.readers import ResearchArtifactReader
from app.ai.artifacts.research.writers import ResearchArtifactWriter

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage


async def test_replay_reconstructs_a_research_artifact(
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

    replay_service = ResearchReplayService(reader)
    replayed = await replay_service.replay(research_id)

    assert replayed.metadata.research_id == research_id
    assert replayed.plan == artifact.plan
    assert replayed.report == artifact.report
    assert replayed.evaluation is None


async def test_replay_reconstructs_optional_evaluation(
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

    replay_service = ResearchReplayService(reader)
    replayed = await replay_service.replay(research_id)

    assert replayed.evaluation == {"score": 0.9}


async def test_replay_raises_when_no_artifact_was_ever_persisted(
    fake_storage: FakeDocumentStorage,
) -> None:
    reader = ResearchArtifactReader(storage_provider=fake_storage)
    replay_service = ResearchReplayService(reader)

    with pytest.raises(ArtifactNotFoundError):
        await replay_service.replay(uuid4())

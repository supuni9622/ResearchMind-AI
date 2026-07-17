from __future__ import annotations

from app.ai.artifacts.generation.builders import GenerationArtifactBuilder
from app.ai.artifacts.generation.readers import GenerationArtifactReader
from app.ai.artifacts.generation.writers import GenerationArtifactWriter
from app.ai.artifacts.replay.generation import GenerationReplayService

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage
from tests.unit.ai.artifacts.generation.conftest import make_generation_result


async def test_replay_reconstructs_a_generation_result(
    fake_storage: FakeDocumentStorage,
) -> None:
    writer = GenerationArtifactWriter(storage_provider=fake_storage)
    reader = GenerationArtifactReader(storage_provider=fake_storage)

    result = make_generation_result()
    artifact = GenerationArtifactBuilder().build(result=result)
    await writer.write(artifact)

    replay_service = GenerationReplayService(reader)
    replayed = await replay_service.replay(result.generation_id)

    assert replayed.generation_id == result.generation_id
    assert replayed.content == result.content
    assert replayed.provider == result.provider
    assert replayed.model == result.model
    assert replayed.request.user_prompt == result.request.user_prompt


async def test_replay_reconstructs_routing_and_cache_metadata(
    fake_storage: FakeDocumentStorage,
) -> None:
    writer = GenerationArtifactWriter(storage_provider=fake_storage)
    reader = GenerationArtifactReader(storage_provider=fake_storage)

    result = make_generation_result(
        metadata={
            "routing": {
                "strategy": "auto",
                "selected_provider": "groq",
                "selected_model": "llama-3.3-70b",
                "score": 0.9,
                "reasons": [],
                "used_fallback": False,
            },
            "cache": {"hit": True, "level": "l1_exact"},
        },
    )
    artifact = GenerationArtifactBuilder().build(result=result)
    await writer.write(artifact)

    replay_service = GenerationReplayService(reader)
    replayed = await replay_service.replay(result.generation_id)

    assert replayed.metadata["routing"]["selected_provider"] == "groq"
    assert replayed.metadata["cache"]["hit"] is True

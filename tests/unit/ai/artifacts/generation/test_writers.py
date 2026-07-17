from __future__ import annotations

from app.ai.artifacts.generation.builders import GenerationArtifactBuilder
from app.ai.artifacts.generation.writers import GenerationArtifactWriter

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage
from tests.unit.ai.artifacts.generation.conftest import make_generation_result


async def test_write_persists_required_files_only_when_optional_fields_absent(
    fake_storage: FakeDocumentStorage,
) -> None:
    writer = GenerationArtifactWriter(storage_provider=fake_storage)

    artifact = GenerationArtifactBuilder().build(result=make_generation_result())

    await writer.write(artifact)

    base = f"artifacts/generations/{artifact.metadata.generation_id}"

    assert set(fake_storage.uploads.keys()) == {
        f"{base}/request.json",
        f"{base}/response.json",
        f"{base}/metadata.json",
    }


async def test_write_persists_optional_files_when_present(
    fake_storage: FakeDocumentStorage,
) -> None:
    writer = GenerationArtifactWriter(storage_provider=fake_storage)

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
            "cache": {"hit": False, "level": None},
        },
    )
    artifact = GenerationArtifactBuilder().build(result=result)

    await writer.write(artifact)

    base = f"artifacts/generations/{artifact.metadata.generation_id}"

    assert set(fake_storage.uploads.keys()) == {
        f"{base}/request.json",
        f"{base}/response.json",
        f"{base}/metadata.json",
        f"{base}/routing.json",
        f"{base}/cache.json",
    }

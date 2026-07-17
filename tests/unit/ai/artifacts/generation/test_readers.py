from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.artifacts.exceptions import ArtifactNotFoundError
from app.ai.artifacts.generation.builders import GenerationArtifactBuilder
from app.ai.artifacts.generation.readers import GenerationArtifactReader
from app.ai.artifacts.generation.writers import GenerationArtifactWriter

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage
from tests.unit.ai.artifacts.generation.conftest import make_generation_result


async def test_read_roundtrips_a_written_artifact(fake_storage: FakeDocumentStorage) -> None:
    writer = GenerationArtifactWriter(storage_provider=fake_storage)
    reader = GenerationArtifactReader(storage_provider=fake_storage)

    artifact = GenerationArtifactBuilder().build(result=make_generation_result())
    await writer.write(artifact)

    read_back = await reader.read(artifact.metadata.generation_id)

    assert read_back.metadata.generation_id == artifact.metadata.generation_id
    assert read_back.response.content == artifact.response.content
    assert read_back.routing is None
    assert read_back.cache is None


async def test_read_raises_when_generation_id_unknown(
    fake_storage: FakeDocumentStorage,
) -> None:
    reader = GenerationArtifactReader(storage_provider=fake_storage)

    with pytest.raises(ArtifactNotFoundError):
        await reader.read(uuid4())

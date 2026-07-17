from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from app.ai.artifacts.exceptions import ArtifactNotFoundError
from app.ai.artifacts.streaming.builders import StreamArtifactBuilder
from app.ai.artifacts.streaming.readers import StreamArtifactReader
from app.ai.artifacts.streaming.writers import StreamArtifactWriter
from app.ai.runtime.generation.enums import GenerationProvider

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage
from tests.unit.ai.artifacts.streaming.conftest import make_events, utcnow


async def test_read_roundtrips_a_written_artifact(fake_storage: FakeDocumentStorage) -> None:
    writer = StreamArtifactWriter(storage_provider=fake_storage)
    reader = StreamArtifactReader(storage_provider=fake_storage)

    started_at = utcnow()
    artifact = StreamArtifactBuilder().build(
        provider=GenerationProvider.GROQ,
        model="llama-3.3-70b",
        events=make_events(started_at),
        started_at=started_at,
        completed_at=started_at + timedelta(milliseconds=150),
    )
    await writer.write(artifact)

    read_back = await reader.read(artifact.metadata.stream_id)

    assert read_back.metadata.stream_id == artifact.metadata.stream_id
    assert len(read_back.events) == len(artifact.events)
    assert len(read_back.timeline) == len(artifact.timeline)
    assert read_back.metrics == artifact.metrics


async def test_read_raises_when_stream_id_unknown(fake_storage: FakeDocumentStorage) -> None:
    reader = StreamArtifactReader(storage_provider=fake_storage)

    with pytest.raises(ArtifactNotFoundError):
        await reader.read(uuid4())

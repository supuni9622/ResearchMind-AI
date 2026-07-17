from __future__ import annotations

from datetime import timedelta

from app.ai.artifacts.streaming.builders import StreamArtifactBuilder
from app.ai.artifacts.streaming.writers import StreamArtifactWriter
from app.ai.runtime.generation.enums import GenerationProvider

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage
from tests.unit.ai.artifacts.streaming.conftest import make_events, utcnow


async def test_write_persists_all_four_files(fake_storage: FakeDocumentStorage) -> None:
    writer = StreamArtifactWriter(storage_provider=fake_storage)

    started_at = utcnow()
    artifact = StreamArtifactBuilder().build(
        provider=GenerationProvider.GROQ,
        model="llama-3.3-70b",
        events=make_events(started_at),
        started_at=started_at,
        completed_at=started_at + timedelta(milliseconds=150),
    )

    await writer.write(artifact)

    base = f"artifacts/streams/{artifact.metadata.stream_id}"

    assert set(fake_storage.uploads.keys()) == {
        f"{base}/events.json",
        f"{base}/timeline.json",
        f"{base}/stream.json",
        f"{base}/metrics.json",
    }

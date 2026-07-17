from __future__ import annotations

from datetime import timedelta

from app.ai.artifacts.replay.streaming import StreamReplayService
from app.ai.artifacts.streaming.builders import StreamArtifactBuilder
from app.ai.artifacts.streaming.readers import StreamArtifactReader
from app.ai.artifacts.streaming.writers import StreamArtifactWriter
from app.ai.runtime.generation.enums import GenerationProvider

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage
from tests.unit.ai.artifacts.streaming.conftest import make_events, utcnow


async def test_replay_re_emits_events_in_original_order(
    fake_storage: FakeDocumentStorage,
) -> None:
    writer = StreamArtifactWriter(storage_provider=fake_storage)
    reader = StreamArtifactReader(storage_provider=fake_storage)

    started_at = utcnow()
    events = make_events(started_at)
    artifact = StreamArtifactBuilder().build(
        provider=GenerationProvider.GROQ,
        model="llama-3.3-70b",
        events=events,
        started_at=started_at,
        completed_at=started_at + timedelta(milliseconds=150),
    )
    await writer.write(artifact)

    replay_service = StreamReplayService(reader)

    replayed = [event async for event in replay_service.replay(artifact.metadata.stream_id)]

    assert [event.type for event in replayed] == [event.type for event in events]
    assert [event.content for event in replayed] == [event.content for event in events]

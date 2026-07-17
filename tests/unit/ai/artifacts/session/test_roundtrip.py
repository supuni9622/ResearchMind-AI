from __future__ import annotations

from uuid import uuid4

from app.ai.artifacts.session.builders import SessionArtifactBuilder
from app.ai.artifacts.session.models import SessionStatistics, SessionTimelineEntry
from app.ai.artifacts.session.readers import SessionArtifactReader
from app.ai.artifacts.session.writers import SessionArtifactWriter

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage
from tests.unit.ai.artifacts.streaming.conftest import utcnow


async def test_write_then_read_roundtrips(fake_storage: FakeDocumentStorage) -> None:
    writer = SessionArtifactWriter(storage_provider=fake_storage)
    reader = SessionArtifactReader(storage_provider=fake_storage)

    session_id = uuid4()

    artifact = SessionArtifactBuilder().build(
        session_id=session_id,
        timeline=[SessionTimelineEntry(event="session_started", timestamp=utcnow())],
        statistics=SessionStatistics(turn_count=2, total_duration_ms=500),
    )

    await writer.write(artifact)
    read_back = await reader.read(session_id)

    assert read_back.metadata.session_id == session_id
    assert read_back.statistics.turn_count == 2
    assert len(read_back.timeline) == 1

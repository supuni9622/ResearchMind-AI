"""
Stream Replay (PRD §21): Stored Events -> Re-Emit SSE Events.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID

from app.ai.artifacts.streaming.readers import StreamArtifactReader
from app.ai.runtime.events.models import StreamEvent


class StreamReplayService:
    """
    Re-emits a previously persisted `StreamArtifact`'s events in
    original order -- usable behind the same SSE/WS transports live
    streaming uses (`generation/streaming/transports/`), since both
    consume an `AsyncGenerator[StreamEvent, None]`.
    """

    def __init__(
        self,
        reader: StreamArtifactReader,
    ) -> None:
        self._reader = reader

    async def replay(
        self,
        stream_id: UUID,
    ) -> AsyncGenerator[StreamEvent, None]:

        artifact = await self._reader.read(stream_id)

        for event in artifact.events:
            yield event

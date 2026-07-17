"""
Streaming artifact reader -- reconstructs a StreamArtifact previously
persisted by StreamArtifactWriter.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.artifacts.readers.base import BaseArtifactReader
from app.ai.artifacts.streaming.models import (
    StreamArtifact,
    StreamArtifactMetadata,
    StreamEventsFile,
    StreamMetrics,
    StreamTimelineFile,
)


class StreamArtifactReader(BaseArtifactReader):
    async def read(
        self,
        stream_id: UUID,
    ) -> StreamArtifact:

        base_path = f"artifacts/streams/{stream_id}"

        metadata = await self._read_json(
            key=f"{base_path}/stream.json",
            model=StreamArtifactMetadata,
        )
        events_file = await self._read_json(
            key=f"{base_path}/events.json",
            model=StreamEventsFile,
        )
        timeline_file = await self._read_json(
            key=f"{base_path}/timeline.json",
            model=StreamTimelineFile,
        )
        metrics = await self._read_json(
            key=f"{base_path}/metrics.json",
            model=StreamMetrics,
        )

        return StreamArtifact(
            metadata=metadata,
            events=events_file.events,
            timeline=timeline_file.entries,
            metrics=metrics,
        )

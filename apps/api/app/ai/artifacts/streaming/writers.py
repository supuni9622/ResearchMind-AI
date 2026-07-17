"""
Streaming artifact writer.
"""

from __future__ import annotations

import structlog

from app.ai.artifacts.streaming.models import (
    StreamArtifact,
    StreamEventsFile,
    StreamTimelineFile,
)
from app.ai.artifacts.writers.base import BaseArtifactWriter

logger = structlog.get_logger()


class StreamArtifactWriter(BaseArtifactWriter):
    async def write(
        self,
        artifact: StreamArtifact,
    ) -> None:
        """
        Storage layout (PRD §14):

        artifacts/streams/{stream_id}/
            events.json
            timeline.json
            stream.json     (= metadata)
            metrics.json
        """

        base_path = f"artifacts/streams/{artifact.metadata.stream_id}"

        log = logger.bind(
            stream_id=str(artifact.metadata.stream_id),
            artifact_id=str(artifact.metadata.artifact_id),
            base_path=base_path,
        )

        log.debug("artifacts.stream.write.started")

        try:
            await self._write_json(
                key=f"{base_path}/events.json",
                payload=StreamEventsFile(events=artifact.events),
            )
            await self._write_json(
                key=f"{base_path}/timeline.json",
                payload=StreamTimelineFile(entries=artifact.timeline),
            )
            await self._write_json(
                key=f"{base_path}/stream.json",
                payload=artifact.metadata,
            )
            await self._write_json(
                key=f"{base_path}/metrics.json",
                payload=artifact.metrics,
            )
        except Exception as exc:
            log.exception(
                "artifacts.stream.write_failed",
                exc_type=type(exc).__name__,
            )
            raise

        log.info("artifacts.stream.write.completed")

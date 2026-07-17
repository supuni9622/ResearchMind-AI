"""
Session artifact writer -- scaffold-only, see `models.py` docstring.
"""

from __future__ import annotations

from app.ai.artifacts.session.models import SessionArtifact, SessionTimelineFile
from app.ai.artifacts.writers.base import BaseArtifactWriter


class SessionArtifactWriter(BaseArtifactWriter):
    async def write(
        self,
        artifact: SessionArtifact,
    ) -> None:

        base_path = f"artifacts/sessions/{artifact.metadata.session_id}"

        await self._write_json(key=f"{base_path}/session.json", payload=artifact.metadata)
        await self._write_json(
            key=f"{base_path}/timeline.json",
            payload=SessionTimelineFile(entries=artifact.timeline),
        )
        await self._write_json(key=f"{base_path}/statistics.json", payload=artifact.statistics)

"""
Session artifact reader -- scaffold-only, see `models.py` docstring.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.artifacts.readers.base import BaseArtifactReader
from app.ai.artifacts.session.models import (
    SessionArtifact,
    SessionArtifactMetadata,
    SessionStatistics,
    SessionTimelineFile,
)


class SessionArtifactReader(BaseArtifactReader):
    async def read(
        self,
        session_id: UUID,
    ) -> SessionArtifact:

        base_path = f"artifacts/sessions/{session_id}"

        metadata = await self._read_json(
            key=f"{base_path}/session.json",
            model=SessionArtifactMetadata,
        )
        timeline_file = await self._read_json(
            key=f"{base_path}/timeline.json",
            model=SessionTimelineFile,
        )
        statistics = await self._read_json(
            key=f"{base_path}/statistics.json",
            model=SessionStatistics,
        )

        return SessionArtifact(
            metadata=metadata,
            timeline=timeline_file.entries,
            statistics=statistics,
        )

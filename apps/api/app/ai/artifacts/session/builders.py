"""
Session artifact builder -- scaffold-only, see `models.py` docstring.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.artifacts.session.models import (
    SessionArtifact,
    SessionArtifactMetadata,
    SessionStatistics,
    SessionTimelineEntry,
)


class SessionArtifactBuilder:
    def build(
        self,
        *,
        session_id: UUID,
        timeline: list[SessionTimelineEntry],
        statistics: SessionStatistics,
        owner_id: UUID | None = None,
    ) -> SessionArtifact:

        return SessionArtifact(
            metadata=SessionArtifactMetadata(
                owner_id=owner_id,
                session_id=session_id,
            ),
            timeline=timeline,
            statistics=statistics,
        )

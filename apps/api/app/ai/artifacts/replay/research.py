"""
Research Replay (PRD §21) -- scaffold-only.

No Research Runtime exists yet to persist Research Artifacts against
(see `research/models.py` docstring), so there is nothing to replay.
`replay()` raises rather than silently returning empty data, so a
caller can't mistake "not implemented" for "an empty research run".
"""

from __future__ import annotations

from uuid import UUID

from app.ai.artifacts.research.models import ResearchArtifact


class ResearchReplayService:
    async def replay(
        self,
        research_id: UUID,
    ) -> ResearchArtifact:

        raise NotImplementedError(
            "Research Replay is unimplemented -- no Research Runtime exists "
            "yet to have persisted a ResearchArtifact for "
            f"research_id={research_id}. See research/models.py."
        )

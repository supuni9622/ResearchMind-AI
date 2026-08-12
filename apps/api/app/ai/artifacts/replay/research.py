"""
Research Replay (PRD §21): Stored Research Artifact -> `ResearchArtifact`.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.artifacts.research.models import ResearchArtifact
from app.ai.artifacts.research.readers import ResearchArtifactReader


class ResearchReplayService:
    """
    Reconstructs a `ResearchArtifact` from a previously persisted
    Research Artifact (plan/queries/retrievals/citations/report), without
    re-running retrieval or generation.

    Mirrors `GenerationReplayService`/`StreamReplayService`'s reader-backed
    shape. Not yet wired into an API route -- see
    `docs/IMPLEMENTATION_GAP_CROSSCHECK_2026-08-12.md` Table B
    ("Artifact-replay API routes") for that still-open item.
    """

    def __init__(
        self,
        reader: ResearchArtifactReader,
    ) -> None:
        self._reader = reader

    async def replay(
        self,
        research_id: UUID,
    ) -> ResearchArtifact:

        return await self._reader.read(research_id)

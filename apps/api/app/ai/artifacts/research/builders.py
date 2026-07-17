"""
Research artifact builder, see `models.py` docstring.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.ai.artifacts.research.models import ResearchArtifact, ResearchArtifactMetadata


class ResearchArtifactBuilder:
    def build(
        self,
        *,
        research_id: UUID,
        plan: dict[str, Any],
        queries: dict[str, Any],
        retrievals: dict[str, Any],
        citations: dict[str, Any],
        report: dict[str, Any],
        evaluation: dict[str, Any] | None = None,
        owner_id: UUID | None = None,
    ) -> ResearchArtifact:

        return ResearchArtifact(
            metadata=ResearchArtifactMetadata(
                owner_id=owner_id,
                research_id=research_id,
            ),
            plan=plan,
            queries=queries,
            retrievals=retrievals,
            citations=citations,
            report=report,
            evaluation=evaluation,
        )

"""
Agent artifact builder -- scaffold-only, see `models.py` docstring.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.ai.artifacts.agent.models import AgentArtifact, AgentArtifactMetadata


class AgentArtifactBuilder:
    def build(
        self,
        *,
        run_id: UUID,
        state: dict[str, Any],
        tools: dict[str, Any],
        execution_graph: dict[str, Any],
        events: dict[str, Any],
        memory: dict[str, Any],
        owner_id: UUID | None = None,
    ) -> AgentArtifact:

        return AgentArtifact(
            metadata=AgentArtifactMetadata(
                owner_id=owner_id,
                run_id=run_id,
            ),
            state=state,
            tools=tools,
            execution_graph=execution_graph,
            events=events,
            memory=memory,
        )

"""
Agent artifact reader -- scaffold-only, see `models.py` docstring.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.artifacts.agent.models import AgentArtifact, AgentArtifactMetadata
from app.ai.artifacts.models import JsonDictFile
from app.ai.artifacts.readers.base import BaseArtifactReader


class AgentArtifactReader(BaseArtifactReader):
    async def read(
        self,
        run_id: UUID,
    ) -> AgentArtifact:

        base_path = f"artifacts/agents/{run_id}"

        state = await self._read_json(key=f"{base_path}/state.json", model=JsonDictFile)
        tools = await self._read_json(key=f"{base_path}/tools.json", model=JsonDictFile)
        execution_graph = await self._read_json(
            key=f"{base_path}/execution_graph.json", model=JsonDictFile
        )
        events = await self._read_json(key=f"{base_path}/events.json", model=JsonDictFile)
        memory = await self._read_json(key=f"{base_path}/memory.json", model=JsonDictFile)

        return AgentArtifact(
            metadata=AgentArtifactMetadata(run_id=run_id),
            state=state.data,
            tools=tools.data,
            execution_graph=execution_graph.data,
            events=events.data,
            memory=memory.data,
        )

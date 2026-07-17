"""
Agent artifact writer -- scaffold-only, see `models.py` docstring.
"""

from __future__ import annotations

from app.ai.artifacts.agent.models import AgentArtifact
from app.ai.artifacts.models import JsonDictFile
from app.ai.artifacts.writers.base import BaseArtifactWriter


class AgentArtifactWriter(BaseArtifactWriter):
    async def write(
        self,
        artifact: AgentArtifact,
    ) -> None:

        base_path = f"artifacts/agents/{artifact.metadata.run_id}"

        await self._write_json(
            key=f"{base_path}/state.json", payload=JsonDictFile(data=artifact.state)
        )
        await self._write_json(
            key=f"{base_path}/tools.json", payload=JsonDictFile(data=artifact.tools)
        )
        await self._write_json(
            key=f"{base_path}/execution_graph.json",
            payload=JsonDictFile(data=artifact.execution_graph),
        )
        await self._write_json(
            key=f"{base_path}/events.json", payload=JsonDictFile(data=artifact.events)
        )
        await self._write_json(
            key=f"{base_path}/memory.json", payload=JsonDictFile(data=artifact.memory)
        )

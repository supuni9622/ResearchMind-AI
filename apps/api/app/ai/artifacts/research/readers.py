"""
Research artifact reader, see `models.py` docstring.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.artifacts.models import JsonDictFile
from app.ai.artifacts.readers.base import BaseArtifactReader
from app.ai.artifacts.research.models import ResearchArtifact, ResearchArtifactMetadata


class ResearchArtifactReader(BaseArtifactReader):
    async def read(
        self,
        research_id: UUID,
    ) -> ResearchArtifact:

        base_path = f"artifacts/research/{research_id}"

        metadata = ResearchArtifactMetadata(research_id=research_id)

        plan = await self._read_json(key=f"{base_path}/plan.json", model=JsonDictFile)
        queries = await self._read_json(key=f"{base_path}/queries.json", model=JsonDictFile)
        retrievals = await self._read_json(key=f"{base_path}/retrievals.json", model=JsonDictFile)
        citations = await self._read_json(key=f"{base_path}/citations.json", model=JsonDictFile)
        report = await self._read_json(key=f"{base_path}/report.json", model=JsonDictFile)
        evaluation = await self._read_json_optional(
            key=f"{base_path}/evaluation.json", model=JsonDictFile
        )

        return ResearchArtifact(
            metadata=metadata,
            plan=plan.data,
            queries=queries.data,
            retrievals=retrievals.data,
            citations=citations.data,
            report=report.data,
            evaluation=(evaluation.data if evaluation is not None else None),
        )

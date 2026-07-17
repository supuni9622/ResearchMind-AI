"""
Research artifact writer -- scaffold-only, see `models.py` docstring.
"""

from __future__ import annotations

from app.ai.artifacts.models import JsonDictFile
from app.ai.artifacts.research.models import ResearchArtifact
from app.ai.artifacts.writers.base import BaseArtifactWriter


class ResearchArtifactWriter(BaseArtifactWriter):
    async def write(
        self,
        artifact: ResearchArtifact,
    ) -> None:

        base_path = f"artifacts/research/{artifact.metadata.research_id}"

        await self._write_json(
            key=f"{base_path}/plan.json", payload=JsonDictFile(data=artifact.plan)
        )
        await self._write_json(
            key=f"{base_path}/queries.json", payload=JsonDictFile(data=artifact.queries)
        )
        await self._write_json(
            key=f"{base_path}/retrievals.json", payload=JsonDictFile(data=artifact.retrievals)
        )
        await self._write_json(
            key=f"{base_path}/citations.json", payload=JsonDictFile(data=artifact.citations)
        )
        await self._write_json(
            key=f"{base_path}/report.json", payload=JsonDictFile(data=artifact.report)
        )

        if artifact.evaluation is not None:
            await self._write_json(
                key=f"{base_path}/evaluation.json",
                payload=JsonDictFile(data=artifact.evaluation),
            )

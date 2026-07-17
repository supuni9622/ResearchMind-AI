"""
Evaluation artifact writer -- scaffold-only, see `models.py` docstring.
"""

from __future__ import annotations

from app.ai.artifacts.evaluation.models import EvaluationArtifact
from app.ai.artifacts.models import JsonDictFile
from app.ai.artifacts.writers.base import BaseArtifactWriter


class EvaluationArtifactWriter(BaseArtifactWriter):
    async def write(
        self,
        artifact: EvaluationArtifact,
    ) -> None:

        base_path = f"artifacts/evaluations/{artifact.metadata.evaluation_id}"

        await self._write_json(
            key=f"{base_path}/dataset.json", payload=JsonDictFile(data=artifact.dataset)
        )
        await self._write_json(
            key=f"{base_path}/results.json", payload=JsonDictFile(data=artifact.results)
        )
        await self._write_json(
            key=f"{base_path}/metrics.json", payload=JsonDictFile(data=artifact.metrics)
        )

        if artifact.comparison is not None:
            await self._write_json(
                key=f"{base_path}/comparison.json",
                payload=JsonDictFile(data=artifact.comparison),
            )

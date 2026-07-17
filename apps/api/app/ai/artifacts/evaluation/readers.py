"""
Evaluation artifact reader -- scaffold-only, see `models.py` docstring.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.artifacts.evaluation.models import EvaluationArtifact, EvaluationArtifactMetadata
from app.ai.artifacts.models import JsonDictFile
from app.ai.artifacts.readers.base import BaseArtifactReader


class EvaluationArtifactReader(BaseArtifactReader):
    async def read(
        self,
        evaluation_id: UUID,
    ) -> EvaluationArtifact:

        base_path = f"artifacts/evaluations/{evaluation_id}"

        dataset = await self._read_json(key=f"{base_path}/dataset.json", model=JsonDictFile)
        results = await self._read_json(key=f"{base_path}/results.json", model=JsonDictFile)
        metrics = await self._read_json(key=f"{base_path}/metrics.json", model=JsonDictFile)
        comparison = await self._read_json_optional(
            key=f"{base_path}/comparison.json", model=JsonDictFile
        )

        return EvaluationArtifact(
            metadata=EvaluationArtifactMetadata(evaluation_id=evaluation_id),
            dataset=dataset.data,
            results=results.data,
            metrics=metrics.data,
            comparison=(comparison.data if comparison is not None else None),
        )

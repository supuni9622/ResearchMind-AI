"""
Evaluation artifact builder -- scaffold-only, see `models.py` docstring.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.ai.artifacts.evaluation.models import EvaluationArtifact, EvaluationArtifactMetadata


class EvaluationArtifactBuilder:
    def build(
        self,
        *,
        evaluation_id: UUID,
        dataset: dict[str, Any],
        results: dict[str, Any],
        metrics: dict[str, Any],
        comparison: dict[str, Any] | None = None,
        owner_id: UUID | None = None,
    ) -> EvaluationArtifact:

        return EvaluationArtifact(
            metadata=EvaluationArtifactMetadata(
                owner_id=owner_id,
                evaluation_id=evaluation_id,
            ),
            dataset=dataset,
            results=results,
            metrics=metrics,
            comparison=comparison,
        )

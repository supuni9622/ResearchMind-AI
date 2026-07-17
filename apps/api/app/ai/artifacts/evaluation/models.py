"""
Evaluation artifact models (PRD §19) -- scaffold-only.

No runtime emits or consumes this today: `app/ai/quality/{evaluation,
regression}/` and `app/ai/evaluation/runtime/` contain only empty
`__init__.py` files, confirmed via repo search -- there is no
evaluation harness yet to produce a dataset, run results, or a
comparison. Built ahead of the API surface per this codebase's
established pattern. Fields are left loosely typed (`dict[str, Any]`)
for the same reason as `research/models.py`.

Storage layout (unwired):

    artifacts/evaluations/{evaluation_id}/
        dataset.json
        results.json
        metrics.json
        comparison.json
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.artifacts.models import ArtifactMetadata


class EvaluationArtifactMetadata(ArtifactMetadata):
    model_config = ConfigDict(extra="forbid")

    evaluation_id: UUID


class EvaluationArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata: EvaluationArtifactMetadata

    dataset: dict[str, Any]

    results: dict[str, Any]

    metrics: dict[str, Any]

    comparison: dict[str, Any] | None = None

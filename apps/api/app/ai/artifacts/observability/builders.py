"""
Observability artifact builder. Pure -- no knowledge of storage.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.ai.artifacts.observability.models import (
    ObservabilityArtifact,
    ObservabilityArtifactMetadata,
)


class ObservabilityArtifactBuilder:
    """
    Builds the canonical ObservabilityArtifact from an already-computed
    metrics snapshot (+ optional statistics snapshot + report markdown).
    Never derives metrics itself -- callers build the snapshot via
    `app/ai/observability/metrics/*.py`'s `build_*_metrics_snapshot`
    functions first.
    """

    @staticmethod
    def build(
        *,
        execution_id: UUID,
        runtime: str,
        metrics: BaseModel,
        report: str,
        statistics: BaseModel | None = None,
        owner_id: UUID | None = None,
        session_id: UUID | None = None,
    ) -> ObservabilityArtifact:

        return ObservabilityArtifact(
            metadata=ObservabilityArtifactMetadata(
                execution_id=execution_id,
                runtime=runtime,
                owner_id=owner_id,
                session_id=session_id,
            ),
            metrics=metrics.model_dump(mode="json"),
            statistics=(statistics.model_dump(mode="json") if statistics is not None else None),
            report=report,
        )

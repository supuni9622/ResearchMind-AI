"""
Observability artifact reader -- reconstructs an ObservabilityArtifact
previously persisted by ObservabilityArtifactWriter.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.artifacts.models import JsonDictFile
from app.ai.artifacts.observability.models import (
    ObservabilityArtifact,
    ObservabilityArtifactMetadata,
)
from app.ai.artifacts.readers.base import BaseArtifactReader


class ObservabilityArtifactReader(BaseArtifactReader):
    async def read(
        self,
        execution_id: UUID,
    ) -> ObservabilityArtifact:

        base_path = f"observability/{execution_id}"

        metadata = await self._read_json(
            key=f"{base_path}/metadata.json",
            model=ObservabilityArtifactMetadata,
        )
        metrics_file = await self._read_json(
            key=f"{base_path}/metrics.json",
            model=JsonDictFile,
        )
        statistics_file = await self._read_json_optional(
            key=f"{base_path}/statistics.json",
            model=JsonDictFile,
        )
        report = await self._read_text(
            key=f"{base_path}/report.md",
        )

        return ObservabilityArtifact(
            metadata=metadata,
            metrics=metrics_file.data,
            statistics=(statistics_file.data if statistics_file is not None else None),
            report=report,
        )

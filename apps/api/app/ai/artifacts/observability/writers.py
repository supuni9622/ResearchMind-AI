"""
Observability artifact writer.
"""

from __future__ import annotations

import structlog

from app.ai.artifacts.models import JsonDictFile
from app.ai.artifacts.observability.models import ObservabilityArtifact
from app.ai.artifacts.writers.base import BaseArtifactWriter

logger = structlog.get_logger()


class ObservabilityArtifactWriter(BaseArtifactWriter):
    async def write(
        self,
        artifact: ObservabilityArtifact,
    ) -> None:
        """
        Storage layout (PRD §8):

        observability/{execution_id}/
            metadata.json
            metrics.json
            statistics.json   (only when present)
            report.md
        """

        base_path = f"observability/{artifact.metadata.execution_id}"

        log = logger.bind(
            execution_id=str(artifact.metadata.execution_id),
            runtime=artifact.metadata.runtime,
            artifact_id=str(artifact.metadata.artifact_id),
            base_path=base_path,
        )

        log.debug("artifacts.observability.write.started")

        try:
            await self._write_json(key=f"{base_path}/metadata.json", payload=artifact.metadata)
            await self._write_json(
                key=f"{base_path}/metrics.json",
                payload=JsonDictFile(data=artifact.metrics),
            )

            if artifact.statistics is not None:
                await self._write_json(
                    key=f"{base_path}/statistics.json",
                    payload=JsonDictFile(data=artifact.statistics),
                )

            await self._write_text(
                key=f"{base_path}/report.md",
                content=artifact.report,
            )
        except Exception as exc:
            log.exception(
                "artifacts.observability.write_failed",
                exc_type=type(exc).__name__,
            )
            raise

        log.info("artifacts.observability.write.completed")

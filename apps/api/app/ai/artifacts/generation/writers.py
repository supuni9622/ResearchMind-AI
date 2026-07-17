"""
Generation artifact writer.

Persists generation artifacts using the application's storage
abstraction. Responsible only for writing -- does not build artifacts
or decide whether one should be persisted (see `policies/service.py`).
"""

from __future__ import annotations

import structlog
from pydantic import BaseModel

from app.ai.artifacts.generation.models import GenerationArtifact
from app.ai.artifacts.writers.base import BaseArtifactWriter

logger = structlog.get_logger()


class GenerationArtifactWriter(BaseArtifactWriter):
    async def write(
        self,
        artifact: GenerationArtifact,
    ) -> None:
        """
        Storage layout (PRD §13):

        artifacts/generations/{generation_id}/
            request.json
            response.json
            metadata.json
            validation.json   (only when present)
            guardrails.json   (only when present)
            routing.json      (only when present)
            cache.json        (only when present)
        """

        base_path = f"artifacts/generations/{artifact.metadata.generation_id}"

        log = logger.bind(
            generation_id=str(artifact.metadata.generation_id),
            artifact_id=str(artifact.metadata.artifact_id),
            base_path=base_path,
        )

        log.debug("artifacts.generation.write.started")

        try:
            await self._write_json(key=f"{base_path}/request.json", payload=artifact.request)
            await self._write_json(key=f"{base_path}/response.json", payload=artifact.response)
            await self._write_json(key=f"{base_path}/metadata.json", payload=artifact.metadata)

            optional_files: list[tuple[str, BaseModel | None]] = [
                ("validation", artifact.validation),
                ("guardrails", artifact.guardrails),
                ("routing", artifact.routing),
                ("cache", artifact.cache),
            ]

            for name, payload in optional_files:
                if payload is None:
                    continue

                await self._write_json(key=f"{base_path}/{name}.json", payload=payload)
        except Exception as exc:
            log.exception(
                "artifacts.generation.write_failed",
                exc_type=type(exc).__name__,
            )
            raise

        log.info("artifacts.generation.write.completed")

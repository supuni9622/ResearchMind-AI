"""
Chunk artifact writer.

Persists chunk artifacts using the application's storage abstraction.

This class is responsible only for writing chunk artifacts. It does not
generate chunks or build chunk artifacts.
"""

from __future__ import annotations

from io import BytesIO

import structlog
from app.ai.knowledge.chunking.artifacts.models import ChunkArtifact
from app.infrastructure.storage.interfaces import DocumentStorage

logger = structlog.get_logger()


class ChunkArtifactWriter:
    """
    Persists chunk artifacts.
    """

    def __init__(
        self,
        storage_provider: DocumentStorage,
    ) -> None:
        self._storage = storage_provider

    async def write(
        self,
        *,
        owner_id: str,
        artifact: ChunkArtifact,
    ) -> None:
        """
        Persist a chunk artifact.

        Storage layout:

        documents/
            {owner_id}/
                {document_id}/
                    chunking/
                        {strategy}/
                            {artifact_id}/
                                chunks.json
        """

        base_path = (
            f"documents/"
            f"{owner_id}/"
            f"{artifact.document.document_id}/"
            f"chunking/"
            f"{artifact.strategy.strategy.value}/"
            f"{artifact.artifact_id}"
        )

        log = logger.bind(
            owner_id=owner_id,
            document_id=str(artifact.document.document_id),
            artifact_id=str(artifact.artifact_id),
            strategy=artifact.strategy.strategy.value,
            base_path=base_path,
        )

        log.debug("chunk_artifact_writer.write.started")

        key = f"{base_path}/chunks.json"

        try:
            await self._storage.upload(
                key=key,
                file=BytesIO(
                    artifact.model_dump_json(
                        indent=2,
                        exclude_none=True,
                    ).encode("utf-8")
                ),
                content_type="application/json",
            )
        except Exception as exc:
            log.exception(
                "chunk_artifact_writer.write_failed",
                key=key,
                strategy=artifact.strategy.strategy.value,
                exc_type=type(exc).__name__,
            )
            raise

        log.info(
            "chunk_artifact_writer.write.completed",
            key=key,
            chunk_count=artifact.statistics.total_chunks,
        )

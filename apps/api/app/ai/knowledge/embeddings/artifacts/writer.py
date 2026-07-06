"""
Embedding artifact writer.

Persists embedding artifacts using the application's storage abstraction.

This class is responsible only for writing embedding artifacts.
It does not generate embeddings or build embedding artifacts.
"""

from __future__ import annotations

from io import BytesIO

import structlog
from app.ai.knowledge.embeddings.artifacts.models import (
    EmbeddingArtifact,
)
from app.infrastructure.storage.interfaces import DocumentStorage

logger = structlog.get_logger()


class EmbeddingArtifactWriter:
    """
    Persists embedding artifacts.
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
        artifact: EmbeddingArtifact,
    ) -> None:
        """
        Persist an embedding artifact.

        Storage layout:

        documents/
            {owner_id}/
                {document_id}/
                    embeddings/
                        {provider}/
                            {artifact_id}/
                                embeddings.json
        """

        base_path = (
            f"documents/"
            f"{owner_id}/"
            f"{artifact.document.document_id}/"
            f"embeddings/"
            f"{artifact.execution.provider.value}/"
            f"{artifact.artifact_id}"
        )

        log = logger.bind(
            owner_id=owner_id,
            document_id=str(artifact.document.document_id),
            artifact_id=str(artifact.artifact_id),
            provider=artifact.execution.provider.value,
            model=artifact.execution.model,
            base_path=base_path,
        )

        log.debug(
            "embedding_artifact_writer.write.started",
        )

        key = f"{base_path}/embeddings.json"

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
                "embedding_artifact_writer.write_failed",
                key=key,
                provider=artifact.execution.provider.value,
                model=artifact.execution.model,
                exc_type=type(exc).__name__,
            )
            raise

        log.info(
            "embedding_artifact_writer.write.completed",
            key=key,
            embedding_count=artifact.statistics.total_embeddings,
            dimensions=artifact.statistics.dimensions,
        )

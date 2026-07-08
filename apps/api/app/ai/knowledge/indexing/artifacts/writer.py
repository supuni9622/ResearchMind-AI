"""
Indexing artifact writer.

Persists indexing artifacts using the application's storage abstraction.

This class is responsible only for writing indexing artifacts.
It does not perform indexing or build indexing artifacts.
"""

from __future__ import annotations

from io import BytesIO

import structlog
from app.ai.knowledge.indexing.artifacts.models import (
    IndexingArtifact,
)
from app.infrastructure.storage.interfaces import DocumentStorage

logger = structlog.get_logger()


class IndexingArtifactWriter:
    """
    Persists indexing artifacts.
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
        document_id: str,
        artifact: IndexingArtifact,
    ) -> None:
        """
        Persist an indexing artifact.

        Storage layout:

        documents/
            {owner_id}/
                {document_id}/
                    indexing/
                        {execution_id}/
                            indexing.json
        """

        base_path = f"documents/{owner_id}/{document_id}/indexing/{artifact.execution.execution_id}"

        log = logger.bind(
            owner_id=owner_id,
            document_id=document_id,
            execution_id=str(artifact.execution.execution_id),
            base_path=base_path,
        )

        log.debug(
            "indexing_artifact_writer.write.started",
        )

        key = f"{base_path}/indexing.json"

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
                "indexing_artifact_writer.write_failed",
                key=key,
                exc_type=type(exc).__name__,
            )
            raise

        log.info(
            "indexing_artifact_writer.write.completed",
            key=key,
        )

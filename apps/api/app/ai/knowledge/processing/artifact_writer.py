"""
Processing artifact writer.

Persists processing artifacts using the application's storage
abstraction.

This class is responsible only for writing artifacts. It does not
generate artifacts or perform document processing.
"""

from __future__ import annotations

from io import BytesIO

import structlog

from app.ai.knowledge.processing.artifacts import ProcessingArtifact, ProcessingArtifacts
from app.infrastructure.storage.interfaces import DocumentStorage

logger = structlog.get_logger()


class ArtifactWriter:
    """
    Persists processing artifacts.
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
        artifacts: ProcessingArtifacts,
    ) -> None:
        """
        Persist all processing artifacts.

        Storage layout:

        documents/
            {owner_id}/
                {document_id}/
                    parsed.md
                    parsed.txt
                    processed_document.json
        """

        base_path = f"documents/{owner_id}/{document_id}"

        log = logger.bind(owner_id=owner_id, document_id=document_id, base_path=base_path)
        log.debug("artifact_writer.write.started")

        await self._write_artifact(base_path=base_path, artifact=artifacts.markdown, log=log)
        await self._write_artifact(base_path=base_path, artifact=artifacts.text, log=log)

        if artifacts.json_blocks is not None:
            await self._write_artifact(base_path=base_path, artifact=artifacts.json_blocks, log=log)

        artifact_count = 2 + (artifacts.json_blocks is not None)
        log.info("artifact_writer.write.completed", artifact_count=artifact_count)

    async def _write_artifact(
        self,
        *,
        base_path: str,
        artifact: ProcessingArtifact,
        log: structlog.typing.FilteringBoundLogger,
    ) -> None:
        """
        Persist a single processing artifact.
        """

        key = f"{base_path}/{artifact.filename}"

        try:
            await self._storage.upload(
                key=key,
                file=BytesIO(artifact.content.encode("utf-8")),
                content_type=artifact.content_type,
            )
        except Exception as exc:
            log.exception(
                "artifact_writer.artifact.write_failed",
                key=key,
                content_type=artifact.content_type,
                exc_type=type(exc).__name__,
            )
            raise

        log.debug("artifact_writer.artifact.written", key=key, content_type=artifact.content_type)

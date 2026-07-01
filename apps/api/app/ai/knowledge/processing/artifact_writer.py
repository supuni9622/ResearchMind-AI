"""
Processing artifact writer.

Persists processing artifacts using the application's storage
abstraction.

This class is responsible only for writing artifacts. It does not
generate artifacts or perform document processing.
"""

from __future__ import annotations

from io import BytesIO

from app.ai.knowledge.processing.artifacts import ProcessingArtifacts
from app.infrastructure.storage.interfaces import DocumentStorage


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

        await self._write_artifact(
            base_path=base_path,
            artifact=artifacts.markdown,
        )

        await self._write_artifact(
            base_path=base_path,
            artifact=artifacts.text,
        )

        if artifacts.json_blocks is not None:
            await self._write_artifact(
                base_path=base_path,
                artifact=artifacts.json_blocks,
            )

    async def _write_artifact(
        self,
        *,
        base_path: str,
        artifact,
    ) -> None:
        """
        Persist a single processing artifact.
        """

        await self._storage.upload(
            key=f"{base_path}/{artifact.filename}",
            file=BytesIO(artifact.content.encode("utf-8")),
            content_type=artifact.content_type,
        )

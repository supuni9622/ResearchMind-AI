"""
Chunk artifact reader.

Loads persisted chunk artifacts from storage.

The reader intentionally knows nothing about retrieval,
context building, or parent expansion.
"""

from __future__ import annotations

import json
from uuid import UUID

from app.ai.knowledge.chunking.artifacts.models import (
    ChunkArtifact,
)
from app.infrastructure.storage.interfaces import (
    DocumentStorage,
)


class ChunkArtifactReader:
    """
    Reads chunk artifacts from storage.
    """

    def __init__(
        self,
        storage: DocumentStorage,
    ) -> None:
        self._storage = storage

    async def load(
        self,
        *,
        owner_id: str,
        document_id: UUID,
        strategy: str,
        artifact_id: UUID,
    ) -> ChunkArtifact:
        """
        Load chunk artifact.
        """

        key = f"documents/{owner_id}/{document_id}/chunking/{strategy}/{artifact_id}/chunks.json"

        payload = await self._storage.download(
            key=key,
        )

        return ChunkArtifact.model_validate(
            json.loads(
                payload.decode(
                    "utf-8",
                )
            )
        )

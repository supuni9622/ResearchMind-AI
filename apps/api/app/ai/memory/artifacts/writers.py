"""
Memory artifact writer. Persists memory artifacts using the
application's storage abstraction -- writing only, no evaluation or
building logic.
"""

from __future__ import annotations

from io import BytesIO

import structlog

from app.ai.memory.artifacts.models import MemoryContextArtifact, MemorySearchArtifact
from app.infrastructure.storage.interfaces import DocumentStorage

logger = structlog.get_logger()


class MemoryArtifactWriter:
    def __init__(
        self,
        storage_provider: DocumentStorage,
    ) -> None:
        self._storage = storage_provider

    async def write_search(
        self,
        artifact: MemorySearchArtifact,
    ) -> None:
        await self._write_json(
            key=f"memory/{artifact.owner_id}/{artifact.artifact_id}/memory_search.json",
            payload=artifact,
        )

    async def write_context(
        self,
        artifact: MemoryContextArtifact,
    ) -> None:
        await self._write_json(
            key=f"memory/{artifact.owner_id}/{artifact.artifact_id}/memory_context.json",
            payload=artifact,
        )

    async def _write_json(
        self,
        *,
        key: str,
        payload: MemorySearchArtifact | MemoryContextArtifact,
    ) -> None:
        await self._storage.upload(
            key=key,
            file=BytesIO(
                payload.model_dump_json(
                    indent=2,
                    exclude_none=True,
                ).encode("utf-8")
            ),
            content_type="application/json",
        )

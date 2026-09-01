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
        scope = self._scope_path(artifact.scope_type.value, artifact.project_id)
        await self._write_json(
            key=f"memory/{artifact.owner_id}/{scope}/{artifact.artifact_id}/memory_search.json",
            payload=artifact,
        )

    async def write_context(
        self,
        artifact: MemoryContextArtifact,
    ) -> None:
        scope = self._scope_path(artifact.scope_type.value, artifact.project_id)
        await self._write_json(
            key=f"memory/{artifact.owner_id}/{scope}/{artifact.artifact_id}/memory_context.json",
            payload=artifact,
        )

    async def purge_scope(
        self, *, owner_id: object, scope_type: str, project_id: object | None
    ) -> int:
        prefix = f"memory/{owner_id}/{self._scope_path(scope_type, project_id)}/"
        keys = await self._storage.list_keys(prefix=prefix)
        for key in keys:
            await self._storage.delete(key=key)
        return len(keys)

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

    @staticmethod
    def _scope_path(scope_type: str, project_id: object | None) -> str:
        # Explicit 3-way -- GLOBAL (also project_id=None) must not fall
        # through to "project/None".
        if scope_type == "personal":
            return "personal"
        if scope_type == "global":
            return "global"
        return f"project/{project_id}"

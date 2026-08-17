"""
Valkey-backed store for SESSION memory (PRD §6.1) -- 7-day TTL, high
read frequency, no durability guarantee.

Each record is written under its own key (`memory:session:record:
{owner_id}:{id}`) so `recall()`/`forget()` work by id alone, without
needing the caller to already know which session a record belongs to
-- required by the generic `GET/PUT/DELETE /memory/{id}` contract every
memory type shares. A per-session id list (`memory:session:index:
{owner_id}:{session_id}`) tracks insertion order for `get_recent()`;
ids whose record key has since expired are simply skipped on read
rather than eagerly cleaned up, which keeps `forget()` a single `DEL`.

Reads/writes fail open: a Valkey hiccup is logged and treated as an
empty result rather than propagated, matching `ValkeyEmbeddingCache`.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from redis.asyncio import Redis

from app.ai.memory.enums import MemoryScopeType
from app.ai.memory.models import MemoryRecord

logger = structlog.get_logger()

_RECORD_KEY_PREFIX = "memory:session:record"
_INDEX_KEY_PREFIX = "memory:session:index"

_MAX_SESSION_ENTRIES = 200


class ValkeySessionStore:
    def __init__(
        self,
        client: Redis,
        *,
        ttl_seconds: int,
    ) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    async def put(
        self,
        record: MemoryRecord,
        *,
        session_id: UUID,
    ) -> None:
        record_key = self._record_key(
            record.owner_id, record.scope_type, record.project_id, record.id
        )
        index_key = self._index_key(
            record.owner_id, record.scope_type, record.project_id, session_id
        )

        try:
            pipeline = self._client.pipeline(transaction=False)

            pipeline.set(
                record_key,
                record.model_dump_json(),
                ex=self._ttl_seconds,
            )

            pipeline.rpush(index_key, str(record.id))
            pipeline.ltrim(index_key, -_MAX_SESSION_ENTRIES, -1)
            pipeline.expire(index_key, self._ttl_seconds)

            await pipeline.execute()
        except Exception:
            logger.exception(
                "memory.session.write_failed",
                owner_id=str(record.owner_id),
                memory_id=str(record.id),
            )

    async def replace(
        self,
        record: MemoryRecord,
    ) -> bool:
        """
        Overwrite an existing record in place (refreshing its TTL)
        without touching the session index -- backs `update_memory()`,
        which only needs `owner_id`/`id`, not the session_id `put()`
        requires to maintain ordering.
        """

        record_key = self._record_key(
            record.owner_id, record.scope_type, record.project_id, record.id
        )

        try:
            updated = await self._client.set(
                record_key,
                record.model_dump_json(),
                ex=self._ttl_seconds,
                xx=True,
            )
        except Exception:
            logger.exception(
                "memory.session.replace_failed",
                owner_id=str(record.owner_id),
                memory_id=str(record.id),
            )
            return False

        return bool(updated)

    async def get(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> MemoryRecord | None:
        try:
            raw = await self._client.get(
                self._record_key(owner_id, scope_type, project_id, memory_id)
            )
        except Exception:
            logger.exception(
                "memory.session.read_failed",
                owner_id=str(owner_id),
                memory_id=str(memory_id),
            )
            return None

        if raw is None:
            return None

        return MemoryRecord.model_validate_json(raw)

    async def get_recent(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        limit: int,
    ) -> list[MemoryRecord]:
        index_key = self._index_key(owner_id, scope_type, project_id, session_id)

        try:
            # redis-py's command mixin types `lrange` as `Awaitable[list] |
            # list` since it's shared between the sync and async clients --
            # on `Redis` (async) it's always awaitable.
            ids = await self._client.lrange(index_key, -limit, -1)  # type: ignore[misc]
        except Exception:
            logger.exception(
                "memory.session.index_read_failed",
                owner_id=str(owner_id),
                session_id=str(session_id),
            )
            return []

        if not ids:
            return []

        record_keys = [
            self._record_key(owner_id, scope_type, project_id, UUID(raw_id)) for raw_id in ids
        ]

        try:
            raw_records = await self._client.mget(record_keys)
        except Exception:
            logger.exception(
                "memory.session.batch_read_failed",
                owner_id=str(owner_id),
                session_id=str(session_id),
            )
            return []

        return [MemoryRecord.model_validate_json(raw) for raw in raw_records if raw is not None]

    async def delete(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> bool:
        try:
            deleted = await self._client.delete(
                self._record_key(owner_id, scope_type, project_id, memory_id)
            )
        except Exception:
            logger.exception(
                "memory.session.delete_failed",
                owner_id=str(owner_id),
                memory_id=str(memory_id),
            )
            return False

        return bool(deleted)

    async def purge_scope(
        self,
        *,
        owner_id: UUID,
        scope_type: MemoryScopeType,
        project_id: UUID | None,
    ) -> int:
        """Remove SESSION, interest, idempotency, and cache keys for one scope.

        This administrative erasure path fails closed: callers need an exact
        success/failure signal so a governance job cannot claim completion
        while owner data remains in Valkey.
        """

        scope = self._scope_key(scope_type, project_id)
        patterns = (
            f"memory:*:{owner_id}:{scope}:*",
            f"memory:interest:{owner_id}:*",
            f"memory:extraction:*:{owner_id}:*",
            f"memory:availability:{owner_id}:*",
        )
        keys: set[str] = set()
        for pattern in patterns:
            async for key in self._client.scan_iter(match=pattern, count=500):
                keys.add(str(key))
        if not keys:
            return 0
        return int(await self._client.delete(*keys))

    @staticmethod
    def _scope_key(scope_type: MemoryScopeType, project_id: UUID | None) -> str:
        return "personal" if scope_type == MemoryScopeType.PERSONAL else f"project:{project_id}"

    @classmethod
    def _record_key(
        cls,
        owner_id: UUID,
        scope_type: MemoryScopeType,
        project_id: UUID | None,
        memory_id: UUID,
    ) -> str:
        return (
            f"{_RECORD_KEY_PREFIX}:{owner_id}:{cls._scope_key(scope_type, project_id)}:{memory_id}"
        )

    @classmethod
    def _index_key(
        cls,
        owner_id: UUID,
        scope_type: MemoryScopeType,
        project_id: UUID | None,
        session_id: UUID,
    ) -> str:
        return (
            f"{_INDEX_KEY_PREFIX}:{owner_id}:{cls._scope_key(scope_type, project_id)}:{session_id}"
        )

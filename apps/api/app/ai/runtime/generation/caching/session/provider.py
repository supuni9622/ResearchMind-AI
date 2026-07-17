"""
Valkey-backed L3 Session Cache.

A general-purpose, session-namespaced store for `GenerationResult`s —
conversation responses, research intermediate findings, or agent node
outputs (PRD "Session Cache Design"). Distinct from L1/L2: those cache
by request *content*; this caches by an explicit `session_id` the
caller already tracks (`session_id`, `research_session_id`, or
`run_id` — the provider itself is session-type agnostic).

Same fail-open contract as `ValkeyExactCacheProvider`.
"""

from __future__ import annotations

import structlog
from app.ai.runtime.generation.caching.interfaces import (
    SessionCacheProviderInterface,
)
from app.ai.runtime.generation.models import (
    GenerationResult,
)
from redis.asyncio import Redis

logger = structlog.get_logger()

_KEY_PREFIX = "cache:session"


class ValkeySessionCacheProvider(
    SessionCacheProviderInterface,
):
    def __init__(
        self,
        client: Redis,
    ) -> None:
        self._client = client

    async def get(
        self,
        *,
        session_id: str,
        key: str,
    ) -> GenerationResult | None:

        try:
            raw_value = await self._client.get(
                self._redis_key(session_id, key),
            )
        except Exception:
            logger.exception(
                "caching.session.read_failed",
                session_id=session_id,
            )
            return None

        if raw_value is None:
            return None

        try:
            return GenerationResult.model_validate_json(
                raw_value,
            )
        except Exception:
            logger.warning(
                "caching.session.corrupt_entry",
                session_id=session_id,
                key=key,
            )
            return None

    async def set(
        self,
        *,
        session_id: str,
        key: str,
        result: GenerationResult,
        ttl_seconds: int | None,
    ) -> None:

        try:
            await self._client.set(
                self._redis_key(session_id, key),
                result.model_dump_json(),
                ex=ttl_seconds,
            )
        except Exception:
            logger.exception(
                "caching.session.write_failed",
                session_id=session_id,
                key=key,
            )

    async def invalidate(
        self,
        *,
        session_id: str,
        key: str,
    ) -> None:

        try:
            await self._client.delete(
                self._redis_key(session_id, key),
            )
        except Exception:
            logger.exception(
                "caching.session.invalidate_failed",
                session_id=session_id,
                key=key,
            )

    async def clear(
        self,
        *,
        session_id: str,
    ) -> None:

        pattern = f"{_KEY_PREFIX}:{session_id}:*"

        try:
            keys = [key async for key in self._client.scan_iter(match=pattern)]

            if keys:
                await self._client.delete(*keys)
        except Exception:
            logger.exception(
                "caching.session.clear_failed",
                session_id=session_id,
            )

    @staticmethod
    def _redis_key(
        session_id: str,
        key: str,
    ) -> str:
        return f"{_KEY_PREFIX}:{session_id}:{key}"

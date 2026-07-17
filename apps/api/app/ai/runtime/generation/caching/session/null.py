from __future__ import annotations

from app.ai.runtime.generation.caching.interfaces import (
    SessionCacheProviderInterface,
)
from app.ai.runtime.generation.models import (
    GenerationResult,
)


class NullSessionCacheProvider(
    SessionCacheProviderInterface,
):
    """No-op provider, used when `settings.session_cache_enabled` is `False`."""

    async def get(
        self,
        *,
        session_id: str,
        key: str,
    ) -> GenerationResult | None:
        return None

    async def set(
        self,
        *,
        session_id: str,
        key: str,
        result: GenerationResult,
        ttl_seconds: int | None,
    ) -> None:
        return None

    async def invalidate(
        self,
        *,
        session_id: str,
        key: str,
    ) -> None:
        return None

    async def clear(
        self,
        *,
        session_id: str,
    ) -> None:
        return None

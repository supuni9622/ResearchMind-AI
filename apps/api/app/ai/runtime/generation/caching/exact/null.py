from __future__ import annotations

from app.ai.runtime.generation.caching.interfaces import (
    ExactCacheProviderInterface,
)
from app.ai.runtime.generation.caching.models import (
    CacheKey,
)
from app.ai.runtime.generation.models import (
    GenerationResult,
)


class NullExactCacheProvider(
    ExactCacheProviderInterface,
):
    """No-op provider, used when `settings.exact_cache_enabled` is `False`."""

    async def get(
        self,
        key: CacheKey,
    ) -> GenerationResult | None:
        return None

    async def set(
        self,
        key: CacheKey,
        result: GenerationResult,
        *,
        ttl_seconds: int | None,
    ) -> None:
        return None

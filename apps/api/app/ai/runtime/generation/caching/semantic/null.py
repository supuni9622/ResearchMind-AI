from __future__ import annotations

from app.ai.runtime.generation.caching.interfaces import (
    SemanticCacheProviderInterface,
)
from app.ai.runtime.generation.models import (
    GenerationResult,
)


class NullSemanticCacheProvider(
    SemanticCacheProviderInterface,
):
    """No-op provider, used when `settings.semantic_cache_enabled` is `False`."""

    async def get(
        self,
        *,
        prompt: str,
        context_hash: str,
        discriminator: str,
    ) -> tuple[GenerationResult, float | None] | None:
        return None

    async def set(
        self,
        *,
        prompt: str,
        context_hash: str,
        discriminator: str,
        result: GenerationResult,
    ) -> None:
        return None

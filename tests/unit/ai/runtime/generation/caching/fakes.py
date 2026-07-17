"""
In-memory fakes for the Runtime Caching Platform's provider interfaces
— not a test module itself, imported by tests/unit/ai/runtime/generation/caching/test_service.py.
"""

from __future__ import annotations

from app.ai.runtime.generation.caching.interfaces import (
    ExactCacheProviderInterface,
    SemanticCacheProviderInterface,
    SessionCacheProviderInterface,
)
from app.ai.runtime.generation.caching.models import CacheKey
from app.ai.runtime.generation.models import GenerationResult


class FakeExactCacheProvider(ExactCacheProviderInterface):
    def __init__(self) -> None:
        self.store: dict[str, GenerationResult] = {}
        self.get_calls = 0
        self.set_calls = 0

    async def get(self, key: CacheKey) -> GenerationResult | None:
        self.get_calls += 1
        return self.store.get(key.redis_key())

    async def set(
        self,
        key: CacheKey,
        result: GenerationResult,
        *,
        ttl_seconds: int | None,
    ) -> None:
        self.set_calls += 1
        self.store[key.redis_key()] = result


class FakeSemanticCacheProvider(SemanticCacheProviderInterface):
    """
    Ignores embedding/similarity entirely — keyed exactly by
    (context_hash, discriminator, prompt), which is enough to exercise
    CachingService's policy branching without a real vector backend.
    """

    def __init__(self) -> None:
        self.store: dict[tuple[str, str, str], GenerationResult] = {}
        self.get_calls = 0
        self.set_calls = 0

    async def get(
        self,
        *,
        prompt: str,
        context_hash: str,
        discriminator: str,
    ) -> tuple[GenerationResult, float | None] | None:
        self.get_calls += 1
        cached = self.store.get((context_hash, discriminator, prompt))
        return (cached, 0.97) if cached is not None else None

    async def set(
        self,
        *,
        prompt: str,
        context_hash: str,
        discriminator: str,
        result: GenerationResult,
    ) -> None:
        self.set_calls += 1
        self.store[(context_hash, discriminator, prompt)] = result


class FakeSessionCacheProvider(SessionCacheProviderInterface):
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], GenerationResult] = {}

    async def get(self, *, session_id: str, key: str) -> GenerationResult | None:
        return self.store.get((session_id, key))

    async def set(
        self,
        *,
        session_id: str,
        key: str,
        result: GenerationResult,
        ttl_seconds: int | None,
    ) -> None:
        self.store[(session_id, key)] = result

    async def invalidate(self, *, session_id: str, key: str) -> None:
        self.store.pop((session_id, key), None)

    async def clear(self, *, session_id: str) -> None:
        for stored_session_id, key in list(self.store):
            if stored_session_id == session_id:
                self.store.pop((stored_session_id, key))

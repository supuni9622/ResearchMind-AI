from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.runtime.generation.caching.models import (
    CacheKey,
)
from app.ai.runtime.generation.models import (
    GenerationResult,
)


class ExactCacheProviderInterface(
    ABC,
):
    """
    L1 Exact Cache backend contract. Implementations must fail open:
    a backend error is logged and treated as a miss (`get` returns
    `None`) or a no-op (`set`), never raised — a cache outage must
    never fail generation.
    """

    @abstractmethod
    async def get(
        self,
        key: CacheKey,
    ) -> GenerationResult | None:
        pass

    @abstractmethod
    async def set(
        self,
        key: CacheKey,
        result: GenerationResult,
        *,
        ttl_seconds: int | None,
    ) -> None:
        pass


class SemanticCacheProviderInterface(
    ABC,
):
    """
    L2 Semantic Cache backend contract. `context_hash` must be folded
    into whatever the implementation uses to scope similarity search
    (ADR-027 "Important Constraint") so a similar prompt over a
    different document never reuses another document's response.
    Same fail-open contract as `ExactCacheProviderInterface`.
    """

    @abstractmethod
    async def get(
        self,
        *,
        prompt: str,
        context_hash: str,
        discriminator: str,
    ) -> tuple[GenerationResult, float | None] | None:
        """
        Returns `(result, similarity)` on a hit above threshold, else
        `None`. `similarity` is `None` when the backend's hit interface
        doesn't surface the matched distance/score (see
        `RedisSemanticCacheProvider`).
        """

        pass

    @abstractmethod
    async def set(
        self,
        *,
        prompt: str,
        context_hash: str,
        discriminator: str,
        result: GenerationResult,
    ) -> None:
        pass


class SessionCacheProviderInterface(
    ABC,
):
    """
    L3 Session Cache backend contract — a general-purpose, namespaced
    key/value store scoped to a session (conversation, research, or
    agent run). Same fail-open contract as the other providers.
    """

    @abstractmethod
    async def get(
        self,
        *,
        session_id: str,
        key: str,
    ) -> GenerationResult | None:
        pass

    @abstractmethod
    async def set(
        self,
        *,
        session_id: str,
        key: str,
        result: GenerationResult,
        ttl_seconds: int | None,
    ) -> None:
        pass

    @abstractmethod
    async def invalidate(
        self,
        *,
        session_id: str,
        key: str,
    ) -> None:
        pass

    @abstractmethod
    async def clear(
        self,
        *,
        session_id: str,
    ) -> None:
        pass

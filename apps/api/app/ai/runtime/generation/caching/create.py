"""
Runtime Caching Platform composition root.

Assembles L1/L2/L3 providers and the policy resolver into a ready-to-use
`CachingService`. Mirrors `routing/create.py` / `validation/create.py`.
"""

from __future__ import annotations

from functools import lru_cache

import structlog
from app.ai.runtime.generation.caching.enums import (
    CachePolicy,
    CacheRuntime,
)
from app.ai.runtime.generation.caching.exact.null import (
    NullExactCacheProvider,
)
from app.ai.runtime.generation.caching.exact.provider import (
    ValkeyExactCacheProvider,
)
from app.ai.runtime.generation.caching.interfaces import (
    ExactCacheProviderInterface,
    SemanticCacheProviderInterface,
    SessionCacheProviderInterface,
)
from app.ai.runtime.generation.caching.policies.models import (
    RuntimeCacheProfile,
)
from app.ai.runtime.generation.caching.policies.service import (
    CachePolicyResolver,
)
from app.ai.runtime.generation.caching.semantic.embeddings_adapter import (
    OpenAISemanticCacheEmbeddings,
)
from app.ai.runtime.generation.caching.semantic.null import (
    NullSemanticCacheProvider,
)
from app.ai.runtime.generation.caching.semantic.provider import (
    RedisSemanticCacheProvider,
)
from app.ai.runtime.generation.caching.service import (
    CachingService,
)
from app.ai.runtime.generation.caching.session.null import (
    NullSessionCacheProvider,
)
from app.ai.runtime.generation.caching.session.provider import (
    ValkeySessionCacheProvider,
)
from app.core.settings import settings
from langchain_redis import RedisSemanticCache
from openai import OpenAI
from redis.asyncio import Redis

logger = structlog.get_logger()

_DEFAULT_RUNTIME_POLICIES: dict[CacheRuntime, CachePolicy] = {
    CacheRuntime.CHAT: CachePolicy.AUTO,
    # Research answers are context-sensitive, but the exact-cache key includes
    # the fully rendered transcript and retrieval context. AUTO can therefore
    # safely replay truly identical research requests before falling back to
    # semantic matching for equivalent context.
    CacheRuntime.RESEARCH: CachePolicy.AUTO,
    CacheRuntime.BENCHMARK: CachePolicy.EXACT_ONLY,
    CacheRuntime.PLANNER: CachePolicy.NEVER,
    CacheRuntime.TOOL_AGENT: CachePolicy.NEVER,
    CacheRuntime.SUMMARIZER: CachePolicy.AUTO,
    CacheRuntime.REVIEWER: CachePolicy.NEVER,
    CacheRuntime.CRITIC: CachePolicy.NEVER,
}

_DEFAULT_RUNTIME_TTL_SECONDS: dict[CacheRuntime, int | None] = {
    CacheRuntime.CHAT: settings.exact_cache_default_ttl_seconds,
    CacheRuntime.RESEARCH: settings.exact_cache_research_ttl_seconds,
    CacheRuntime.BENCHMARK: settings.exact_cache_benchmark_ttl_seconds,
}


def build_runtime_cache_profiles() -> dict[CacheRuntime, RuntimeCacheProfile]:

    return {
        runtime: RuntimeCacheProfile(
            runtime=runtime,
            policy=policy,
            exact_ttl_seconds=_DEFAULT_RUNTIME_TTL_SECONDS.get(
                runtime,
                settings.exact_cache_default_ttl_seconds,
            ),
        )
        for runtime, policy in _DEFAULT_RUNTIME_POLICIES.items()
    }


def create_exact_cache_provider(
    client: Redis,
) -> ExactCacheProviderInterface:

    if not settings.exact_cache_enabled:
        return NullExactCacheProvider()

    return ValkeyExactCacheProvider(
        client=client,
    )


def create_session_cache_provider(
    client: Redis,
) -> SessionCacheProviderInterface:

    if not settings.session_cache_enabled:
        return NullSessionCacheProvider()

    return ValkeySessionCacheProvider(
        client=client,
    )


def create_semantic_cache_provider() -> SemanticCacheProviderInterface:
    """
    Returns a `NullSemanticCacheProvider` when semantic caching is
    disabled, so L2 gracefully no-ops (see `CachingService.lookup`/
    `store`) instead of every call site needing an `is not None` check.
    """

    if not settings.semantic_cache_enabled:
        return NullSemanticCacheProvider()

    embeddings = OpenAISemanticCacheEmbeddings(
        client=OpenAI(
            api_key=settings.openai_api_key,
        ),
        model=settings.semantic_cache_embedding_model,
    )

    #
    # RedisSemanticCache's distance_threshold is a *distance*
    # (0 = identical), while the PRD's 0.92 default is expressed as a
    # cosine *similarity* (1 = identical). For normalized embeddings,
    # cosine distance == 1 - cosine similarity.
    #
    distance_threshold = 1 - settings.semantic_cache_similarity_threshold

    cache = RedisSemanticCache(
        embeddings=embeddings,
        redis_url=settings.semantic_cache_redis_url,
        distance_threshold=distance_threshold,
        ttl=settings.semantic_cache_ttl_seconds,
        name="researchmind_generation_semantic_cache",
    )

    return RedisSemanticCacheProvider(
        cache=cache,
    )


@lru_cache
def create_caching_service() -> CachingService:

    valkey_client: Redis = Redis.from_url(
        settings.valkey_url,
        decode_responses=True,
    )

    profiles = build_runtime_cache_profiles()

    default_profile = RuntimeCacheProfile(
        runtime=CacheRuntime.CHAT,
        policy=CachePolicy.AUTO,
        exact_ttl_seconds=settings.exact_cache_default_ttl_seconds,
    )

    service = CachingService(
        exact_provider=create_exact_cache_provider(
            valkey_client,
        ),
        semantic_provider=create_semantic_cache_provider(),
        session_provider=create_session_cache_provider(
            valkey_client,
        ),
        policy_resolver=CachePolicyResolver(
            profiles=profiles,
            default_profile=default_profile,
        ),
    )

    logger.info(
        "caching.service.initialized",
        exact_cache_enabled=settings.exact_cache_enabled,
        semantic_cache_enabled=settings.semantic_cache_enabled,
        session_cache_enabled=settings.session_cache_enabled,
    )

    return service

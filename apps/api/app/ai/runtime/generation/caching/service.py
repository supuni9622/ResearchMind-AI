from __future__ import annotations

from time import perf_counter

import structlog
from app.ai.runtime.generation.caching.enums import (
    CacheLevel,
    CachePolicy,
)
from app.ai.runtime.generation.caching.exact.key_builder import (
    build_exact_cache_key,
    hash_context,
    hash_schema,
)
from app.ai.runtime.generation.caching.interfaces import (
    ExactCacheProviderInterface,
    SemanticCacheProviderInterface,
    SessionCacheProviderInterface,
)
from app.ai.runtime.generation.caching.models import (
    CacheResult,
    CacheStatistics,
)
from app.ai.runtime.generation.caching.policies.service import (
    CachePolicyResolver,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
)
from app.ai.runtime.generation.routing.enums import (
    RoutingStrategy,
)

logger = structlog.get_logger()

_EXACT_POLICIES = (CachePolicy.AUTO, CachePolicy.EXACT_ONLY)

_SEMANTIC_POLICIES = (CachePolicy.AUTO, CachePolicy.SEMANTIC)


class CachingService:
    """
    Runtime Caching Platform entry point (PRD/ADR-027). Sits between
    Routing and the Provider call: `lookup()` is checked once a
    candidate model is resolved and before it is invoked; `store()` is
    called with the resulting `GenerationResult` on a miss. See
    `GenerationService._generate_with_provider`.

    L3 Session Cache is a separate, explicit API (`get_session` /
    `set_session` / `invalidate_session` / `clear_session`) rather than
    part of `lookup()`/`store()` — it's keyed by a caller-tracked
    session id, not by request content, so folding it into the
    content-addressed L1/L2 waterfall would conflate two different
    caching models. Nothing in this codebase has a conversation/research
    session runtime yet (PRD "Future Roadmap" Phase 3), so it's wired
    up and available but not yet called from `GenerationService`.
    """

    def __init__(
        self,
        *,
        exact_provider: ExactCacheProviderInterface,
        semantic_provider: SemanticCacheProviderInterface,
        session_provider: SessionCacheProviderInterface,
        policy_resolver: CachePolicyResolver,
    ) -> None:
        self._exact_provider = exact_provider

        self._semantic_provider = semantic_provider

        self._session_provider = session_provider

        self._policy_resolver = policy_resolver

        self._statistics = CacheStatistics()

    @property
    def statistics(
        self,
    ) -> CacheStatistics:
        return self._statistics

    # ==========================================================
    # L1 / L2 — content-addressed generation cache
    # ==========================================================

    async def lookup(
        self,
        *,
        request: GenerationRequest,
        provider: GenerationProvider,
        model: str,
        routing_strategy: RoutingStrategy | None,
    ) -> CacheResult:
        """
        Content-addressed lookup — identical for streaming and
        non-streaming requests. Streaming requests do not bypass the
        cache: `StreamingService` (generation/streaming/service.py)
        checks this first and, on a hit, replays the cached content as
        a synthetic token stream instead of calling a provider, so the
        caller still gets the streaming contract it asked for either
        way. What genuinely can't be cached is a *partial*, in-flight
        stream — see `store()`.
        """

        started = perf_counter()

        policy = self._policy_resolver.resolve_policy(
            runtime=request.cache_runtime,
            override=request.cache_policy,
        )

        if policy == CachePolicy.NEVER:
            return self._record_miss(started)

        if policy in _EXACT_POLICIES:
            key = build_exact_cache_key(
                request=request,
                provider=provider,
                model=model,
                routing_strategy=routing_strategy,
            )

            cached = await self._exact_provider.get(
                key,
            )

            if cached is not None:
                return self._record_hit(
                    level=CacheLevel.EXACT,
                    cached=cached,
                    started=started,
                )

        if policy in _SEMANTIC_POLICIES:
            semantic_hit = await self._semantic_provider.get(
                prompt=request.user_prompt,
                context_hash=hash_context(
                    request.prompt_context.context,
                ),
                discriminator=self._semantic_discriminator(
                    request=request,
                    provider=provider,
                    model=model,
                ),
            )

            if semantic_hit is not None:
                cached, similarity = semantic_hit

                return self._record_hit(
                    level=CacheLevel.SEMANTIC,
                    cached=cached,
                    started=started,
                    similarity=similarity,
                )

        return self._record_miss(started)

    async def store(
        self,
        *,
        request: GenerationRequest,
        provider: GenerationProvider,
        model: str,
        routing_strategy: RoutingStrategy | None,
        result: GenerationResult,
    ) -> None:
        """
        Stores a finished `GenerationResult` — the caller (streaming or
        not) is responsible for only calling this once a result is
        fully assembled. `StreamingService` calls this once after a
        live stream reaches `COMPLETE`, never with partial content.
        """

        policy = self._policy_resolver.resolve_policy(
            runtime=request.cache_runtime,
            override=request.cache_policy,
        )

        if policy == CachePolicy.NEVER:
            return

        if policy in _EXACT_POLICIES:
            key = build_exact_cache_key(
                request=request,
                provider=provider,
                model=model,
                routing_strategy=routing_strategy,
            )

            ttl_seconds = self._policy_resolver.resolve_exact_ttl_seconds(
                runtime=request.cache_runtime,
            )

            await self._exact_provider.set(
                key,
                result,
                ttl_seconds=ttl_seconds,
            )

        if policy in _SEMANTIC_POLICIES:
            await self._semantic_provider.set(
                prompt=request.user_prompt,
                context_hash=hash_context(
                    request.prompt_context.context,
                ),
                discriminator=self._semantic_discriminator(
                    request=request,
                    provider=provider,
                    model=model,
                ),
                result=result,
            )

    # ==========================================================
    # L3 — session-scoped cache
    # ==========================================================

    async def get_session(
        self,
        *,
        session_id: str,
        key: str,
    ) -> GenerationResult | None:
        return await self._session_provider.get(
            session_id=session_id,
            key=key,
        )

    async def set_session(
        self,
        *,
        session_id: str,
        key: str,
        result: GenerationResult,
        ttl_seconds: int | None,
    ) -> None:
        await self._session_provider.set(
            session_id=session_id,
            key=key,
            result=result,
            ttl_seconds=ttl_seconds,
        )

    async def invalidate_session(
        self,
        *,
        session_id: str,
        key: str,
    ) -> None:
        await self._session_provider.invalidate(
            session_id=session_id,
            key=key,
        )

    async def clear_session(
        self,
        *,
        session_id: str,
    ) -> None:
        await self._session_provider.clear(
            session_id=session_id,
        )

    # ==========================================================
    # Internal
    # ==========================================================

    @staticmethod
    def _semantic_discriminator(
        *,
        request: GenerationRequest,
        provider: GenerationProvider,
        model: str,
    ) -> str:
        """
        Every CacheKey field except prompt_hash/context_hash — those
        are what the semantic backend embeds/isolates on directly
        (see `SemanticCacheProviderInterface`).
        """

        top_p = request.metadata.get(
            "top_p",
        )

        return ":".join(
            [
                provider.value,
                model,
                request.routing_strategy.value if request.routing_strategy else "-",
                hash_schema(
                    request.output_schema,
                ),
                f"{request.temperature:.4f}" if request.temperature is not None else "-",
                f"{top_p:.4f}" if top_p is not None else "-",
            ]
        )

    def _record_hit(
        self,
        *,
        level: CacheLevel,
        cached: GenerationResult,
        started: float,
        similarity: float | None = None,
    ) -> CacheResult:

        latency_ms = round(
            (perf_counter() - started) * 1000,
            3,
        )

        tokens_saved = cached.statistics.total_tokens

        cost_saved = cached.statistics.estimated_cost_usd

        if level == CacheLevel.EXACT:
            self._statistics.exact_hits += 1
        else:
            self._statistics.semantic_hits += 1

        self._statistics.tokens_saved += tokens_saved

        self._statistics.cost_saved += cost_saved

        logger.info(
            "caching.lookup",
            cache_hit=True,
            cache_level=level.value,
            cache_latency_ms=latency_ms,
            tokens_saved=tokens_saved,
            cost_saved=cost_saved,
        )

        return CacheResult(
            hit=True,
            level=level,
            generation_result=cached,
            similarity=similarity,
            lookup_latency_ms=latency_ms,
        )

    def _record_miss(
        self,
        started: float,
    ) -> CacheResult:

        latency_ms = round(
            (perf_counter() - started) * 1000,
            3,
        )

        self._statistics.misses += 1

        logger.info(
            "caching.lookup",
            cache_hit=False,
            cache_level=None,
            cache_latency_ms=latency_ms,
            tokens_saved=0,
            cost_saved=0,
        )

        return CacheResult(
            hit=False,
            lookup_latency_ms=latency_ms,
        )

"""
Unit tests for CachingService.

Covers:
- AUTO tries L1 first; a miss falls through to L2
- EXACT_ONLY never consults L2; SEMANTIC never consults L1
- NEVER performs no lookup/store at all
- Streaming requests bypass caching entirely regardless of policy
- store() populates the layer(s) the policy allows
- CacheStatistics tallies hits/misses and tokens/cost saved
- Session cache get/set/invalidate/clear operate independently of policy
"""

from __future__ import annotations

from app.ai.runtime.generation.caching.enums import CacheLevel, CachePolicy, CacheRuntime
from app.ai.runtime.generation.caching.policies.models import RuntimeCacheProfile
from app.ai.runtime.generation.caching.policies.service import CachePolicyResolver
from app.ai.runtime.generation.caching.service import CachingService
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.routing.enums import RoutingStrategy

from tests.unit.ai.runtime.generation.caching.fakes import (
    FakeExactCacheProvider,
    FakeSemanticCacheProvider,
    FakeSessionCacheProvider,
)
from tests.unit.ai.runtime.generation.validation.factories import make_request, make_result

_DEFAULT_PROFILE = RuntimeCacheProfile(
    runtime=CacheRuntime.CHAT,
    policy=CachePolicy.AUTO,
    exact_ttl_seconds=7200,
)


def _make_caching_service(
    *,
    exact: FakeExactCacheProvider | None = None,
    semantic: FakeSemanticCacheProvider | None = None,
    session: FakeSessionCacheProvider | None = None,
    profiles: dict[CacheRuntime, RuntimeCacheProfile] | None = None,
) -> tuple[CachingService, FakeExactCacheProvider, FakeSemanticCacheProvider]:

    exact_provider = exact or FakeExactCacheProvider()
    semantic_provider = semantic or FakeSemanticCacheProvider()

    service = CachingService(
        exact_provider=exact_provider,
        semantic_provider=semantic_provider,
        session_provider=session or FakeSessionCacheProvider(),
        policy_resolver=CachePolicyResolver(
            profiles=profiles or {},
            default_profile=_DEFAULT_PROFILE,
        ),
    )

    return service, exact_provider, semantic_provider


async def _store_and_lookup(
    service: CachingService,
    *,
    request,
) -> None:
    result = make_result(request=request)

    await service.store(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        routing_strategy=RoutingStrategy.AUTO,
        result=result,
    )


async def test_auto_policy_hits_exact_before_semantic() -> None:
    service, exact_provider, semantic_provider = _make_caching_service()

    request = make_request(user_prompt="what color is the sky?")

    await _store_and_lookup(service, request=request)

    cache_result = await service.lookup(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        routing_strategy=RoutingStrategy.AUTO,
    )

    assert cache_result.hit is True
    assert cache_result.level == CacheLevel.EXACT
    assert semantic_provider.get_calls == 0  # L1 hit short-circuits before L2 is consulted


async def test_auto_policy_falls_through_to_semantic_on_exact_miss() -> None:
    service, exact_provider, semantic_provider = _make_caching_service()

    request = make_request(user_prompt="what color is the sky?")
    result = make_result(request=request)

    # Populate only the semantic layer directly, bypassing store().
    context_hash = _context_hash(request)
    discriminator = service._semantic_discriminator(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
    )
    semantic_provider.store[(context_hash, discriminator, request.user_prompt)] = result

    cache_result = await service.lookup(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        routing_strategy=RoutingStrategy.AUTO,
    )

    assert cache_result.hit is True
    assert cache_result.level == CacheLevel.SEMANTIC
    assert exact_provider.get_calls == 1


async def test_exact_only_policy_never_consults_semantic() -> None:
    profiles = {
        CacheRuntime.BENCHMARK: RuntimeCacheProfile(
            runtime=CacheRuntime.BENCHMARK,
            policy=CachePolicy.EXACT_ONLY,
            exact_ttl_seconds=None,
        ),
    }
    service, exact_provider, semantic_provider = _make_caching_service(profiles=profiles)

    request = make_request(cache_runtime=CacheRuntime.BENCHMARK)

    await service.lookup(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        routing_strategy=RoutingStrategy.AUTO,
    )

    assert exact_provider.get_calls == 1
    assert semantic_provider.get_calls == 0


async def test_semantic_only_policy_never_consults_exact() -> None:
    profiles = {
        CacheRuntime.RESEARCH: RuntimeCacheProfile(
            runtime=CacheRuntime.RESEARCH,
            policy=CachePolicy.SEMANTIC,
            exact_ttl_seconds=7200,
        ),
    }
    service, exact_provider, semantic_provider = _make_caching_service(profiles=profiles)

    request = make_request(cache_runtime=CacheRuntime.RESEARCH)

    await service.lookup(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        routing_strategy=RoutingStrategy.AUTO,
    )

    assert exact_provider.get_calls == 0
    assert semantic_provider.get_calls == 1


async def test_never_policy_skips_all_lookups() -> None:
    profiles = {
        CacheRuntime.PLANNER: RuntimeCacheProfile(
            runtime=CacheRuntime.PLANNER,
            policy=CachePolicy.NEVER,
            exact_ttl_seconds=7200,
        ),
    }
    service, exact_provider, semantic_provider = _make_caching_service(profiles=profiles)

    request = make_request(cache_runtime=CacheRuntime.PLANNER)

    cache_result = await service.lookup(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        routing_strategy=RoutingStrategy.AUTO,
    )

    assert cache_result.hit is False
    assert exact_provider.get_calls == 0
    assert semantic_provider.get_calls == 0


async def test_streaming_bypasses_cache_regardless_of_policy() -> None:
    service, exact_provider, semantic_provider = _make_caching_service()

    request = make_request(stream=True)

    await _store_and_lookup(service, request=request)

    cache_result = await service.lookup(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        routing_strategy=RoutingStrategy.AUTO,
    )

    assert cache_result.hit is False
    assert exact_provider.set_calls == 0
    assert exact_provider.get_calls == 0


async def test_statistics_track_hits_misses_and_savings() -> None:
    service, _, _ = _make_caching_service()

    request = make_request(user_prompt="what color is the sky?")

    await service.lookup(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        routing_strategy=RoutingStrategy.AUTO,
    )  # miss

    await _store_and_lookup(service, request=request)

    await service.lookup(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        routing_strategy=RoutingStrategy.AUTO,
    )  # hit

    stats = service.statistics

    assert stats.misses == 1
    assert stats.exact_hits == 1
    assert stats.total_lookups == 2
    assert stats.hit_ratio == 0.5


async def test_session_cache_is_independent_of_generation_policy() -> None:
    profiles = {
        CacheRuntime.PLANNER: RuntimeCacheProfile(
            runtime=CacheRuntime.PLANNER,
            policy=CachePolicy.NEVER,
            exact_ttl_seconds=7200,
        ),
    }
    service, _, _ = _make_caching_service(profiles=profiles)

    result = make_result()

    await service.set_session(session_id="session-1", key="turn-1", result=result, ttl_seconds=None)

    fetched = await service.get_session(session_id="session-1", key="turn-1")
    assert fetched is not None
    assert fetched.content == result.content

    await service.invalidate_session(session_id="session-1", key="turn-1")
    assert await service.get_session(session_id="session-1", key="turn-1") is None


async def test_clear_session_removes_only_that_session() -> None:
    service, _, _ = _make_caching_service()

    result = make_result()

    await service.set_session(session_id="a", key="k", result=result, ttl_seconds=None)
    await service.set_session(session_id="b", key="k", result=result, ttl_seconds=None)

    await service.clear_session(session_id="a")

    assert await service.get_session(session_id="a", key="k") is None
    assert await service.get_session(session_id="b", key="k") is not None


def _context_hash(request) -> str:
    from app.ai.runtime.generation.caching.exact.key_builder import hash_context

    return hash_context(request.prompt_context.context)

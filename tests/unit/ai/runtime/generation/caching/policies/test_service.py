"""
Unit tests for CachePolicyResolver.

Covers:
- An explicit override always wins over the runtime default
- Each PRD-documented runtime resolves to its documented default policy
- No runtime given falls back to the default profile
- An unrecognized runtime falls back to the default profile
- L1 TTL resolution follows the same precedence
"""

from __future__ import annotations

from app.ai.runtime.generation.caching.enums import CachePolicy, CacheRuntime
from app.ai.runtime.generation.caching.policies.models import RuntimeCacheProfile
from app.ai.runtime.generation.caching.policies.service import CachePolicyResolver

_PROFILES: dict[CacheRuntime, RuntimeCacheProfile] = {
    CacheRuntime.CHAT: RuntimeCacheProfile(
        runtime=CacheRuntime.CHAT,
        policy=CachePolicy.AUTO,
        exact_ttl_seconds=7200,
    ),
    CacheRuntime.RESEARCH: RuntimeCacheProfile(
        runtime=CacheRuntime.RESEARCH,
        policy=CachePolicy.SEMANTIC,
        exact_ttl_seconds=86400,
    ),
    CacheRuntime.BENCHMARK: RuntimeCacheProfile(
        runtime=CacheRuntime.BENCHMARK,
        policy=CachePolicy.EXACT_ONLY,
        exact_ttl_seconds=None,
    ),
    CacheRuntime.PLANNER: RuntimeCacheProfile(
        runtime=CacheRuntime.PLANNER,
        policy=CachePolicy.NEVER,
        exact_ttl_seconds=7200,
    ),
}

_DEFAULT_PROFILE = RuntimeCacheProfile(
    runtime=CacheRuntime.CHAT,
    policy=CachePolicy.AUTO,
    exact_ttl_seconds=7200,
)


def _make_resolver() -> CachePolicyResolver:
    return CachePolicyResolver(
        profiles=_PROFILES,
        default_profile=_DEFAULT_PROFILE,
    )


def test_explicit_override_wins_over_runtime_default() -> None:
    resolver = _make_resolver()

    resolved = resolver.resolve_policy(
        runtime=CacheRuntime.RESEARCH,
        override=CachePolicy.NEVER,
    )

    assert resolved == CachePolicy.NEVER


def test_research_defaults_to_semantic() -> None:
    resolver = _make_resolver()

    assert (
        resolver.resolve_policy(runtime=CacheRuntime.RESEARCH, override=None)
        == CachePolicy.SEMANTIC
    )


def test_benchmark_defaults_to_exact_only_with_infinite_ttl() -> None:
    resolver = _make_resolver()

    assert (
        resolver.resolve_policy(runtime=CacheRuntime.BENCHMARK, override=None)
        == CachePolicy.EXACT_ONLY
    )
    assert resolver.resolve_exact_ttl_seconds(runtime=CacheRuntime.BENCHMARK) is None


def test_planner_defaults_to_never() -> None:
    resolver = _make_resolver()

    assert resolver.resolve_policy(runtime=CacheRuntime.PLANNER, override=None) == CachePolicy.NEVER


def test_no_runtime_falls_back_to_default_profile() -> None:
    resolver = _make_resolver()

    assert resolver.resolve_policy(runtime=None, override=None) == CachePolicy.AUTO
    assert resolver.resolve_exact_ttl_seconds(runtime=None) == 7200


def test_unrecognized_runtime_falls_back_to_default_profile() -> None:
    resolver = CachePolicyResolver(
        profiles={},
        default_profile=_DEFAULT_PROFILE,
    )

    assert resolver.resolve_policy(runtime=CacheRuntime.CRITIC, override=None) == CachePolicy.AUTO

from __future__ import annotations

import structlog
from app.ai.runtime.generation.caching.enums import (
    CachePolicy,
    CacheRuntime,
)
from app.ai.runtime.generation.caching.policies.models import (
    RuntimeCacheProfile,
)

logger = structlog.get_logger()


class CachePolicyResolver:
    """
    Resolves the effective `CachePolicy` and L1 TTL for a request
    (PRD FR-4). An explicit `GenerationRequest.cache_policy` always
    wins; otherwise falls back to the `CacheRuntime` default profile,
    and finally to `default_profile` when no runtime was given either
    — matching `RoutingService._resolve_profile`'s fallback-to-AUTO
    shape for an unrecognized/absent strategy.
    """

    def __init__(
        self,
        *,
        profiles: dict[CacheRuntime, RuntimeCacheProfile],
        default_profile: RuntimeCacheProfile,
    ) -> None:
        self._profiles = profiles

        self._default_profile = default_profile

    def resolve_policy(
        self,
        *,
        runtime: CacheRuntime | None,
        override: CachePolicy | None,
    ) -> CachePolicy:

        if override is not None:
            return override

        return self._resolve_profile(
            runtime,
        ).policy

    def resolve_exact_ttl_seconds(
        self,
        *,
        runtime: CacheRuntime | None,
    ) -> int | None:

        return self._resolve_profile(
            runtime,
        ).exact_ttl_seconds

    def _resolve_profile(
        self,
        runtime: CacheRuntime | None,
    ) -> RuntimeCacheProfile:

        if runtime is None:
            return self._default_profile

        profile = self._profiles.get(
            runtime,
        )

        if profile is not None:
            return profile

        logger.warning(
            "caching.policy.unknown_runtime_fallback_to_default",
            runtime=runtime.value,
        )

        return self._default_profile

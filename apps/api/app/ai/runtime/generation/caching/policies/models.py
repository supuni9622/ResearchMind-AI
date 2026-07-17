from __future__ import annotations

from app.ai.runtime.generation.caching.enums import (
    CachePolicy,
    CacheRuntime,
)
from pydantic import (
    BaseModel,
    ConfigDict,
)


class RuntimeCacheProfile(
    BaseModel,
):
    """
    Everything policy resolution needs to know about a `CacheRuntime`:
    its default `CachePolicy` and its L1 Exact Cache TTL (PRD "Default
    Runtime Policies" / "TTL Recommendations"). Semantic/session TTLs
    are not runtime-specific per the PRD, so they aren't modeled here
    — see `settings.semantic_cache_ttl_seconds` /
    `settings.session_cache_default_ttl_seconds`.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    runtime: CacheRuntime

    policy: CachePolicy

    exact_ttl_seconds: int | None
    """`None` means infinite (no expiry) — used by Benchmark."""

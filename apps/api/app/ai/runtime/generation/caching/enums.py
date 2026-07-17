from __future__ import annotations

from enum import StrEnum


class CacheLevel(StrEnum):
    EXACT = "exact"

    SEMANTIC = "semantic"

    SESSION = "session"


class CachePolicy(StrEnum):
    """
    How a `GenerationRequest` should interact with the Runtime Caching
    Platform. Resolved by `policies/service.py::CachePolicyResolver`
    from an explicit `GenerationRequest.cache_policy` override, or
    else a `CacheRuntime` default (see `policies/models.py`).
    """

    AUTO = "auto"
    """Try L1 Exact, then L2 Semantic. Both are populated on a miss."""

    NEVER = "never"
    """Bypass caching entirely — no lookup, no store."""

    EXACT_ONLY = "exact_only"
    """Only L1 Exact is consulted/populated."""

    SEMANTIC = "semantic"
    """Only L2 Semantic is consulted/populated."""

    SESSION = "session"
    """Only L3 Session is consulted/populated (see `CachingService.get_session`/`set_session`)."""


class CacheRuntime(StrEnum):
    """
    Which runtime is issuing the request, used to look up the default
    `CachePolicy` and (for L1) TTL — see PRD "Default Runtime Policies".
    Distinct from `routing.enums.RoutingStrategy`, which describes a
    task objective for model selection rather than a caching profile.
    """

    CHAT = "chat"

    RESEARCH = "research"

    BENCHMARK = "benchmark"

    PLANNER = "planner"

    TOOL_AGENT = "tool_agent"

    SUMMARIZER = "summarizer"

    REVIEWER = "reviewer"

    CRITIC = "critic"

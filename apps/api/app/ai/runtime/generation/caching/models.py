from __future__ import annotations

from app.ai.runtime.generation.caching.enums import (
    CacheLevel,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.routing.enums import (
    RoutingStrategy,
)
from pydantic import (
    BaseModel,
    ConfigDict,
)


class CacheKey(
    BaseModel,
):
    """
    Every field that must match for two requests to be considered
    identical for L1 Exact Cache purposes (PRD "Exact Cache Design"
    / architecture.md "L1 Exact Cache" — the two canonical docs agree
    on this field set).

    `top_p` is carried for forward compatibility: no provider config
    in this codebase exposes it today, so it is always `None` in
    practice until one does.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    provider: GenerationProvider

    model: str

    routing_strategy: RoutingStrategy | None

    prompt_hash: str

    context_hash: str

    schema_hash: str

    temperature: float | None

    top_p: float | None

    def redis_key(
        self,
    ) -> str:
        """
        Deterministic Valkey key. Field order is fixed (matches
        declaration order above) so the same logical key always
        serializes identically.
        """

        parts = [
            self.provider.value,
            self.model,
            self.routing_strategy.value if self.routing_strategy else "-",
            self.prompt_hash,
            self.context_hash,
            self.schema_hash,
            f"{self.temperature:.4f}" if self.temperature is not None else "-",
            f"{self.top_p:.4f}" if self.top_p is not None else "-",
        ]

        return "cache:exact:" + ":".join(parts)


class CacheResult(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    hit: bool

    level: CacheLevel | None = None

    generation_result: GenerationResult | None = None

    similarity: float | None = None
    """Only set on an L2 Semantic Cache hit — cosine similarity of the matched prompt."""

    lookup_latency_ms: float = 0


class CacheStatistics(
    BaseModel,
):
    """
    In-memory, process-local counters (FR-5). Not persisted — a
    restart resets them, matching how `RoutingService`/`ValidationService`
    carry no cross-process state either.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    exact_hits: int = 0

    semantic_hits: int = 0

    session_hits: int = 0

    misses: int = 0

    tokens_saved: int = 0

    cost_saved: float = 0

    @property
    def total_lookups(
        self,
    ) -> int:
        return self.exact_hits + self.semantic_hits + self.session_hits + self.misses

    @property
    def hit_ratio(
        self,
    ) -> float:
        total = self.total_lookups

        if total == 0:
            return 0.0

        hits = self.exact_hits + self.semantic_hits + self.session_hits

        return hits / total

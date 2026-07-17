from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from app.ai.runtime.generation.catalog.models import (
    ModelMetadata,
)
from app.ai.runtime.generation.routing.enums import (
    RequiredCapability,
    RoutingStrategy,
)
from app.ai.runtime.generation.routing.scoring.weights import (
    ScoringWeights,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class RoutingStrategyProfile(
    BaseModel,
):
    """
    Everything strategy resolution needs to know about a
    `RoutingStrategy`: how to score candidates, and any hard
    requirements they must already meet before scoring runs.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    strategy: RoutingStrategy

    weights: ScoringWeights

    required_capabilities: list[RequiredCapability] = Field(
        default_factory=list,
    )

    min_context_window: int | None = None

    require_local: bool = False
    """
    Narrows candidates to `ModelMetadata.local == True` and implicitly
    lifts the experimental/local policy gates — set only by the LOCAL
    strategy, whose entire point is to opt into the local catalog.
    """


class RoutingRequest(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    strategy: RoutingStrategy = RoutingStrategy.AUTO

    required_capabilities: list[RequiredCapability] = Field(
        default_factory=list,
    )

    min_context_window: int | None = Field(
        default=None,
        ge=0,
    )

    allow_experimental: bool = False

    allow_local: bool = False

    excluded_models: list[str] = Field(
        default_factory=list,
        description="model_name values to skip, e.g. already tried by a caller-side fallback loop.",
    )

    max_fallbacks: int = Field(
        default=2,
        ge=0,
        le=10,
    )

    request_id: UUID = Field(
        default_factory=uuid4,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class RoutingDecision(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    request_id: UUID

    strategy: RoutingStrategy

    selected_model: ModelMetadata

    fallback_models: list[ModelMetadata] = Field(
        default_factory=list,
    )

    score: float

    reasons: list[str] = Field(
        default_factory=list,
    )

    evaluated_count: int = 0
    """How many candidates survived capability/policy filtering and were scored."""

    routing_latency_ms: float = 0

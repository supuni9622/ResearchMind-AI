# Research request/response models.

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.context.citations.models import Citation
from app.ai.research.models import ResearchSource
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.routing.enums import RoutingStrategy

# ==========================================================
# Requests
# ==========================================================


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)

    top_k: int = Field(default=10, ge=1, le=100)

    filters: dict[str, Any] = Field(default_factory=dict)

    provider: GenerationProvider | None = None

    routing_strategy: RoutingStrategy | None = None

    conversation_id: UUID | None = Field(
        default=None,
        description=(
            "Links this call to a continuing research conversation -- "
            "prior turns are folded into the prompt and session memory "
            "is scoped to the conversation, not just this one call. Omit "
            "to start a new, single-turn conversation (its id is "
            "returned in the response so a caller can continue it)."
        ),
    )


class ResearchStreamRequest(ResearchRequest):
    """
    Identical shape to `ResearchRequest` -- kept as its own type (rather
    than reusing `ResearchRequest` directly) since the two routes evolve
    independently per the PRD's separate `/research` and `/research/
    stream` contracts.
    """


class ResearchCitationsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)

    top_k: int = Field(default=10, ge=1, le=100)

    filters: dict[str, Any] = Field(default_factory=dict)


# ==========================================================
# Responses
# ==========================================================


class ResearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    research_id: UUID

    conversation_id: UUID

    query: str

    answer: str

    citations: list[Citation]

    sources: list[ResearchSource]

    duration_ms: float


class ResearchSessionResponse(BaseModel):
    """
    `GET /research/{id}` response (PRD §7) -- deliberately not a subtype
    of `ResearchResponse`: it has no `duration_ms` (that only means
    something for the request that produced it, not a replay) and the
    ORM row's primary key is `id`, not `research_id`, so the route
    builds this explicitly rather than via `model_validate`.
    """

    model_config = ConfigDict(extra="forbid")

    research_id: UUID

    conversation_id: UUID | None

    query: str

    answer: str

    citations: list[Citation]

    sources: list[ResearchSource]

    created_at: datetime


class ResearchCitationsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citations: list[Citation]


class ResearchConversationSummary(BaseModel):
    """
    One row of `GET /research/conversations` -- enough to render a
    "History" sidebar entry without fetching every turn.
    """

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID

    title: str | None

    created_at: datetime

    updated_at: datetime


class ResearchConversationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversations: list[ResearchConversationSummary]


class ResearchConversationResponse(BaseModel):
    """
    `GET /research/conversations/{id}` response -- every turn in the
    thread, oldest first, so a client can replay the whole conversation
    the same way it already replays a single turn via
    `ResearchSessionResponse`.
    """

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID

    title: str | None

    turns: list[ResearchSessionResponse]

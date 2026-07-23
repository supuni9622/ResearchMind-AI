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
from app.ai.runtime.research.planner.models import ResearchComplexity, ResearchPlan
from app.ai.runtime.research.types import ResearchProposalStatus, ResearchRunStatus

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


class ResearchProposalRequest(ResearchRequest):
    """Explicit request to plan Deep Research; it does not begin a run."""


class ResearchReportDecisionRequest(BaseModel):
    """Body for `POST /research/runs/{id}/report-decision` (the report-approval
    interrupt checkpoint) -- distinct from `ResearchProposalRequest`'s plan
    approval, which happens before a run exists at all."""

    model_config = ConfigDict(extra="forbid")

    approved: bool

    reason: str | None = Field(default=None, max_length=1_000)


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

    research_run_id: UUID | None = None

    conversation_id: UUID

    query: str

    answer: str

    citations: list[Citation]

    sources: list[ResearchSource]

    duration_ms: float


class ResearchReportDownloadResponse(BaseModel):
    """Short-lived, owner-authorized URL for a final research-report PDF."""

    model_config = ConfigDict(extra="forbid")

    research_run_id: UUID
    download_url: str
    expires_in_seconds: int = 300


class ResearchRunResponse(BaseModel):
    """Owner-safe lifecycle view; graph state and artifact keys stay private."""

    model_config = ConfigDict(extra="forbid")

    research_run_id: UUID
    status: ResearchRunStatus
    current_phase: str | None = None
    attempt_count: int = Field(ge=0)
    cancellation_requested: bool
    research_id: UUID | None = None
    conversation_id: UUID | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ResearchProposalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: UUID
    status: ResearchProposalStatus
    conversation_id: UUID | None = None
    plan: ResearchPlan
    created_at: datetime


class ResearchEscalationCheckResponse(BaseModel):
    """`POST /research/escalation-check` -- classifies a query without
    committing to Deep Research. `proposal` is only populated when
    `suggested` is true (see `ResearchProposalService.check_escalation`);
    accepting the suggestion approves that same `proposal.proposal_id`
    rather than creating a new one."""

    model_config = ConfigDict(extra="forbid")

    suggested: bool
    complexity: ResearchComplexity
    reason: str
    proposal: ResearchProposalResponse | None = None


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

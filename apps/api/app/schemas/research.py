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
from app.ai.runtime.research.web_search.models import WebSearchMode

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

    project_id: UUID | None = Field(
        default=None,
        description=(
            "Only consulted when starting a new conversation (no "
            "`conversation_id`) -- an existing conversation keeps "
            "whatever project it already belongs to. Authorized "
            "server-side before the conversation is created."
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
    """Explicit request to plan Deep Research; it does not begin a run.

    The web-search fields below are deliberately only on this subclass, not
    the base `ResearchRequest` -- Linear Research (`/research`, `/research/
    stream`) has no LangGraph runtime/interrupt machinery to act on them, so
    keeping them off that contract avoids implying a capability that
    doesn't exist there (web_search_tool_platform_prd.md §31)."""

    web_search_mode: WebSearchMode = WebSearchMode.DISABLED

    web_search_auto_approve: bool = Field(
        default=False,
        description=(
            "Pre-authorize web search: when the agent decides a web search "
            "would help (AUTO mode), proceed without pausing for approval. "
            "Ignored when web_search_mode is DISABLED or REQUIRED (REQUIRED "
            "never pauses -- it was already explicitly requested)."
        ),
    )

    include_domains: list[str] = Field(default_factory=list, max_length=20)

    exclude_domains: list[str] = Field(default_factory=list, max_length=20)

    paper_suggestions_enabled: bool = Field(
        default=False,
        description=(
            "Opt-in, non-blocking: after the report is persisted, suggest "
            "related papers via the Research Intelligence MCP server "
            "(prds/3. mcp_server_setup.md) and emit it purely as run "
            "events -- never gates or pauses the run, unlike web search's "
            "approval checkpoint."
        ),
    )

    socratic_challenger_enabled: bool = Field(
        default=False,
        description=(
            "Opt in to one evidence-aware Socratic question at the existing "
            "pre-synthesis plan checkpoint. The answer is stored as research memory."
        ),
    )


class ResearchDraftFindingEdit(BaseModel):
    """One edited findings section -- keeps the original's `citation_ids`
    (not user-editable here, so an edit can never invalidate the draft's
    citation integrity; see `ResearchRunService.record_report_decision`)."""

    model_config = ConfigDict(extra="forbid")

    heading: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=6_000)


class ResearchDraftEdit(BaseModel):
    """Free-text edits to a pending draft, submitted alongside approval.
    Deliberately excludes `citation_ids`/`schema_version`/`limitations` --
    those are carried over from the original draft unchanged, so an edit
    can only reword content, never introduce an unsupported citation."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    abstract: str = Field(min_length=1, max_length=2_000)
    methodology: str = Field(min_length=1, max_length=2_000)
    findings: list[ResearchDraftFindingEdit] = Field(min_length=1, max_length=8)
    discussion: str = Field(min_length=1, max_length=4_000)
    conclusion: str = Field(min_length=1, max_length=2_000)


class ResearchReportDecisionRequest(BaseModel):
    """Body for `POST /research/runs/{id}/report-decision` (the report-approval
    interrupt checkpoint) -- distinct from `ResearchProposalRequest`'s plan
    approval, which happens before a run exists at all."""

    model_config = ConfigDict(extra="forbid")

    approved: bool

    reason: str | None = Field(default=None, max_length=1_000)

    # Only meaningful when `approved` -- an unapproved decision with edits
    # attached is treated as a plain rejection (see
    # `ResearchRunService.record_report_decision`).
    edited_draft: ResearchDraftEdit | None = None


class ResearchPlanGoalEdit(BaseModel):
    """Free-text edit to the plan's synthesis-driving goal, submitted
    alongside plan approval. `tasks`/`complexity` aren't editable here --
    retrieval for the plan's original tasks has already run by the time
    evidence exists to review, so changing them wouldn't retroactively
    affect what was retrieved (see `ResearchRunService.record_plan_decision`)."""

    model_config = ConfigDict(extra="forbid")

    rewritten_goal: str = Field(min_length=1, max_length=4_000)


class ResearchPlanDecisionRequest(BaseModel):
    """Body for `POST /research/runs/{id}/plan-decision` (the plan-approval
    interrupt checkpoint -- reached after retrieval/evidence-aggregation but
    before the costly synthesis call) -- distinct from both
    `ResearchProposalRequest`'s earlier, pre-run plan approval and
    `ResearchReportDecisionRequest`'s later report approval."""

    model_config = ConfigDict(extra="forbid")

    approved: bool

    reason: str | None = Field(default=None, max_length=1_000)

    # Only meaningful when `approved` -- mirrors `ResearchReportDecisionRequest.edited_draft`.
    edited_plan: ResearchPlanGoalEdit | None = None

    socratic_response: str | None = Field(default=None, min_length=1, max_length=4_000)


class ResearchWebSearchDecisionRequest(BaseModel):
    """Body for `POST /research/runs/{id}/web-search-decision` (the
    web-search-approval interrupt checkpoint, only reached in AUTO mode
    without `web_search_auto_approve`). No `edited_*` field -- unlike a
    rejected plan/report, a rejected web-search suggestion has nothing to
    edit; the run simply continues via the existing document-only
    gap-research path (see `ResearchRunService.record_web_search_decision`)."""

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
    expires_in_seconds: int
    generation_id: UUID | None = Field(
        default=None,
        description=(
            "The synthesis call's generation_id (E21), read from the persisted "
            "final-report.json artifact -- None for reports persisted before this "
            "field existed, or if the JSON artifact is unexpectedly missing/corrupt "
            "(best-effort: never fails the download itself)."
        ),
    )
    memory_used: bool = False


class ResearchDraftFindingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str
    content: str
    citation_ids: list[str]


class ResearchDraftCitationResponse(BaseModel):
    """A citation resolved to its filename (not the raw document UUID --
    see the same fix in `pdf.py::_append_references`)."""

    model_config = ConfigDict(extra="forbid")

    citation_id: str
    filename: str
    excerpt: str
    score: float


class ResearchDraftReviewSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
    citation_integrity_score: float
    completeness_score: float
    limitations: list[str]
    model_quality_score: float | None
    gap_questions: list[str]


class ResearchDraftResponse(BaseModel):
    """`GET /research/runs/{id}/draft` -- the report awaiting approval, read
    directly from the paused run's LangGraph checkpoint (see
    `ResearchDraftInspectionService`). Only available while the run is
    `awaiting_approval`."""

    model_config = ConfigDict(extra="forbid")

    research_run_id: UUID
    title: str
    abstract: str
    methodology: str
    findings: list[ResearchDraftFindingResponse]
    discussion: str
    conclusion: str
    limitations: list[str]
    citations: list[ResearchDraftCitationResponse]
    review: ResearchDraftReviewSummary


class ResearchPendingPlanTaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    question: str


class ResearchPendingPlanEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    completed_task_count: int
    failed_task_count: int
    warning_count: int


class ResearchPendingPlanResponse(BaseModel):
    """`GET /research/runs/{id}/plan` -- the plan and the evidence already
    gathered for it, awaiting approval before the synthesis call is spent.
    Read directly from the paused run's LangGraph checkpoint (see
    `ResearchPlanInspectionService`). Only available while the run is
    `awaiting_plan_approval`."""

    model_config = ConfigDict(extra="forbid")

    research_run_id: UUID
    goal: str
    rewritten_goal: str | None
    complexity: ResearchComplexity
    tasks: list[ResearchPendingPlanTaskResponse]
    evidence: ResearchPendingPlanEvidenceSummary
    citations: list[ResearchDraftCitationResponse]
    socratic_question: str | None = None


class ResearchPendingWebSearchResponse(BaseModel):
    """`GET /research/runs/{id}/web-search` -- the agent's web-search
    suggestion awaiting approval, read directly from the paused run's
    LangGraph checkpoint (see `ResearchWebSearchInspectionService`). Only
    available while the run is `awaiting_web_search_approval`."""

    model_config = ConfigDict(extra="forbid")

    research_run_id: UUID
    suggested_query: str
    reason: str
    gap_question: str | None


class ResearchRunResponse(BaseModel):
    """Owner-safe lifecycle view; graph state and artifact keys stay private."""

    model_config = ConfigDict(extra="forbid")

    research_run_id: UUID
    status: ResearchRunStatus
    current_phase: str | None = None
    attempt_count: int = Field(ge=0)
    retry_count: int = Field(ge=0)
    cancellation_requested: bool
    research_id: UUID | None = None
    conversation_id: UUID | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    # A short, fixed reason code for why a terminal run ended a particular
    # way (e.g. `"report_rejected_returned_as_answer"`) -- never a raw
    # exception message (those stay in the private `error_summary` column).
    # Lets a client tell "rejected, but the answer still published" apart
    # from "PDF still being prepared" without guessing from a failed
    # download fetch.
    terminal_reason: str | None = None


class ResearchProposalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: UUID
    status: ResearchProposalStatus
    conversation_id: UUID | None = None
    # The user's literal original question, not `plan.goal` (which is the
    # planner LLM's own restatement) -- needed verbatim to reconstruct a
    # Deep Research turn's displayed query when replaying a conversation
    # after a page refresh (see `use-deep-research.ts`'s
    # `hydrateFromConversation`).
    query: str
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

    generation_id: UUID | None = None

    memory_used: bool = False

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


class DeepResearchTurnResponse(BaseModel):
    """One Deep Research turn in a conversation replay -- pairs the
    approved plan with its execution lifecycle record so a client can
    reconstruct the same UI it shows for a run in progress, even for one
    that's still running, awaiting approval, or long since terminal."""

    model_config = ConfigDict(extra="forbid")

    proposal: ResearchProposalResponse
    run: ResearchRunResponse


class ResearchConversationResponse(BaseModel):
    """
    `GET /research/conversations/{id}` response -- every turn in the
    thread, oldest first, so a client can replay the whole conversation
    the same way it already replays a single turn via
    `ResearchSessionResponse`. `deep_research_runs` is separate from
    `turns` (rather than merged into one list) because a Deep Research run
    only produces a `ResearchSession` turn once it completes -- an
    in-flight or awaiting-approval run has no session yet, so it would be
    invisible to a client that only reads `turns`.
    """

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID

    title: str | None

    turns: list[ResearchSessionResponse]

    deep_research_runs: list[DeepResearchTurnResponse] = Field(default_factory=list)

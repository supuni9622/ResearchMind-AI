from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.ai.research.service import ResearchService
from app.ai.runtime.events.enums import EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.generation.streaming.transports.sse import sse_stream_response
from app.ai.runtime.research.draft_inspection import (
    PendingDraftUnavailableError,
    ResearchDraftInspectionService,
)
from app.ai.runtime.research.exceptions import ResearchQueueSaturatedError
from app.ai.runtime.research.plan_inspection import (
    PendingPlanUnavailableError,
    ResearchPlanInspectionService,
)
from app.ai.runtime.research.planner.models import ResearchComplexity, ResearchPlan
from app.ai.runtime.research.proposal_service import ResearchProposalService
from app.ai.runtime.research.report_download import ResearchReportDownloadService
from app.ai.runtime.research.run_service import ResearchRunService
from app.ai.runtime.research.types import ResearchProposalStatus, ResearchRunStatus
from app.ai.runtime.research.web_search_inspection import (
    PendingWebSearchUnavailableError,
    ResearchWebSearchInspectionService,
)
from app.auth.dependencies import get_current_user
from app.core.settings import settings
from app.dependencies.generation_usage import get_generation_usage_repository
from app.dependencies.project import get_project_authorization_service
from app.dependencies.rate_limiting import enforce_rate_limit, get_rate_limiter
from app.dependencies.research import (
    get_research_conversation_service,
    get_research_draft_inspection_service,
    get_research_plan_inspection_service,
    get_research_proposal_repository,
    get_research_proposal_service,
    get_research_report_download_service,
    get_research_repository,
    get_research_run_event_repository,
    get_research_run_repository,
    get_research_run_service,
    get_research_service,
    get_research_web_search_inspection_service,
)
from app.exceptions.base import NotFoundException, ServiceUnavailableException
from app.infrastructure.rate_limiting import ValkeyRateLimiter
from app.models.research import ResearchSession
from app.models.research_proposal import ResearchProposal
from app.models.research_run import ResearchRun
from app.models.user import User
from app.repositories.generation_usage import GenerationUsageRepository
from app.repositories.research import ResearchRepository
from app.repositories.research_proposal import ResearchProposalRepository
from app.repositories.research_run import ResearchRunRepository
from app.repositories.research_run_event import ResearchRunEventRepository
from app.schemas.generation_usage import ConversationUsageSummary
from app.schemas.research import (
    DeepResearchTurnResponse,
    ResearchCitationsRequest,
    ResearchCitationsResponse,
    ResearchConversationListResponse,
    ResearchConversationResponse,
    ResearchConversationSummary,
    ResearchDraftCitationResponse,
    ResearchDraftFindingResponse,
    ResearchDraftResponse,
    ResearchDraftReviewSummary,
    ResearchEscalationCheckResponse,
    ResearchPendingPlanEvidenceSummary,
    ResearchPendingPlanResponse,
    ResearchPendingPlanTaskResponse,
    ResearchPendingWebSearchResponse,
    ResearchPlanDecisionRequest,
    ResearchProposalRequest,
    ResearchProposalResponse,
    ResearchReportDecisionRequest,
    ResearchReportDownloadResponse,
    ResearchRequest,
    ResearchResponse,
    ResearchRunResponse,
    ResearchSessionResponse,
    ResearchStreamRequest,
    ResearchWebSearchDecisionRequest,
)
from app.services.project_authorization import ProjectAuthorizationService
from app.services.research_conversation import ResearchConversationService

router = APIRouter(
    prefix="/research",
    tags=["Research"],
)

# The generic SSE transport defaults to a ceiling tuned for chat/generation
# streams (seconds-to-low-minutes). A Deep Research run's progress feed can
# legitimately run for the runtime's full duration budget (see
# ResearchPlanningPolicy.max_duration_seconds, currently <=600s for COMPLEX
# plans); give this route enough headroom that plans don't get force-closed
# mid-run. See ADR-034.
RESEARCH_RUN_EVENTS_MAX_STREAM_DURATION_SECONDS = 1800


def _session_response(research_session: ResearchSession) -> ResearchSessionResponse:
    runtime_metadata = research_session.runtime_metadata or {}
    raw_generation_id = runtime_metadata.get("generation_id")
    try:
        generation_id = UUID(str(raw_generation_id)) if raw_generation_id else None
    except (TypeError, ValueError):
        generation_id = None
    return ResearchSessionResponse(
        research_id=research_session.id,
        conversation_id=research_session.conversation_id,
        query=research_session.query,
        answer=research_session.answer,
        citations=research_session.citations,
        sources=research_session.sources,
        generation_id=generation_id,
        memory_used=bool(runtime_metadata.get("memory_used", False)),
        created_at=research_session.created_at,
    )


def _run_response(run: ResearchRun) -> ResearchRunResponse:
    return ResearchRunResponse(
        research_run_id=run.id,
        status=ResearchRunStatus(run.status),
        current_phase=run.current_phase,
        attempt_count=run.attempt_count,
        retry_count=run.retry_count,
        cancellation_requested=run.cancellation_requested,
        research_id=run.research_session_id,
        conversation_id=run.conversation_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        terminal_reason=run.terminal_reason,
    )


def _proposal_response(proposal: ResearchProposal) -> ResearchProposalResponse:
    return ResearchProposalResponse(
        proposal_id=proposal.id,
        status=ResearchProposalStatus(proposal.status),
        conversation_id=proposal.conversation_id,
        query=str(proposal.request["query"]),
        plan=ResearchProposalService.plan(proposal),
        created_at=proposal.created_at,
    )


def _escalation_reason(plan: ResearchPlan) -> str:
    """Deterministic, user-safe justification derived from the plan's own
    fields -- not freeform LLM text, so it can't drift from what the plan
    actually says or introduce injected/off-tone copy."""

    if plan.complexity == ResearchComplexity.SIMPLE:
        return "This looks like a single, focused question."
    if len(plan.tasks) > 1:
        return (
            f"This looks like it needs evidence gathered from {len(plan.tasks)} different "
            "angles and synthesized together."
        )
    return "This looks like it needs deeper, multi-step analysis than a single answer can cover."


async def _check_linear_research_rate_limit(
    *, rate_limiter: ValkeyRateLimiter, owner_id: UUID
) -> None:
    """Shared by `/research`, `/research/stream`, `/research/citations` --
    one bucket per owner across all three, since they draw on the same
    retrieval/generation cost pool from the caller's perspective."""

    await enforce_rate_limit(
        rate_limiter,
        scope="research",
        owner_id=owner_id,
        limit=settings.research_rate_limit_requests,
        window_seconds=settings.research_rate_limit_window_seconds,
    )


async def _check_deep_research_proposal_rate_limit(
    *, rate_limiter: ValkeyRateLimiter, owner_id: UUID
) -> None:
    """Each proposal is an uncached planner LLM call."""

    await enforce_rate_limit(
        rate_limiter,
        scope="deep_research_proposal",
        owner_id=owner_id,
        limit=settings.deep_research_proposal_rate_limit_requests,
        window_seconds=settings.deep_research_proposal_rate_limit_window_seconds,
    )


async def _check_deep_research_approval_rate_limit(
    *, rate_limiter: ValkeyRateLimiter, owner_id: UUID
) -> None:
    """Each approval queues a real multi-step, multi-LLM-call run --
    the single most expensive action in the product (see
    PRODUCT_FLOWS_AND_GAPS.md, Loophole D3)."""

    await enforce_rate_limit(
        rate_limiter,
        scope="deep_research_approval",
        owner_id=owner_id,
        limit=settings.deep_research_approval_rate_limit_requests,
        window_seconds=settings.deep_research_approval_rate_limit_window_seconds,
    )


@router.post(
    "/proposals",
    response_model=ResearchProposalResponse,
    summary="Propose a bounded Deep Research plan without starting a research run",
)
async def create_research_proposal(
    payload: ResearchProposalRequest,
    current_user: User = Depends(get_current_user),
    proposals: ResearchProposalService = Depends(get_research_proposal_service),
    rate_limiter: ValkeyRateLimiter = Depends(get_rate_limiter),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> ResearchProposalResponse:
    await _check_deep_research_proposal_rate_limit(
        rate_limiter=rate_limiter, owner_id=current_user.id
    )
    await project_authorization.authorize_for_new_conversation(
        conversation_id=payload.conversation_id,
        project_id=payload.project_id,
        user_id=current_user.id,
    )
    proposal = await proposals.propose(
        query=payload.query,
        top_k=payload.top_k,
        filters=payload.filters,
        owner_id=current_user.id,
        provider=payload.provider,
        routing_strategy=payload.routing_strategy,
        conversation_id=payload.conversation_id,
        project_id=payload.project_id,
        web_search_mode=payload.web_search_mode.value,
        web_search_auto_approve=payload.web_search_auto_approve,
        include_domains=payload.include_domains,
        exclude_domains=payload.exclude_domains,
        paper_suggestions_enabled=payload.paper_suggestions_enabled,
    )
    return _proposal_response(proposal)


@router.post(
    "/escalation-check",
    response_model=ResearchEscalationCheckResponse,
    summary="Check whether a query would benefit from Deep Research, without committing to it",
)
async def check_research_escalation(
    payload: ResearchProposalRequest,
    current_user: User = Depends(get_current_user),
    proposals: ResearchProposalService = Depends(get_research_proposal_service),
    rate_limiter: ValkeyRateLimiter = Depends(get_rate_limiter),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> ResearchEscalationCheckResponse:
    """Backs the Research UI's "this looks like it needs Deep Research"
    suggestion (explicit-consent escalation, never automatic -- see
    RESEARCH_RUNTIME_IMPLEMENTATION_TRACKER.md). Shares the proposal-creation
    rate-limit bucket: it runs the same uncached planner call and, for a
    suggested (non-SIMPLE) result, persists the same kind of proposal row.
    """

    await _check_deep_research_proposal_rate_limit(
        rate_limiter=rate_limiter, owner_id=current_user.id
    )
    await project_authorization.authorize_for_new_conversation(
        conversation_id=payload.conversation_id,
        project_id=payload.project_id,
        user_id=current_user.id,
    )
    plan, proposal = await proposals.check_escalation(
        query=payload.query,
        top_k=payload.top_k,
        filters=payload.filters,
        owner_id=current_user.id,
        provider=payload.provider,
        routing_strategy=payload.routing_strategy,
        conversation_id=payload.conversation_id,
        project_id=payload.project_id,
    )
    return ResearchEscalationCheckResponse(
        suggested=proposal is not None,
        complexity=plan.complexity,
        reason=_escalation_reason(plan),
        proposal=_proposal_response(proposal) if proposal is not None else None,
    )


@router.post(
    "/proposals/{proposal_id}/approve",
    response_model=ResearchRunResponse,
    summary="Approve a Deep Research plan and create its durable runtime record",
)
async def approve_research_proposal(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    proposals: ResearchProposalService = Depends(get_research_proposal_service),
    rate_limiter: ValkeyRateLimiter = Depends(get_rate_limiter),
) -> ResearchRunResponse:
    """Authorize exactly one run; the dedicated worker executes it later."""

    await _check_deep_research_approval_rate_limit(
        rate_limiter=rate_limiter, owner_id=current_user.id
    )
    try:
        run = await proposals.approve(proposal_id=proposal_id, owner_id=current_user.id)
    except ResearchQueueSaturatedError as exc:
        raise ServiceUnavailableException(
            message=str(exc),
            retry_after_seconds=settings.deep_research_queue_full_retry_after_seconds,
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None:
        raise NotFoundException(message=f"Research proposal '{proposal_id}' was not found.")
    return _run_response(run)


@router.post(
    "",
    response_model=ResearchResponse,
    summary="Ask a research question and receive a grounded, cited answer",
)
async def create_research(
    payload: ResearchRequest,
    current_user: User = Depends(get_current_user),
    research_service: ResearchService = Depends(get_research_service),
    rate_limiter: ValkeyRateLimiter = Depends(get_rate_limiter),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> ResearchResponse:
    """Keep the established linear API independent of runtime feature flags."""

    await _check_linear_research_rate_limit(rate_limiter=rate_limiter, owner_id=current_user.id)

    await project_authorization.authorize_for_new_conversation(
        conversation_id=payload.conversation_id,
        project_id=payload.project_id,
        user_id=current_user.id,
    )

    outcome = await research_service.research(
        query=payload.query,
        top_k=payload.top_k,
        filters=payload.filters,
        owner_id=current_user.id,
        provider=payload.provider,
        routing_strategy=payload.routing_strategy,
        conversation_id=payload.conversation_id,
        project_id=payload.project_id,
    )

    return ResearchResponse(
        research_id=outcome.research_id,
        research_run_id=outcome.research_run_id,
        conversation_id=outcome.conversation_id,
        query=outcome.query,
        answer=outcome.answer,
        citations=outcome.citations,
        sources=outcome.sources,
        duration_ms=outcome.duration_ms,
    )


@router.post(
    "/stream",
    summary="Stream a research answer over Server-Sent Events",
)
async def stream_research(
    payload: ResearchStreamRequest,
    current_user: User = Depends(get_current_user),
    research_service: ResearchService = Depends(get_research_service),
    rate_limiter: ValkeyRateLimiter = Depends(get_rate_limiter),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> StreamingResponse:
    await _check_linear_research_rate_limit(rate_limiter=rate_limiter, owner_id=current_user.id)

    await project_authorization.authorize_for_new_conversation(
        conversation_id=payload.conversation_id,
        project_id=payload.project_id,
        user_id=current_user.id,
    )

    events = research_service.stream_research(
        query=payload.query,
        top_k=payload.top_k,
        filters=payload.filters,
        owner_id=current_user.id,
        provider=payload.provider,
        routing_strategy=payload.routing_strategy,
        conversation_id=payload.conversation_id,
        project_id=payload.project_id,
    )

    return sse_stream_response(events)


@router.get(
    "/conversations",
    response_model=ResearchConversationListResponse,
    summary="List this user's research conversations, most recently updated first",
)
async def list_research_conversations(
    # Omitted -> personal conversations only (`project_id IS NULL`), not
    # "every project" -- same contract as `GET /chat/conversations`.
    project_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    repository: ResearchRepository = Depends(get_research_repository),
) -> ResearchConversationListResponse:
    conversations = await repository.list_conversations_for_owner(
        owner_id=current_user.id, project_id=project_id
    )

    return ResearchConversationListResponse(
        conversations=[
            ResearchConversationSummary(
                conversation_id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
            for conversation in conversations
        ],
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ResearchConversationResponse,
    summary="Replay every turn of a research conversation, oldest first",
)
async def get_research_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    repository: ResearchRepository = Depends(get_research_repository),
    conversation_service: ResearchConversationService = Depends(get_research_conversation_service),
    runs: ResearchRunRepository = Depends(get_research_run_repository),
    proposals: ResearchProposalRepository = Depends(get_research_proposal_repository),
) -> ResearchConversationResponse:
    conversation = await conversation_service.get_or_create(
        conversation_id=conversation_id,
        owner_id=current_user.id,
    )

    sessions = await repository.list_sessions_for_conversation(
        conversation_id=conversation.id,
        owner_id=current_user.id,
    )
    conversation_runs = await runs.list_for_conversation(
        conversation_id=conversation.id,
        owner_id=current_user.id,
    )
    deep_research_turns: list[DeepResearchTurnResponse] = []
    for run in conversation_runs:
        proposal = await proposals.get_by_run_id(run_id=run.id)
        if proposal is None:
            # A run without its proposal is unreconstructable client-side
            # (no query/plan to show) -- skip rather than error the whole
            # conversation replay over one orphaned row.
            continue
        deep_research_turns.append(
            DeepResearchTurnResponse(
                proposal=_proposal_response(proposal),
                run=_run_response(run),
            )
        )

    return ResearchConversationResponse(
        conversation_id=conversation.id,
        title=conversation.title,
        turns=[_session_response(session) for session in sessions],
        deep_research_runs=deep_research_turns,
    )


@router.get(
    "/conversations/{conversation_id}/cost",
    response_model=ConversationUsageSummary,
    summary="Roll up estimated generation cost for a research conversation's Linear Research turns",
)
async def get_research_conversation_cost(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    conversation_service: ResearchConversationService = Depends(get_research_conversation_service),
    usage: GenerationUsageRepository = Depends(get_generation_usage_repository),
) -> ConversationUsageSummary:
    conversation = await conversation_service.get_or_create(
        conversation_id=conversation_id,
        owner_id=current_user.id,
    )

    return ConversationUsageSummary(
        **await usage.sum_for_conversation(
            conversation_id=conversation.id,
            owner_id=current_user.id,
        )
    )


@router.post(
    "/citations",
    response_model=ResearchCitationsResponse,
    summary="Preview citations for a query without generating an answer",
)
async def research_citations(
    payload: ResearchCitationsRequest,
    current_user: User = Depends(get_current_user),
    research_service: ResearchService = Depends(get_research_service),
    rate_limiter: ValkeyRateLimiter = Depends(get_rate_limiter),
) -> ResearchCitationsResponse:
    await _check_linear_research_rate_limit(rate_limiter=rate_limiter, owner_id=current_user.id)

    citations = await research_service.citations_only(
        query=payload.query,
        top_k=payload.top_k,
        filters=payload.filters,
        owner_id=current_user.id,
    )

    return ResearchCitationsResponse(citations=citations)


@router.get(
    "/runs/{research_run_id}",
    response_model=ResearchRunResponse,
    summary="Inspect an owner-scoped Research Runtime lifecycle record",
)
async def get_research_run(
    research_run_id: UUID,
    current_user: User = Depends(get_current_user),
    runs: ResearchRunRepository = Depends(get_research_run_repository),
) -> ResearchRunResponse:
    run = await runs.get_by_id_for_owner(run_id=research_run_id, owner_id=current_user.id)
    if run is None:
        raise NotFoundException(message=f"Research run '{research_run_id}' was not found.")
    return _run_response(run)


@router.post(
    "/runs/{research_run_id}/cancel",
    response_model=ResearchRunResponse,
    summary="Request cancellation of a non-terminal Research Runtime run",
)
async def cancel_research_run(
    research_run_id: UUID,
    current_user: User = Depends(get_current_user),
    runs: ResearchRunService = Depends(get_research_run_service),
) -> ResearchRunResponse:
    """Flag cooperative cancellation; the worker observes it at its next checkpoint.

    This does not synchronously stop execution -- see the run's `status` on
    subsequent polls/events for the actual terminal outcome.
    """

    run = await runs.request_cancellation(run_id=research_run_id, owner_id=current_user.id)
    if run is None:
        raise NotFoundException(message=f"Research run '{research_run_id}' was not found.")
    return _run_response(run)


@router.post(
    "/runs/{research_run_id}/retry",
    response_model=ResearchRunResponse,
    summary="Retry a failed Research Runtime run, resuming from its last checkpoint",
)
async def retry_research_run(
    research_run_id: UUID,
    current_user: User = Depends(get_current_user),
    runs: ResearchRunService = Depends(get_research_run_service),
) -> ResearchRunResponse:
    """Move a FAILED run back to RESEARCHING and re-queue its dispatch.

    The worker's next poll resumes the LangGraph checkpoint that already
    exists for this run's `graph_thread_id` -- the same mechanism used for
    crash-resume, triggered explicitly instead of by a dead worker's
    expired lease. Bounded to a small number of attempts per run.
    """

    try:
        run = await runs.retry_run(run_id=research_run_id, owner_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None:
        raise NotFoundException(message=f"Research run '{research_run_id}' was not found.")
    return _run_response(run)


@router.get(
    "/runs/{research_run_id}/plan",
    response_model=ResearchPendingPlanResponse,
    summary="Inspect the plan and gathered evidence awaiting approval before synthesis",
)
async def get_research_run_plan(
    research_run_id: UUID,
    current_user: User = Depends(get_current_user),
    runs: ResearchRunRepository = Depends(get_research_run_repository),
    plan_inspection: ResearchPlanInspectionService = Depends(get_research_plan_inspection_service),
) -> ResearchPendingPlanResponse:
    """Reads the pending plan and evidence straight out of the paused run's
    LangGraph checkpoint (see `ResearchPlanInspectionService`) -- reached
    after retrieval/evidence-aggregation but before the synthesis call."""

    run = await runs.get_by_id_for_owner(run_id=research_run_id, owner_id=current_user.id)
    if run is None:
        raise NotFoundException(message=f"Research run '{research_run_id}' was not found.")
    if run.status != ResearchRunStatus.AWAITING_PLAN_APPROVAL.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Research run '{research_run_id}' is not awaiting a plan decision.",
        )
    try:
        pending = await plan_inspection.get_pending_plan(run)
    except PendingPlanUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ResearchPendingPlanResponse(
        research_run_id=run.id,
        goal=pending.plan.goal,
        rewritten_goal=pending.plan.rewritten_goal,
        complexity=pending.plan.complexity,
        tasks=[
            ResearchPendingPlanTaskResponse(task_id=task.task_id, question=task.question)
            for task in pending.plan.tasks
        ],
        evidence=ResearchPendingPlanEvidenceSummary(
            completed_task_count=pending.evidence.completed_task_count,
            failed_task_count=pending.evidence.failed_task_count,
            warning_count=len(pending.evidence.warnings),
        ),
        citations=[
            ResearchDraftCitationResponse(
                citation_id=item.citation_id,
                filename=item.filename,
                excerpt=item.excerpt,
                score=item.score,
            )
            for item in pending.evidence.evidence
            if item.citation_id is not None
        ],
        socratic_question=pending.socratic_question,
    )


@router.post(
    "/runs/{research_run_id}/plan-decision",
    response_model=ResearchRunResponse,
    summary="Approve or reject the plan before synthesis runs",
)
async def submit_research_plan_decision(
    research_run_id: UUID,
    payload: ResearchPlanDecisionRequest,
    current_user: User = Depends(get_current_user),
    runs: ResearchRunService = Depends(get_research_run_service),
) -> ResearchRunResponse:
    """Resolve the graph's plan-approval `interrupt()`.

    Only valid while the run's status is `awaiting_plan_approval`. The
    decision is persisted and a fresh dispatch wakes the worker to resume
    the run -- continuing into synthesis on approval, or ending the run
    (with no report ever produced) on rejection. Neither happens
    synchronously in this request.
    """

    try:
        run = await runs.record_plan_decision(
            run_id=research_run_id,
            owner_id=current_user.id,
            approved=payload.approved,
            reason=payload.reason,
            edited_goal=(
                payload.edited_plan.rewritten_goal if payload.edited_plan is not None else None
            ),
            socratic_response=payload.socratic_response,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None:
        raise NotFoundException(message=f"Research run '{research_run_id}' was not found.")
    return _run_response(run)


@router.get(
    "/runs/{research_run_id}/web-search",
    response_model=ResearchPendingWebSearchResponse,
    summary="Inspect the agent's web-search suggestion awaiting approval",
)
async def get_research_run_web_search(
    research_run_id: UUID,
    current_user: User = Depends(get_current_user),
    runs: ResearchRunRepository = Depends(get_research_run_repository),
    web_search_inspection: ResearchWebSearchInspectionService = Depends(
        get_research_web_search_inspection_service
    ),
) -> ResearchPendingWebSearchResponse:
    """Reads the pending web-search suggestion straight out of the paused
    run's LangGraph checkpoint (see `ResearchWebSearchInspectionService`) --
    reached only in AUTO mode without `web_search_auto_approve`, when the
    agent decided a web search would help."""

    run = await runs.get_by_id_for_owner(run_id=research_run_id, owner_id=current_user.id)
    if run is None:
        raise NotFoundException(message=f"Research run '{research_run_id}' was not found.")
    if run.status != ResearchRunStatus.AWAITING_WEB_SEARCH_APPROVAL.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Research run '{research_run_id}' is not awaiting a web-search decision.",
        )
    try:
        pending = await web_search_inspection.get_pending_suggestion(run)
    except PendingWebSearchUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ResearchPendingWebSearchResponse(
        research_run_id=run.id,
        suggested_query=pending.suggested_query,
        reason=pending.reason,
        gap_question=pending.gap_question,
    )


@router.post(
    "/runs/{research_run_id}/web-search-decision",
    response_model=ResearchRunResponse,
    summary="Approve or reject the agent's web-search suggestion",
)
async def submit_research_web_search_decision(
    research_run_id: UUID,
    payload: ResearchWebSearchDecisionRequest,
    current_user: User = Depends(get_current_user),
    runs: ResearchRunService = Depends(get_research_run_service),
) -> ResearchRunResponse:
    """Resolve the graph's web-search-approval `interrupt()`.

    Only valid while the run's status is `awaiting_web_search_approval`. On
    rejection, the run continues via the existing document-only
    gap-research path -- no report content or evidence gathered so far is
    discarded either way.
    """

    try:
        run = await runs.record_web_search_decision(
            run_id=research_run_id,
            owner_id=current_user.id,
            approved=payload.approved,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None:
        raise NotFoundException(message=f"Research run '{research_run_id}' was not found.")
    return _run_response(run)


@router.get(
    "/runs/{research_run_id}/draft",
    response_model=ResearchDraftResponse,
    summary="Inspect the draft report awaiting approval before deciding",
)
async def get_research_run_draft(
    research_run_id: UUID,
    current_user: User = Depends(get_current_user),
    runs: ResearchRunRepository = Depends(get_research_run_repository),
    draft_inspection: ResearchDraftInspectionService = Depends(
        get_research_draft_inspection_service
    ),
) -> ResearchDraftResponse:
    """Reads the pending draft straight out of the paused run's LangGraph
    checkpoint (see `ResearchDraftInspectionService`) -- there's no other
    durable copy of it until `persist_final_report` runs, which only
    happens after approval."""

    run = await runs.get_by_id_for_owner(run_id=research_run_id, owner_id=current_user.id)
    if run is None:
        raise NotFoundException(message=f"Research run '{research_run_id}' was not found.")
    if run.status != ResearchRunStatus.AWAITING_APPROVAL.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Research run '{research_run_id}' is not awaiting a report decision.",
        )
    try:
        pending = await draft_inspection.get_pending_draft(run)
    except PendingDraftUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    evidence_by_citation = {item.citation_id: item for item in pending.evidence.evidence}
    used_citation_ids = set(pending.draft.citation_ids)
    for finding in pending.draft.findings:
        used_citation_ids.update(finding.citation_ids)
    citations = [
        (
            ResearchDraftCitationResponse(
                citation_id=citation_id,
                filename=item.filename,
                excerpt=item.excerpt,
                score=item.score,
            )
            if (item := evidence_by_citation.get(citation_id)) is not None
            else ResearchDraftCitationResponse(
                citation_id=citation_id,
                filename="Evidence reference unavailable",
                excerpt="",
                score=0.0,
            )
        )
        for citation_id in sorted(used_citation_ids)
    ]

    return ResearchDraftResponse(
        research_run_id=run.id,
        title=pending.draft.title,
        abstract=pending.draft.abstract,
        methodology=pending.draft.methodology,
        findings=[
            ResearchDraftFindingResponse(
                heading=finding.heading,
                content=finding.content,
                citation_ids=finding.citation_ids,
            )
            for finding in pending.draft.findings
        ],
        discussion=pending.draft.discussion,
        conclusion=pending.draft.conclusion,
        limitations=pending.draft.limitations,
        citations=citations,
        review=ResearchDraftReviewSummary(
            decision=pending.review.decision.value,
            citation_integrity_score=pending.review.citation_integrity_score,
            completeness_score=pending.review.completeness_score,
            limitations=pending.review.limitations,
            model_quality_score=pending.review.model_quality_score,
            gap_questions=pending.review.gap_questions,
        ),
    )


@router.post(
    "/runs/{research_run_id}/report-decision",
    response_model=ResearchRunResponse,
    summary="Approve or reject a completed report before it is published",
)
async def submit_research_report_decision(
    research_run_id: UUID,
    payload: ResearchReportDecisionRequest,
    current_user: User = Depends(get_current_user),
    runs: ResearchRunService = Depends(get_research_run_service),
    draft_inspection: ResearchDraftInspectionService = Depends(
        get_research_draft_inspection_service
    ),
) -> ResearchRunResponse:
    """Resolve the graph's report-approval `interrupt()`.

    Only valid while the run's status is `awaiting_approval`. The decision is
    persisted and a fresh dispatch wakes the worker to resume the run --
    finalizing on approval, or terminally failing it on rejection. Neither
    happens synchronously in this request.
    """

    try:
        run = await runs.record_report_decision(
            run_id=research_run_id,
            owner_id=current_user.id,
            approved=payload.approved,
            reason=payload.reason,
            edited_draft=(
                payload.edited_draft.model_dump() if payload.edited_draft is not None else None
            ),
            draft_inspection=draft_inspection,
        )
    except (ValueError, PendingDraftUnavailableError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None:
        raise NotFoundException(message=f"Research run '{research_run_id}' was not found.")
    return _run_response(run)


@router.get(
    "/runs/{research_run_id}/events",
    summary="Replay and follow safe Deep Research progress events over SSE",
)
async def stream_research_run_events(
    research_run_id: UUID,
    after: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    runs: ResearchRunRepository = Depends(get_research_run_repository),
    events: ResearchRunEventRepository = Depends(get_research_run_event_repository),
) -> StreamingResponse:
    run = await runs.get_by_id_for_owner(run_id=research_run_id, owner_id=current_user.id)
    if run is None:
        raise NotFoundException(message=f"Research run '{research_run_id}' was not found.")

    async def replay() -> AsyncGenerator[StreamEvent, None]:
        cursor = after
        terminal = {
            ResearchRunStatus.COMPLETED.value,
            ResearchRunStatus.COMPLETED_WITH_LIMITATIONS.value,
            ResearchRunStatus.CANCELLED.value,
            ResearchRunStatus.FAILED.value,
        }
        while True:
            persisted = await events.list_after_for_owner(
                run_id=research_run_id,
                owner_id=current_user.id,
                after=cursor,
            )
            for event in persisted:
                cursor = event.id
                yield StreamEvent(
                    session_id=research_run_id,
                    category=EventCategory.RESEARCH,
                    type=event.type,
                    timestamp=event.occurred_at,
                    metadata={**event.event_metadata, "cursor": event.id},
                )
            current = await runs.get_by_id_for_owner(
                run_id=research_run_id, owner_id=current_user.id
            )
            if current is None or current.status in terminal:
                return
            await asyncio.sleep(0.5)

    return sse_stream_response(
        replay(), max_duration_seconds=RESEARCH_RUN_EVENTS_MAX_STREAM_DURATION_SECONDS
    )


@router.get(
    "/runs/{research_run_id}/report",
    response_model=ResearchReportDownloadResponse,
    summary="Get a short-lived download URL for a final research-report PDF",
)
async def get_research_report_download(
    research_run_id: UUID,
    current_user: User = Depends(get_current_user),
    report_downloads: ResearchReportDownloadService = Depends(get_research_report_download_service),
) -> ResearchReportDownloadResponse:
    download = await report_downloads.get_download_url(
        research_run_id=research_run_id,
        owner_id=current_user.id,
    )
    if download is None:
        raise NotFoundException(
            message=f"Research report for run '{research_run_id}' was not found."
        )
    return ResearchReportDownloadResponse(
        research_run_id=research_run_id,
        download_url=download.download_url,
        expires_in_seconds=ResearchReportDownloadService.EXPIRES_IN_SECONDS,
        generation_id=download.generation_id,
        memory_used=download.memory_used,
    )


@router.get(
    "/{research_id}",
    response_model=ResearchSessionResponse,
    summary="Replay a previous research session",
)
async def get_research(
    research_id: UUID,
    current_user: User = Depends(get_current_user),
    repository: ResearchRepository = Depends(get_research_repository),
) -> ResearchSessionResponse:
    research_session = await repository.get_by_id_for_owner(
        research_id=research_id,
        owner_id=current_user.id,
    )

    if research_session is None:
        raise NotFoundException(
            message=f"Research session '{research_id}' was not found.",
        )

    return _session_response(research_session)

"""Create compact Deep Research plans before explicit user approval."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID, uuid4

import structlog
from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory.services.formatting import FormattedMemoryContext, format_memory_context_with_ids
from app.ai.memory.services.memory_service import MemoryService
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface
from app.ai.runtime.generation.routing.enums import RoutingStrategy
from app.ai.runtime.research.exceptions import ResearchQueueSaturatedError
from app.ai.runtime.research.planner.models import ResearchComplexity, ResearchPlan
from app.ai.runtime.research.planner.service import ResearchPlanner
from app.ai.runtime.research.run_service import ResearchRunService
from app.ai.runtime.research.types import ResearchProposalStatus
from app.ai.runtime.research.web_search.models import WebSearchMode
from app.core.settings import settings
from app.models.research_proposal import ResearchProposal
from app.repositories.research_proposal import ResearchProposalRepository
from app.repositories.research_run_dispatch import ResearchRunDispatchRepository
from app.services.research_conversation import ResearchConversationService

logger = structlog.get_logger()


class ResearchProposalService:
    """Planner-only operation; it does not create a run or retrieve evidence."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        generation_runtime: GenerationRuntimeInterface,
        run_service: ResearchRunService | None = None,
        memory_service: MemoryService | None = None,
    ) -> None:
        self._session = session
        self._planner = ResearchPlanner(generation_runtime)
        self._repository = ResearchProposalRepository(session)
        self._runs = run_service or ResearchRunService(session)
        self._dispatches = ResearchRunDispatchRepository(session)
        self._memory = memory_service
        self._conversations = ResearchConversationService(session)

    async def propose(
        self,
        *,
        query: str,
        top_k: int,
        filters: dict[str, object],
        owner_id: UUID,
        provider: GenerationProvider | None,
        routing_strategy: RoutingStrategy | None,
        conversation_id: UUID | None,
        web_search_mode: str = WebSearchMode.DISABLED.value,
        web_search_auto_approve: bool = False,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        paper_suggestions_enabled: bool = False,
    ) -> ResearchProposal:
        proposal = await self._repository.create(
            ResearchProposal(
                id=uuid4(),
                owner_id=owner_id,
                conversation_id=conversation_id,
                status=ResearchProposalStatus.PROPOSING.value,
                request={
                    "query": query,
                    "top_k": top_k,
                    "filters": filters,
                    "provider": provider.value if provider else None,
                    "routing_strategy": routing_strategy.value if routing_strategy else None,
                    "web_search_mode": web_search_mode,
                    "web_search_auto_approve": web_search_auto_approve,
                    "include_domains": include_domains or [],
                    "exclude_domains": exclude_domains or [],
                    "paper_suggestions_enabled": paper_suggestions_enabled,
                },
            )
        )
        memory_context = await self._retrieve_memory_context(
            owner_id=owner_id,
            session_id=conversation_id or proposal.id,
            query=query,
        )
        transcript = await self._load_transcript(conversation_id=conversation_id, owner_id=owner_id)
        plan = await self._planner.plan(
            query=query,
            owner_id=owner_id,
            research_run_id=proposal.id,
            provider=provider,
            routing_strategy=routing_strategy,
            memory_context=memory_context.text,
            injected_memory_ids=[str(item) for item in memory_context.memory_ids],
            transcript=transcript,
        )
        proposal.plan = plan.model_dump(mode="json")
        proposal.request = {
            **proposal.request,
            "injected_memory_ids": [str(item) for item in memory_context.memory_ids],
        }
        proposal.status = ResearchProposalStatus.AWAITING_APPROVAL.value
        await self._session.commit()
        logger.info(
            "research_runtime.proposal.created",
            proposal_id=str(proposal.id),
            owner_id=str(owner_id),
            complexity=plan.complexity.value,
            task_count=len(plan.tasks),
            memory_context_used=bool(memory_context.memory_ids),
            transcript_used=bool(transcript),
        )
        return proposal

    async def check_escalation(
        self,
        *,
        query: str,
        top_k: int,
        filters: dict[str, object],
        owner_id: UUID,
        provider: GenerationProvider | None,
        routing_strategy: RoutingStrategy | None,
        conversation_id: UUID | None,
    ) -> tuple[ResearchPlan, ResearchProposal | None]:
        """Classify whether `query` would benefit from Deep Research, without
        committing to it up front.

        A `SIMPLE` plan persists nothing at all -- the caller's Linear
        Research request proceeds unaffected, and no proposal is left
        behind. A `MODERATE`/`COMPLEX` plan *is* persisted as a real,
        immediately-approvable `ResearchProposal` (identical shape to what
        `propose()` produces), so accepting the suggestion costs no second
        planner call -- the caller just approves the returned `proposal.id`.
        """

        session_id = conversation_id or uuid4()
        memory_context = await self._retrieve_memory_context(
            owner_id=owner_id,
            session_id=session_id,
            query=query,
        )
        transcript = await self._load_transcript(conversation_id=conversation_id, owner_id=owner_id)
        plan = await self._planner.plan(
            query=query,
            owner_id=owner_id,
            research_run_id=session_id,
            provider=provider,
            routing_strategy=routing_strategy,
            memory_context=memory_context.text,
            injected_memory_ids=[str(item) for item in memory_context.memory_ids],
            transcript=transcript,
        )
        if plan.complexity == ResearchComplexity.SIMPLE:
            logger.info(
                "research_runtime.proposal.escalation_not_suggested",
                owner_id=str(owner_id),
                complexity=plan.complexity.value,
            )
            return plan, None

        proposal = await self._repository.create(
            ResearchProposal(
                id=uuid4(),
                owner_id=owner_id,
                conversation_id=conversation_id,
                status=ResearchProposalStatus.AWAITING_APPROVAL.value,
                request={
                    "query": query,
                    "top_k": top_k,
                    "filters": filters,
                    "provider": provider.value if provider else None,
                    "routing_strategy": routing_strategy.value if routing_strategy else None,
                    "injected_memory_ids": [str(item) for item in memory_context.memory_ids],
                },
                plan=plan.model_dump(mode="json"),
            )
        )
        await self._session.commit()
        logger.info(
            "research_runtime.proposal.created_via_escalation_check",
            proposal_id=str(proposal.id),
            owner_id=str(owner_id),
            complexity=plan.complexity.value,
            task_count=len(plan.tasks),
            memory_context_used=bool(memory_context.memory_ids),
            transcript_used=bool(transcript),
        )
        return plan, proposal

    async def _load_transcript(
        self,
        *,
        conversation_id: UUID | None,
        owner_id: UUID,
    ) -> str | None:
        """Prior Linear Research turns in this conversation, folded into the
        planner's prompt the same way `ResearchService._format_transcript`
        folds them for a Linear Research follow-up -- without this, a
        Deep Research request made mid-conversation (e.g. "conduct a
        literature review" right after asking about earthquakes) has no
        way to resolve what the request is actually about, since Deep
        Research planning never saw the earlier turns."""

        if conversation_id is None:
            return None
        history = await self._conversations.load_history(
            conversation_id=conversation_id,
            owner_id=owner_id,
        )
        if not history:
            return None
        return "\n".join(
            f"{'User' if isinstance(message, HumanMessage) else 'Assistant'}: {message.content}"
            for message in history
        )

    async def _retrieve_memory_context(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        query: str,
    ) -> FormattedMemoryContext:
        """Best-effort (PRD §9's Runtime Memory Injection Pipeline): a memory
        outage must never block plan creation, so every failure here is
        caught and logged rather than raised."""

        if self._memory is None:
            return FormattedMemoryContext(text=None, memory_ids=())
        try:
            context = await self._memory.get_context(
                owner_id=owner_id,
                session_id=session_id,
                semantic_query=query,
            )
        except Exception as exc:
            logger.warning(
                "research_runtime.proposal.memory_retrieval_failed",
                owner_id=str(owner_id),
                error_type=type(exc).__name__,
            )
            return FormattedMemoryContext(text=None, memory_ids=())
        return format_memory_context_with_ids(context)

    async def get_for_owner(self, *, proposal_id: UUID, owner_id: UUID) -> ResearchProposal | None:
        return await self._repository.get_by_id_for_owner(
            proposal_id=proposal_id, owner_id=owner_id
        )

    async def approve(self, *, proposal_id: UUID, owner_id: UUID):
        """Create the one durable run authorized by an approved proposal.

        This deliberately stops at persistence. A dedicated runtime dispatcher
        claims the resulting run in the next slice; API requests never execute
        LangGraph work in-process.
        """

        proposal = await self.get_for_owner(proposal_id=proposal_id, owner_id=owner_id)
        if proposal is None:
            return None
        if proposal.research_run_id is not None:
            run = await self._runs.get_for_owner(run_id=proposal.research_run_id, owner_id=owner_id)
            if run is None:
                raise RuntimeError("Research proposal references a missing research run.")
            return run
        if proposal.status != ResearchProposalStatus.AWAITING_APPROVAL.value:
            raise ValueError(f"Research proposal cannot be approved from '{proposal.status}'.")

        active_count = await self._dispatches.count_active()
        if active_count >= settings.deep_research_max_queued_runs:
            logger.warning(
                "research_runtime.proposal.approval_shed",
                proposal_id=str(proposal.id),
                owner_id=str(owner_id),
                active_count=active_count,
                max_queued_runs=settings.deep_research_max_queued_runs,
            )
            raise ResearchQueueSaturatedError(
                f"Research runtime queue is full ({active_count} active runs)."
            )

        request = proposal.request
        fingerprint = ResearchRunServiceFingerprint.from_request(request, proposal.conversation_id)
        run = await self._runs.create_or_get(
            owner_id=owner_id,
            request_fingerprint=fingerprint,
            idempotency_key=f"research-proposal:{proposal.id}",
            conversation_id=proposal.conversation_id,
        )
        proposal.research_run_id = run.id
        proposal.status = ResearchProposalStatus.APPROVED.value
        run.current_phase = "awaiting_runtime_dispatch"
        await self._dispatches.create(run_id=run.id)
        await self._session.commit()
        logger.info(
            "research_runtime.proposal.approved",
            proposal_id=str(proposal.id),
            research_run_id=str(run.id),
            owner_id=str(owner_id),
        )
        return run

    @staticmethod
    def plan(proposal: ResearchProposal) -> ResearchPlan:
        if proposal.plan is None:
            raise ValueError("Research proposal does not contain a valid plan.")
        return ResearchPlan.model_validate(proposal.plan)


class ResearchRunServiceFingerprint:
    """Keep proposal persistence independent from the execution service."""

    @staticmethod
    def from_request(request: dict[str, object], conversation_id: UUID | None) -> str:
        from app.ai.runtime.research.execution import ResearchRuntimeExecutionService

        payload = cast(dict[str, Any], request)
        provider = payload.get("provider")
        routing_strategy = payload.get("routing_strategy")
        return ResearchRuntimeExecutionService.request_fingerprint(
            query=str(payload["query"]),
            top_k=int(payload["top_k"]),
            filters=dict(payload.get("filters") or {}),
            provider=GenerationProvider(provider) if provider is not None else None,
            routing_strategy=(
                RoutingStrategy(routing_strategy) if routing_strategy is not None else None
            ),
            conversation_id=conversation_id,
        )

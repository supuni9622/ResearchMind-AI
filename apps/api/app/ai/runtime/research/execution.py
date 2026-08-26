"""Feature-flagged bridge from the live Research API to its durable runtime."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import UUID

import structlog
from langchain_core.runnables.config import RunnableConfig
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.knowledge.context.citations.models import Citation
from app.ai.knowledge.context.interfaces import ContextBuilderInterface
from app.ai.knowledge.retrieval.service import RetrievalService
from app.ai.memory.enums import MemoryType
from app.ai.memory.services.formatting import FormattedMemoryContext, format_memory_context_with_ids
from app.ai.memory.services.memory_service import MemoryService
from app.ai.research.models import ResearchOutcome, ResearchSource
from app.ai.research.service import ResearchService
from app.ai.runtime.chat.paper_query import PaperQueryExtractionService
from app.ai.runtime.events.research.models import ResearchEventType
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface
from app.ai.runtime.generation.routing.enums import RoutingStrategy
from app.ai.runtime.research.checkpointing import postgres_checkpointer
from app.ai.runtime.research.decomposition.scheduler import dependency_waves
from app.ai.runtime.research.decomposition.validators import validate_plan
from app.ai.runtime.research.event_journal import ResearchRuntimeEventJournal
from app.ai.runtime.research.evidence_artifact import ResearchEvidenceArtifactWriter
from app.ai.runtime.research.exceptions import (
    ResearchReportRejectedError,
    ResearchRunBudgetExceededError,
    ResearchRunCancelledError,
)
from app.ai.runtime.research.lifecycle import transition_run
from app.ai.runtime.research.planner.models import ResearchPlan
from app.ai.runtime.research.planner.policies import ResearchPlanningPolicy
from app.ai.runtime.research.planner.service import ResearchPlanner
from app.ai.runtime.research.report_artifact import ResearchFinalReportArtifactWriter
from app.ai.runtime.research.retrieval.service import ResearchTaskRetrievalService
from app.ai.runtime.research.review import ResearchReview, ResearchReviewService, ReviewDecision
from app.ai.runtime.research.review_artifact import ResearchReviewArtifactWriter
from app.ai.runtime.research.run_service import ResearchRunService
from app.ai.runtime.research.service import ResearchRuntimeService
from app.ai.runtime.research.socratic import SocraticChallengerService
from app.ai.runtime.research.synthesis.service import ResearchSynthesisService
from app.ai.runtime.research.types import (
    ResearchRunStatus,
    ResearchRuntimeRequest,
)
from app.ai.runtime.research.web_search.models import WebSearchMode
from app.ai.runtime.research.web_search.necessity import WebSearchNecessityService
from app.ai.runtime.research.workflows.multi_wave_research import compile_multi_wave_research_graph
from app.ai.tools.paper_search.service import PaperSearchService
from app.ai.tools.web_search.service import WebSearchService
from app.core.settings import settings
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.metrics.noop import NoOpMetricsRecorder
from app.infrastructure.metrics.research import RESEARCH_RUN_DURATION
from app.infrastructure.storage.interfaces import DocumentStorage
from app.models.research_run import ResearchRun
from app.repositories.generation_usage import GenerationUsageRepository
from app.repositories.research import ResearchRepository
from app.repositories.research_proposal import ResearchProposalRepository
from app.repositories.research_run_event import ResearchRunEventRepository

logger = structlog.get_logger()

_RESUMABLE_IN_PROGRESS_STATUSES = frozenset(
    {
        ResearchRunStatus.PLANNING.value,
        ResearchRunStatus.RESEARCHING.value,
        ResearchRunStatus.REVIEWING.value,
        ResearchRunStatus.SYNTHESIZING.value,
        # A run paused at the report-approval interrupt() is also "resumable
        # in progress": a decision was recorded and a fresh dispatch was
        # created (see ResearchRunDispatchRepository.reopen), so this is not
        # a crashed/dead attempt, but `_begin` treats it identically -- bump
        # attempt_count and continue rather than re-transition to PLANNING.
        ResearchRunStatus.AWAITING_APPROVAL.value,
        # Same reasoning for the plan-approval checkpoint.
        ResearchRunStatus.AWAITING_PLAN_APPROVAL.value,
        # Same reasoning for the web-search-approval checkpoint.
        ResearchRunStatus.AWAITING_WEB_SEARCH_APPROVAL.value,
    }
)


class ResearchRuntimeExecutionService:
    """Owns the Phase 2 migration bridge, not research business logic.

    The compact LangGraph foundation is checkpointed before the existing linear
    service runs. That preserves the public API while giving every flagged
    request a durable lifecycle/thread ready for the Phase 3 graph nodes.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        research_service: ResearchService,
        database_url: str,
        generation_runtime: GenerationRuntimeInterface | None = None,
        retrieval_service: RetrievalService | None = None,
        context_builder: ContextBuilderInterface | None = None,
        storage: DocumentStorage | None = None,
        v1_graph_enabled: bool = False,
        memory_service: MemoryService | None = None,
        web_search: WebSearchService | None = None,
        web_search_necessity: WebSearchNecessityService | None = None,
        paper_search: PaperSearchService | None = None,
        paper_query_extraction: PaperQueryExtractionService | None = None,
        metrics: MetricsRecorder | None = None,
    ) -> None:
        self._session = session
        self._research_service = research_service
        self._database_url = database_url
        self._generation_runtime = generation_runtime
        self._retrieval = retrieval_service
        self._context_builder = context_builder
        self._storage = storage
        self._v1_graph_enabled = v1_graph_enabled
        self._memory = memory_service
        self._web_search = web_search
        self._web_search_necessity = web_search_necessity
        self._paper_search = paper_search
        self._paper_query_extraction = paper_query_extraction
        self._metrics = metrics or NoOpMetricsRecorder()
        self._runs = ResearchRunService(session)
        self._research_sessions = ResearchRepository(session)
        self._proposals = ResearchProposalRepository(session)
        self._event_journal = ResearchRuntimeEventJournal(ResearchRunEventRepository(session))

    async def execute_approved_run(self, *, run_id: UUID) -> ResearchOutcome | None:
        """Execute a persisted, explicitly approved plan in the runtime worker.

        Returns `None` when the graph pauses at the report-approval
        interrupt() rather than reaching a terminal outcome -- the caller
        (the worker) treats that the same as a normal, non-exceptional
        completion of *this* dispatch attempt; a fresh dispatch resumes the
        run once a decision is recorded (see `ResearchRunDispatchRepository.
        reopen`).
        """

        proposal = await self._proposals.get_by_run_id(run_id=run_id)
        if proposal is None:
            raise RuntimeError(f"Approved research run '{run_id}' has no proposal.")
        run = await self._runs.get_for_owner(run_id=run_id, owner_id=proposal.owner_id)
        if run is None:
            raise RuntimeError(f"Approved research run '{run_id}' was not found.")
        # This worker's session lives for its whole process lifetime and uses
        # `expire_on_commit=False` (see `db/session.py`), so a `run` this
        # session already loaded earlier -- e.g. during the dispatch that
        # first reached `awaiting_approval` -- is never automatically
        # invalidated by writes another session (the report-decision API
        # request) commits afterward. Refresh in place before any branch
        # reads its fields, so `status`/`budget_usage` reflect the DB, not a
        # stale in-memory snapshot from earlier in this run's lifecycle.
        await self._session.refresh(run)
        if run.status == ResearchRunStatus.COMPLETED.value:
            logger.info(
                "research_runtime.execution.replaying_completed_run",
                research_run_id=str(run.id),
            )
            return await self._replay_completed(run=run, owner_id=proposal.owner_id)

        resuming_after_report_decision = run.status == ResearchRunStatus.AWAITING_APPROVAL.value
        resuming_after_plan_decision = run.status == ResearchRunStatus.AWAITING_PLAN_APPROVAL.value
        resuming_after_web_search_decision = (
            run.status == ResearchRunStatus.AWAITING_WEB_SEARCH_APPROVAL.value
        )
        logger.info(
            "research_runtime.execution.approved_run_started",
            research_run_id=str(run.id),
            owner_id=str(proposal.owner_id),
            attempt_count=(run.attempt_count or 0) + 1,
            resuming_after_report_decision=resuming_after_report_decision,
            resuming_after_plan_decision=resuming_after_plan_decision,
            resuming_after_web_search_decision=resuming_after_web_search_decision,
        )
        request = proposal.request
        try:
            if not self._v1_graph_enabled:
                raise RuntimeError("Research Runtime V1 graph execution is not enabled.")
            plan = ResearchPlan.model_validate(proposal.plan)
            if await self._is_cancellation_requested(run.id):
                raise ResearchRunCancelledError(f"Research run '{run.id}' was cancelled.")
            await self._begin(run, allow_resume_in_progress=True)
            if resuming_after_report_decision:
                decision = (run.budget_usage or {}).get("report_decision")
                if decision is None:
                    raise RuntimeError(
                        f"Research run '{run.id}' is awaiting a report decision "
                        "that was never recorded."
                    )
                outcome = await self._resume_v1_graph_after_report_approval(
                    run=run,
                    query=str(request["query"]),
                    owner_id=proposal.owner_id,
                    conversation_id=proposal.conversation_id,
                    plan=plan,
                    decision=decision,
                )
            elif resuming_after_plan_decision:
                decision = (run.budget_usage or {}).get("plan_decision")
                if decision is None:
                    raise RuntimeError(
                        f"Research run '{run.id}' is awaiting a plan decision "
                        "that was never recorded."
                    )
                outcome = await self._resume_v1_graph_after_plan_approval(
                    run=run,
                    query=str(request["query"]),
                    owner_id=proposal.owner_id,
                    conversation_id=proposal.conversation_id,
                    plan=plan,
                    decision=decision,
                )
            elif resuming_after_web_search_decision:
                decision = (run.budget_usage or {}).get("web_search_decision")
                if decision is None:
                    raise RuntimeError(
                        f"Research run '{run.id}' is awaiting a web-search decision "
                        "that was never recorded."
                    )
                outcome = await self._resume_v1_graph_after_web_search_approval(
                    run=run,
                    query=str(request["query"]),
                    owner_id=proposal.owner_id,
                    conversation_id=proposal.conversation_id,
                    plan=plan,
                    decision=decision,
                )
            else:
                await self._event_journal.publish(
                    run_id=run.id, event_type=ResearchEventType.RESEARCH_STARTED
                )
                await self._event_journal.publish(
                    run_id=run.id, event_type=ResearchEventType.PLANNER_COMPLETED
                )
                await self._event_journal.publish(
                    run_id=run.id, event_type=ResearchEventType.RETRIEVAL_STARTED
                )
                await self._session.commit()
                outcome = await self._execute_v1_graph(
                    run=run,
                    query=str(request["query"]),
                    top_k=int(request["top_k"]),
                    filters=dict(request.get("filters") or {}),
                    owner_id=proposal.owner_id,
                    provider=(
                        GenerationProvider(request["provider"])
                        if request.get("provider") is not None
                        else None
                    ),
                    routing_strategy=(
                        RoutingStrategy(request["routing_strategy"])
                        if request.get("routing_strategy") is not None
                        else None
                    ),
                    conversation_id=proposal.conversation_id,
                    plan=plan,
                    web_search_mode=str(
                        request.get("web_search_mode") or WebSearchMode.DISABLED.value
                    ),
                    web_search_auto_approve=bool(request.get("web_search_auto_approve") or False),
                    web_search_include_domains=list(request.get("include_domains") or []),
                    web_search_exclude_domains=list(request.get("exclude_domains") or []),
                    paper_suggestions_enabled=bool(
                        request.get("paper_suggestions_enabled") or False
                    ),
                    socratic_challenger_enabled=bool(
                        request.get("socratic_challenger_enabled") or False
                    ),
                    injected_memory_ids=list(request.get("injected_memory_ids") or []),
                )
        except ResearchReportRejectedError as exc:
            # A genuine user rejection no longer raises this -- it routes to
            # `END` inside the graph and completes normally (see
            # `await_report_approval`/`route_after_report_approval` in
            # `multi_wave_research.py`, and `_complete_run` above). This is
            # now only reachable for a malformed `interrupt()` resume
            # payload, which nothing downstream can recover from.
            await self._mark_failed(run, exc, reason="report_decision_payload_invalid")
            await self._event_journal.publish(
                run_id=run.id, event_type=ResearchEventType.RESEARCH_FAILED
            )
            await self._session.commit()
            raise
        except ResearchRunCancelledError:
            await self._mark_terminal(run, ResearchRunStatus.CANCELLED, "user_cancelled")
            await self._event_journal.publish(
                run_id=run.id, event_type=ResearchEventType.RESEARCH_CANCELLED
            )
            await self._session.commit()
            raise
        except ResearchRunBudgetExceededError as exc:
            await self._mark_failed(run, exc, reason="duration_budget_exceeded")
            await self._event_journal.publish(
                run_id=run.id, event_type=ResearchEventType.RESEARCH_FAILED
            )
            await self._session.commit()
            raise
        except asyncio.CancelledError:
            await self._mark_terminal(run, ResearchRunStatus.CANCELLED, "worker_cancelled")
            await self._event_journal.publish(
                run_id=run.id, event_type=ResearchEventType.RESEARCH_CANCELLED
            )
            await self._session.commit()
            raise
        except Exception as exc:
            await self._mark_failed(run, exc)
            await self._event_journal.publish(
                run_id=run.id, event_type=ResearchEventType.RESEARCH_FAILED
            )
            await self._session.commit()
            raise

        if outcome is None:
            return None

        await self._event_journal.publish(
            run_id=run.id, event_type=ResearchEventType.RESEARCH_COMPLETED
        )
        await self._complete_run(run=run, outcome=outcome)
        logger.info(
            "research_runtime.execution.approved_run_completed",
            research_run_id=str(run.id),
            duration_ms=outcome.duration_ms,
        )
        return outcome

    async def execute(
        self,
        *,
        query: str,
        top_k: int,
        filters: dict[str, Any],
        owner_id: UUID,
        provider: GenerationProvider | None,
        routing_strategy: RoutingStrategy | None,
        conversation_id: UUID | None,
        idempotency_key: str | None,
    ) -> ResearchOutcome | None:
        fingerprint = self.request_fingerprint(
            query=query,
            top_k=top_k,
            filters=filters,
            provider=provider,
            routing_strategy=routing_strategy,
            conversation_id=conversation_id,
        )
        run = await self._runs.create_or_get(
            owner_id=owner_id,
            request_fingerprint=fingerprint,
            idempotency_key=idempotency_key,
            conversation_id=conversation_id,
        )

        if run.status == ResearchRunStatus.COMPLETED.value:
            return await self._replay_completed(run=run, owner_id=owner_id)
        if run.status in {
            ResearchRunStatus.CANCELLED.value,
            ResearchRunStatus.FAILED.value,
            ResearchRunStatus.COMPLETED_WITH_LIMITATIONS.value,
        }:
            raise RuntimeError(f"Research run '{run.id}' is terminal and cannot be resumed.")

        try:
            await self._begin(run)
            if self._v1_graph_enabled:
                outcome = await self._execute_v1_graph(
                    run=run,
                    query=query,
                    top_k=top_k,
                    filters=filters,
                    owner_id=owner_id,
                    provider=provider,
                    routing_strategy=routing_strategy,
                    conversation_id=conversation_id,
                )
            else:
                outcome = await self._execute_compatibility_bridge(
                    run=run,
                    query=query,
                    top_k=top_k,
                    filters=filters,
                    owner_id=owner_id,
                    provider=provider,
                    routing_strategy=routing_strategy,
                    conversation_id=conversation_id,
                )
        except ResearchReportRejectedError as exc:
            # See the matching handler in `execute_approved_run` -- only
            # reachable for a malformed decision payload now, not a normal
            # user rejection.
            await self._mark_failed(run, exc, reason="report_decision_payload_invalid")
            raise
        except ResearchRunCancelledError:
            await self._mark_terminal(run, ResearchRunStatus.CANCELLED, "user_cancelled")
            raise
        except ResearchRunBudgetExceededError as exc:
            await self._mark_failed(run, exc, reason="duration_budget_exceeded")
            raise
        except asyncio.CancelledError:
            await self._mark_terminal(run, ResearchRunStatus.CANCELLED, "request_cancelled")
            raise
        except Exception as exc:
            await self._mark_failed(run, exc)
            raise

        if outcome is None:
            # Paused at the report-approval interrupt(); this compatibility
            # path has no dispatch/decision plumbing to resume it later (see
            # execute_approved_run for the supported resume flow), so the
            # run simply stays AWAITING_APPROVAL until an operator inspects it.
            return None
        await self._complete_run(run=run, outcome=outcome)
        return outcome

    async def _complete_run(self, *, run: ResearchRun, outcome: ResearchOutcome) -> None:
        run.research_session_id = outcome.research_id
        run.conversation_id = outcome.conversation_id
        outcome.research_run_id = run.id
        if self._v1_graph_enabled:
            report_rejected = ((run.budget_usage or {}).get("report_decision") or {}).get(
                "decision"
            ) == "rejected"
            terminal_status = (
                ResearchRunStatus.COMPLETED_WITH_LIMITATIONS
                if report_rejected
                or (run.budget_usage or {}).get("review_decision")
                == ReviewDecision.FINALIZE_WITH_LIMITATIONS.value
                else ResearchRunStatus.COMPLETED
            )
            if report_rejected:
                # The user rejected the polished PDF report -- the run still
                # completed (the draft was still published as a plain answer
                # via `publish_runtime_report`), just without that artifact.
                # Distinct from `ResearchReportRejectedError`'s old FAILED
                # outcome, which discarded the synthesized content entirely.
                run.terminal_reason = "report_rejected_returned_as_answer"
            transition_run(run, target=terminal_status, phase="runtime_report_published")
        else:
            transition_run(run, target=ResearchRunStatus.REVIEWING, phase="compatibility_review")
            transition_run(run, target=ResearchRunStatus.SYNTHESIZING, phase="persisted_answer")
            transition_run(run, target=ResearchRunStatus.COMPLETED, phase="complete")
        self._record_run_duration(run)
        await self._session.commit()

    async def _execute_compatibility_bridge(
        self,
        *,
        run: ResearchRun,
        query: str,
        top_k: int,
        filters: dict[str, Any],
        owner_id: UUID,
        provider: GenerationProvider | None,
        routing_strategy: RoutingStrategy | None,
        conversation_id: UUID | None,
    ) -> ResearchOutcome:
        async with postgres_checkpointer(self._database_url) as checkpointer:
            runtime = ResearchRuntimeService(checkpointer=checkpointer)
            await runtime.run(
                ResearchRuntimeRequest(
                    research_run_id=run.id,
                    graph_thread_id=run.graph_thread_id,
                    owner_id=owner_id,
                )
            )
        transition_run(
            run, target=ResearchRunStatus.RESEARCHING, phase="linear_research_compatibility_bridge"
        )
        await self._session.commit()
        return await self._research_service.research(
            query=query,
            top_k=top_k,
            filters=filters,
            owner_id=owner_id,
            provider=provider,
            routing_strategy=routing_strategy,
            conversation_id=conversation_id,
        )

    def _v1_graph_dependencies(
        self,
    ) -> tuple[
        GenerationRuntimeInterface, RetrievalService, ContextBuilderInterface, DocumentStorage
    ]:
        if any(
            dependency is None
            for dependency in (
                self._generation_runtime,
                self._retrieval,
                self._context_builder,
                self._storage,
            )
        ):
            raise RuntimeError("Research Runtime V1 graph dependencies are not configured.")
        assert self._generation_runtime is not None
        assert self._retrieval is not None
        assert self._context_builder is not None
        assert self._storage is not None
        return self._generation_runtime, self._retrieval, self._context_builder, self._storage

    def _compile_graph_for_run(
        self,
        *,
        run: ResearchRun,
        checkpointer: Any,
        generation_runtime: GenerationRuntimeInterface,
        retrieval: RetrievalService,
        context_builder: ContextBuilderInterface,
        storage: DocumentStorage,
    ) -> Any:
        async def progress(
            event_type: ResearchEventType, extra_metadata: Mapping[str, Any] | None = None
        ) -> None:
            await self._publish_runtime_event(
                run_id=run.id, event_type=event_type, extra_metadata=extra_metadata
            )

        return compile_multi_wave_research_graph(
            checkpointer=checkpointer,
            task_retrieval=ResearchTaskRetrievalService(
                retrieval_service=retrieval,
                context_builder=context_builder,
            ),
            evidence_writer=ResearchEvidenceArtifactWriter(storage),
            synthesis=ResearchSynthesisService(generation_runtime),
            final_report_writer=ResearchFinalReportArtifactWriter(storage),
            reviewer=ResearchReviewService(generation_runtime),
            review_writer=ResearchReviewArtifactWriter(storage),
            progress=progress,
            cancellation_check=lambda: self._is_cancellation_requested(run.id),
            cost_lookup=lambda: self._cost_so_far(run.id),
            web_search=self._web_search,
            web_search_necessity=self._web_search_necessity,
            paper_search=self._paper_search,
            paper_query_extraction=self._paper_query_extraction,
            metrics=self._metrics,
            socratic_challenge=lambda goal, evidence: SocraticChallengerService(
                generation_runtime
            ).generate(
                goal=goal,
                evidence=evidence,
                owner_id=run.owner_id,
                research_run_id=run.id,
            ),
            remember_socratic_response=(
                lambda question, response: self._remember_socratic_response(
                    run=run, question=question, response=response
                )
            ),
        )

    async def _remember_socratic_response(
        self, *, run: ResearchRun, question: str, response: str
    ) -> None:
        """Persist the researcher's answer as the Wave-2 plain RESEARCH note."""

        if self._memory is None:
            return
        await self._memory.remember(
            owner_id=run.owner_id,
            type=MemoryType.RESEARCH,
            content=f"Socratic question: {question}\nResearcher response: {response}",
            metadata={
                "source": "socratic_challenger",
                "research_run_id": str(run.id),
                "prompt_version": "socratic-challenger-v1",
            },
            importance_score=0.8,
        )

    async def _execute_v1_graph(
        self,
        *,
        run: ResearchRun,
        query: str,
        top_k: int,
        filters: dict[str, Any],
        owner_id: UUID,
        provider: GenerationProvider | None,
        routing_strategy: RoutingStrategy | None,
        conversation_id: UUID | None,
        plan: ResearchPlan | None = None,
        web_search_mode: str = WebSearchMode.DISABLED.value,
        web_search_auto_approve: bool = False,
        web_search_include_domains: list[str] | None = None,
        web_search_exclude_domains: list[str] | None = None,
        paper_suggestions_enabled: bool = False,
        socratic_challenger_enabled: bool = False,
        injected_memory_ids: list[str] | None = None,
    ) -> ResearchOutcome | None:
        generation_runtime, retrieval, context_builder, storage = self._v1_graph_dependencies()

        started = perf_counter()
        memory_context = await self._retrieve_memory_context(
            owner_id=owner_id,
            session_id=conversation_id or run.id,
            query=query,
        )
        execution_memory_ids = [str(item) for item in memory_context.memory_ids]
        if execution_memory_ids:
            injected_memory_ids = execution_memory_ids
        if plan is None:
            planner = ResearchPlanner(generation_runtime)
            plan = await planner.plan(
                query=query,
                owner_id=owner_id,
                research_run_id=run.id,
                provider=provider,
                routing_strategy=routing_strategy,
                memory_context=memory_context.text,
                injected_memory_ids=[str(item) for item in memory_context.memory_ids],
            )
            injected_memory_ids = [str(item) for item in memory_context.memory_ids]
        validate_plan(plan)
        transition_run(run, target=ResearchRunStatus.RESEARCHING, phase="task_retrieval")
        await self._session.commit()
        budget = ResearchPlanningPolicy().budget_for(plan.complexity)
        async with postgres_checkpointer(self._database_url) as checkpointer:
            graph = self._compile_graph_for_run(
                run=run,
                checkpointer=checkpointer,
                generation_runtime=generation_runtime,
                retrieval=retrieval,
                context_builder=context_builder,
                storage=storage,
            )
            graph_config: RunnableConfig = {
                "configurable": {"thread_id": run.graph_thread_id},
                "recursion_limit": settings.research_runtime_graph_recursion_limit,
            }
            # A checkpoint already existing for this thread means a prior
            # attempt made durable progress (e.g. the worker crashed
            # mid-run); resume from it with `None` input rather than
            # replaying the planner/waves and restarting the graph.
            existing_checkpoint = await checkpointer.aget_tuple(graph_config)
            if existing_checkpoint is not None:
                logger.info(
                    "research_runtime.execution.resuming_graph_thread",
                    research_run_id=str(run.id),
                    graph_thread_id=run.graph_thread_id,
                )
                graph_input: dict[str, Any] | None = None
            else:
                graph_input = {
                    "research_run_id": str(run.id),
                    "owner_id": str(owner_id),
                    "plan": plan.model_dump(mode="json"),
                    "waves": [
                        [task.model_dump(mode="json") for task in wave]
                        for wave in dependency_waves(plan)
                    ],
                    "filters": filters,
                    "top_k": top_k,
                    "task_results": {},
                    "web_search_mode": web_search_mode,
                    "web_search_auto_approve": web_search_auto_approve,
                    "web_search_include_domains": web_search_include_domains or [],
                    "web_search_exclude_domains": web_search_exclude_domains or [],
                    "web_search_count": 0,
                    "paper_suggestions_enabled": paper_suggestions_enabled,
                    "socratic_challenger_enabled": socratic_challenger_enabled,
                    "injected_memory_ids": injected_memory_ids or [],
                    "memory_context": memory_context.text,
                }
            try:
                result = await asyncio.wait_for(
                    graph.ainvoke(graph_input, config=graph_config),
                    timeout=budget.max_duration_seconds,
                )
            except TimeoutError as exc:
                raise ResearchRunBudgetExceededError(
                    f"Research run '{run.id}' exceeded its "
                    f"{budget.max_duration_seconds}s duration budget."
                ) from exc
        return await self._finalize_or_pause(
            run=run,
            result=result,
            query=query,
            owner_id=owner_id,
            conversation_id=conversation_id,
            started=started,
        )

    async def _resume_v1_graph_after_report_approval(
        self,
        *,
        run: ResearchRun,
        query: str,
        owner_id: UUID,
        conversation_id: UUID | None,
        plan: ResearchPlan,
        decision: dict[str, Any],
    ) -> ResearchOutcome | None:
        """Continue a graph paused at `await_report_approval` with a recorded decision.

        No `graph_input` reconstruction happens here -- the checkpoint already
        holds the full accumulated state (evidence, draft, review); only the
        pending `interrupt()` needs a resume value.
        """

        generation_runtime, retrieval, context_builder, storage = self._v1_graph_dependencies()
        started = perf_counter()
        budget = ResearchPlanningPolicy().budget_for(plan.complexity)
        # Mirrors `_begin`'s PAUSED->PLANNING resume transition: leaves the
        # lifecycle FSM in a state (RESEARCHING) from which `_finalize_or_pause`
        # can reach REVIEWING/SYNTHESIZING/COMPLETED, or FAILED on rejection.
        transition_run(
            run, target=ResearchRunStatus.RESEARCHING, phase="resuming_after_report_decision"
        )
        await self._session.commit()
        await self._publish_runtime_event(
            run_id=run.id, event_type=ResearchEventType.RESEARCH_RESUMED
        )
        async with postgres_checkpointer(self._database_url) as checkpointer:
            graph = self._compile_graph_for_run(
                run=run,
                checkpointer=checkpointer,
                generation_runtime=generation_runtime,
                retrieval=retrieval,
                context_builder=context_builder,
                storage=storage,
            )
            graph_config: RunnableConfig = {
                "configurable": {"thread_id": run.graph_thread_id},
                "recursion_limit": settings.research_runtime_graph_recursion_limit,
            }
            try:
                result = await asyncio.wait_for(
                    graph.ainvoke(Command(resume=decision), config=graph_config),
                    timeout=budget.max_duration_seconds,
                )
            except TimeoutError as exc:
                raise ResearchRunBudgetExceededError(
                    f"Research run '{run.id}' exceeded its "
                    f"{budget.max_duration_seconds}s duration budget."
                ) from exc
        return await self._finalize_or_pause(
            run=run,
            result=result,
            query=query,
            owner_id=owner_id,
            conversation_id=conversation_id,
            started=started,
        )

    async def _resume_v1_graph_after_plan_approval(
        self,
        *,
        run: ResearchRun,
        query: str,
        owner_id: UUID,
        conversation_id: UUID | None,
        plan: ResearchPlan,
        decision: dict[str, Any],
    ) -> ResearchOutcome | None:
        """Continue a graph paused at `await_plan_approval` with a recorded decision.

        Mirrors `_resume_v1_graph_after_report_approval` -- no `graph_input`
        reconstruction happens here, the checkpoint already holds the
        accumulated state (plan, evidence); only the pending `interrupt()`
        needs a resume value.
        """

        generation_runtime, retrieval, context_builder, storage = self._v1_graph_dependencies()
        started = perf_counter()
        budget = ResearchPlanningPolicy().budget_for(plan.complexity)
        transition_run(
            run, target=ResearchRunStatus.RESEARCHING, phase="resuming_after_plan_decision"
        )
        await self._session.commit()
        await self._publish_runtime_event(
            run_id=run.id, event_type=ResearchEventType.RESEARCH_RESUMED
        )
        async with postgres_checkpointer(self._database_url) as checkpointer:
            graph = self._compile_graph_for_run(
                run=run,
                checkpointer=checkpointer,
                generation_runtime=generation_runtime,
                retrieval=retrieval,
                context_builder=context_builder,
                storage=storage,
            )
            graph_config: RunnableConfig = {
                "configurable": {"thread_id": run.graph_thread_id},
                "recursion_limit": settings.research_runtime_graph_recursion_limit,
            }
            try:
                result = await asyncio.wait_for(
                    graph.ainvoke(Command(resume=decision), config=graph_config),
                    timeout=budget.max_duration_seconds,
                )
            except TimeoutError as exc:
                raise ResearchRunBudgetExceededError(
                    f"Research run '{run.id}' exceeded its "
                    f"{budget.max_duration_seconds}s duration budget."
                ) from exc
        if result.get("plan_decision") == "rejected" and not result.get("__interrupt__"):
            # No draft was ever produced -- `route_after_plan_approval` sent
            # the graph straight to `END` without touching `synthesize`, so
            # there is nothing for `_finalize_or_pause` to publish. Distinct
            # from a rejected *report*, which still has a draft to publish
            # as a plain answer.
            await self._mark_terminal(run, ResearchRunStatus.CANCELLED, "plan_rejected_by_user")
            await self._publish_runtime_event(
                run_id=run.id, event_type=ResearchEventType.RESEARCH_CANCELLED
            )
            logger.info(
                "research_runtime.execution.plan_rejected",
                research_run_id=str(run.id),
            )
            return None
        return await self._finalize_or_pause(
            run=run,
            result=result,
            query=query,
            owner_id=owner_id,
            conversation_id=conversation_id,
            started=started,
        )

    async def _resume_v1_graph_after_web_search_approval(
        self,
        *,
        run: ResearchRun,
        query: str,
        owner_id: UUID,
        conversation_id: UUID | None,
        plan: ResearchPlan,
        decision: dict[str, Any],
    ) -> ResearchOutcome | None:
        """Continue a graph paused at `await_web_search_approval` with a
        recorded decision. Simpler than the plan/report resumes: there is no
        "rejected with nothing to publish" case here -- rejection routes
        `await_web_search_approval` -> `prepare_gap_research` inside the
        same graph invocation (the existing document-only gap path), which
        always leaves the graph at either another interrupt or a normal
        completion, exactly as if this feature had never suggested a search."""

        generation_runtime, retrieval, context_builder, storage = self._v1_graph_dependencies()
        started = perf_counter()
        budget = ResearchPlanningPolicy().budget_for(plan.complexity)
        transition_run(
            run, target=ResearchRunStatus.RESEARCHING, phase="resuming_after_web_search_decision"
        )
        await self._session.commit()
        await self._publish_runtime_event(
            run_id=run.id, event_type=ResearchEventType.RESEARCH_RESUMED
        )
        async with postgres_checkpointer(self._database_url) as checkpointer:
            graph = self._compile_graph_for_run(
                run=run,
                checkpointer=checkpointer,
                generation_runtime=generation_runtime,
                retrieval=retrieval,
                context_builder=context_builder,
                storage=storage,
            )
            graph_config: RunnableConfig = {
                "configurable": {"thread_id": run.graph_thread_id},
                "recursion_limit": settings.research_runtime_graph_recursion_limit,
            }
            try:
                result = await asyncio.wait_for(
                    graph.ainvoke(Command(resume=decision), config=graph_config),
                    timeout=budget.max_duration_seconds,
                )
            except TimeoutError as exc:
                raise ResearchRunBudgetExceededError(
                    f"Research run '{run.id}' exceeded its "
                    f"{budget.max_duration_seconds}s duration budget."
                ) from exc
        return await self._finalize_or_pause(
            run=run,
            result=result,
            query=query,
            owner_id=owner_id,
            conversation_id=conversation_id,
            started=started,
        )

    async def _finalize_or_pause(
        self,
        *,
        run: ResearchRun,
        result: dict[str, Any],
        query: str,
        owner_id: UUID,
        conversation_id: UUID | None,
        started: float,
    ) -> ResearchOutcome | None:
        if result.get("__interrupt__"):
            interrupt_kind = self._interrupt_kind(result["__interrupt__"])
            if interrupt_kind == "plan_approval":
                transition_run(
                    run,
                    target=ResearchRunStatus.AWAITING_PLAN_APPROVAL,
                    phase="awaiting_plan_approval",
                )
                await self._session.commit()
                await self._publish_runtime_event(
                    run_id=run.id, event_type=ResearchEventType.RESEARCH_AWAITING_PLAN_APPROVAL
                )
                logger.info(
                    "research_runtime.execution.paused_for_plan_approval",
                    research_run_id=str(run.id),
                )
                return None
            if interrupt_kind == "web_search_approval":
                transition_run(
                    run,
                    target=ResearchRunStatus.AWAITING_WEB_SEARCH_APPROVAL,
                    phase="awaiting_web_search_approval",
                )
                await self._session.commit()
                await self._publish_runtime_event(
                    run_id=run.id,
                    event_type=ResearchEventType.RESEARCH_AWAITING_WEB_SEARCH_APPROVAL,
                )
                logger.info(
                    "research_runtime.execution.paused_for_web_search_approval",
                    research_run_id=str(run.id),
                )
                return None
            transition_run(
                run, target=ResearchRunStatus.AWAITING_APPROVAL, phase="awaiting_report_approval"
            )
            await self._session.commit()
            await self._publish_runtime_event(
                run_id=run.id, event_type=ResearchEventType.RESEARCH_AWAITING_APPROVAL
            )
            logger.info(
                "research_runtime.execution.paused_for_report_approval",
                research_run_id=str(run.id),
            )
            return None

        review = ResearchReview.model_validate(result["review"])
        run.budget_usage = {
            **(run.budget_usage or {}),
            "review_decision": review.decision.value,
            "synthesis_revision_count": result.get("synthesis_revision_count", 0),
            "gap_research_count": result.get("gap_research_count", 0),
            "plan_version": result.get("plan_version", 1),
            "review_artifact_refs": result.get("review_artifact_refs", []),
            **self._web_search_signal(result),
        }
        transition_run(run, target=ResearchRunStatus.REVIEWING, phase="deterministic_review")
        transition_run(run, target=ResearchRunStatus.SYNTHESIZING, phase="persist_runtime_report")
        await self._session.commit()
        from app.ai.runtime.research.evidence import ResearchEvidenceBundle
        from app.ai.runtime.research.synthesis.models import ResearchDraft

        return await self._research_service.publish_runtime_report(
            query=query,
            draft=ResearchDraft.model_validate(result["draft"]),
            evidence=ResearchEvidenceBundle.model_validate(result["evidence_bundle"]),
            owner_id=owner_id,
            conversation_id=conversation_id,
            duration_ms=(perf_counter() - started) * 1000,
            memory_used=bool(result.get("injected_memory_ids")),
        )

    @staticmethod
    def _interrupt_kind(interrupts: Any) -> str:
        """Distinguish which checkpoint a graph paused at from `result["__interrupt__"]`
        (a tuple of LangGraph `Interrupt` objects). Defaults to `"report_approval"`
        when the kind can't be determined -- that was this codebase's only
        interrupt before the plan-approval checkpoint existed, so an
        unrecognized/malformed payload should fail the same way it always did
        rather than silently misrouting to a plan-approval status."""

        for item in interrupts:
            value = getattr(item, "value", None)
            if isinstance(value, dict) and value.get("kind") == "plan_approval":
                return "plan_approval"
            if isinstance(value, dict) and value.get("kind") == "web_search_approval":
                return "web_search_approval"
        return "report_approval"

    async def _publish_runtime_event(
        self,
        *,
        run_id: UUID,
        event_type: ResearchEventType,
        extra_metadata: Mapping[str, Any] | None = None,
    ) -> None:
        # Only forward `extra_metadata` when a call site actually sets it --
        # keeps the recorded call shape identical to before this parameter
        # existed for the (still far more common) plain calls, which several
        # tests assert on via `assert_any_await(run_id=..., event_type=...)`.
        if extra_metadata is not None:
            await self._event_journal.publish(
                run_id=run_id, event_type=event_type, extra_metadata=extra_metadata
            )
        else:
            await self._event_journal.publish(run_id=run_id, event_type=event_type)
        await self._session.commit()

    @staticmethod
    def request_fingerprint(
        *,
        query: str,
        top_k: int,
        filters: dict[str, Any],
        provider: GenerationProvider | None,
        routing_strategy: RoutingStrategy | None,
        conversation_id: UUID | None,
    ) -> str:
        payload = {
            "query": query,
            "top_k": top_k,
            "filters": filters,
            "provider": provider.value if provider else None,
            "routing_strategy": routing_strategy.value if routing_strategy else None,
            "conversation_id": str(conversation_id) if conversation_id else None,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(encoded.encode()).hexdigest()

    async def _begin(self, run: ResearchRun, *, allow_resume_in_progress: bool = False) -> None:
        if run.status == ResearchRunStatus.CREATED.value:
            transition_run(run, target=ResearchRunStatus.PLANNING, phase="runtime_initialize")
        elif run.status == ResearchRunStatus.PAUSED.value:
            transition_run(run, target=ResearchRunStatus.PLANNING, phase="runtime_resume")
        elif allow_resume_in_progress and run.status in _RESUMABLE_IN_PROGRESS_STATUSES:
            # A prior attempt never reached a terminal state -- most likely the
            # worker process crashed mid-run. The dispatch outbox only
            # re-delivers a run after its lease expires (see
            # ResearchRunDispatchRepository.claim_next), so a second attempt
            # reaching this branch means the earlier one is dead, not
            # concurrently running. The LangGraph checkpoint resumes the graph
            # from its last completed step rather than restarting.
            logger.warning(
                "research_runtime.execution.resuming_interrupted_run",
                research_run_id=str(run.id),
                status=run.status,
            )
        else:
            raise RuntimeError(f"Research run '{run.id}' is already in progress.")
        run.attempt_count = (run.attempt_count or 0) + 1
        await self._session.commit()

    async def _retrieve_memory_context(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        query: str,
    ) -> FormattedMemoryContext:
        """Best-effort, mirrors `ResearchProposalService._retrieve_memory_context`:
        this fallback path only runs when a plan wasn't already proposed/approved
        (the `execute()` compatibility path), so it needs the same injection."""

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
                "research_runtime.execution.memory_retrieval_failed",
                owner_id=str(owner_id),
                error_type=type(exc).__name__,
            )
            return FormattedMemoryContext(text=None, memory_ids=())
        return format_memory_context_with_ids(context)

    async def _is_cancellation_requested(self, run_id: UUID) -> bool:
        return await self._runs.is_cancellation_requested(run_id=run_id)

    async def _cost_so_far(self, run_id: UUID) -> float:
        return await GenerationUsageRepository(self._session).sum_cost_for_session(run_id)

    async def _replay_completed(self, *, run: ResearchRun, owner_id: UUID) -> ResearchOutcome:
        if run.research_session_id is None:
            raise RuntimeError(f"Completed research run '{run.id}' has no persisted answer.")
        session = await self._research_sessions.get_by_id_for_owner(
            research_id=run.research_session_id,
            owner_id=owner_id,
        )
        if session is None or session.conversation_id is None:
            raise RuntimeError(f"Completed research run '{run.id}' cannot be replayed.")
        duration_ms = 0.0
        if run.started_at and run.completed_at:
            duration_ms = (run.completed_at - run.started_at).total_seconds() * 1000
        return ResearchOutcome(
            research_id=session.id,
            conversation_id=session.conversation_id,
            query=session.query,
            answer=session.answer,
            citations=[Citation.model_validate(item) for item in session.citations],
            sources=[ResearchSource.model_validate(item) for item in session.sources],
            duration_ms=duration_ms,
        )

    @staticmethod
    def _web_search_signal(result: dict[str, Any]) -> dict[str, object]:
        """E23 follow-up (`EVALUATION_PLAN.md` §10): mirrors Chat's
        `web_search_invoked`/`web_search_success` semantics exactly --
        only written at all when web search was genuinely eligible for
        this run (`WebSearchMode` not `DISABLED`), and `web_search_success`
        only set when `web_search_invoked` is `True` (success is
        meaningless for a run that never searched). Folded into
        `run.budget_usage` here so `OnlineScoringJob` can read it back
        with the exact same single-row lookup already used for
        `review_decision` -- no new event-aggregation query needed."""

        mode = result.get("web_search_mode") or WebSearchMode.DISABLED.value
        if mode == WebSearchMode.DISABLED.value:
            return {}
        invoked = result.get("web_search_count", 0) > 0
        signal: dict[str, object] = {"web_search_invoked": invoked}
        if invoked:
            signal["web_search_success"] = result.get("web_search_success_count", 0) > 0
        return signal

    def _record_run_duration(self, run: ResearchRun) -> None:
        """E17 follow-up: end-to-end run duration, `completed_at -
        started_at` -- includes human-approval wait time by design (that's
        a real part of "how long did this run take," not noise to strip
        out), so this uses its own metric/bucket set
        (`RESEARCH_RUN_DURATION`/`DEEP_RESEARCH_RUN_BUCKETS`), not
        `RESEARCH_DURATION` (Chat/Linear Research's single-turn, seconds-
        scale latency). Called from every terminal-transition path
        (`_complete_run`, `_mark_terminal`, `_mark_failed`) right after
        `transition_run()` sets `run.completed_at` -- best-effort, a
        metrics failure must never break run completion itself."""

        if run.started_at is None or run.completed_at is None:
            return
        try:
            duration_ms = (run.completed_at - run.started_at).total_seconds() * 1000
            self._metrics.record_duration(operation=RESEARCH_RUN_DURATION, duration_ms=duration_ms)
        except Exception:
            logger.exception("research_runtime.duration_metric_failed", run_id=str(run.id))

    async def _mark_terminal(
        self, run: ResearchRun, status: ResearchRunStatus, reason: str
    ) -> None:
        try:
            transition_run(run, target=status, phase="terminal")
            run.terminal_reason = reason
            self._record_run_duration(run)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            logger.exception("research_runtime.terminal_persistence_failed", run_id=str(run.id))

    async def _mark_failed(
        self,
        run: ResearchRun,
        exc: Exception,
        *,
        reason: str = "runtime_or_compatibility_bridge_failed",
    ) -> None:
        try:
            transition_run(run, target=ResearchRunStatus.FAILED, phase="failed")
            run.terminal_reason = reason
            run.error_summary = {
                "type": type(exc).__name__,
                "message": str(exc)[:500],
                "recorded_at": datetime.now(UTC).isoformat(),
            }
            self._record_run_duration(run)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            logger.exception("research_runtime.failure_persistence_failed", run_id=str(run.id))

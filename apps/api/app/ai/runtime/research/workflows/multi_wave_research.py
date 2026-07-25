"""Top-level LangGraph loop that executes every validated dependency wave."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Annotated, Any, Literal, TypedDict
from uuid import UUID

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from app.ai.runtime.chat.paper_query import PaperQueryExtractionService
from app.ai.runtime.events.research.models import ResearchEventType
from app.ai.runtime.research.evidence import ResearchEvidenceBundle, build_evidence_bundle
from app.ai.runtime.research.evidence_artifact import (
    ResearchEvidenceArtifact,
    ResearchEvidenceArtifactWriter,
)
from app.ai.runtime.research.exceptions import (
    ResearchPlanRejectedError,
    ResearchReportRejectedError,
    ResearchRunCancelledError,
)
from app.ai.runtime.research.planner.models import ResearchComplexity, ResearchPlanTask
from app.ai.runtime.research.planner.policies import ResearchPlanningPolicy
from app.ai.runtime.research.reducers import merge_by_stable_id
from app.ai.runtime.research.report_artifact import ResearchFinalReportArtifactWriter
from app.ai.runtime.research.retrieval.models import (
    ResearchEvidenceReference,
    ResearchTaskResult,
    ResearchTaskStatus,
)
from app.ai.runtime.research.retrieval.service import ResearchTaskRetrievalService
from app.ai.runtime.research.review import (
    ResearchReview,
    ResearchReviewService,
    ReviewDecision,
    review_draft,
)
from app.ai.runtime.research.review_artifact import (
    ResearchReviewArtifact,
    ResearchReviewArtifactWriter,
)
from app.ai.runtime.research.synthesis.models import ResearchDraft
from app.ai.runtime.research.synthesis.service import (
    ResearchSynthesisError,
    ResearchSynthesisService,
)
from app.ai.runtime.research.web_search.evidence import normalize_web_search_result
from app.ai.runtime.research.web_search.models import WebSearchMode
from app.ai.runtime.research.web_search.necessity import WebSearchNecessityService
from app.ai.tools.paper_search.models import PaperSearchRequest
from app.ai.tools.paper_search.service import PaperSearchService
from app.ai.tools.web_search.models import WebSearchRequest
from app.ai.tools.web_search.service import WebSearchService
from app.core.settings import settings

logger = structlog.get_logger()


class MultiWaveResearchState(TypedDict):
    research_run_id: str
    owner_id: str
    plan: dict[str, object]
    waves: list[list[dict[str, object]]]
    wave_index: int
    current_wave: list[dict[str, object]]
    filters: dict[str, object]
    top_k: int
    task: dict[str, object]
    task_results: Annotated[dict[str, dict[str, object]], merge_by_stable_id]
    evidence_bundle: dict[str, object]
    evidence_artifact_ref: str
    draft: dict[str, object]
    review: dict[str, object]
    synthesis_revision_count: int
    revision_instructions: list[str]
    gap_research_count: int
    plan_version: int
    plan_versions: list[dict[str, object]]
    review_artifact_refs: list[str]
    final_report_ref: str
    final_report_pdf_ref: str
    plan_decision: str
    plan_rejection_reason: str | None
    report_decision: str
    report_rejection_reason: str | None
    web_search_mode: str
    web_search_auto_approve: bool
    web_search_include_domains: list[str]
    web_search_exclude_domains: list[str]
    web_search_count: int
    web_search_suggestion: dict[str, object]
    web_search_decision: str
    web_search_rejection_reason: str | None
    paper_suggestions_enabled: bool
    related_papers_suggestion: dict[str, object]


def compile_multi_wave_research_graph(
    *,
    checkpointer: Any,
    task_retrieval: ResearchTaskRetrievalService,
    evidence_writer: ResearchEvidenceArtifactWriter,
    synthesis: ResearchSynthesisService,
    final_report_writer: ResearchFinalReportArtifactWriter,
    reviewer: ResearchReviewService | None = None,
    review_writer: ResearchReviewArtifactWriter | None = None,
    progress: (
        Callable[[ResearchEventType, Mapping[str, object] | None], Awaitable[None]] | None
    ) = None,
    cancellation_check: Callable[[], Awaitable[bool]] | None = None,
    cost_lookup: Callable[[], Awaitable[float]] | None = None,
    web_search: WebSearchService | None = None,
    web_search_necessity: WebSearchNecessityService | None = None,
    paper_search: PaperSearchService | None = None,
    paper_query_extraction: PaperQueryExtractionService | None = None,
) -> Any:
    """Compile bounded waves through synthesis, review, and final artifacts.

    Draft content is schema-bounded and lives in state only for the immediate
    review/finalization handoff. Durable artifact keys are the long-lived graph
    outputs; raw documents and provider responses never enter graph state.
    """

    async def emit(
        event_type: ResearchEventType,
        *,
        extra_metadata: Mapping[str, object] | None = None,
    ) -> None:
        if progress is not None:
            await progress(event_type, extra_metadata)

    async def check_not_cancelled(research_run_id: str) -> None:
        if cancellation_check is not None and await cancellation_check():
            logger.info(
                "research_runtime.graph.cancellation_observed",
                research_run_id=research_run_id,
            )
            raise ResearchRunCancelledError(f"Research run '{research_run_id}' was cancelled.")

    async def prepare_wave(state: MultiWaveResearchState) -> dict[str, object]:
        await check_not_cancelled(state["research_run_id"])
        index = state.get("wave_index", 0)
        wave = state["waves"][index]
        logger.info(
            "research_runtime.graph.wave_started",
            research_run_id=state["research_run_id"],
            wave_index=index,
            wave_count=len(state["waves"]),
            task_count=len(wave),
        )
        return {"current_wave": wave}

    def dispatch_wave(state: MultiWaveResearchState) -> list[Send]:
        return [
            Send(
                "retrieve_task",
                {
                    "task": task,
                    "owner_id": state["owner_id"],
                    "research_run_id": state["research_run_id"],
                    "filters": state.get("filters", {}),
                    "top_k": state.get("top_k", 5),
                },
            )
            for task in state["current_wave"]
        ]

    async def retrieve_task(state: MultiWaveResearchState) -> dict[str, object]:
        task = ResearchPlanTask.model_validate(state["task"])
        result = await task_retrieval.execute_task(
            task=task,
            owner_id=UUID(state["owner_id"]),
            filters=state.get("filters", {}),
            top_k=state.get("top_k", 5),
        )
        logger.info(
            "research_runtime.graph.task_retrieved",
            research_run_id=state["research_run_id"],
            task_id=task.task_id,
            status=result.status.value,
            evidence_count=len(result.evidence),
        )
        return {"task_results": {task.task_id: result.model_dump(mode="json")}}

    def advance_wave(state: MultiWaveResearchState) -> dict[str, object]:
        return {"wave_index": state.get("wave_index", 0) + 1}

    def route_after_wave(state: MultiWaveResearchState) -> Literal["prepare_wave", "aggregate"]:
        return "prepare_wave" if state["wave_index"] < len(state["waves"]) else "aggregate"

    async def aggregate(state: MultiWaveResearchState) -> dict[str, object]:
        await emit(ResearchEventType.RETRIEVAL_COMPLETED)
        await emit(ResearchEventType.EVIDENCE_STARTED)
        task_results = {
            task_id: ResearchTaskResult.model_validate(result)
            for task_id, result in state.get("task_results", {}).items()
        }
        bundle = build_evidence_bundle(task_results)
        artifact = ResearchEvidenceArtifact(
            research_run_id=UUID(state["research_run_id"]),
            plan=state["plan"],
            task_results=task_results,
            evidence_bundle=bundle,
        )
        update: dict[str, object] = {
            "evidence_bundle": bundle.model_dump(mode="json"),
            "evidence_artifact_ref": await evidence_writer.write(artifact),
        }
        logger.info(
            "research_runtime.graph.evidence_aggregated",
            research_run_id=state["research_run_id"],
            completed_task_count=bundle.completed_task_count,
            failed_task_count=bundle.failed_task_count,
            evidence_count=len(bundle.evidence),
            warning_count=len(bundle.warnings),
        )
        await emit(ResearchEventType.EVIDENCE_COMPLETED)
        return update

    def route_after_aggregate(
        state: MultiWaveResearchState,
    ) -> Literal["evaluate_web_search_need", "await_plan_approval"]:
        """Detour through the web-search-need evaluation before plan
        approval whenever web search is enabled -- catching a private
        corpus that's topically irrelevant to the goal (not just "thin")
        before the costly synthesis call is ever spent on it, rather than
        only after a post-synthesis reviewer flags a gap. `REQUIRED` always
        detours (deterministic, no LLM call inside `evaluate_web_search_need`
        -- see `WebSearchNecessityService.decide`); `AUTO` detours
        unconditionally too, since the necessity call itself is the cheap
        judgment of whether the evidence just gathered is even on-topic --
        there's no reliable numeric signal on `ResearchEvidenceReference.
        score` to gate this on instead (it's a Reciprocal Rank Fusion sum,
        rank-derived rather than a semantic-similarity measure). `DISABLED`
        or an unconfigured web-search platform skips straight to plan
        approval, exactly as before this detour existed."""

        mode = WebSearchMode(state.get("web_search_mode", WebSearchMode.DISABLED.value))
        if not _web_search_ready():
            if mode is WebSearchMode.REQUIRED:
                logger.warning(
                    "research_runtime.graph.web_search_required_unavailable",
                    research_run_id=state["research_run_id"],
                )
            return "await_plan_approval"
        if mode is WebSearchMode.DISABLED:
            return "await_plan_approval"
        return "evaluate_web_search_need"

    async def await_plan_approval(state: MultiWaveResearchState) -> dict[str, object]:
        """Pause for a human plan-approval decision (`interrupt()`), once real
        evidence exists but before the costly synthesis call spends it.

        Reached once per run, but from one of two edges depending on whether
        web search is enabled: directly from `aggregate` when web search is
        `disabled` (or unavailable), or -- when `auto`/`required` -- after
        the early evidence-relevance detour (`evaluate_web_search_need` /
        `await_web_search_approval` / `search_web_gap` /
        `aggregate_gap_evidence`, see `route_after_aggregate` and
        `route_after_gap_evidence_aggregation`) resolves, so this node
        always sees the final evidence bundle either way. The automatic
        `REVISE_SYNTHESIS`/`RESEARCH_GAPS` repair loops that run *after*
        this checkpoint route `prepare_synthesis_revision`/
        `aggregate_gap_evidence` straight back to `synthesize` instead,
        bypassing it a second time, since those are bounded system retries,
        not new human decision points.

        Same no-side-effects-before-`interrupt()` rule as
        `await_report_approval` -- LangGraph replays this node's body from
        the top on every resume attempt for this thread.

        An approval can carry `edited_plan` (currently just a revised
        `rewritten_goal` -- editing `tasks` here would be moot, since
        retrieval for the original tasks has already run), overwriting
        `state["plan"]["rewritten_goal"]` before `synthesize` reads it.

        Rejection does not fail the run: `route_after_plan_approval` sends
        it straight to `END` without ever calling `synthesize`. There is no
        draft to publish as a plain answer in this case (unlike a rejected
        *report*, which still has one) -- the execution service marks the
        run terminal without a `publish_runtime_report` call.
        """

        decision = interrupt({"kind": "plan_approval", "research_run_id": state["research_run_id"]})
        if not isinstance(decision, dict):
            raise ResearchPlanRejectedError(
                "The plan-approval interrupt resumed with an invalid decision payload."
            )
        if decision.get("decision") != "approved":
            reason = decision.get("reason")
            logger.info(
                "research_runtime.graph.plan_rejected",
                research_run_id=state["research_run_id"],
                reason=reason,
            )
            return {"plan_decision": "rejected", "plan_rejection_reason": reason}
        update: dict[str, object] = {"plan_decision": "approved"}
        edited_plan = decision.get("edited_plan")
        if isinstance(edited_plan, dict) and isinstance(edited_plan.get("rewritten_goal"), str):
            update["plan"] = {**state["plan"], "rewritten_goal": edited_plan["rewritten_goal"]}
        return update

    async def synthesize(state: MultiWaveResearchState) -> dict[str, object]:
        await check_not_cancelled(state["research_run_id"])
        await emit(ResearchEventType.SYNTHESIS_STARTED)
        plan = state["plan"]
        goal = plan.get("rewritten_goal") or plan.get("goal")
        if not isinstance(goal, str) or not goal:
            raise ValueError("Research plan is missing its goal.")
        evidence = ResearchEvidenceBundle.model_validate(state["evidence_bundle"])
        is_revision = bool(state.get("revision_instructions"))
        revision_instructions = state.get("revision_instructions", [])
        synthesis_revision_count = state.get("synthesis_revision_count", 0)
        budget = ResearchPlanningPolicy().budget_for(ResearchComplexity(str(plan["complexity"])))
        try:
            draft = await synthesis.synthesize(
                goal=goal,
                evidence=evidence,
                owner_id=UUID(state["owner_id"]),
                research_run_id=UUID(state["research_run_id"]),
                revision_instructions=revision_instructions,
            )
        except ResearchSynthesisError as exc:
            if synthesis_revision_count >= budget.max_review_iterations:
                logger.exception(
                    "research_runtime.graph.synthesis_failed",
                    research_run_id=state["research_run_id"],
                    is_revision=is_revision,
                )
                raise
            logger.warning(
                "research_runtime.graph.synthesis_retrying_after_failure",
                research_run_id=state["research_run_id"],
                reason=str(exc),
            )
            synthesis_revision_count += 1
            draft = await synthesis.synthesize(
                goal=goal,
                evidence=evidence,
                owner_id=UUID(state["owner_id"]),
                research_run_id=UUID(state["research_run_id"]),
                revision_instructions=[str(exc)],
            )
        except Exception:
            logger.exception(
                "research_runtime.graph.synthesis_failed",
                research_run_id=state["research_run_id"],
                is_revision=is_revision,
            )
            raise
        logger.info(
            "research_runtime.graph.synthesis_completed",
            research_run_id=state["research_run_id"],
            is_revision=is_revision,
            finding_count=len(draft.findings),
        )
        await emit(ResearchEventType.SYNTHESIS_COMPLETED)
        update: dict[str, object] = {"draft": draft.model_dump(mode="json")}
        if synthesis_revision_count != state.get("synthesis_revision_count", 0):
            update["synthesis_revision_count"] = synthesis_revision_count
        return update

    async def review(state: MultiWaveResearchState) -> dict[str, object]:
        await emit(ResearchEventType.REVIEW_STARTED)
        draft = ResearchDraft.model_validate(state["draft"])
        evidence = ResearchEvidenceBundle.model_validate(state["evidence_bundle"])
        goal = state["plan"].get("rewritten_goal") or state["plan"].get("goal")
        if not isinstance(goal, str) or not goal:
            raise ValueError("Research plan is missing its goal.")
        result = (
            await reviewer.review(
                goal=goal,
                draft=draft,
                evidence=evidence,
                owner_id=UUID(state["owner_id"]),
                research_run_id=UUID(state["research_run_id"]),
            )
            if reviewer is not None
            else review_draft(draft=draft, evidence=evidence)
        )
        update: dict[str, object] = {"review": result.model_dump(mode="json")}
        if review_writer is not None:
            iteration = state.get("synthesis_revision_count", 0) + state.get(
                "gap_research_count", 0
            )
            ref = await review_writer.write(
                ResearchReviewArtifact(
                    research_run_id=UUID(state["research_run_id"]),
                    iteration=iteration,
                    review=result,
                )
            )
            update["review_artifact_refs"] = [*state.get("review_artifact_refs", []), ref]
        logger.info(
            "research_runtime.graph.review_completed",
            research_run_id=state["research_run_id"],
            decision=result.decision.value,
            citation_integrity_score=result.citation_integrity_score,
            completeness_score=result.completeness_score,
        )
        await emit(ResearchEventType.REVIEW_COMPLETED)
        return update

    async def await_report_approval(state: MultiWaveResearchState) -> dict[str, object]:
        """Pause for a human report-approval decision (`interrupt()`).

        No side effects belong before `interrupt()`: LangGraph re-runs this
        node's body from the top on every resume attempt for this thread,
        replaying anything ahead of the call -- the `RESEARCH_AWAITING_
        APPROVAL`/`RESEARCH_RESUMED` events are emitted by the execution
        service around each `ainvoke()` call instead, exactly once each.

        Rejection does not fail the run: `route_after_report_approval` sends
        it straight to `END`, skipping `persist_final_report` (the PDF-
        writing node) rather than raising. `draft`/`evidence_bundle`/
        `review` are already set in state by earlier nodes and survive
        regardless of which node the graph terminates at, so the execution
        service can still publish the already-synthesized draft as a plain
        answer (`ResearchService.publish_runtime_report` only needs
        `draft`/`evidence_bundle` -- never the PDF) -- only the polished PDF
        report is skipped, not the whole run.

        An approval can carry `edited_draft` (a fully valid, already-merged
        `ResearchDraft` dict -- see `ResearchRunService.
        record_report_decision`), overwriting `state["draft"]` before
        `persist_final_report`/`publish_runtime_report` read it, so a
        reviewer's edits apply to both the PDF and the plain-answer path
        uniformly.
        """

        decision = interrupt(
            {"kind": "report_approval", "research_run_id": state["research_run_id"]}
        )
        if not isinstance(decision, dict):
            # Not a rejection -- a genuinely malformed resume payload (e.g. a
            # bug upstream of this node), which nothing downstream can
            # recover from.
            raise ResearchReportRejectedError(
                "The report-approval interrupt resumed with an invalid decision payload."
            )
        if decision.get("decision") != "approved":
            reason = decision.get("reason")
            logger.info(
                "research_runtime.graph.report_rejected",
                research_run_id=state["research_run_id"],
                reason=reason,
            )
            return {"report_decision": "rejected", "report_rejection_reason": reason}
        update: dict[str, object] = {"report_decision": "approved"}
        edited_draft = decision.get("edited_draft")
        if isinstance(edited_draft, dict):
            update["draft"] = edited_draft
        return update

    def prepare_synthesis_revision(state: MultiWaveResearchState) -> dict[str, object]:
        review_result = ResearchReview.model_validate(state["review"])
        return {
            "synthesis_revision_count": state.get("synthesis_revision_count", 0) + 1,
            "revision_instructions": review_result.revision_instructions,
        }

    def prepare_gap_research(state: MultiWaveResearchState) -> dict[str, object]:
        review_result = ResearchReview.model_validate(state["review"])
        if not review_result.gap_questions:
            raise ValueError("Gap-research routing requires a targeted question.")
        next_count = state.get("gap_research_count", 0) + 1
        task = ResearchPlanTask(
            task_id=f"gap-{next_count}",
            question=review_result.gap_questions[0],
            priority=1,
        )
        next_version = state.get("plan_version", 1) + 1
        logger.info(
            "research_runtime.graph.gap_research_triggered",
            research_run_id=state["research_run_id"],
            gap_research_count=next_count,
            plan_version=next_version,
            task_id=task.task_id,
        )
        return {
            "task": task.model_dump(mode="json"),
            "gap_research_count": next_count,
            "plan_version": next_version,
            "plan_versions": [
                *state.get("plan_versions", []),
                {
                    "version": next_version,
                    "reason": "review_evidence_gap",
                    "task_id": task.task_id,
                    "question": task.question,
                },
            ],
        }

    def finalize_gap_limitations(state: MultiWaveResearchState) -> dict[str, object]:
        """Publish the existing draft as `completed_with_limitations` instead
        of failing outright once the review-repair budget runs out --
        reached both when a `RESEARCH_GAPS` follow-up couldn't close every
        gap in time, and (since 2026-07-25) when a `REVISE_SYNTHESIS`
        citation-integrity fix couldn't be attempted again in time either.
        The disclosed limitation differs by which one triggered it, so a
        reader knows what's actually still wrong with the report."""

        review_result = ResearchReview.model_validate(state["review"])
        limitation = (
            "The draft's citation issues could not be corrected within the review budget."
            if review_result.decision is ReviewDecision.REVISE_SYNTHESIS
            else "The bounded targeted evidence follow-up did not close every review gap."
        )
        logger.info(
            "research_runtime.graph.finalizing_with_limitations",
            research_run_id=state["research_run_id"],
            limitations=review_result.limitations,
            triggering_decision=review_result.decision.value,
        )
        return {
            "review": review_result.model_copy(
                update={
                    "decision": ReviewDecision.FINALIZE_WITH_LIMITATIONS,
                    "limitations": [*review_result.limitations, limitation],
                }
            ).model_dump(mode="json")
        }

    async def retrieve_gap_task(state: MultiWaveResearchState) -> dict[str, object]:
        task = ResearchPlanTask.model_validate(state["task"])
        result = await task_retrieval.execute_task(
            task=task,
            owner_id=UUID(state["owner_id"]),
            filters=state.get("filters", {}),
            top_k=state.get("top_k", 5),
        )
        return {"task_results": {task.task_id: result.model_dump(mode="json")}}

    async def aggregate_gap_evidence(state: MultiWaveResearchState) -> dict[str, object]:
        task_results = {
            task_id: ResearchTaskResult.model_validate(result)
            for task_id, result in state.get("task_results", {}).items()
        }
        bundle = build_evidence_bundle(task_results)
        artifact = ResearchEvidenceArtifact(
            research_run_id=UUID(state["research_run_id"]),
            plan={
                **state["plan"],
                "plan_version": state.get("plan_version", 1),
                "plan_versions": state.get("plan_versions", []),
            },
            task_results=task_results,
            evidence_bundle=bundle,
        )
        return {
            "evidence_bundle": bundle.model_dump(mode="json"),
            "evidence_artifact_ref": await evidence_writer.write(artifact, version=2),
        }

    def _web_search_ready() -> bool:
        return web_search is not None and web_search_necessity is not None

    def _before_plan_approval(state: MultiWaveResearchState) -> bool:
        """True until `await_plan_approval` has actually resolved once.
        Distinguishes the *early* evidence-relevance detour (reached from
        `aggregate`, before plan approval) from the *post-review* gap-repair
        detour (reached from `review`'s `RESEARCH_GAPS` decision, always
        after plan approval already resolved) -- both routes share the same
        `evaluate_web_search_need`/`await_web_search_approval`/
        `search_web_gap`/`aggregate_gap_evidence` nodes, so the "what do we
        do when there's nothing to suggest/it's rejected" fallback and the
        "where does aggregated evidence go next" edge both need to know
        which context they're in."""

        return state.get("plan_decision") in (None, "")

    def route_after_gap_evidence_aggregation(
        state: MultiWaveResearchState,
    ) -> Literal["await_plan_approval", "synthesize"]:
        """`aggregate_gap_evidence` is shared by two contexts: the early,
        pre-plan-approval evidence-relevance detour (`search_web_gap` ->
        here -> should continue on to `await_plan_approval`, since
        `synthesize` hasn't run yet) and the post-review repair loop
        (`retrieve_gap_task`/`search_web_gap` -> here -> should loop back to
        `synthesize`, since a draft already exists to revise)."""

        return "await_plan_approval" if _before_plan_approval(state) else "synthesize"

    async def evaluate_web_search_need(state: MultiWaveResearchState) -> dict[str, object]:
        """Decide whether web search would help -- reached either early,
        right after initial evidence aggregation and before plan approval
        (so a topically-irrelevant private corpus gets caught before a
        synthesis call is ever spent on it, not just after a reviewer flags
        a gap post-synthesis), or from a real reviewer-identified gap
        (`RESEARCH_GAPS`) in the post-review repair loop (see
        `route_after_aggregate` / `route_after_review`). Deterministic
        pre-rules short-circuit `DISABLED`/`REQUIRED` (no LLM call); `AUTO`
        defers to `WebSearchNecessityService`'s cheap model call, which
        judges topical relevance as well as recency/coverage gaps -- not a
        numeric retrieval-score threshold (Reciprocal Rank Fusion scores are
        rank-derived, not a semantic-similarity signal, so a raw threshold
        on them can't distinguish a genuinely irrelevant top hit from a
        genuinely relevant one). Writes only a suggestion into state --
        `search_web_gap` is the node that actually spends the per-run
        web-search budget."""

        if not _web_search_ready():
            return {"web_search_suggestion": {}}
        mode = WebSearchMode(state.get("web_search_mode", WebSearchMode.DISABLED.value))
        if mode is WebSearchMode.DISABLED:
            return {"web_search_suggestion": {}}
        assert web_search is not None and web_search_necessity is not None
        if state.get("web_search_count", 0) >= web_search.policy.max_search_calls_per_run:
            logger.info(
                "research_runtime.graph.web_search_budget_exhausted",
                research_run_id=state["research_run_id"],
                web_search_count=state.get("web_search_count", 0),
            )
            return {"web_search_suggestion": {}}

        review_result = (
            ResearchReview.model_validate(state["review"]) if state.get("review") else None
        )
        gap_question = (
            review_result.gap_questions[0]
            if review_result is not None and review_result.gap_questions
            else None
        )
        goal = state["plan"].get("rewritten_goal") or state["plan"].get("goal")
        evidence = ResearchEvidenceBundle.model_validate(state["evidence_bundle"])
        decision = await web_search_necessity.decide(
            mode=mode,
            goal=str(goal),
            gap_question=gap_question,
            evidence=evidence,
            owner_id=UUID(state["owner_id"]),
            research_run_id=UUID(state["research_run_id"]),
        )
        logger.info(
            "research_runtime.graph.web_search_evaluated",
            research_run_id=state["research_run_id"],
            mode=mode.value,
            needs_web_search=decision.needs_web_search,
        )
        if not decision.needs_web_search:
            return {"web_search_suggestion": {}}
        return {
            "web_search_suggestion": {
                "query": decision.query,
                "reason": decision.reason,
                "gap_question": gap_question,
            }
        }

    def route_after_web_search_evaluation(
        state: MultiWaveResearchState,
    ) -> Literal[
        "await_plan_approval", "prepare_gap_research", "await_web_search_approval", "search_web_gap"
    ]:
        suggestion = state.get("web_search_suggestion") or {}
        if not suggestion.get("query"):
            # Disabled, budget-exhausted, or the model/deterministic rule
            # said no -- fall back to exactly the node this run would have
            # reached without this feature: `await_plan_approval` when this
            # is the early, pre-plan-approval check, `prepare_gap_research`
            # (today's doc-only gap path) when it's the post-review one.
            return "await_plan_approval" if _before_plan_approval(state) else "prepare_gap_research"
        mode = WebSearchMode(state.get("web_search_mode", WebSearchMode.DISABLED.value))
        if mode is WebSearchMode.REQUIRED or state.get("web_search_auto_approve", False):
            return "search_web_gap"
        return "await_web_search_approval"

    async def await_web_search_approval(state: MultiWaveResearchState) -> dict[str, object]:
        """Pause for a human decision on the agent's own web-search
        suggestion (`AUTO` mode, not pre-approved). Mirrors
        `await_plan_approval`'s `interrupt()` contract exactly -- no side
        effects before the call, since LangGraph replays this node's body
        from the top on every resume attempt for this thread.

        Unlike plan/report rejection, a rejection here is never a dead end:
        `route_after_web_search_approval` sends it to whichever node a
        `DISABLED`/AUTO-declined suggestion would have reached anyway --
        `await_plan_approval` if reached early (before plan approval),
        `prepare_gap_research` if reached from the post-review repair loop
        -- "reject and the run continues exactly as it would have without
        this feature." A malformed resume payload is treated the same way
        (as a rejection) rather than raising, for the same reason: there is
        always a safe existing fallback to fall back to here.
        """

        suggestion = state.get("web_search_suggestion") or {}
        decision = interrupt(
            {
                "kind": "web_search_approval",
                "research_run_id": state["research_run_id"],
                "suggested_query": suggestion.get("query"),
                "reason": suggestion.get("reason"),
            }
        )
        if not isinstance(decision, dict) or decision.get("decision") != "approved":
            reason = (
                decision.get("reason") if isinstance(decision, dict) else "invalid_resume_payload"
            )
            logger.info(
                "research_runtime.graph.web_search_rejected",
                research_run_id=state["research_run_id"],
                reason=reason,
            )
            return {"web_search_decision": "rejected", "web_search_rejection_reason": reason}
        return {"web_search_decision": "approved"}

    def route_after_web_search_approval(
        state: MultiWaveResearchState,
    ) -> Literal["await_plan_approval", "prepare_gap_research", "search_web_gap"]:
        if state.get("web_search_decision") == "rejected":
            return "await_plan_approval" if _before_plan_approval(state) else "prepare_gap_research"
        return "search_web_gap"

    async def search_web_gap(state: MultiWaveResearchState) -> dict[str, object]:
        """Spend one round of the per-run web-search budget and fold the
        result into `task_results` under a synthetic `web-{n}` task id, the
        same shape `retrieve_gap_task` produces for a document gap round --
        `aggregate_gap_evidence` (reused unchanged) doesn't need to know
        which kind of task produced an entry.

        Only increments `gap_research_count` -- the shared post-review
        repair budget (`ResearchPlanningPolicy.max_review_iterations`,
        checked in `route_after_review`) -- when reached from the
        post-review repair loop. The early, pre-plan-approval round (see
        `route_after_aggregate`) is evidence-gathering before any synthesis
        attempt has happened, not a repair of one; charging it against the
        same tiny budget (as low as 1 for MODERATE complexity) would leave
        zero budget for a genuine post-synthesis citation-integrity fix and
        turn an otherwise-recoverable `REVISE_SYNTHESIS` into a hard
        `fail()`."""

        assert web_search is not None
        suggestion = state.get("web_search_suggestion") or {}
        goal = state["plan"].get("rewritten_goal") or state["plan"].get("goal")
        query = str(suggestion.get("query") or goal)[:500]
        next_web_count = state.get("web_search_count", 0) + 1
        await emit(ResearchEventType.RESEARCH_WEB_SEARCH_STARTED)

        references: list[ResearchEvidenceReference] = []
        try:
            result = await web_search.search(
                WebSearchRequest(
                    query=query,
                    include_domains=list(state.get("web_search_include_domains", [])),
                    exclude_domains=list(state.get("web_search_exclude_domains", [])),
                )
            )
            references = await normalize_web_search_result(
                result,
                owner_id=UUID(state["owner_id"]),
                research_run_id=UUID(state["research_run_id"]),
                round_number=next_web_count,
            )
        except Exception as exc:
            logger.warning(
                "research_runtime.graph.web_search_failed",
                research_run_id=state["research_run_id"],
                error_type=type(exc).__name__,
            )

        next_gap_count = (
            state.get("gap_research_count", 0)
            if _before_plan_approval(state)
            else state.get("gap_research_count", 0) + 1
        )
        task_id = f"web-{next_web_count}"
        task_result = ResearchTaskResult(
            task_id=task_id,
            status=ResearchTaskStatus.COMPLETED if references else ResearchTaskStatus.FAILED,
            evidence=references,
            citation_ids=[ref.citation_id for ref in references if ref.citation_id],
            error_type=None if references else "no_web_evidence",
        )
        await emit(
            ResearchEventType.RESEARCH_WEB_SEARCH_COMPLETED
            if references
            else ResearchEventType.RESEARCH_WEB_SEARCH_SKIPPED
        )
        logger.info(
            "research_runtime.graph.web_search_gap_completed",
            research_run_id=state["research_run_id"],
            web_search_count=next_web_count,
            evidence_count=len(references),
        )
        return {
            "task_results": {task_id: task_result.model_dump(mode="json")},
            "web_search_count": next_web_count,
            "gap_research_count": next_gap_count,
            "plan_version": state.get("plan_version", 1) + 1,
            "plan_versions": [
                *state.get("plan_versions", []),
                {
                    "version": state.get("plan_version", 1) + 1,
                    "reason": "web_search_gap",
                    "task_id": task_id,
                    "question": query,
                },
            ],
        }

    async def route_after_review(
        state: MultiWaveResearchState,
    ) -> Literal[
        "prepare_synthesis_revision",
        "prepare_gap_research",
        "evaluate_web_search_need",
        "finalize_gap_limitations",
        "await_report_approval",
        "fail",
    ]:
        review_result = ResearchReview.model_validate(state["review"])
        mode = WebSearchMode(state.get("web_search_mode", WebSearchMode.DISABLED.value))

        if review_result.decision is ReviewDecision.FAIL:
            return "fail"
        if review_result.decision is ReviewDecision.PASS:
            # REQUIRED's "at least one web source" guarantee is already
            # enforced earlier, unconditionally, by `route_after_aggregate`
            # (before plan approval, before any synthesis call is spent) --
            # nothing left to force here.
            return "await_report_approval"

        budget = ResearchPlanningPolicy().budget_for(
            ResearchComplexity(str(state["plan"]["complexity"]))
        )
        iterations_used = state.get("synthesis_revision_count", 0) + state.get(
            "gap_research_count", 0
        )
        cost_so_far = await cost_lookup() if cost_lookup is not None else 0.0
        within_iteration_budget = iterations_used < budget.max_review_iterations
        within_cost_budget = cost_so_far < budget.max_estimated_cost_usd
        if not (within_iteration_budget and within_cost_budget):
            logger.info(
                "research_runtime.graph.review_budget_exhausted",
                research_run_id=state["research_run_id"],
                iterations_used=iterations_used,
                max_review_iterations=budget.max_review_iterations,
                cost_so_far_usd=cost_so_far,
                max_estimated_cost_usd=budget.max_estimated_cost_usd,
            )

        if review_result.decision is ReviewDecision.REVISE_SYNTHESIS:
            if within_iteration_budget and within_cost_budget:
                return "prepare_synthesis_revision"
            # A citation-integrity fix that can't be attempted again within
            # budget still has a real, synthesized draft to publish --
            # finalize with an explicit limitation instead of failing the
            # run outright (2026-07-25; matches how a budget-exhausted
            # RESEARCH_GAPS follow-up already degrades below).
            return "finalize_gap_limitations"
        if review_result.decision is ReviewDecision.RESEARCH_GAPS:
            if within_iteration_budget and within_cost_budget:
                if _web_search_ready() and mode is not WebSearchMode.DISABLED:
                    return "evaluate_web_search_need"
                return "prepare_gap_research"
            return "finalize_gap_limitations"
        return "await_report_approval"

    def fail(state: MultiWaveResearchState) -> dict[str, object]:
        review_result = ResearchReview.model_validate(state["review"])
        logger.warning(
            "research_runtime.graph.review_failed_terminally",
            research_run_id=state["research_run_id"],
            limitations=review_result.limitations,
        )
        raise RuntimeError("Research review failed: " + "; ".join(review_result.limitations))

    def route_after_report_approval(
        state: MultiWaveResearchState,
    ) -> Literal["persist_final_report", "__end__"]:
        if state.get("report_decision") == "rejected":
            return "__end__"
        return "persist_final_report"

    def route_after_plan_approval(
        state: MultiWaveResearchState,
    ) -> Literal["synthesize", "__end__"]:
        if state.get("plan_decision") == "rejected":
            return "__end__"
        return "synthesize"

    async def persist_final_report(state: MultiWaveResearchState) -> dict[str, object]:
        await emit(ResearchEventType.REPORT_STARTED)
        draft = ResearchDraft.model_validate(state["draft"])
        evidence = ResearchEvidenceBundle.model_validate(state["evidence_bundle"])
        review_result = ResearchReview.model_validate(state["review"])
        refs = await final_report_writer.write(
            research_run_id=UUID(state["research_run_id"]),
            draft=draft,
            review=review_result,
            evidence=evidence,
        )
        logger.info(
            "research_runtime.graph.final_report_persisted",
            research_run_id=state["research_run_id"],
            report_ref=refs.report_ref,
            pdf_ref=refs.pdf_ref,
            decision=review_result.decision.value,
        )
        await emit(ResearchEventType.REPORT_COMPLETED)
        return {
            "final_report_ref": refs.report_ref,
            "final_report_pdf_ref": refs.pdf_ref,
        }

    async def suggest_related_papers(state: MultiWaveResearchState) -> dict[str, object]:
        """Non-blocking, best-effort: suggest related papers via the
        Research Intelligence MCP server after the report is already
        persisted. Never gates or pauses the run (unlike the web-search
        approval checkpoint) -- any failure here is swallowed and reported
        as a SKIPPED event, never raised, so a broken/slow MCP server can
        never break report delivery."""

        if not state.get("paper_suggestions_enabled"):
            logger.info(
                "research_runtime.graph.related_papers_skipped",
                research_run_id=state["research_run_id"],
                reason="disabled_for_this_run",
            )
            return {"related_papers_suggestion": {}}
        if paper_search is None or not paper_search.available:
            logger.info(
                "research_runtime.graph.related_papers_skipped",
                research_run_id=state["research_run_id"],
                reason="service_unavailable",
            )
            return {"related_papers_suggestion": {}}

        await emit(ResearchEventType.RESEARCH_RELATED_PAPERS_STARTED)
        plan = state["plan"]
        goal = str(plan.get("rewritten_goal") or plan.get("goal") or "")
        # `goal` is typically a full sentence/question ("how tsunami
        # works?"), not a topic phrase -- confirmed live (2026-07-25) that
        # the MCP search backend returns zero results for that, the same
        # class of issue already fixed for Chat's raw-prompt query. Reuse
        # the same distillation service to get a short, focused query
        # before searching.
        query = goal
        if paper_query_extraction is not None:
            query = await paper_query_extraction.extract(
                user_prompt=goal,
                owner_id=UUID(state["owner_id"]),
                session_id=UUID(state["research_run_id"]),
            )

        try:
            result = await asyncio.wait_for(
                paper_search.search(PaperSearchRequest(query=query)),
                timeout=settings.mcp_papers_timeout_seconds,
            )
        except Exception as exc:
            logger.warning(
                "research_runtime.graph.related_papers_failed",
                research_run_id=state["research_run_id"],
                error_type=type(exc).__name__,
            )
            await emit(ResearchEventType.RESEARCH_RELATED_PAPERS_SKIPPED)
            return {"related_papers_suggestion": {}}

        if not result.items:
            await emit(ResearchEventType.RESEARCH_RELATED_PAPERS_SKIPPED)
            return {"related_papers_suggestion": {}}

        papers = [
            {
                "title": item.title,
                "authors": item.authors,
                "year": item.year,
                "url": item.url,
            }
            for item in result.items
        ]
        await emit(
            ResearchEventType.RESEARCH_RELATED_PAPERS_COMPLETED,
            extra_metadata={"papers": papers},
        )
        return {"related_papers_suggestion": {"query": query, "papers": papers}}

    graph = StateGraph(MultiWaveResearchState)
    graph.add_node("prepare_wave", prepare_wave)
    graph.add_node("retrieve_task", retrieve_task)
    graph.add_node("advance_wave", advance_wave)
    graph.add_node("aggregate", aggregate)
    graph.add_node("await_plan_approval", await_plan_approval)
    graph.add_node("synthesize", synthesize)
    graph.add_node("review", review)
    graph.add_node("prepare_synthesis_revision", prepare_synthesis_revision)
    graph.add_node("prepare_gap_research", prepare_gap_research)
    graph.add_node("retrieve_gap_task", retrieve_gap_task)
    graph.add_node("aggregate_gap_evidence", aggregate_gap_evidence)
    graph.add_node("finalize_gap_limitations", finalize_gap_limitations)
    graph.add_node("await_report_approval", await_report_approval)
    graph.add_node("persist_final_report", persist_final_report)
    graph.add_node("fail", fail)
    graph.add_node("evaluate_web_search_need", evaluate_web_search_need)
    graph.add_node("await_web_search_approval", await_web_search_approval)
    graph.add_node("search_web_gap", search_web_gap)
    graph.add_node("suggest_related_papers", suggest_related_papers)
    graph.add_edge(START, "prepare_wave")
    graph.add_conditional_edges("prepare_wave", dispatch_wave, ["retrieve_task"])
    graph.add_edge("retrieve_task", "advance_wave")
    graph.add_conditional_edges("advance_wave", route_after_wave)
    graph.add_conditional_edges("aggregate", route_after_aggregate)
    graph.add_conditional_edges("await_plan_approval", route_after_plan_approval)
    graph.add_edge("synthesize", "review")
    graph.add_conditional_edges("review", route_after_review)
    graph.add_edge("prepare_synthesis_revision", "synthesize")
    graph.add_edge("prepare_gap_research", "retrieve_gap_task")
    graph.add_edge("retrieve_gap_task", "aggregate_gap_evidence")
    graph.add_conditional_edges("aggregate_gap_evidence", route_after_gap_evidence_aggregation)
    graph.add_edge("finalize_gap_limitations", "await_report_approval")
    graph.add_conditional_edges("await_report_approval", route_after_report_approval)
    graph.add_conditional_edges("evaluate_web_search_need", route_after_web_search_evaluation)
    graph.add_conditional_edges("await_web_search_approval", route_after_web_search_approval)
    graph.add_edge("search_web_gap", "aggregate_gap_evidence")
    graph.add_edge("persist_final_report", "suggest_related_papers")
    graph.add_edge("suggest_related_papers", END)
    graph.add_edge("fail", END)
    return graph.compile(checkpointer=checkpointer)

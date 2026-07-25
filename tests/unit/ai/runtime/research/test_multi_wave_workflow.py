from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.research.evidence_artifact import ResearchEvidenceArtifactWriter
from app.ai.runtime.research.exceptions import (
    ResearchPlanRejectedError,
    ResearchReportRejectedError,
    ResearchRunCancelledError,
)
from app.ai.runtime.research.planner.models import ResearchPlanTask
from app.ai.runtime.research.report_artifact import (
    ResearchFinalReportArtifactWriter,
    ResearchFinalReportReferences,
)
from app.ai.runtime.research.retrieval.models import ResearchTaskResult, ResearchTaskStatus
from app.ai.runtime.research.review import ResearchReview, ResearchReviewService, ReviewDecision
from app.ai.runtime.research.synthesis.models import ResearchDraft, ResearchDraftSection
from app.ai.runtime.research.synthesis.service import (
    ResearchSynthesisError,
    ResearchSynthesisService,
)
from app.ai.runtime.research.workflows.multi_wave_research import compile_multi_wave_research_graph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command


async def _approve_plan(graph: object, config: dict[str, Any]) -> dict[str, Any]:
    """Every test below now hits the plan-approval interrupt (after
    evidence aggregation, before synthesis) before it can reach whatever
    it actually wants to assert on -- this resumes past it with a bare
    approval, same shape as approving the report-approval interrupt."""

    return await graph.ainvoke(Command(resume={"decision": "approved"}), config=config)  # type: ignore[attr-defined,no-any-return]


@pytest.mark.asyncio
async def test_multi_wave_graph_waits_for_dependencies_before_aggregation() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()
    calls: list[str] = []

    async def execute_task(*, task, **_kwargs) -> ResearchTaskResult:
        calls.append(task.task_id)
        return ResearchTaskResult(task_id=task.task_id, status=ResearchTaskStatus.COMPLETED)

    retrieval.execute_task.side_effect = execute_task
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    synthesis.synthesize.return_value = ResearchDraft(
        title="Report",
        abstract="Abstract.",
        methodology="Methodology.",
        findings=[ResearchDraftSection(heading="Finding", content="Grounded finding.")],
        discussion="Discussion.",
        conclusion="Conclusion.",
    )
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    final_report_writer.write.return_value = ResearchFinalReportReferences(
        report_ref="artifacts/research-runs/final-report.json",
        pdf_ref="artifacts/research-runs/final-report.pdf",
    )
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
    )
    first = ResearchPlanTask(task_id="first", question="first")
    parallel = ResearchPlanTask(task_id="parallel", question="parallel")
    second = ResearchPlanTask(task_id="second", question="second", dependencies=["first"])

    config = {"configurable": {"thread_id": str(run_id)}}
    paused = await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {"goal": "q", "complexity": "moderate"},
            "waves": [
                [first.model_dump(mode="json"), parallel.model_dump(mode="json")],
                [second.model_dump(mode="json")],
            ],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config=config,
    )

    assert "__interrupt__" in paused
    assert final_report_writer.write.await_count == 0
    assert synthesis.synthesize.await_count == 0

    plan_approved = await _approve_plan(graph, config)
    assert "__interrupt__" in plan_approved
    assert final_report_writer.write.await_count == 0

    result = await graph.ainvoke(Command(resume={"decision": "approved"}), config=config)

    assert set(calls[:2]) == {"first", "parallel"}
    assert calls[-1] == "second"
    assert set(result["task_results"]) == {"first", "parallel", "second"}
    assert result["evidence_bundle"]["completed_task_count"] == 3
    assert writer.write.await_count == 1
    assert synthesis.synthesize.await_count == 1
    assert result["final_report_pdf_ref"].endswith("final-report.pdf")
    assert final_report_writer.write.await_count == 1


@pytest.mark.asyncio
async def test_multi_wave_graph_runs_one_targeted_gap_retrieval_then_finalizes_limited() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()

    async def execute_task(*, task, **_kwargs) -> ResearchTaskResult:
        citation_id = "c2" if task.task_id == "gap-1" else "c1"
        return ResearchTaskResult(
            task_id=task.task_id,
            status=ResearchTaskStatus.COMPLETED,
            citation_ids=[citation_id],
        )

    retrieval.execute_task.side_effect = execute_task
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    synthesis.synthesize.return_value = ResearchDraft(
        title="Report",
        abstract="Abstract.",
        methodology="Methodology.",
        findings=[ResearchDraftSection(heading="Finding", content="Grounded finding.")],
        discussion="Discussion.",
        conclusion="Conclusion.",
    )
    reviewer = AsyncMock(spec=ResearchReviewService)
    reviewer.review.side_effect = [
        ResearchReview(
            decision=ReviewDecision.RESEARCH_GAPS,
            citation_integrity_score=1,
            completeness_score=0.5,
            gap_questions=["What comparative benchmark evidence is available?"],
        ),
        ResearchReview(
            decision=ReviewDecision.RESEARCH_GAPS,
            citation_integrity_score=1,
            completeness_score=0.8,
            gap_questions=["What comparative benchmark evidence is available?"],
        ),
    ]
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    final_report_writer.write.return_value = ResearchFinalReportReferences(
        report_ref="artifacts/research-runs/final-report.json",
        pdf_ref="artifacts/research-runs/final-report.pdf",
    )
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {"goal": "q", "complexity": "moderate"},
            "waves": [[initial.model_dump(mode="json")]],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config=config,
    )
    result = await _approve_plan(graph, config)

    assert set(result["task_results"]) == {"initial", "gap-1"}
    assert result["gap_research_count"] == 1
    assert result["plan_version"] == 2
    assert synthesis.synthesize.await_count == 2
    assert result["review"]["decision"] == ReviewDecision.FINALIZE_WITH_LIMITATIONS.value


@pytest.mark.asyncio
async def test_multi_wave_graph_finalizes_limited_when_citation_fix_has_no_budget() -> None:
    """A gap-repair round can exhaust a MODERATE plan's one review-iteration
    budget; if the *next* review then wants a citation-integrity revision
    (`REVISE_SYNTHESIS`), there's no budget left to attempt it -- this must
    finalize with an explicit limitation and publish the existing draft,
    not crash the run (2026-07-25; previously routed straight to `fail()`,
    raising an unhandled `RuntimeError`)."""

    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()

    async def execute_task(*, task, **_kwargs) -> ResearchTaskResult:
        citation_id = "c2" if task.task_id == "gap-1" else "c1"
        return ResearchTaskResult(
            task_id=task.task_id,
            status=ResearchTaskStatus.COMPLETED,
            citation_ids=[citation_id],
        )

    retrieval.execute_task.side_effect = execute_task
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    synthesis.synthesize.return_value = ResearchDraft(
        title="Report",
        abstract="Abstract.",
        methodology="Methodology.",
        findings=[ResearchDraftSection(heading="Finding", content="Grounded finding.")],
        discussion="Discussion.",
        conclusion="Conclusion.",
    )
    reviewer = AsyncMock(spec=ResearchReviewService)
    reviewer.review.side_effect = [
        ResearchReview(
            decision=ReviewDecision.RESEARCH_GAPS,
            citation_integrity_score=1,
            completeness_score=0.5,
            gap_questions=["What comparative benchmark evidence is available?"],
        ),
        ResearchReview(
            decision=ReviewDecision.REVISE_SYNTHESIS,
            citation_integrity_score=0,
            completeness_score=1,
            revision_instructions=["Add citations from the supplied evidence to findings."],
        ),
    ]
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    final_report_writer.write.return_value = ResearchFinalReportReferences(
        report_ref="artifacts/research-runs/final-report.json",
        pdf_ref="artifacts/research-runs/final-report.pdf",
    )
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {"goal": "q", "complexity": "moderate"},
            "waves": [[initial.model_dump(mode="json")]],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config=config,
    )
    result = await _approve_plan(graph, config)

    assert result["review"]["decision"] == ReviewDecision.FINALIZE_WITH_LIMITATIONS.value
    assert any("citation" in limitation.lower() for limitation in result["review"]["limitations"])
    assert "__interrupt__" in result
    assert [item.value.get("kind") for item in result["__interrupt__"]] == ["report_approval"]
    assert writer.write.await_args_list[-1].kwargs["version"] == 2


@pytest.mark.asyncio
async def test_multi_wave_graph_stops_at_the_next_checkpoint_once_cancelled() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()
    retrieval.execute_task.return_value = ResearchTaskResult(
        task_id="initial", status=ResearchTaskStatus.COMPLETED
    )
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        cancellation_check=AsyncMock(return_value=True),
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")

    with pytest.raises(ResearchRunCancelledError):
        await graph.ainvoke(
            {
                "research_run_id": str(run_id),
                "owner_id": str(owner_id),
                "plan": {"goal": "q", "complexity": "moderate"},
                "waves": [[initial.model_dump(mode="json")]],
                "filters": {},
                "top_k": 5,
                "task_results": {},
            },
            config={"configurable": {"thread_id": str(run_id)}},
        )

    retrieval.execute_task.assert_not_awaited()
    synthesis.synthesize.assert_not_awaited()


@pytest.mark.asyncio
async def test_multi_wave_graph_never_repairs_a_simple_plan() -> None:
    """A SIMPLE plan's max_review_iterations=0 must skip the repair loop entirely."""

    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()
    retrieval.execute_task.return_value = ResearchTaskResult(
        task_id="initial", status=ResearchTaskStatus.COMPLETED, citation_ids=["c1"]
    )
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    synthesis.synthesize.return_value = ResearchDraft(
        title="Report",
        abstract="Abstract.",
        methodology="Methodology.",
        findings=[ResearchDraftSection(heading="Finding", content="Grounded finding.")],
        discussion="Discussion.",
        conclusion="Conclusion.",
    )
    reviewer = AsyncMock(spec=ResearchReviewService)
    reviewer.review.return_value = ResearchReview(
        decision=ReviewDecision.RESEARCH_GAPS,
        citation_integrity_score=1,
        completeness_score=0.5,
        gap_questions=["What comparative benchmark evidence is available?"],
    )
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    final_report_writer.write.return_value = ResearchFinalReportReferences(
        report_ref="artifacts/research-runs/final-report.json",
        pdf_ref="artifacts/research-runs/final-report.pdf",
    )
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {"goal": "q", "complexity": "simple"},
            "waves": [[initial.model_dump(mode="json")]],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config=config,
    )
    result = await _approve_plan(graph, config)

    assert reviewer.review.await_count == 1
    assert result["review"]["decision"] == ReviewDecision.FINALIZE_WITH_LIMITATIONS.value


@pytest.mark.asyncio
async def test_multi_wave_graph_stops_repair_once_cost_budget_exhausted() -> None:
    """A MODERATE plan allows one repair round by iteration count alone, but an

    exhausted cost budget must still block it.
    """

    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()
    retrieval.execute_task.return_value = ResearchTaskResult(
        task_id="initial", status=ResearchTaskStatus.COMPLETED, citation_ids=["c1"]
    )
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    synthesis.synthesize.return_value = ResearchDraft(
        title="Report",
        abstract="Abstract.",
        methodology="Methodology.",
        findings=[ResearchDraftSection(heading="Finding", content="Grounded finding.")],
        discussion="Discussion.",
        conclusion="Conclusion.",
    )
    reviewer = AsyncMock(spec=ResearchReviewService)
    reviewer.review.return_value = ResearchReview(
        decision=ReviewDecision.RESEARCH_GAPS,
        citation_integrity_score=1,
        completeness_score=0.5,
        gap_questions=["What comparative benchmark evidence is available?"],
    )
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    final_report_writer.write.return_value = ResearchFinalReportReferences(
        report_ref="artifacts/research-runs/final-report.json",
        pdf_ref="artifacts/research-runs/final-report.pdf",
    )
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
        cost_lookup=AsyncMock(return_value=999.0),
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {"goal": "q", "complexity": "moderate"},
            "waves": [[initial.model_dump(mode="json")]],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config=config,
    )
    result = await _approve_plan(graph, config)

    assert reviewer.review.await_count == 1
    assert result["review"]["decision"] == ReviewDecision.FINALIZE_WITH_LIMITATIONS.value


@pytest.mark.asyncio
async def test_multi_wave_graph_retries_synthesis_once_after_a_schema_failure() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()
    retrieval.execute_task.return_value = ResearchTaskResult(
        task_id="initial", status=ResearchTaskStatus.COMPLETED
    )
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    draft = ResearchDraft(
        title="Report",
        abstract="Abstract.",
        methodology="Methodology.",
        findings=[ResearchDraftSection(heading="Finding", content="Grounded finding.")],
        discussion="Discussion.",
        conclusion="Conclusion.",
    )
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    synthesis.synthesize.side_effect = [
        ResearchSynthesisError("Draft referenced unknown citation IDs."),
        draft,
    ]
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    final_report_writer.write.return_value = ResearchFinalReportReferences(
        report_ref="artifacts/research-runs/final-report.json",
        pdf_ref="artifacts/research-runs/final-report.pdf",
    )
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {"goal": "q", "complexity": "moderate"},
            "waves": [[initial.model_dump(mode="json")]],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config=config,
    )
    result = await _approve_plan(graph, config)

    assert synthesis.synthesize.await_count == 2
    assert result["synthesis_revision_count"] == 1


@pytest.mark.asyncio
async def test_multi_wave_graph_synthesizes_and_reviews_against_the_rewritten_goal() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()
    retrieval.execute_task.return_value = ResearchTaskResult(
        task_id="only", status=ResearchTaskStatus.COMPLETED
    )
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    synthesis.synthesize.return_value = ResearchDraft(
        title="Report",
        abstract="Abstract.",
        methodology="Methodology.",
        findings=[ResearchDraftSection(heading="Finding", content="Grounded finding.")],
        discussion="Discussion.",
        conclusion="Conclusion.",
    )
    reviewer = AsyncMock(spec=ResearchReviewService)
    reviewer.review.return_value = ResearchReview(
        decision=ReviewDecision.PASS,
        citation_integrity_score=1.0,
        completeness_score=1.0,
    )
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    final_report_writer.write.return_value = ResearchFinalReportReferences(
        report_ref="artifacts/research-runs/final-report.json",
        pdf_ref="artifacts/research-runs/final-report.pdf",
    )
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
    )
    only = ResearchPlanTask(task_id="only", question="only")
    config = {"configurable": {"thread_id": str(run_id)}}

    paused = await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {
                "goal": "compare it with QLoRA",
                "rewritten_goal": "compare LoRA with QLoRA",
                "complexity": "simple",
            },
            "waves": [[only.model_dump(mode="json")]],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config=config,
    )
    assert "__interrupt__" in paused

    plan_approved = await _approve_plan(graph, config)
    assert "__interrupt__" in plan_approved

    result = await graph.ainvoke(Command(resume={"decision": "approved"}), config=config)

    assert synthesis.synthesize.await_args.kwargs["goal"] == "compare LoRA with QLoRA"
    assert reviewer.review.await_args.kwargs["goal"] == "compare LoRA with QLoRA"
    assert result["final_report_pdf_ref"].endswith("final-report.pdf")


@pytest.mark.asyncio
async def test_multi_wave_graph_skips_pdf_and_completes_when_the_user_rejects_the_report() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()
    retrieval.execute_task.return_value = ResearchTaskResult(
        task_id="only", status=ResearchTaskStatus.COMPLETED
    )
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    synthesis.synthesize.return_value = ResearchDraft(
        title="Report",
        abstract="Abstract.",
        methodology="Methodology.",
        findings=[ResearchDraftSection(heading="Finding", content="Grounded finding.")],
        discussion="Discussion.",
        conclusion="Conclusion.",
    )
    reviewer = AsyncMock(spec=ResearchReviewService)
    reviewer.review.return_value = ResearchReview(
        decision=ReviewDecision.PASS,
        citation_integrity_score=1.0,
        completeness_score=1.0,
    )
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    final_report_writer.write.return_value = ResearchFinalReportReferences(
        report_ref="artifacts/research-runs/final-report.json",
        pdf_ref="artifacts/research-runs/final-report.pdf",
    )
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
    )
    only = ResearchPlanTask(task_id="only", question="only")
    config = {"configurable": {"thread_id": str(run_id)}}

    paused = await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {"goal": "q", "complexity": "simple"},
            "waves": [[only.model_dump(mode="json")]],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config=config,
    )

    assert "__interrupt__" in paused
    final_report_writer.write.assert_not_awaited()

    plan_approved = await _approve_plan(graph, config)
    assert "__interrupt__" in plan_approved
    final_report_writer.write.assert_not_awaited()

    result = await graph.ainvoke(
        Command(resume={"decision": "rejected", "reason": "not accurate"}), config=config
    )

    # Rejection routes straight to END (skipping `persist_final_report`) --
    # no PDF is written, but the already-synthesized draft/evidence/review
    # survive in the returned state so the run can still complete and
    # publish a plain answer (see `execution.py::_finalize_or_pause`).
    final_report_writer.write.assert_not_awaited()
    assert result["report_decision"] == "rejected"
    assert result["report_rejection_reason"] == "not accurate"
    assert "final_report_ref" not in result
    assert result["draft"]["title"] == "Report"
    assert result["review"]["decision"] == "pass"


@pytest.mark.asyncio
async def test_multi_wave_graph_raises_on_a_malformed_report_decision_payload() -> None:
    """A rejection (`decision != "approved"`) completes normally now -- only
    a resume payload that isn't even a dict (nothing downstream can
    interpret it) still raises."""

    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()
    retrieval.execute_task.return_value = ResearchTaskResult(
        task_id="only", status=ResearchTaskStatus.COMPLETED
    )
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    synthesis.synthesize.return_value = ResearchDraft(
        title="Report",
        abstract="Abstract.",
        methodology="Methodology.",
        findings=[ResearchDraftSection(heading="Finding", content="Grounded finding.")],
        discussion="Discussion.",
        conclusion="Conclusion.",
    )
    reviewer = AsyncMock(spec=ResearchReviewService)
    reviewer.review.return_value = ResearchReview(
        decision=ReviewDecision.PASS,
        citation_integrity_score=1.0,
        completeness_score=1.0,
    )
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
    )
    only = ResearchPlanTask(task_id="only", question="only")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {"goal": "q", "complexity": "simple"},
            "waves": [[only.model_dump(mode="json")]],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config=config,
    )
    await _approve_plan(graph, config)

    with pytest.raises(ResearchReportRejectedError, match="invalid decision payload"):
        await graph.ainvoke(Command(resume="not-a-dict"), config=config)

    final_report_writer.write.assert_not_awaited()


@pytest.mark.asyncio
async def test_multi_wave_graph_pauses_for_plan_approval_before_synthesis() -> None:
    """The plan-approval interrupt sits between `aggregate` and `synthesize`
    -- reached once evidence exists, before the synthesis call is spent."""

    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()
    retrieval.execute_task.return_value = ResearchTaskResult(
        task_id="only", status=ResearchTaskStatus.COMPLETED
    )
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
    )
    only = ResearchPlanTask(task_id="only", question="only")
    config = {"configurable": {"thread_id": str(run_id)}}

    paused = await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {"goal": "q", "complexity": "simple"},
            "waves": [[only.model_dump(mode="json")]],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config=config,
    )

    assert "__interrupt__" in paused
    assert paused["evidence_bundle"]["completed_task_count"] == 1
    synthesis.synthesize.assert_not_awaited()


@pytest.mark.asyncio
async def test_multi_wave_graph_applies_an_edited_goal_from_plan_approval() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()
    retrieval.execute_task.return_value = ResearchTaskResult(
        task_id="only", status=ResearchTaskStatus.COMPLETED
    )
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    synthesis.synthesize.return_value = ResearchDraft(
        title="Report",
        abstract="Abstract.",
        methodology="Methodology.",
        findings=[ResearchDraftSection(heading="Finding", content="Grounded finding.")],
        discussion="Discussion.",
        conclusion="Conclusion.",
    )
    reviewer = AsyncMock(spec=ResearchReviewService)
    reviewer.review.return_value = ResearchReview(
        decision=ReviewDecision.PASS, citation_integrity_score=1.0, completeness_score=1.0
    )
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    final_report_writer.write.return_value = ResearchFinalReportReferences(
        report_ref="artifacts/research-runs/final-report.json",
        pdf_ref="artifacts/research-runs/final-report.pdf",
    )
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
    )
    only = ResearchPlanTask(task_id="only", question="only")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {"goal": "compare it with QLoRA", "complexity": "simple"},
            "waves": [[only.model_dump(mode="json")]],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config=config,
    )

    await graph.ainvoke(
        Command(
            resume={
                "decision": "approved",
                "edited_plan": {"rewritten_goal": "compare LoRA with QLoRA, cite benchmarks"},
            }
        ),
        config=config,
    )

    assert (
        synthesis.synthesize.await_args.kwargs["goal"] == "compare LoRA with QLoRA, cite benchmarks"
    )


@pytest.mark.asyncio
async def test_multi_wave_graph_ends_without_synthesizing_when_the_plan_is_rejected() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()
    retrieval.execute_task.return_value = ResearchTaskResult(
        task_id="only", status=ResearchTaskStatus.COMPLETED
    )
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
    )
    only = ResearchPlanTask(task_id="only", question="only")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {"goal": "q", "complexity": "simple"},
            "waves": [[only.model_dump(mode="json")]],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config=config,
    )

    result = await graph.ainvoke(
        Command(resume={"decision": "rejected", "reason": "evidence looks thin"}), config=config
    )

    synthesis.synthesize.assert_not_awaited()
    final_report_writer.write.assert_not_awaited()
    assert result["plan_decision"] == "rejected"
    assert result["plan_rejection_reason"] == "evidence looks thin"
    # The gathered evidence survives the rejection -- nothing is discarded,
    # even though there's no draft to publish from it (see
    # `execution.py::_resume_v1_graph_after_plan_approval`).
    assert result["evidence_bundle"]["completed_task_count"] == 1
    assert "draft" not in result


@pytest.mark.asyncio
async def test_multi_wave_graph_raises_on_a_malformed_plan_decision_payload() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval = AsyncMock()
    retrieval.execute_task.return_value = ResearchTaskResult(
        task_id="only", status=ResearchTaskStatus.COMPLETED
    )
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    graph = compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
    )
    only = ResearchPlanTask(task_id="only", question="only")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {"goal": "q", "complexity": "simple"},
            "waves": [[only.model_dump(mode="json")]],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config=config,
    )

    with pytest.raises(ResearchPlanRejectedError, match="invalid decision payload"):
        await graph.ainvoke(Command(resume="not-a-dict"), config=config)

    synthesis.synthesize.assert_not_awaited()

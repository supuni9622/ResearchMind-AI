from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.research.evidence_artifact import ResearchEvidenceArtifactWriter
from app.ai.runtime.research.planner.models import ResearchPlanTask
from app.ai.runtime.research.report_artifact import (
    ResearchFinalReportArtifactWriter,
    ResearchFinalReportReferences,
)
from app.ai.runtime.research.retrieval.models import ResearchTaskResult, ResearchTaskStatus
from app.ai.runtime.research.review import ResearchReview, ResearchReviewService, ReviewDecision
from app.ai.runtime.research.synthesis.models import ResearchDraft, ResearchDraftSection
from app.ai.runtime.research.synthesis.service import ResearchSynthesisService
from app.ai.runtime.research.web_search.models import WebSearchNecessityDecision
from app.ai.runtime.research.web_search.necessity import WebSearchNecessityService
from app.ai.runtime.research.workflows.multi_wave_research import compile_multi_wave_research_graph
from app.ai.tools.web_search.models import WebSearchResult, WebSearchResultItem
from app.ai.tools.web_search.policies import WebSearchPolicy
from app.ai.tools.web_search.service import WebSearchService
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command


async def _approve_plan(graph: object, config: dict[str, Any]) -> dict[str, Any]:
    return await graph.ainvoke(Command(resume={"decision": "approved"}), config=config)  # type: ignore[attr-defined,no-any-return]


def _draft() -> ResearchDraft:
    return ResearchDraft(
        title="Report",
        abstract="Abstract.",
        methodology="Methodology.",
        findings=[ResearchDraftSection(heading="Finding", content="Grounded finding.")],
        discussion="Discussion.",
        conclusion="Conclusion.",
    )


def _fake_web_search(*, max_calls: int = 1) -> AsyncMock:
    mock = AsyncMock(spec=WebSearchService)
    mock.policy = WebSearchPolicy(max_search_calls_per_run=max_calls)
    mock.search.return_value = WebSearchResult(
        query="latest info",
        items=[
            WebSearchResultItem(
                title="Recent article",
                url="https://example.com/article",
                snippet="Safe, relevant web content.",
                provider="fake",
                domain="example.com",
                provider_score=0.9,
            )
        ],
        provider="fake",
        duration_ms=5.0,
    )
    return mock


def _fake_necessity(*, needs_web_search: bool) -> AsyncMock:
    mock = AsyncMock(spec=WebSearchNecessityService)
    mock.decide.return_value = WebSearchNecessityDecision(
        needs_web_search=needs_web_search,
        query="latest info",
        reason="explains the decision",
    )
    return mock


def _base_graph_input(
    *,
    run_id: Any,
    owner_id: Any,
    task: ResearchPlanTask,
    complexity: str = "moderate",
    web_search_mode: str = "disabled",
    web_search_auto_approve: bool = False,
    web_search_count: int = 0,
) -> dict[str, Any]:
    return {
        "research_run_id": str(run_id),
        "owner_id": str(owner_id),
        "plan": {"goal": "q", "complexity": complexity},
        "waves": [[task.model_dump(mode="json")]],
        "filters": {},
        "top_k": 5,
        "task_results": {},
        "web_search_mode": web_search_mode,
        "web_search_auto_approve": web_search_auto_approve,
        "web_search_count": web_search_count,
    }


def _gap_reviewer(second_decision: ReviewDecision = ReviewDecision.PASS) -> AsyncMock:
    """First review call finds a gap; the second (after a repair round) settles."""

    reviewer = AsyncMock(spec=ResearchReviewService)
    second = (
        ResearchReview(decision=second_decision, citation_integrity_score=1, completeness_score=1)
        if second_decision is ReviewDecision.PASS
        else ResearchReview(
            decision=second_decision,
            citation_integrity_score=1,
            completeness_score=0.8,
            gap_questions=["What is the current state of the art?"],
        )
    )
    reviewer.review.side_effect = [
        ResearchReview(
            decision=ReviewDecision.RESEARCH_GAPS,
            citation_integrity_score=1,
            completeness_score=0.5,
            gap_questions=["What is the current state of the art?"],
        ),
        second,
    ]
    return reviewer


def _compile(
    *,
    retrieval: AsyncMock,
    writer: AsyncMock,
    synthesis: AsyncMock,
    final_report_writer: AsyncMock,
    reviewer: AsyncMock,
    web_search: AsyncMock | None,
    web_search_necessity: AsyncMock | None,
) -> Any:
    return compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
        web_search=web_search,
        web_search_necessity=web_search_necessity,
    )


def _standard_collaborators(
    *, citation_id_for_gap: str = "c2"
) -> tuple[AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    retrieval = AsyncMock()

    async def execute_task(*, task, **_kwargs) -> ResearchTaskResult:
        citation_id = citation_id_for_gap if task.task_id == "gap-1" else "c1"
        return ResearchTaskResult(
            task_id=task.task_id, status=ResearchTaskStatus.COMPLETED, citation_ids=[citation_id]
        )

    retrieval.execute_task.side_effect = execute_task
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = "artifacts/research-runs/evidence.json"
    synthesis = AsyncMock(spec=ResearchSynthesisService)
    synthesis.synthesize.return_value = _draft()
    final_report_writer = AsyncMock(spec=ResearchFinalReportArtifactWriter)
    final_report_writer.write.return_value = ResearchFinalReportReferences(
        report_ref="artifacts/research-runs/final-report.json",
        pdf_ref="artifacts/research-runs/final-report.pdf",
    )
    return retrieval, writer, synthesis, final_report_writer


@pytest.mark.asyncio
async def test_disabled_mode_never_consults_web_search_and_matches_existing_gap_flow() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval, writer, synthesis, final_report_writer = _standard_collaborators()
    reviewer = _gap_reviewer(ReviewDecision.RESEARCH_GAPS)
    web_search = _fake_web_search()
    necessity = _fake_necessity(needs_web_search=True)
    graph = _compile(
        retrieval=retrieval,
        writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
        web_search=web_search,
        web_search_necessity=necessity,
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        _base_graph_input(
            run_id=run_id, owner_id=owner_id, task=initial, web_search_mode="disabled"
        ),
        config=config,
    )
    result = await _approve_plan(graph, config)

    assert set(result["task_results"]) == {"initial", "gap-1"}
    necessity.decide.assert_not_awaited()
    web_search.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_mode_declines_falls_back_to_document_gap_path() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval, writer, synthesis, final_report_writer = _standard_collaborators()
    reviewer = _gap_reviewer(ReviewDecision.RESEARCH_GAPS)
    web_search = _fake_web_search()
    necessity = _fake_necessity(needs_web_search=False)
    graph = _compile(
        retrieval=retrieval,
        writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
        web_search=web_search,
        web_search_necessity=necessity,
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        _base_graph_input(run_id=run_id, owner_id=owner_id, task=initial, web_search_mode="auto"),
        config=config,
    )
    result = await _approve_plan(graph, config)

    assert set(result["task_results"]) == {"initial", "gap-1"}
    necessity.decide.assert_awaited_once()
    web_search.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_mode_needed_pauses_for_approval_then_merges_web_evidence() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval, writer, synthesis, final_report_writer = _standard_collaborators()
    reviewer = _gap_reviewer(ReviewDecision.PASS)
    web_search = _fake_web_search()
    necessity = _fake_necessity(needs_web_search=True)
    graph = _compile(
        retrieval=retrieval,
        writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
        web_search=web_search,
        web_search_necessity=necessity,
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        _base_graph_input(run_id=run_id, owner_id=owner_id, task=initial, web_search_mode="auto"),
        config=config,
    )
    paused = await _approve_plan(graph, config)

    assert "__interrupt__" in paused
    kinds = [item.value.get("kind") for item in paused["__interrupt__"]]
    assert "web_search_approval" in kinds
    web_search.search.assert_not_awaited()

    result = await graph.ainvoke(Command(resume={"decision": "approved"}), config=config)

    web_search.search.assert_awaited_once()
    assert any(task_id.startswith("web-") for task_id in result["task_results"])
    web_task = next(v for k, v in result["task_results"].items() if k.startswith("web-"))
    assert web_task["evidence"][0]["source_type"] == "web"


@pytest.mark.asyncio
async def test_auto_approve_toggle_skips_the_interrupt() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval, writer, synthesis, final_report_writer = _standard_collaborators()
    reviewer = _gap_reviewer(ReviewDecision.PASS)
    web_search = _fake_web_search()
    necessity = _fake_necessity(needs_web_search=True)
    graph = _compile(
        retrieval=retrieval,
        writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
        web_search=web_search,
        web_search_necessity=necessity,
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        _base_graph_input(
            run_id=run_id,
            owner_id=owner_id,
            task=initial,
            web_search_mode="auto",
            web_search_auto_approve=True,
        ),
        config=config,
    )
    result = await _approve_plan(graph, config)

    web_search.search.assert_awaited_once()
    if "__interrupt__" in result:
        kinds = [item.value.get("kind") for item in result["__interrupt__"]]
        assert "web_search_approval" not in kinds


@pytest.mark.asyncio
async def test_rejecting_the_web_search_suggestion_falls_back_to_existing_flow() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval, writer, synthesis, final_report_writer = _standard_collaborators()
    reviewer = _gap_reviewer(ReviewDecision.RESEARCH_GAPS)
    web_search = _fake_web_search()
    necessity = _fake_necessity(needs_web_search=True)
    graph = _compile(
        retrieval=retrieval,
        writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
        web_search=web_search,
        web_search_necessity=necessity,
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        _base_graph_input(run_id=run_id, owner_id=owner_id, task=initial, web_search_mode="auto"),
        config=config,
    )
    await _approve_plan(graph, config)

    result = await graph.ainvoke(
        Command(resume={"decision": "rejected", "reason": "not now"}), config=config
    )

    web_search.search.assert_not_awaited()
    assert set(result["task_results"]) == {"initial", "gap-1"}


@pytest.mark.asyncio
async def test_malformed_web_search_decision_payload_is_treated_as_rejection() -> None:
    """Unlike plan/report rejection, there's always a safe fallback here, so a
    malformed resume payload does not raise -- it just falls back too."""

    run_id, owner_id = uuid4(), uuid4()
    retrieval, writer, synthesis, final_report_writer = _standard_collaborators()
    reviewer = _gap_reviewer(ReviewDecision.RESEARCH_GAPS)
    web_search = _fake_web_search()
    necessity = _fake_necessity(needs_web_search=True)
    graph = _compile(
        retrieval=retrieval,
        writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
        web_search=web_search,
        web_search_necessity=necessity,
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        _base_graph_input(run_id=run_id, owner_id=owner_id, task=initial, web_search_mode="auto"),
        config=config,
    )
    await _approve_plan(graph, config)

    result = await graph.ainvoke(Command(resume="not-a-dict"), config=config)

    web_search.search.assert_not_awaited()
    assert set(result["task_results"]) == {"initial", "gap-1"}


@pytest.mark.asyncio
async def test_required_mode_forces_one_web_round_without_asking() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval, writer, synthesis, final_report_writer = _standard_collaborators()
    reviewer = AsyncMock(spec=ResearchReviewService)
    reviewer.review.return_value = ResearchReview(
        decision=ReviewDecision.PASS, citation_integrity_score=1.0, completeness_score=1.0
    )
    web_search = _fake_web_search()
    necessity = _fake_necessity(needs_web_search=True)
    graph = _compile(
        retrieval=retrieval,
        writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
        web_search=web_search,
        web_search_necessity=necessity,
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        _base_graph_input(
            run_id=run_id, owner_id=owner_id, task=initial, web_search_mode="required"
        ),
        config=config,
    )
    result = await _approve_plan(graph, config)

    web_search.search.assert_awaited_once()
    assert "__interrupt__" in result
    kinds = [item.value.get("kind") for item in result["__interrupt__"]]
    assert kinds == ["report_approval"]


@pytest.mark.asyncio
async def test_web_search_budget_exhausted_skips_the_necessity_call() -> None:
    run_id, owner_id = uuid4(), uuid4()
    retrieval, writer, synthesis, final_report_writer = _standard_collaborators()
    reviewer = _gap_reviewer(ReviewDecision.RESEARCH_GAPS)
    web_search = _fake_web_search(max_calls=1)
    necessity = _fake_necessity(needs_web_search=True)
    graph = _compile(
        retrieval=retrieval,
        writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=reviewer,
        web_search=web_search,
        web_search_necessity=necessity,
    )
    initial = ResearchPlanTask(task_id="initial", question="initial")
    config = {"configurable": {"thread_id": str(run_id)}}

    await graph.ainvoke(
        _base_graph_input(
            run_id=run_id,
            owner_id=owner_id,
            task=initial,
            web_search_mode="auto",
            web_search_count=1,
        ),
        config=config,
    )
    result = await _approve_plan(graph, config)

    necessity.decide.assert_not_awaited()
    web_search.search.assert_not_awaited()
    assert set(result["task_results"]) == {"initial", "gap-1"}

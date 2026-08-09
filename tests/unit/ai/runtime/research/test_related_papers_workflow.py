"""`suggest_related_papers` node -- non-blocking, best-effort, inserted
between `persist_final_report` and `END`. Mirrors
`test_web_search_workflow.py`'s full-graph-invocation style. The critical
property under test is "never breaks the flow": disabled, unavailable, or a
raising provider must all still let the run reach a normal completed
outcome, exactly as it would without this feature.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.chat.paper_query import PaperQueryExtractionResult
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
from app.ai.runtime.research.workflows.multi_wave_research import compile_multi_wave_research_graph
from app.ai.tools.paper_search.models import PaperSearchResult, PaperSearchResultItem
from app.ai.tools.paper_search.service import PaperSearchService
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command


def _draft() -> ResearchDraft:
    return ResearchDraft(
        title="Report",
        abstract="Abstract.",
        methodology="Methodology.",
        findings=[ResearchDraftSection(heading="Finding", content="Grounded finding.")],
        discussion="Discussion.",
        conclusion="Conclusion.",
    )


def _standard_collaborators() -> tuple[AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    retrieval = AsyncMock()

    async def execute_task(*, task, **_kwargs) -> ResearchTaskResult:
        return ResearchTaskResult(task_id=task.task_id, status=ResearchTaskStatus.COMPLETED)

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


def _pass_reviewer() -> AsyncMock:
    reviewer = AsyncMock(spec=ResearchReviewService)
    reviewer.review.return_value = ResearchReview(
        decision=ReviewDecision.PASS, citation_integrity_score=1.0, completeness_score=1.0
    )
    return reviewer


def _fake_paper_search(*, available: bool = True, search: AsyncMock | None = None) -> AsyncMock:
    mock = AsyncMock(spec=PaperSearchService)
    mock.available = available
    mock.search = search or AsyncMock(
        return_value=PaperSearchResult(
            query="q",
            items=[
                PaperSearchResultItem(
                    title="A Related Paper", authors=["A. Author"], year=2024, url="https://x.com"
                )
            ],
            provider="research_intelligence_mcp",
            duration_ms=1.0,
        )
    )
    return mock


def _compile(
    *, paper_search: AsyncMock | None, paper_query_extraction: AsyncMock | None = None
) -> Any:
    retrieval, writer, synthesis, final_report_writer = _standard_collaborators()
    return compile_multi_wave_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
        synthesis=synthesis,
        final_report_writer=final_report_writer,
        reviewer=_pass_reviewer(),
        paper_search=paper_search,
        paper_query_extraction=paper_query_extraction,
    )


def _graph_input(
    *, run_id: Any, owner_id: Any, task: ResearchPlanTask, paper_suggestions_enabled: bool
) -> dict[str, Any]:
    return {
        "research_run_id": str(run_id),
        "owner_id": str(owner_id),
        "plan": {"goal": "retrieval augmented generation", "complexity": "moderate"},
        "waves": [[task.model_dump(mode="json")]],
        "filters": {},
        "top_k": 5,
        "task_results": {},
        "paper_suggestions_enabled": paper_suggestions_enabled,
    }


async def _run_to_completion(
    graph: Any, config: dict[str, Any], run_id: Any, owner_id: Any, *, enabled: bool
) -> dict[str, Any]:
    task = ResearchPlanTask(task_id="initial", question="initial")
    plan_paused = await graph.ainvoke(
        _graph_input(
            run_id=run_id, owner_id=owner_id, task=task, paper_suggestions_enabled=enabled
        ),
        config=config,
    )
    assert [item.value.get("kind") for item in plan_paused["__interrupt__"]] == ["plan_approval"]

    report_paused = await graph.ainvoke(Command(resume={"decision": "approved"}), config=config)
    assert [item.value.get("kind") for item in report_paused["__interrupt__"]] == [
        "report_approval"
    ]

    return await graph.ainvoke(Command(resume={"decision": "approved"}), config=config)  # type: ignore[no-any-return]


@pytest.mark.asyncio
async def test_disabled_toggle_never_calls_paper_search() -> None:
    run_id, owner_id = uuid4(), uuid4()
    paper_search = _fake_paper_search()
    graph = _compile(paper_search=paper_search)
    config = {"configurable": {"thread_id": str(run_id)}}

    result = await _run_to_completion(graph, config, run_id, owner_id, enabled=False)

    assert "__interrupt__" not in result
    assert result["final_report_pdf_ref"].endswith("final-report.pdf")
    assert result["related_papers_suggestion"] == {}
    paper_search.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_unavailable_service_never_breaks_the_run() -> None:
    run_id, owner_id = uuid4(), uuid4()
    paper_search = _fake_paper_search(available=False)
    graph = _compile(paper_search=paper_search)
    config = {"configurable": {"thread_id": str(run_id)}}

    result = await _run_to_completion(graph, config, run_id, owner_id, enabled=True)

    assert result["final_report_pdf_ref"].endswith("final-report.pdf")
    assert result["related_papers_suggestion"] == {}
    paper_search.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_enabled_toggle_populates_the_suggestion() -> None:
    run_id, owner_id = uuid4(), uuid4()
    paper_search = _fake_paper_search()
    graph = _compile(paper_search=paper_search)
    config = {"configurable": {"thread_id": str(run_id)}}

    result = await _run_to_completion(graph, config, run_id, owner_id, enabled=True)

    assert result["final_report_pdf_ref"].endswith("final-report.pdf")
    paper_search.search.assert_awaited_once()
    suggestion = result["related_papers_suggestion"]
    assert suggestion["papers"][0]["title"] == "A Related Paper"


@pytest.mark.asyncio
async def test_query_extraction_distills_the_goal_before_searching() -> None:
    """Regression coverage for the production bug (2026-07-25): the node
    sent the plan's raw goal ("how tsunami works?") straight to
    search_papers, which returns zero results for full-sentence queries
    the same way Chat's raw-prompt query did before that was fixed. When a
    query-extraction collaborator is provided, its distilled topic -- not
    the raw goal -- must be what's actually searched."""

    run_id, owner_id = uuid4(), uuid4()
    paper_search = _fake_paper_search()
    extraction = AsyncMock()
    extraction.extract_details = AsyncMock(
        return_value=PaperQueryExtractionResult(query="earthquake mechanisms")
    )
    graph = _compile(paper_search=paper_search, paper_query_extraction=extraction)
    config = {"configurable": {"thread_id": str(run_id)}}

    await _run_to_completion(graph, config, run_id, owner_id, enabled=True)

    extraction.extract_details.assert_awaited_once()
    assert (
        extraction.extract_details.await_args.kwargs["user_prompt"]
        == "retrieval augmented generation"
    )
    paper_search.search.assert_awaited_once()
    assert paper_search.search.await_args.args[0].query == "earthquake mechanisms"


@pytest.mark.asyncio
async def test_provider_failure_never_breaks_report_delivery() -> None:
    """The whole point of this node being non-blocking: a broken/raising
    MCP provider must still let the run complete normally."""

    run_id, owner_id = uuid4(), uuid4()
    search = AsyncMock(side_effect=RuntimeError("mcp server unreachable"))
    paper_search = _fake_paper_search(search=search)
    graph = _compile(paper_search=paper_search)
    config = {"configurable": {"thread_id": str(run_id)}}

    result = await _run_to_completion(graph, config, run_id, owner_id, enabled=True)

    assert "__interrupt__" not in result
    assert result["final_report_pdf_ref"].endswith("final-report.pdf")
    assert result["related_papers_suggestion"] == {}


@pytest.mark.asyncio
async def test_no_results_never_breaks_the_run() -> None:
    run_id, owner_id = uuid4(), uuid4()
    empty = AsyncMock(
        return_value=PaperSearchResult(
            query="q", items=[], provider="research_intelligence_mcp", duration_ms=1.0
        )
    )
    paper_search = _fake_paper_search(search=empty)
    graph = _compile(paper_search=paper_search)
    config = {"configurable": {"thread_id": str(run_id)}}

    result = await _run_to_completion(graph, config, run_id, owner_id, enabled=True)

    assert result["final_report_pdf_ref"].endswith("final-report.pdf")
    assert result["related_papers_suggestion"] == {}


@pytest.mark.asyncio
async def test_missing_paper_search_collaborator_never_breaks_the_run() -> None:
    run_id, owner_id = uuid4(), uuid4()
    graph = _compile(paper_search=None)
    config = {"configurable": {"thread_id": str(run_id)}}

    result = await _run_to_completion(graph, config, run_id, owner_id, enabled=True)

    assert result["final_report_pdf_ref"].endswith("final-report.pdf")
    assert result["related_papers_suggestion"] == {}

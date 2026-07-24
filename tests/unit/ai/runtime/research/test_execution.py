from __future__ import annotations

from contextlib import asynccontextmanager
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.knowledge.context.interfaces import ContextBuilderInterface
from app.ai.knowledge.retrieval.service import RetrievalService
from app.ai.research.models import ResearchOutcome
from app.ai.runtime.events.research.models import ResearchEventType
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface
from app.ai.runtime.research.exceptions import (
    ResearchReportRejectedError,
    ResearchRunCancelledError,
)
from app.ai.runtime.research.execution import ResearchRuntimeExecutionService
from app.ai.runtime.research.planner.models import (
    ResearchComplexity,
    ResearchExecutionStrategy,
    ResearchPlan,
    ResearchPlanTask,
)
from app.ai.runtime.research.synthesis.models import ResearchDraft, ResearchDraftSection
from app.ai.runtime.research.types import ResearchRunStatus
from app.infrastructure.storage.interfaces import DocumentStorage
from app.models.research_proposal import ResearchProposal
from app.models.research_run import ResearchRun
from langgraph.types import Command


def _stub_v1_graph_dependencies() -> tuple[
    GenerationRuntimeInterface, RetrievalService, ContextBuilderInterface, DocumentStorage
]:
    """Typed stand-ins for dependencies the monkeypatched graph/planner never call.

    A plain `object()` satisfies every test here at runtime (the real graph
    compilation is always monkeypatched away), but fails static type
    checking against these protocol/ABC parameter types -- `cast` keeps the
    stub-object simplicity without that mismatch.
    """

    return (
        cast(GenerationRuntimeInterface, object()),
        cast(RetrievalService, object()),
        cast(ContextBuilderInterface, object()),
        cast(DocumentStorage, object()),
    )


def _publish_mock(execution: ResearchRuntimeExecutionService) -> AsyncMock:
    """Typed view of the event-journal `publish` collaborator every test here
    replaces with an `AsyncMock` -- `execution._event_journal.publish` is
    statically typed as the real bound method, so assertions need this cast
    rather than accessing `.assert_any_await` on it directly."""

    return cast(AsyncMock, execution._event_journal.publish)


def _run() -> ResearchRun:
    return ResearchRun(
        id=uuid4(),
        owner_id=uuid4(),
        graph_thread_id=str(uuid4()),
        status=ResearchRunStatus.CREATED.value,
    )


def _outcome(owner_id) -> ResearchOutcome:
    return ResearchOutcome(
        research_id=uuid4(),
        conversation_id=uuid4(),
        query="How does RAG work?",
        answer="RAG retrieves context before generation.",
        citations=[],
        sources=[],
        duration_ms=4.0,
    )


@pytest.mark.asyncio
async def test_execution_checkpoints_then_persists_completed_lifecycle(monkeypatch) -> None:
    run = _run()
    session = AsyncMock()
    research_service = AsyncMock()
    research_service.research.return_value = _outcome(run.owner_id)
    execution = ResearchRuntimeExecutionService(
        session=session,
        research_service=research_service,
        database_url="postgresql://example/researchmind_test",
    )
    execution._runs.create_or_get = AsyncMock(return_value=run)  # type: ignore[method-assign]

    @asynccontextmanager
    async def fake_checkpointer(_: str):
        yield object()

    class FakeRuntime:
        def __init__(self, *, checkpointer) -> None:
            assert checkpointer is not None

        async def run(self, request) -> dict:
            assert request.research_run_id == run.id
            assert request.graph_thread_id == run.graph_thread_id
            return {"completed": True}

    monkeypatch.setattr(
        "app.ai.runtime.research.execution.postgres_checkpointer", fake_checkpointer
    )
    monkeypatch.setattr("app.ai.runtime.research.execution.ResearchRuntimeService", FakeRuntime)

    outcome = await execution.execute(
        query="How does RAG work?",
        top_k=10,
        filters={},
        owner_id=run.owner_id,
        provider=None,
        routing_strategy=None,
        conversation_id=None,
        idempotency_key="request-1",
    )

    assert outcome is not None
    assert outcome.research_id == research_service.research.return_value.research_id
    assert run.status == ResearchRunStatus.COMPLETED.value
    assert run.research_session_id == outcome.research_id
    assert run.conversation_id == outcome.conversation_id
    assert run.attempt_count == 1
    assert session.commit.await_count == 3


@pytest.mark.asyncio
async def test_execute_approved_run_fails_visibly_when_v1_graph_disabled() -> None:
    """A disabled flag must not leave the run silently stuck at 'created'."""

    run = _run()
    proposal = ResearchProposal(
        id=uuid4(),
        owner_id=run.owner_id,
        status="approved",
        request={"query": "How does RAG work?", "top_k": 5, "filters": {}},
        research_run_id=run.id,
    )
    session = AsyncMock()
    execution = ResearchRuntimeExecutionService(
        session=session,
        research_service=AsyncMock(),
        database_url="postgresql://example/researchmind_test",
        v1_graph_enabled=False,
    )
    execution._proposals.get_by_run_id = AsyncMock(return_value=proposal)  # type: ignore[method-assign]
    execution._runs.get_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]
    execution._event_journal.publish = AsyncMock()  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="not enabled"):
        await execution.execute_approved_run(run_id=run.id)

    assert run.status == ResearchRunStatus.FAILED.value
    assert run.terminal_reason is not None
    assert run.error_summary is not None
    _publish_mock(execution).assert_any_await(
        run_id=run.id, event_type=ResearchEventType.RESEARCH_FAILED
    )


def test_request_fingerprint_is_stable_and_request_sensitive() -> None:
    def fingerprint(*, top_k: int) -> str:
        return ResearchRuntimeExecutionService.request_fingerprint(
            query="How does RAG work?",
            top_k=top_k,
            filters={"document_type": "pdf"},
            provider=None,
            routing_strategy=None,
            conversation_id=None,
        )

    first = fingerprint(top_k=10)
    second = fingerprint(top_k=10)
    changed = fingerprint(top_k=11)

    assert first == second
    assert first != changed


@pytest.mark.asyncio
async def test_v1_execution_publishes_only_the_reviewed_graph_draft(monkeypatch) -> None:
    run = _run()
    session = AsyncMock()
    research_service = AsyncMock()
    research_service.publish_runtime_report.return_value = _outcome(run.owner_id)
    generation_runtime, retrieval_service, context_builder, storage = _stub_v1_graph_dependencies()
    execution = ResearchRuntimeExecutionService(
        session=session,
        research_service=research_service,
        database_url="postgresql://example/researchmind_test",
        generation_runtime=generation_runtime,
        retrieval_service=retrieval_service,
        context_builder=context_builder,
        storage=storage,
        v1_graph_enabled=True,
    )
    execution._runs.create_or_get = AsyncMock(return_value=run)  # type: ignore[method-assign]

    class FakePlanner:
        def __init__(self, _runtime) -> None:
            pass

        async def plan(self, **_kwargs) -> ResearchPlan:
            return ResearchPlan(
                goal="How does RAG work?",
                complexity=ResearchComplexity.SIMPLE,
                execution_strategy=ResearchExecutionStrategy.FOCUSED,
                tasks=[ResearchPlanTask(task_id="retrieve", question="How does RAG work?")],
            )

    class FakeGraph:
        async def ainvoke(self, _state, *, config) -> dict:
            assert config["configurable"]["thread_id"] == run.graph_thread_id
            return {
                "draft": ResearchDraft(
                    title="RAG",
                    abstract="Abstract.",
                    methodology="Method.",
                    findings=[ResearchDraftSection(heading="Finding", content="Grounded.")],
                    discussion="Discussion.",
                    conclusion="Conclusion.",
                ).model_dump(mode="json"),
                "evidence_bundle": {
                    "completed_task_count": 0,
                    "failed_task_count": 0,
                },
                "review": {
                    "decision": "pass",
                    "citation_integrity_score": 1,
                    "completeness_score": 1,
                },
            }

    class FakeCheckpointer:
        async def aget_tuple(self, _config: object) -> None:
            return None

    @asynccontextmanager
    async def fake_checkpointer(_: str):
        yield FakeCheckpointer()

    monkeypatch.setattr("app.ai.runtime.research.execution.ResearchPlanner", FakePlanner)
    monkeypatch.setattr(
        "app.ai.runtime.research.execution.compile_multi_wave_research_graph",
        lambda **_kwargs: FakeGraph(),
    )
    monkeypatch.setattr(
        "app.ai.runtime.research.execution.postgres_checkpointer", fake_checkpointer
    )

    outcome = await execution.execute(
        query="How does RAG work?",
        top_k=5,
        filters={},
        owner_id=run.owner_id,
        provider=None,
        routing_strategy=None,
        conversation_id=None,
        idempotency_key="v1-request",
    )

    assert outcome is not None
    assert outcome.research_id == research_service.publish_runtime_report.return_value.research_id
    assert outcome.research_run_id == run.id
    research_service.research.assert_not_awaited()
    research_service.publish_runtime_report.assert_awaited_once()
    assert run.status == ResearchRunStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_retrieve_memory_context_returns_none_without_a_memory_service() -> None:
    execution = ResearchRuntimeExecutionService(
        session=AsyncMock(),
        research_service=AsyncMock(),
        database_url="postgresql://",
    )

    context = await execution._retrieve_memory_context(
        owner_id=uuid4(), session_id=uuid4(), query="How does RAG work?"
    )

    assert context is None


@pytest.mark.asyncio
async def test_retrieve_memory_context_survives_a_memory_backend_failure() -> None:
    memory = AsyncMock()
    memory.get_context.side_effect = RuntimeError("memory backend unavailable")
    execution = ResearchRuntimeExecutionService(
        session=AsyncMock(),
        research_service=AsyncMock(),
        database_url="postgresql://",
        memory_service=memory,
    )

    context = await execution._retrieve_memory_context(
        owner_id=uuid4(), session_id=uuid4(), query="How does RAG work?"
    )

    assert context is None


def _approved_proposal(run: ResearchRun) -> ResearchProposal:
    return ResearchProposal(
        id=uuid4(),
        owner_id=run.owner_id,
        status="approved",
        request={"query": "How does RAG work?", "top_k": 5, "filters": {}},
        research_run_id=run.id,
        plan=ResearchPlan(
            goal="How does RAG work?",
            complexity=ResearchComplexity.SIMPLE,
            execution_strategy=ResearchExecutionStrategy.FOCUSED,
            tasks=[ResearchPlanTask(task_id="retrieve", question="How does RAG work?")],
        ).model_dump(mode="json"),
    )


def _v1_execution(*, session, research_service) -> ResearchRuntimeExecutionService:
    generation_runtime, retrieval_service, context_builder, storage = _stub_v1_graph_dependencies()
    execution = ResearchRuntimeExecutionService(
        session=session,
        research_service=research_service,
        database_url="postgresql://example/researchmind_test",
        generation_runtime=generation_runtime,
        retrieval_service=retrieval_service,
        context_builder=context_builder,
        storage=storage,
        v1_graph_enabled=True,
    )
    execution._event_journal.publish = AsyncMock()  # type: ignore[method-assign]
    execution._is_cancellation_requested = AsyncMock(return_value=False)  # type: ignore[method-assign]
    return execution


@pytest.mark.asyncio
async def test_execute_approved_run_pauses_at_report_approval(monkeypatch) -> None:
    run = _run()
    proposal = _approved_proposal(run)
    research_service = AsyncMock()
    execution = _v1_execution(session=AsyncMock(), research_service=research_service)
    execution._proposals.get_by_run_id = AsyncMock(return_value=proposal)  # type: ignore[method-assign]
    execution._runs.get_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    class FakeGraph:
        async def ainvoke(self, _state, *, config) -> dict:
            return {"__interrupt__": [object()]}

    class FakeCheckpointer:
        async def aget_tuple(self, _config: object) -> None:
            return None

    @asynccontextmanager
    async def fake_checkpointer(_: str):
        yield FakeCheckpointer()

    monkeypatch.setattr(
        "app.ai.runtime.research.execution.compile_multi_wave_research_graph",
        lambda **_kwargs: FakeGraph(),
    )
    monkeypatch.setattr(
        "app.ai.runtime.research.execution.postgres_checkpointer", fake_checkpointer
    )

    outcome = await execution.execute_approved_run(run_id=run.id)

    assert outcome is None
    assert run.status == ResearchRunStatus.AWAITING_APPROVAL.value
    research_service.publish_runtime_report.assert_not_awaited()
    _publish_mock(execution).assert_any_await(
        run_id=run.id, event_type=ResearchEventType.RESEARCH_AWAITING_APPROVAL
    )


@pytest.mark.asyncio
async def test_execute_approved_run_resumes_and_completes_after_approval(monkeypatch) -> None:
    run = _run()
    run.status = ResearchRunStatus.AWAITING_APPROVAL.value
    run.budget_usage = {"report_decision": {"decision": "approved", "reason": None}}
    proposal = _approved_proposal(run)
    research_service = AsyncMock()
    research_service.publish_runtime_report.return_value = _outcome(run.owner_id)
    execution = _v1_execution(session=AsyncMock(), research_service=research_service)
    execution._proposals.get_by_run_id = AsyncMock(return_value=proposal)  # type: ignore[method-assign]
    execution._runs.get_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    class FakeGraph:
        async def ainvoke(self, command, *, config) -> dict:
            assert isinstance(command, Command)
            assert command.resume == {"decision": "approved", "reason": None}
            return {
                "draft": ResearchDraft(
                    title="RAG",
                    abstract="Abstract.",
                    methodology="Method.",
                    findings=[ResearchDraftSection(heading="Finding", content="Grounded.")],
                    discussion="Discussion.",
                    conclusion="Conclusion.",
                ).model_dump(mode="json"),
                "evidence_bundle": {"completed_task_count": 0, "failed_task_count": 0},
                "review": {
                    "decision": "pass",
                    "citation_integrity_score": 1,
                    "completeness_score": 1,
                },
            }

    class FakeCheckpointer:
        async def aget_tuple(self, _config: object) -> None:
            return None

    @asynccontextmanager
    async def fake_checkpointer(_: str):
        yield FakeCheckpointer()

    monkeypatch.setattr(
        "app.ai.runtime.research.execution.compile_multi_wave_research_graph",
        lambda **_kwargs: FakeGraph(),
    )
    monkeypatch.setattr(
        "app.ai.runtime.research.execution.postgres_checkpointer", fake_checkpointer
    )

    outcome = await execution.execute_approved_run(run_id=run.id)

    assert outcome is not None
    assert run.status == ResearchRunStatus.COMPLETED.value
    research_service.publish_runtime_report.assert_awaited_once()
    _publish_mock(execution).assert_any_await(
        run_id=run.id, event_type=ResearchEventType.RESEARCH_RESUMED
    )


@pytest.mark.asyncio
async def test_execute_approved_run_completes_without_a_pdf_when_report_is_rejected(
    monkeypatch,
) -> None:
    """A rejected report no longer fails the run -- the graph routes to
    `END` without `persist_final_report` (see `route_after_report_approval`
    in `multi_wave_research.py`), and the already-synthesized draft still
    gets published as a plain answer via `publish_runtime_report`."""

    run = _run()
    run.status = ResearchRunStatus.AWAITING_APPROVAL.value
    run.budget_usage = {"report_decision": {"decision": "rejected", "reason": "inaccurate"}}
    proposal = _approved_proposal(run)
    research_service = AsyncMock()
    research_service.publish_runtime_report.return_value = _outcome(run.owner_id)
    execution = _v1_execution(session=AsyncMock(), research_service=research_service)
    execution._proposals.get_by_run_id = AsyncMock(return_value=proposal)  # type: ignore[method-assign]
    execution._runs.get_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    class FakeGraph:
        async def ainvoke(self, command, *, config) -> dict:
            assert isinstance(command, Command)
            assert command.resume == {"decision": "rejected", "reason": "inaccurate"}
            return {
                "draft": ResearchDraft(
                    title="RAG",
                    abstract="Abstract.",
                    methodology="Method.",
                    findings=[ResearchDraftSection(heading="Finding", content="Grounded.")],
                    discussion="Discussion.",
                    conclusion="Conclusion.",
                ).model_dump(mode="json"),
                "evidence_bundle": {"completed_task_count": 0, "failed_task_count": 0},
                "review": {
                    "decision": "pass",
                    "citation_integrity_score": 1,
                    "completeness_score": 1,
                },
                "report_decision": "rejected",
                "report_rejection_reason": "inaccurate",
                # No `final_report_ref`/`final_report_pdf_ref` -- `persist_final_report` never ran.
            }

    class FakeCheckpointer:
        async def aget_tuple(self, _config: object) -> None:
            return None

    @asynccontextmanager
    async def fake_checkpointer(_: str):
        yield FakeCheckpointer()

    monkeypatch.setattr(
        "app.ai.runtime.research.execution.compile_multi_wave_research_graph",
        lambda **_kwargs: FakeGraph(),
    )
    monkeypatch.setattr(
        "app.ai.runtime.research.execution.postgres_checkpointer", fake_checkpointer
    )

    outcome = await execution.execute_approved_run(run_id=run.id)

    assert outcome is not None
    assert run.status == ResearchRunStatus.COMPLETED_WITH_LIMITATIONS.value
    assert run.terminal_reason == "report_rejected_returned_as_answer"
    research_service.publish_runtime_report.assert_awaited_once()
    _publish_mock(execution).assert_any_await(
        run_id=run.id, event_type=ResearchEventType.RESEARCH_RESUMED
    )


@pytest.mark.asyncio
async def test_execute_approved_run_marks_failed_on_a_malformed_report_decision(
    monkeypatch,
) -> None:
    """Distinct from a real rejection (see the test above): this only
    covers the graph's defensive raise for a resume payload it can't even
    interpret as a decision (see `await_report_approval` in
    `multi_wave_research.py`) -- that's the one case still routed through
    the FAILED terminal state."""

    run = _run()
    run.status = ResearchRunStatus.AWAITING_APPROVAL.value
    run.budget_usage = {"report_decision": {"decision": "rejected", "reason": "inaccurate"}}
    proposal = _approved_proposal(run)
    execution = _v1_execution(session=AsyncMock(), research_service=AsyncMock())
    execution._proposals.get_by_run_id = AsyncMock(return_value=proposal)  # type: ignore[method-assign]
    execution._runs.get_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    class FakeGraph:
        async def ainvoke(self, _command, *, config) -> dict:
            raise ResearchReportRejectedError(
                "The report-approval interrupt resumed with an invalid decision payload."
            )

    class FakeCheckpointer:
        async def aget_tuple(self, _config: object) -> None:
            return None

    @asynccontextmanager
    async def fake_checkpointer(_: str):
        yield FakeCheckpointer()

    monkeypatch.setattr(
        "app.ai.runtime.research.execution.compile_multi_wave_research_graph",
        lambda **_kwargs: FakeGraph(),
    )
    monkeypatch.setattr(
        "app.ai.runtime.research.execution.postgres_checkpointer", fake_checkpointer
    )

    with pytest.raises(ResearchReportRejectedError):
        await execution.execute_approved_run(run_id=run.id)

    assert run.status == ResearchRunStatus.FAILED.value
    assert run.terminal_reason == "report_decision_payload_invalid"
    _publish_mock(execution).assert_any_await(
        run_id=run.id, event_type=ResearchEventType.RESEARCH_FAILED
    )


@pytest.mark.asyncio
async def test_execute_approved_run_honors_cancellation_while_paused_for_approval() -> None:
    run = _run()
    run.status = ResearchRunStatus.AWAITING_APPROVAL.value
    run.budget_usage = {"report_decision": {"decision": "approved", "reason": None}}
    proposal = _approved_proposal(run)
    execution = _v1_execution(session=AsyncMock(), research_service=AsyncMock())
    execution._proposals.get_by_run_id = AsyncMock(return_value=proposal)  # type: ignore[method-assign]
    execution._runs.get_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]
    execution._is_cancellation_requested = AsyncMock(return_value=True)  # type: ignore[method-assign]

    with pytest.raises(ResearchRunCancelledError):
        await execution.execute_approved_run(run_id=run.id)

    assert run.status == ResearchRunStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_execute_approved_run_fails_loudly_without_a_recorded_decision() -> None:
    run = _run()
    run.status = ResearchRunStatus.AWAITING_APPROVAL.value
    run.budget_usage = {}
    proposal = _approved_proposal(run)
    execution = _v1_execution(session=AsyncMock(), research_service=AsyncMock())
    execution._proposals.get_by_run_id = AsyncMock(return_value=proposal)  # type: ignore[method-assign]
    execution._runs.get_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="never recorded"):
        await execution.execute_approved_run(run_id=run.id)


@pytest.mark.asyncio
async def test_execute_approved_run_pauses_at_plan_approval(monkeypatch) -> None:
    run = _run()
    proposal = _approved_proposal(run)
    research_service = AsyncMock()
    execution = _v1_execution(session=AsyncMock(), research_service=research_service)
    execution._proposals.get_by_run_id = AsyncMock(return_value=proposal)  # type: ignore[method-assign]
    execution._runs.get_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    class FakeInterrupt:
        value = {"kind": "plan_approval", "research_run_id": str(run.id)}

    class FakeGraph:
        async def ainvoke(self, _state, *, config) -> dict:
            return {"__interrupt__": [FakeInterrupt()]}

    class FakeCheckpointer:
        async def aget_tuple(self, _config: object) -> None:
            return None

    @asynccontextmanager
    async def fake_checkpointer(_: str):
        yield FakeCheckpointer()

    monkeypatch.setattr(
        "app.ai.runtime.research.execution.compile_multi_wave_research_graph",
        lambda **_kwargs: FakeGraph(),
    )
    monkeypatch.setattr(
        "app.ai.runtime.research.execution.postgres_checkpointer", fake_checkpointer
    )

    outcome = await execution.execute_approved_run(run_id=run.id)

    assert outcome is None
    assert run.status == ResearchRunStatus.AWAITING_PLAN_APPROVAL.value
    research_service.publish_runtime_report.assert_not_awaited()
    _publish_mock(execution).assert_any_await(
        run_id=run.id, event_type=ResearchEventType.RESEARCH_AWAITING_PLAN_APPROVAL
    )


@pytest.mark.asyncio
async def test_execute_approved_run_resumes_into_synthesis_after_plan_approval(monkeypatch) -> None:
    """An approved plan resumes straight into synthesis/review, which then
    pauses again at the *report*-approval interrupt (a fresh one, not the
    plan-approval interrupt just resolved)."""

    run = _run()
    run.status = ResearchRunStatus.AWAITING_PLAN_APPROVAL.value
    run.budget_usage = {"plan_decision": {"decision": "approved", "reason": None}}
    proposal = _approved_proposal(run)
    research_service = AsyncMock()
    execution = _v1_execution(session=AsyncMock(), research_service=research_service)
    execution._proposals.get_by_run_id = AsyncMock(return_value=proposal)  # type: ignore[method-assign]
    execution._runs.get_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    class FakeGraph:
        async def ainvoke(self, command, *, config) -> dict:
            assert isinstance(command, Command)
            assert command.resume == {"decision": "approved", "reason": None}
            return {"__interrupt__": [object()]}

    class FakeCheckpointer:
        async def aget_tuple(self, _config: object) -> None:
            return None

    @asynccontextmanager
    async def fake_checkpointer(_: str):
        yield FakeCheckpointer()

    monkeypatch.setattr(
        "app.ai.runtime.research.execution.compile_multi_wave_research_graph",
        lambda **_kwargs: FakeGraph(),
    )
    monkeypatch.setattr(
        "app.ai.runtime.research.execution.postgres_checkpointer", fake_checkpointer
    )

    outcome = await execution.execute_approved_run(run_id=run.id)

    assert outcome is None
    assert run.status == ResearchRunStatus.AWAITING_APPROVAL.value
    _publish_mock(execution).assert_any_await(
        run_id=run.id, event_type=ResearchEventType.RESEARCH_RESUMED
    )
    _publish_mock(execution).assert_any_await(
        run_id=run.id, event_type=ResearchEventType.RESEARCH_AWAITING_APPROVAL
    )


@pytest.mark.asyncio
async def test_execute_approved_run_ends_without_a_report_when_plan_is_rejected(
    monkeypatch,
) -> None:
    """A rejected plan never reaches synthesis -- there is no draft to
    publish (unlike a rejected *report*, which still has one), so the run
    just ends CANCELLED rather than completing with a plain answer."""

    run = _run()
    run.status = ResearchRunStatus.AWAITING_PLAN_APPROVAL.value
    run.budget_usage = {"plan_decision": {"decision": "rejected", "reason": "thin evidence"}}
    proposal = _approved_proposal(run)
    research_service = AsyncMock()
    execution = _v1_execution(session=AsyncMock(), research_service=research_service)
    execution._proposals.get_by_run_id = AsyncMock(return_value=proposal)  # type: ignore[method-assign]
    execution._runs.get_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    class FakeGraph:
        async def ainvoke(self, command, *, config) -> dict:
            assert isinstance(command, Command)
            assert command.resume == {"decision": "rejected", "reason": "thin evidence"}
            return {
                "plan_decision": "rejected",
                "plan_rejection_reason": "thin evidence",
                "evidence_bundle": {"completed_task_count": 1, "failed_task_count": 0},
            }

    class FakeCheckpointer:
        async def aget_tuple(self, _config: object) -> None:
            return None

    @asynccontextmanager
    async def fake_checkpointer(_: str):
        yield FakeCheckpointer()

    monkeypatch.setattr(
        "app.ai.runtime.research.execution.compile_multi_wave_research_graph",
        lambda **_kwargs: FakeGraph(),
    )
    monkeypatch.setattr(
        "app.ai.runtime.research.execution.postgres_checkpointer", fake_checkpointer
    )

    outcome = await execution.execute_approved_run(run_id=run.id)

    assert outcome is None
    assert run.status == ResearchRunStatus.CANCELLED.value
    assert run.terminal_reason == "plan_rejected_by_user"
    research_service.publish_runtime_report.assert_not_awaited()
    _publish_mock(execution).assert_any_await(
        run_id=run.id, event_type=ResearchEventType.RESEARCH_CANCELLED
    )


@pytest.mark.asyncio
async def test_execute_approved_run_marks_failed_on_a_malformed_plan_decision(
    monkeypatch,
) -> None:
    run = _run()
    run.status = ResearchRunStatus.AWAITING_PLAN_APPROVAL.value
    run.budget_usage = {"plan_decision": {"decision": "rejected", "reason": "thin evidence"}}
    proposal = _approved_proposal(run)
    execution = _v1_execution(session=AsyncMock(), research_service=AsyncMock())
    execution._proposals.get_by_run_id = AsyncMock(return_value=proposal)  # type: ignore[method-assign]
    execution._runs.get_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    from app.ai.runtime.research.exceptions import ResearchPlanRejectedError

    class FakeGraph:
        async def ainvoke(self, _command, *, config) -> dict:
            raise ResearchPlanRejectedError(
                "The plan-approval interrupt resumed with an invalid decision payload."
            )

    class FakeCheckpointer:
        async def aget_tuple(self, _config: object) -> None:
            return None

    @asynccontextmanager
    async def fake_checkpointer(_: str):
        yield FakeCheckpointer()

    monkeypatch.setattr(
        "app.ai.runtime.research.execution.compile_multi_wave_research_graph",
        lambda **_kwargs: FakeGraph(),
    )
    monkeypatch.setattr(
        "app.ai.runtime.research.execution.postgres_checkpointer", fake_checkpointer
    )

    with pytest.raises(ResearchPlanRejectedError):
        await execution.execute_approved_run(run_id=run.id)

    assert run.status == ResearchRunStatus.FAILED.value
    _publish_mock(execution).assert_any_await(
        run_id=run.id, event_type=ResearchEventType.RESEARCH_FAILED
    )


@pytest.mark.asyncio
async def test_execute_approved_run_fails_loudly_without_a_recorded_plan_decision() -> None:
    run = _run()
    run.status = ResearchRunStatus.AWAITING_PLAN_APPROVAL.value
    run.budget_usage = {}
    proposal = _approved_proposal(run)
    execution = _v1_execution(session=AsyncMock(), research_service=AsyncMock())
    execution._proposals.get_by_run_id = AsyncMock(return_value=proposal)  # type: ignore[method-assign]
    execution._runs.get_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="never recorded"):
        await execution.execute_approved_run(run_id=run.id)


@pytest.mark.asyncio
async def test_execute_approved_run_refreshes_the_run_before_reading_its_decision(
    monkeypatch,
) -> None:
    """Regression test: this worker's session lives for its whole process
    lifetime with `expire_on_commit=False` (see `db/session.py`), so a `run`
    it already loaded earlier -- e.g. while first reaching `awaiting_approval`
    -- is never automatically invalidated by the report-decision API request,
    which commits `budget_usage` in its own separate session. Without an
    explicit `session.refresh(run)`, this stale in-memory `run` would still
    read `budget_usage == {}` and fail with "never recorded" even though the
    decision was, in fact, recorded."""

    run = _run()
    run.status = ResearchRunStatus.AWAITING_APPROVAL.value
    run.budget_usage = {}  # the worker's stale in-memory snapshot
    proposal = _approved_proposal(run)
    research_service = AsyncMock()
    research_service.publish_runtime_report.return_value = _outcome(run.owner_id)
    session = AsyncMock()

    async def fake_refresh(instance: object) -> None:
        # Simulates what a real DB refresh would pick up: the decision a
        # separate, short-lived API-request session already committed.
        assert instance is run
        run.budget_usage = {"report_decision": {"decision": "approved", "reason": None}}

    session.refresh.side_effect = fake_refresh
    execution = _v1_execution(session=session, research_service=research_service)
    execution._proposals.get_by_run_id = AsyncMock(return_value=proposal)  # type: ignore[method-assign]
    execution._runs.get_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    class FakeGraph:
        async def ainvoke(self, command, *, config) -> dict:
            assert isinstance(command, Command)
            assert command.resume == {"decision": "approved", "reason": None}
            return {
                "draft": ResearchDraft(
                    title="RAG",
                    abstract="Abstract.",
                    methodology="Method.",
                    findings=[ResearchDraftSection(heading="Finding", content="Grounded.")],
                    discussion="Discussion.",
                    conclusion="Conclusion.",
                ).model_dump(mode="json"),
                "evidence_bundle": {"completed_task_count": 0, "failed_task_count": 0},
                "review": {
                    "decision": "pass",
                    "citation_integrity_score": 1,
                    "completeness_score": 1,
                },
            }

    class FakeCheckpointer:
        async def aget_tuple(self, _config: object) -> None:
            return None

    @asynccontextmanager
    async def fake_checkpointer(_: str):
        yield FakeCheckpointer()

    monkeypatch.setattr(
        "app.ai.runtime.research.execution.compile_multi_wave_research_graph",
        lambda **_kwargs: FakeGraph(),
    )
    monkeypatch.setattr(
        "app.ai.runtime.research.execution.postgres_checkpointer", fake_checkpointer
    )

    outcome = await execution.execute_approved_run(run_id=run.id)

    session.refresh.assert_awaited_once_with(run)
    assert outcome is not None
    assert run.status == ResearchRunStatus.COMPLETED.value

from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.runtime.events.research.models import ResearchEventType
from app.ai.runtime.research.events import LangGraphResearchEventAdapter
from app.ai.runtime.research.graph import compile_research_runtime_graph, initial_state
from app.ai.runtime.research.reducers import merge_by_stable_id, merge_non_decreasing_usage
from app.ai.runtime.research.types import ResearchRuntimeRequest, ResearchRuntimeStatus
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command


def _request(*, pause_after_initialize: bool = False) -> ResearchRuntimeRequest:
    return ResearchRuntimeRequest(
        research_run_id=uuid4(),
        graph_thread_id=str(uuid4()),
        owner_id=uuid4(),
        pause_after_initialize=pause_after_initialize,
    )


def test_reducers_are_order_independent_and_retry_idempotent() -> None:
    first = {"task-a": {"attempt": 1}, "task-b": {"attempt": 1}}
    second = {"task-b": {"attempt": 1}, "task-a": {"attempt": 1}}

    assert merge_by_stable_id(None, first) == merge_by_stable_id(None, second)
    assert merge_by_stable_id(first, {"task-a": {"attempt": 1}}) == first
    assert merge_non_decreasing_usage({"tokens": 5}, {"tokens": 8}) == {"tokens": 8}


def test_reducers_reject_conflicts_and_budget_decreases() -> None:
    with pytest.raises(ValueError, match="Conflicting"):
        merge_by_stable_id({"task-a": {"attempt": 1}}, {"task-a": {"attempt": 2}})
    with pytest.raises(ValueError, match="cannot decrease"):
        merge_non_decreasing_usage({"tokens": 8}, {"tokens": 5})


@pytest.mark.asyncio
async def test_in_memory_checkpoint_interrupt_resumes_same_thread() -> None:
    request = _request(pause_after_initialize=True)
    graph = compile_research_runtime_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": request.graph_thread_id}}

    state = initial_state(request=request.model_dump(mode="json"))
    interrupted = await graph.ainvoke(state, config)
    assert "__interrupt__" in interrupted

    completed = await graph.ainvoke(Command(resume=True), config)
    assert completed["status"] == ResearchRuntimeStatus.COMPLETED.value
    assert completed["completed"] is True
    assert completed["graph_thread_id"] == request.graph_thread_id


def test_event_adapter_never_leaks_graph_state() -> None:
    request = _request()
    event = LangGraphResearchEventAdapter().adapt_update(
        {"initialize": {"hidden_prompt": "do not expose", "checkpoint": {"secret": "x"}}},
        research_run_id=request.research_run_id,
        graph_thread_id=request.graph_thread_id,
    )

    assert event is not None
    assert event.metadata == {"graph_thread_id": request.graph_thread_id, "phase": "foundation"}
    assert "hidden_prompt" not in event.model_dump_json()


def test_progress_event_uses_a_stable_user_safe_label() -> None:
    request = _request()
    event = LangGraphResearchEventAdapter().progress(
        research_run_id=request.research_run_id,
        event_type=ResearchEventType.RETRIEVAL_STARTED,
    )

    assert event.type == ResearchEventType.RETRIEVAL_STARTED.value
    assert event.metadata == {"label": "Searching selected sources"}
    assert "graph_thread_id" not in event.metadata

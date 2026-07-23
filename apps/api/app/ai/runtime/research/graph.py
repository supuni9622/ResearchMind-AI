"""Minimal compiled LangGraph workflow used only by Phase 1 tests/services."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.ai.runtime.research.state import ResearchRuntimeState, validate_json_state
from app.ai.runtime.research.types import ResearchRuntimeStatus


def _initialize(state: ResearchRuntimeState) -> ResearchRuntimeState:
    if state.get("pause_after_initialize"):
        interrupt({"kind": "research_runtime_foundation_pause", "schema_version": 1})
    return {"status": ResearchRuntimeStatus.INITIALIZED.value}


def _complete(_: ResearchRuntimeState) -> ResearchRuntimeState:
    return {"status": ResearchRuntimeStatus.COMPLETED.value, "completed": True}


def compile_research_runtime_graph(*, checkpointer: Any) -> Any:
    """Compile the deterministic walking skeleton with an injected saver."""

    graph = StateGraph(ResearchRuntimeState)
    graph.add_node("initialize", _initialize)
    graph.add_node("complete", _complete)  # type: ignore[arg-type]
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "complete")
    graph.add_edge("complete", END)
    return graph.compile(checkpointer=checkpointer)


def initial_state(*, request: dict[str, object]) -> ResearchRuntimeState:
    state: ResearchRuntimeState = {
        "schema_version": 1,
        "research_run_id": str(request["research_run_id"]),
        "graph_thread_id": str(request["graph_thread_id"]),
        "owner_id": str(request["owner_id"]),
        "status": ResearchRuntimeStatus.CREATED.value,
        "pause_after_initialize": bool(request.get("pause_after_initialize", False)),
    }
    validate_json_state(state)
    return state

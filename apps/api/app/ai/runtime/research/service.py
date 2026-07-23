"""Application-facing shell for the disabled Phase 1 Research Runtime."""

from __future__ import annotations

from typing import Any, cast

from langgraph.checkpoint.memory import InMemorySaver

from app.ai.runtime.research.graph import compile_research_runtime_graph, initial_state
from app.ai.runtime.research.types import ResearchRuntimeRequest


class ResearchRuntimeService:
    """Runs the deterministic graph only when explicitly constructed.

    Public APIs do not construct this service in Phase 1. ``InMemorySaver`` is
    intentionally the default solely for local/unit use; production wiring is
    blocked on a verified Postgres checkpointer.
    """

    def __init__(self, *, checkpointer: Any | None = None) -> None:
        self._graph = compile_research_runtime_graph(checkpointer=checkpointer or InMemorySaver())

    async def run(self, request: ResearchRuntimeRequest) -> dict[str, Any]:
        result = await self._graph.ainvoke(
            initial_state(request=request.model_dump(mode="json")),
            config={"configurable": {"thread_id": request.graph_thread_id}},
        )
        return cast(dict[str, Any], result)

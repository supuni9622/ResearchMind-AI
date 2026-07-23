"""Integration proof for LangGraph's production Postgres checkpoint saver."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.runtime.research.checkpointing import (
    postgres_checkpointer,
    provision_postgres_checkpoints,
)
from app.ai.runtime.research.graph import compile_research_runtime_graph, initial_state
from app.ai.runtime.research.types import ResearchRuntimeRequest, ResearchRuntimeStatus
from app.core.settings import settings
from langgraph.types import Command


@pytest.mark.asyncio
async def test_postgres_checkpoint_resumes_across_saver_connections() -> None:
    """A fresh saver instance can resume the same persisted graph thread."""

    request = ResearchRuntimeRequest(
        research_run_id=uuid4(),
        graph_thread_id=str(uuid4()),
        owner_id=uuid4(),
        pause_after_initialize=True,
    )
    config = {"configurable": {"thread_id": request.graph_thread_id}}

    await provision_postgres_checkpoints(settings.database_url)

    async with postgres_checkpointer(settings.database_url) as first_saver:
        first_graph = compile_research_runtime_graph(checkpointer=first_saver)
        interrupted = await first_graph.ainvoke(
            initial_state(request=request.model_dump(mode="json")),
            config,
        )
        assert "__interrupt__" in interrupted

    async with postgres_checkpointer(settings.database_url) as second_saver:
        second_graph = compile_research_runtime_graph(checkpointer=second_saver)
        completed = await second_graph.ainvoke(Command(resume=True), config)

    assert completed["status"] == ResearchRuntimeStatus.COMPLETED.value
    assert completed["graph_thread_id"] == request.graph_thread_id

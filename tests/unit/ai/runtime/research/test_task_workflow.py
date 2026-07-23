from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.research.evidence_artifact import ResearchEvidenceArtifactWriter
from app.ai.runtime.research.planner.models import ResearchPlanTask
from app.ai.runtime.research.retrieval.models import ResearchTaskResult, ResearchTaskStatus
from app.ai.runtime.research.workflows.task_research import compile_task_research_graph
from langgraph.checkpoint.memory import InMemorySaver


@pytest.mark.asyncio
async def test_task_graph_fans_out_then_persists_one_compact_evidence_artifact() -> None:
    run_id = uuid4()
    owner_id = uuid4()
    retrieval = AsyncMock()

    async def execute_task(*, task, **_kwargs) -> ResearchTaskResult:
        return ResearchTaskResult(task_id=task.task_id, status=ResearchTaskStatus.COMPLETED)

    retrieval.execute_task.side_effect = execute_task
    writer = AsyncMock(spec=ResearchEvidenceArtifactWriter)
    writer.write.return_value = f"artifacts/research-runs/{run_id}/evidence.json"
    graph = compile_task_research_graph(
        checkpointer=InMemorySaver(),
        task_retrieval=retrieval,
        evidence_writer=writer,
    )
    tasks = [
        ResearchPlanTask(task_id="first", question="first"),
        ResearchPlanTask(task_id="second", question="second"),
    ]

    result = await graph.ainvoke(
        {
            "research_run_id": str(run_id),
            "owner_id": str(owner_id),
            "plan": {"goal": "compare"},
            "wave": [task.model_dump(mode="json") for task in tasks],
            "filters": {},
            "top_k": 5,
            "task_results": {},
        },
        config={"configurable": {"thread_id": str(run_id)}},
    )

    assert set(result["task_results"]) == {"first", "second"}
    assert retrieval.execute_task.await_count == 2
    assert result["evidence_artifact_ref"].endswith("/evidence.json")
    persisted = writer.write.await_args.args[0]
    assert set(persisted.task_results) == {"first", "second"}

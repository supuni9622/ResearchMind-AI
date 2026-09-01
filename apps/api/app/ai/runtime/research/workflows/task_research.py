"""LangGraph fan-out for one validated dependency wave, followed by evidence persistence."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.ai.runtime.research.evidence_artifact import (
    ResearchEvidenceArtifact,
    ResearchEvidenceArtifactWriter,
)
from app.ai.runtime.research.planner.models import ResearchPlanTask
from app.ai.runtime.research.reducers import merge_by_stable_id
from app.ai.runtime.research.retrieval.models import ResearchTaskResult
from app.ai.runtime.research.retrieval.service import ResearchTaskRetrievalService


class ResearchTaskWorkflowState(TypedDict):
    """Bounded state for a single DAG wave; full documents never enter this graph."""

    research_run_id: str
    owner_id: str
    project_id: str | None
    plan: dict[str, object]
    wave: list[dict[str, object]]
    filters: dict[str, object]
    top_k: int
    task: dict[str, object]
    task_results: Annotated[dict[str, dict[str, object]], merge_by_stable_id]
    evidence_artifact_ref: str


def compile_task_research_graph(
    *,
    checkpointer: Any,
    task_retrieval: ResearchTaskRetrievalService,
    evidence_writer: ResearchEvidenceArtifactWriter,
) -> Any:
    """Compile fan-out → fan-in → immutable evidence artifact for one planned wave."""

    async def retrieve_task(state: ResearchTaskWorkflowState) -> dict[str, object]:
        task = ResearchPlanTask.model_validate(state["task"])
        raw_project_id = state.get("project_id")
        result = await task_retrieval.execute_task(
            task=task,
            owner_id=UUID(state["owner_id"]),
            filters=state.get("filters", {}),
            top_k=state.get("top_k", 5),
            project_id=UUID(raw_project_id) if raw_project_id else None,
        )
        return {"task_results": {task.task_id: result.model_dump(mode="json")}}

    async def persist_evidence(state: ResearchTaskWorkflowState) -> dict[str, object]:
        artifact = ResearchEvidenceArtifact(
            research_run_id=UUID(state["research_run_id"]),
            plan=state["plan"],
            task_results={
                task_id: ResearchTaskResult.model_validate(result)
                for task_id, result in state.get("task_results", {}).items()
            },
        )
        return {"evidence_artifact_ref": await evidence_writer.write(artifact)}

    def dispatch_wave(state: ResearchTaskWorkflowState) -> list[Send]:
        return [
            Send(
                "retrieve_task",
                {
                    "task": task,
                    "owner_id": state["owner_id"],
                    "filters": state.get("filters", {}),
                    "top_k": state.get("top_k", 5),
                },
            )
            for task in state.get("wave", [])
        ]

    def dispatch_node(state: ResearchTaskWorkflowState) -> dict[str, object]:
        """Anchor conditional fan-out without changing shared graph state."""

        del state
        return {}

    graph = StateGraph(ResearchTaskWorkflowState)
    graph.add_node("dispatch_wave", dispatch_node)
    graph.add_node("retrieve_task", retrieve_task)
    graph.add_node("persist_evidence", persist_evidence)
    graph.add_edge(START, "dispatch_wave")
    graph.add_conditional_edges("dispatch_wave", dispatch_wave, ["retrieve_task"])
    graph.add_edge("retrieve_task", "persist_evidence")
    graph.add_edge("persist_evidence", END)
    return graph.compile(checkpointer=checkpointer)

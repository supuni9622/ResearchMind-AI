from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.research.planner.models import (
    ResearchComplexity,
    ResearchExecutionStrategy,
    ResearchPlan,
    ResearchPlanTask,
)
from app.ai.runtime.research.planner.service import ResearchPlanner, ResearchPlannerError


def _focused_plan() -> ResearchPlan:
    return ResearchPlan(
        goal="How does RAG work?",
        complexity=ResearchComplexity.SIMPLE,
        execution_strategy=ResearchExecutionStrategy.FOCUSED,
        tasks=[ResearchPlanTask(task_id="research", question="How does RAG work?")],
    )


@pytest.mark.asyncio
async def test_planner_uses_the_generation_runtime_with_a_structured_contract() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(parsed_output=_focused_plan())
    planner = ResearchPlanner(runtime)

    plan = await planner.plan(
        query="How does RAG work?",
        owner_id=uuid4(),
        research_run_id=uuid4(),
    )

    assert plan == _focused_plan()
    request = runtime.execute.await_args.args[0]
    assert request.output_model is ResearchPlan
    assert request.max_tokens == 800
    assert request.metadata["prompt_version"] == "research-planner-v1"


@pytest.mark.asyncio
async def test_planner_folds_memory_context_into_the_user_prompt() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(parsed_output=_focused_plan())
    planner = ResearchPlanner(runtime)

    await planner.plan(
        query="How does RAG work?",
        owner_id=uuid4(),
        research_run_id=uuid4(),
        memory_context="Background memory from prior turns:\n- Prefers concise answers",
    )

    request = runtime.execute.await_args.args[0]
    assert "Prefers concise answers" in request.user_prompt


@pytest.mark.asyncio
async def test_planner_prompt_omits_memory_block_when_no_context_is_supplied() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(parsed_output=_focused_plan())
    planner = ResearchPlanner(runtime)

    await planner.plan(
        query="How does RAG work?",
        owner_id=uuid4(),
        research_run_id=uuid4(),
    )

    request = runtime.execute.await_args.args[0]
    assert "Background memory" not in request.user_prompt


@pytest.mark.asyncio
async def test_planner_rejects_missing_or_over_budget_output() -> None:
    runtime = AsyncMock()
    planner = ResearchPlanner(runtime)
    runtime.execute.return_value = SimpleNamespace(parsed_output=None, content="")

    with pytest.raises(ResearchPlannerError, match="schema-valid"):
        await planner.plan(query="q", owner_id=uuid4(), research_run_id=uuid4())

    runtime.execute.return_value = SimpleNamespace(
        parsed_output={
            "goal": "Compare approaches",
            "complexity": "simple",
            "execution_strategy": "decomposed",
            "tasks": [
                {"task_id": "one", "question": "one"},
                {"task_id": "two", "question": "two"},
            ],
        }
    )
    with pytest.raises(ResearchPlannerError, match="exceeding"):
        await planner.plan(query="q", owner_id=uuid4(), research_run_id=uuid4())


def test_plan_rejects_unknown_dependencies_and_focused_fan_out() -> None:
    with pytest.raises(ValueError, match="unknown dependencies"):
        ResearchPlan(
            goal="q",
            complexity=ResearchComplexity.MODERATE,
            execution_strategy=ResearchExecutionStrategy.DECOMPOSED,
            tasks=[ResearchPlanTask(task_id="research", question="q", dependencies=["missing"])],
        )

    with pytest.raises(ValueError, match="exactly one"):
        ResearchPlan(
            goal="q",
            complexity=ResearchComplexity.SIMPLE,
            execution_strategy=ResearchExecutionStrategy.FOCUSED,
            tasks=[
                ResearchPlanTask(task_id="one", question="one"),
                ResearchPlanTask(task_id="two", question="two"),
            ],
        )


def test_effective_goal_falls_back_to_goal_when_not_rewritten() -> None:
    plan = _focused_plan()
    assert plan.rewritten_goal is None
    assert plan.effective_goal == plan.goal


def test_effective_goal_prefers_the_memory_aware_rewrite() -> None:
    plan = _focused_plan().model_copy(update={"rewritten_goal": "How does RAG work vs QLoRA?"})
    assert plan.effective_goal == "How does RAG work vs QLoRA?"

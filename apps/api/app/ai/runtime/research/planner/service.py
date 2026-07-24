"""Planner service that uses the canonical Generation Runtime, never providers directly."""

from __future__ import annotations

from uuid import UUID

import structlog

from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.caching.enums import CacheRuntime
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface
from app.ai.runtime.generation.routing.enums import RoutingStrategy
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType
from app.ai.runtime.research.planner.models import ResearchPlan
from app.ai.runtime.research.planner.policies import ResearchPlanningPolicy
from app.ai.runtime.research.planner.prompts import (
    PLANNER_PROMPT_VERSION,
    planner_system_prompt,
    planner_user_prompt,
)

logger = structlog.get_logger()


class ResearchPlannerError(ValueError):
    """Classified planner failure; callers must not begin retrieval after this."""


class ResearchPlanner:
    def __init__(
        self,
        generation_runtime: GenerationRuntimeInterface,
        policy: ResearchPlanningPolicy | None = None,
    ) -> None:
        self._generation_runtime = generation_runtime
        self._policy = policy or ResearchPlanningPolicy()

    async def plan(
        self,
        *,
        query: str,
        owner_id: UUID,
        research_run_id: UUID,
        provider: GenerationProvider | None = None,
        routing_strategy: RoutingStrategy | None = None,
        memory_context: str | None = None,
    ) -> ResearchPlan:
        result = await self._generation_runtime.execute(
            GenerationRequest(
                prompt_context=PromptContext(context="", chunks=[]),
                user_prompt=planner_user_prompt(query=query, memory_context=memory_context),
                system_prompt=planner_system_prompt(),
                response_format=ResponseFormat.STRUCTURED,
                output_model=ResearchPlan,
                # Claude's native schema-constrained decoding rejects
                # `minItems`/`maxItems`/`maxLength`/etc. (see
                # `_strip_unsupported_claude_schema_keywords`), so the API no
                # longer bounds `tasks`/`question`/`goal` length itself --
                # only this budget does. 800 was sized for a schema-bounded
                # response and truncates mid-JSON on a real (up to 5-task,
                # per `ResearchPlanningPolicy`) plan, which then fails
                # `ResearchPlan.model_validate()` below.
                max_tokens=2000,
                max_regeneration_attempts=1,
                owner_id=owner_id,
                session_id=research_run_id,
                routing_strategy=routing_strategy,
                cache_runtime=CacheRuntime.PLANNER,
                runtime=RuntimeType.PLANNER,
                metadata={
                    "prompt_version": PLANNER_PROMPT_VERSION,
                    "research_run_id": str(research_run_id),
                },
            ),
            provider=provider,
        )
        try:
            plan = (
                result.parsed_output
                if isinstance(result.parsed_output, ResearchPlan)
                else ResearchPlan.model_validate(result.parsed_output)
            )
        except Exception as exc:
            logger.warning(
                "research_runtime.planner.schema_invalid",
                research_run_id=str(research_run_id),
                error=str(exc),
                raw_content=result.content[:2000],
            )
            raise ResearchPlannerError("Planner did not return a schema-valid plan.") from exc

        budget = self._policy.budget_for(plan.complexity)
        if len(plan.tasks) > budget.max_tasks:
            logger.warning(
                "research_runtime.planner.budget_exceeded",
                research_run_id=str(research_run_id),
                complexity=plan.complexity.value,
                task_count=len(plan.tasks),
                max_tasks=budget.max_tasks,
            )
            raise ResearchPlannerError(
                "Planner returned "
                f"{len(plan.tasks)} tasks, exceeding the {budget.max_tasks}-task policy."
            )
        logger.info(
            "research_runtime.planner.completed",
            research_run_id=str(research_run_id),
            complexity=plan.complexity.value,
            execution_strategy=plan.execution_strategy.value,
            task_count=len(plan.tasks),
            memory_context_used=bool(memory_context),
        )
        return plan

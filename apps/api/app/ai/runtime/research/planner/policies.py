"""Hard ceilings for planner output, independent of model recommendations."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.runtime.research.planner.models import ResearchComplexity


@dataclass(frozen=True)
class ResearchPlanningBudget:
    max_tasks: int
    max_review_iterations: int
    max_duration_seconds: int
    max_estimated_cost_usd: float


class ResearchPlanningPolicy:
    """Maps complexity to bounded execution policy; callers cannot exceed it."""

    _BUDGETS = {
        ResearchComplexity.SIMPLE: ResearchPlanningBudget(
            max_tasks=1,
            max_review_iterations=0,
            max_duration_seconds=120,
            max_estimated_cost_usd=0.50,
        ),
        ResearchComplexity.MODERATE: ResearchPlanningBudget(
            max_tasks=3,
            max_review_iterations=1,
            max_duration_seconds=300,
            max_estimated_cost_usd=2.00,
        ),
        ResearchComplexity.COMPLEX: ResearchPlanningBudget(
            max_tasks=5,
            max_review_iterations=2,
            max_duration_seconds=600,
            max_estimated_cost_usd=5.00,
        ),
    }

    def budget_for(self, complexity: ResearchComplexity) -> ResearchPlanningBudget:
        return self._BUDGETS[complexity]

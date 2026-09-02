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
    # A human rejecting a report with feedback gets its own small
    # allowance, tracked separately from `max_review_iterations` (the
    # automatic REVISE_SYNTHESIS/RESEARCH_GAPS repair loop's shared
    # counter) -- a human is never blocked from asking for one revision
    # just because the automatic reviewer already spent its own budget.
    max_human_revisions: int


class ResearchPlanningPolicy:
    """Maps complexity to bounded execution policy; callers cannot exceed it."""

    _BUDGETS = {
        ResearchComplexity.SIMPLE: ResearchPlanningBudget(
            max_tasks=1,
            max_review_iterations=0,
            max_duration_seconds=120,
            max_estimated_cost_usd=0.50,
            max_human_revisions=1,
        ),
        ResearchComplexity.MODERATE: ResearchPlanningBudget(
            max_tasks=3,
            max_review_iterations=1,
            max_duration_seconds=300,
            max_estimated_cost_usd=2.00,
            max_human_revisions=1,
        ),
        ResearchComplexity.COMPLEX: ResearchPlanningBudget(
            max_tasks=5,
            max_review_iterations=2,
            max_duration_seconds=600,
            max_estimated_cost_usd=5.00,
            max_human_revisions=1,
        ),
    }

    def budget_for(self, complexity: ResearchComplexity) -> ResearchPlanningBudget:
        return self._BUDGETS[complexity]

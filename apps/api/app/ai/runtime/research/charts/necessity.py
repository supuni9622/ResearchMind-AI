"""Decide whether a Deep Research draft's findings warrant AI-generated
charts, and extract the data for them -- one small, cheap, bounded LLM
call (never the main synthesis/review-tier model), mirroring
`WebSearchNecessityService` (web_search/necessity.py).

Combined decide-and-extract in a single call, unlike web/paper search:
those need a real external tool call after deciding (fetch results), so
they're a genuine two-step decide-then-invoke. A chart's "invoke" step
is a deterministic, non-LLM render (matplotlib, see reporting/charts.py)
-- there's nothing external to fetch, so a second LLM round-trip would
only add latency/cost for no benefit.
"""

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
from app.ai.runtime.research.charts.models import ChartGenerationDecision
from app.ai.runtime.research.synthesis.models import ResearchDraft
from app.core.settings import settings

logger = structlog.get_logger()

_MAX_FINDING_CHARACTERS = 1_200
_SYSTEM_PROMPT = (
    "You decide whether a research report's findings contain numeric data "
    "worth visualizing as a chart, and if so, extract that data. Rules: "
    "(1) Only use numbers that are explicitly written in the findings text "
    "below -- never invent, estimate, extrapolate, or round a number that "
    "isn't literally stated. (2) If the findings are purely qualitative or "
    "narrative with no comparable numeric values, return needs_charts=false "
    "and an empty charts list -- a report with nothing to chart is a "
    "correct, common outcome, not a failure. (3) Prefer a small number of "
    "clear charts over many marginal ones -- at most 3. (4) Each chart's "
    "data must trace back to one specific finding; set section_heading to "
    "that finding's heading and citation_ids to the citations backing the "
    "numbers you charted. Respond with ONLY a single JSON object matching "
    "the requested schema -- no markdown code fences, no prose before or "
    "after it."
)


class ChartGenerationService:
    """A settings flag gates this entirely off; otherwise falls to a cheap
    OpenAI/Claude model (`cheap_provider`, resolved at composition time),
    with the same `RoutingStrategy.CLASSIFICATION` fallback shape
    `WebSearchNecessityService` uses when neither is configured. Fails
    closed to "no charts" on any exception -- a broken/slow chart step
    must never fail or block report finalization.
    """

    def __init__(
        self,
        *,
        cheap_generation_runtime: GenerationRuntimeInterface,
        cheap_provider: GenerationProvider | None,
        fallback_generation_runtime: GenerationRuntimeInterface | None = None,
    ) -> None:
        self._cheap_runtime = cheap_generation_runtime
        self._cheap_provider = cheap_provider
        self._fallback_runtime = fallback_generation_runtime

    async def decide(
        self,
        *,
        draft: ResearchDraft,
        owner_id: UUID,
        research_run_id: UUID,
    ) -> ChartGenerationDecision:
        if not settings.deep_research_chart_generation_enabled:
            return ChartGenerationDecision(
                needs_charts=False,
                charts=[],
                reason="Chart generation is disabled for this deployment.",
            )

        try:
            return await self._decide_with_model(
                draft=draft,
                owner_id=owner_id,
                research_run_id=research_run_id,
            )
        except Exception as exc:
            logger.warning(
                "research_runtime.charts.necessity_unavailable",
                research_run_id=str(research_run_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return ChartGenerationDecision(
                needs_charts=False,
                charts=[],
                reason="The chart-generation necessity check was unavailable.",
            )

    async def _decide_with_model(
        self,
        *,
        draft: ResearchDraft,
        owner_id: UUID,
        research_run_id: UUID,
    ) -> ChartGenerationDecision:
        findings_summary = "\n\n".join(
            f"## {finding.heading}\n{finding.content[:_MAX_FINDING_CHARACTERS]}"
            for finding in draft.findings
        )

        request = GenerationRequest(
            prompt_context=PromptContext(context=findings_summary, chunks=[]),
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=(
                f"Report title: {draft.title}\n\n"
                "Do these findings contain numeric data worth charting? If "
                "so, extract it."
            ),
            response_format=ResponseFormat.STRUCTURED,
            output_model=ChartGenerationDecision,
            # Generous relative to the schema's worst case (3 charts x 12
            # points each, plus captions) -- same sizing philosophy as
            # WebSearchNecessityService/ResearchSynthesisService: a too-
            # tight budget can silently exhaust the regeneration attempts
            # without ever tripping truncation auto-escalation.
            max_tokens=2_000,
            max_regeneration_attempts=2,
            owner_id=owner_id,
            session_id=research_run_id,
            temperature=0.0,
            routing_strategy=(
                RoutingStrategy.CLASSIFICATION if self._cheap_provider is None else None
            ),
            cache_runtime=CacheRuntime.REVIEWER,
            runtime=RuntimeType.RESEARCH,
            metadata={
                "research_run_id": str(research_run_id),
                "usage_category": "chart_generation_decision",
                "prompt_version": "chart-generation-necessity-v1",
            },
        )

        runtime = (
            self._cheap_runtime
            if self._cheap_provider is not None
            else (self._fallback_runtime or self._cheap_runtime)
        )
        result = await runtime.execute(request, provider=self._cheap_provider)
        decision = result.parsed_output
        if isinstance(decision, dict):
            decision = ChartGenerationDecision.model_validate(decision)
        if not isinstance(decision, ChartGenerationDecision):
            raise ValueError("Chart necessity check did not return a schema-valid decision.")
        return decision

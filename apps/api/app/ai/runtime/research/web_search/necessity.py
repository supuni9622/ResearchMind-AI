"""Decide whether a research gap needs a web search -- a small, cheap,
bounded LLM call (never the main synthesis/review-tier model), plus the
deterministic pre-rules from web_search_tool_platform_prd.md §16.2/§17.
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
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.web_search.models import WebSearchMode, WebSearchNecessityDecision

logger = structlog.get_logger()

_MAX_EVIDENCE_ITEMS = 8
_SYSTEM_PROMPT = (
    "You decide whether a bounded research task needs a public web search. "
    "The private evidence already gathered is summarized below. Say yes only "
    "when the goal or open question concerns recent, changing, or external "
    "information the private evidence plausibly cannot answer. Prefer no "
    "when the private evidence already looks sufficient. Return a short "
    "search query and a one-sentence reason a reviewer can read."
)


class WebSearchNecessityService:
    """Deterministic pre-rules first; an AUTO decision falls to a cheap
    OpenAI/Claude model (`cheap_provider`, resolved at composition time from
    whichever of those two is configured -- never Groq/Gemini/Ollama for
    this call). If neither is configured, falls through once more to
    `fallback_generation_runtime` with `RoutingStrategy.CLASSIFICATION`
    (still not `AUTO`, which hard-defaults to Groq) so the decision is never
    unavailable, only ever de-prioritized to whatever's actually configured.
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
        mode: WebSearchMode,
        goal: str,
        gap_question: str | None,
        evidence: ResearchEvidenceBundle,
        owner_id: UUID,
        research_run_id: UUID,
    ) -> WebSearchNecessityDecision:
        query = gap_question or goal
        if mode is WebSearchMode.DISABLED:
            return WebSearchNecessityDecision(
                needs_web_search=False, query=query, reason="Web search is disabled for this run."
            )
        if mode is WebSearchMode.REQUIRED:
            return WebSearchNecessityDecision(
                needs_web_search=True,
                query=query,
                reason="Web search is required for this run.",
            )

        try:
            return await self._decide_with_model(
                goal=goal,
                gap_question=gap_question,
                evidence=evidence,
                owner_id=owner_id,
                research_run_id=research_run_id,
            )
        except Exception as exc:
            # Fail closed on the decision itself (no search) but never fail
            # the run -- the existing document-only gap-research path still
            # runs unaffected (PRD §5.7 "best-effort behavior").
            logger.warning(
                "research_runtime.web_search.necessity_unavailable",
                research_run_id=str(research_run_id),
                error_type=type(exc).__name__,
            )
            return WebSearchNecessityDecision(
                needs_web_search=False,
                query=query,
                reason="The web-search necessity check was unavailable.",
            )

    async def _decide_with_model(
        self,
        *,
        goal: str,
        gap_question: str | None,
        evidence: ResearchEvidenceBundle,
        owner_id: UUID,
        research_run_id: UUID,
    ) -> WebSearchNecessityDecision:
        evidence_summary = (
            "\n".join(
                f"- {item.filename}: {item.excerpt[:200]}"
                for item in evidence.evidence[:_MAX_EVIDENCE_ITEMS]
            )
            or "(no private evidence gathered yet)"
        )
        request = GenerationRequest(
            prompt_context=PromptContext(context=evidence_summary, chunks=[]),
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=(
                f"Research goal: {goal}\n"
                + (f"Open question: {gap_question}\n" if gap_question else "")
                + "Does answering this need a public web search?"
            ),
            response_format=ResponseFormat.STRUCTURED,
            output_model=WebSearchNecessityDecision,
            max_tokens=300,
            max_regeneration_attempts=1,
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
                "usage_category": "web_search_decision",
                "prompt_version": "web-search-necessity-v1",
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
            decision = WebSearchNecessityDecision.model_validate(decision)
        if not isinstance(decision, WebSearchNecessityDecision):
            raise ValueError("Necessity check did not return a schema-valid decision.")
        return decision

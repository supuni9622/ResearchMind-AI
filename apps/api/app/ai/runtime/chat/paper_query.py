"""Lightweight query extraction for paper search.

Distills a Chat turn's raw message into a short academic search topic
before calling `search_papers`, rather than sending the conversational
sentence through unmodified. Confirmed necessary in practice (2026-07-25):
sending the raw prompt directly returned zero results for both a full
natural-language question and a meta-request like "can I have research
papers" -- neither reads as a topic to an academic search backend.

A second, subtler tuning pass was needed the same day: the search backend
(Semantic Scholar/arXiv via the MCP server) appears to match short, 2-4
word phrases well ("earthquake", "plate tectonics", "earthquake
prediction" all returned results) but a longer keyword-stuffed query like
"earthquake mechanisms plate tectonics fault rupture seismicity" returned
zero -- likely a conjunctive/AND-like match under the hood that a 5+ term
query rarely satisfies. The prompt below now explicitly caps the output at
2-4 words, not just "short."

A third gap found 2026-07-26: `extract()` only ever saw the single latest
message, never prior turns. A topicless follow-up like "find me some
research articles in this field" has no resolvable subject without the
conversation that came before it, so the model either guessed a generic
non-topic or produced something the search backend matched nothing
against -- indistinguishable, from the caller's side, from "nothing was
found," which is silently swallowed (see `paper_search.py`'s
`chat_paper_search_skipped` event, which the frontend renders as no
badge at all). `conversation_context` (optional, best-effort, recent
turns only -- not the full history) lets the model resolve "this field"-
style anaphora against what was actually being discussed.

Mirrors `WebSearchNecessityService`'s cheap-model pattern (small, bounded,
dedicated GenerationService/Runtime pair, `gpt-5-mini`/`claude-haiku-4-5`,
never the main synthesis-tier model) minus the yes/no decision -- the
Papers toggle being on already is the approval to search, so this only
ever extracts a query, never decides whether to search.
"""

from __future__ import annotations

from functools import lru_cache
from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.caching.enums import CacheRuntime
from app.ai.runtime.generation.catalog.models import CLAUDE_HAIKU_4_5, GPT_5_MINI
from app.ai.runtime.generation.config import ClaudeGenerationConfig, OpenAIGenerationConfig
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.interfaces import GenerationProviderInterface
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.orchestration.create import get_generation_runtime
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface
from app.ai.runtime.generation.orchestration.orchestrator import GenerationRuntime
from app.ai.runtime.generation.providers.claude import ClaudeProvider
from app.ai.runtime.generation.providers.openai import OpenAIProvider
from app.ai.runtime.generation.registry import GenerationRegistry
from app.ai.runtime.generation.routing.enums import RoutingStrategy
from app.ai.runtime.generation.service import GenerationService
from app.core.settings import settings

logger = structlog.get_logger()

_MAX_PROMPT_CHARACTERS = 2000
_FALLBACK_QUERY_CHARACTERS = 500

_SYSTEM_PROMPT = (
    "Distill the user's LATEST message into a SHORT academic search query "
    "of 2 to 4 words -- never more than 4 words, never a question or a "
    "request sentence -- suitable for searching Semantic Scholar or arXiv. "
    "The search backend matches short phrases well but returns nothing for "
    "long, keyword-stuffed queries, so shorter is always better; when in "
    "doubt, pick the single most central 2-3 word topic rather than "
    "listing every related concept. Examples: 'can I have research papers "
    "about retrieval augmented generation' becomes 'retrieval augmented "
    "generation'; 'why do earthquakes happen' becomes 'earthquake "
    "mechanisms' (not 'earthquake mechanisms plate tectonics fault "
    "rupture seismicity'). If the message has no clear research subject, "
    "return your single best-guess topic in 2-4 words -- never an empty "
    "or generic query like 'research papers'. A 'Conversation so far' "
    "block may precede the latest message -- use it ONLY to resolve "
    "references the latest message makes to earlier topics (e.g. 'this "
    "field', 'those papers', 'the same topic'); the query must still "
    "describe the latest message's actual subject, not the whole "
    "conversation. Respond with ONLY a single JSON object matching the "
    "requested schema -- no markdown code fences, no prose before or "
    "after it."
)


class PaperQueryExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=60)


class PaperQueryExtractionService:
    """Falls through to `fallback_generation_runtime` (shared production
    runtime, `RoutingStrategy.CLASSIFICATION`) only when neither a cheap
    OpenAI nor Claude key is configured -- matches
    `WebSearchNecessityService`'s composition exactly."""

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

    async def extract(
        self,
        *,
        user_prompt: str,
        owner_id: UUID,
        session_id: UUID,
        conversation_context: str | None = None,
    ) -> str:
        """Best-effort: any failure falls back to the raw (truncated)
        prompt, never raises -- mirrors `WebSearchNecessityService.decide()`'s
        fail-closed behavior."""

        effective_prompt = user_prompt[:_MAX_PROMPT_CHARACTERS]
        if conversation_context:
            effective_prompt = (
                f"Conversation so far:\n{conversation_context}\n\n"
                f"Latest message: {effective_prompt}"
            )

        try:
            request = GenerationRequest(
                prompt_context=PromptContext(context="", chunks=[]),
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=effective_prompt,
                response_format=ResponseFormat.STRUCTURED,
                output_model=PaperQueryExtractionResult,
                max_tokens=300,
                max_regeneration_attempts=2,
                owner_id=owner_id,
                session_id=session_id,
                temperature=0.0,
                routing_strategy=(
                    RoutingStrategy.CLASSIFICATION if self._cheap_provider is None else None
                ),
                cache_runtime=CacheRuntime.CHAT,
                metadata={
                    "usage_category": "paper_search_query_extraction",
                    "prompt_version": "paper-query-extraction-v1",
                },
            )
            runtime = (
                self._cheap_runtime
                if self._cheap_provider is not None
                else (self._fallback_runtime or self._cheap_runtime)
            )
            result = await runtime.execute(request, provider=self._cheap_provider)
            parsed = result.parsed_output
            if isinstance(parsed, dict):
                parsed = PaperQueryExtractionResult.model_validate(parsed)
            if not isinstance(parsed, PaperQueryExtractionResult):
                raise ValueError("Query extraction did not return a schema-valid result.")
            return parsed.query
        except Exception as exc:
            logger.warning(
                "chat.paper_search.query_extraction_failed",
                session_id=str(session_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return user_prompt[:_FALLBACK_QUERY_CHARACTERS]


@lru_cache
def create_paper_query_extraction_service() -> PaperQueryExtractionService:
    providers: list[GenerationProviderInterface] = []
    preferred_provider: GenerationProvider | None = None

    if settings.openai_api_key:
        providers.append(
            OpenAIProvider(
                config=OpenAIGenerationConfig(
                    model_name=settings.mcp_papers_query_openai_model,
                    cost_per_input_1m=GPT_5_MINI.cost_per_input_1m,
                    cost_per_output_1m=GPT_5_MINI.cost_per_output_1m,
                )
            )
        )
        preferred_provider = GenerationProvider.OPENAI
    elif getattr(settings, "anthropic_api_key", None):
        providers.append(
            ClaudeProvider(
                config=ClaudeGenerationConfig(
                    model_name=settings.mcp_papers_query_claude_model,
                    cost_per_input_1m=CLAUDE_HAIKU_4_5.cost_per_input_1m,
                    cost_per_output_1m=CLAUDE_HAIKU_4_5.cost_per_output_1m,
                )
            )
        )
        preferred_provider = GenerationProvider.CLAUDE

    cheap_runtime = GenerationRuntime(
        generation_service=GenerationService(registry=GenerationRegistry(providers=providers))
    )

    return PaperQueryExtractionService(
        cheap_generation_runtime=cheap_runtime,
        cheap_provider=preferred_provider,
        fallback_generation_runtime=get_generation_runtime(),
    )

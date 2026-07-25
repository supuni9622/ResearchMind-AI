"""Composition root for the web-search necessity decision.

Builds a small, dedicated provider registry pinned to a cheap OpenAI
(`gpt-5-mini`) and/or cheap Claude (`claude-haiku-4-5`) model -- deliberately
separate from the app's main `GenerationRegistry` (whose OpenAI/Claude
entries use whatever model is configured for *all* other generation calls,
e.g. synthesis) so this one bounded, cheap decision never depends on --
or changes the cost of -- the rest of the app's model configuration.

Not `gpt-5-nano`, the cheapest OpenAI tier: confirmed in production
(2026-07-25) that it unreliably follows the structured-output contract for
this call, silently failing closed to "no search needed" every time. See
`settings.web_search_decision_openai_model`'s comment.

Falls through to the shared production `GenerationRuntime` (via
`RoutingStrategy.CLASSIFICATION`, not `AUTO`) only when neither OpenAI nor
Claude is configured at all -- see `WebSearchNecessityService`.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.runtime.generation.catalog.models import CLAUDE_HAIKU_4_5, GPT_5_MINI
from app.ai.runtime.generation.config import ClaudeGenerationConfig, OpenAIGenerationConfig
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.interfaces import GenerationProviderInterface
from app.ai.runtime.generation.orchestration.create import get_generation_runtime
from app.ai.runtime.generation.orchestration.orchestrator import GenerationRuntime
from app.ai.runtime.generation.providers.claude import ClaudeProvider
from app.ai.runtime.generation.providers.openai import OpenAIProvider
from app.ai.runtime.generation.registry import GenerationRegistry
from app.ai.runtime.generation.service import GenerationService
from app.ai.runtime.research.web_search.necessity import WebSearchNecessityService
from app.core.settings import settings


@lru_cache
def create_web_search_necessity_service() -> WebSearchNecessityService:
    providers: list[GenerationProviderInterface] = []
    preferred_provider: GenerationProvider | None = None

    if settings.openai_api_key:
        providers.append(
            OpenAIProvider(
                config=OpenAIGenerationConfig(
                    model_name=settings.web_search_decision_openai_model,
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
                    model_name=settings.web_search_decision_claude_model,
                    cost_per_input_1m=CLAUDE_HAIKU_4_5.cost_per_input_1m,
                    cost_per_output_1m=CLAUDE_HAIKU_4_5.cost_per_output_1m,
                )
            )
        )
        preferred_provider = GenerationProvider.CLAUDE

    cheap_runtime = GenerationRuntime(
        generation_service=GenerationService(registry=GenerationRegistry(providers=providers))
    )

    return WebSearchNecessityService(
        cheap_generation_runtime=cheap_runtime,
        cheap_provider=preferred_provider,
        fallback_generation_runtime=get_generation_runtime(),
    )

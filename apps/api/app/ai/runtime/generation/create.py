"""
Generation Platform composition root.

Assembles the Generation Platform by registering all available
generation providers and constructing the GenerationService.

This module is the single composition root for the Generation Platform.

Adding a new provider should require only registering the provider here
without modifying the rest of the application.
"""

from __future__ import annotations

import structlog
from app.ai.artifacts.create import (
    create_generation_artifact_writer,
    get_artifact_policy_service,
)
from app.ai.guardrails.create import (
    get_guardrail_service,
)
from app.ai.observability.create import (
    get_observability_service,
)
from app.ai.observability.prometheus.create import get_metrics_recorder
from app.ai.observability.providers.langsmith.create import (
    create_runtime_tracer,
)
from app.ai.runtime.generation.caching.create import (
    create_caching_service,
)
from app.ai.runtime.generation.catalog.models import (
    CLAUDE_SONNET_4,
    GEMINI_2_5_FLASH,
    GEMMA_4_12B,
    GPT_5_MINI,
    LLAMA_3_3_70B,
)
from app.ai.runtime.generation.config import (
    ClaudeGenerationConfig,
    GeminiGenerationConfig,
    GroqGenerationConfig,
    OllamaGenerationConfig,
    OpenAIGenerationConfig,
)
from app.ai.runtime.generation.interfaces import (
    GenerationProviderInterface,
)
from app.ai.runtime.generation.observability.service import (
    GenerationMetricsService,
)
from app.ai.runtime.generation.prompts.create import (
    get_prompt_service,
)
from app.ai.runtime.generation.providers.claude import (
    ClaudeProvider,
)
from app.ai.runtime.generation.providers.gemini import (
    GeminiProvider,
)
from app.ai.runtime.generation.providers.groq import (
    GroqProvider,
)
from app.ai.runtime.generation.providers.ollama import (
    OllamaProvider,
)
from app.ai.runtime.generation.providers.openai import (
    OpenAIProvider,
)
from app.ai.runtime.generation.registry import (
    GenerationRegistry,
)
from app.ai.runtime.generation.routing.create import (
    create_routing_service,
)
from app.ai.runtime.generation.service import (
    GenerationService,
)
from app.ai.runtime.generation.structured_output.create import (
    get_structured_output_registry,
)
from app.ai.runtime.generation.validation.create import (
    get_validation_service,
)
from app.core.settings import settings
from app.services.generation_usage import GenerationUsageService

logger = structlog.get_logger()


def create_generation_registry() -> GenerationRegistry:
    """
    Create a fully configured GenerationRegistry.

    Only providers with valid configuration
    are registered.

    This allows:

    - local development
    - experimentation
    - partial deployments
    - benchmark environments
    """

    providers: list[GenerationProviderInterface] = []

    #
    # Groq
    #

    if settings.groq_api_key:
        providers.append(
            GroqProvider(
                config=GroqGenerationConfig(
                    model_name=(
                        getattr(
                            settings,
                            "groq_model",
                            LLAMA_3_3_70B.model_name,
                        )
                    ),
                    cost_per_input_1m=LLAMA_3_3_70B.cost_per_input_1m,
                    cost_per_output_1m=LLAMA_3_3_70B.cost_per_output_1m,
                ),
            )
        )

    #
    # OpenAI
    #

    if settings.openai_api_key:
        providers.append(
            OpenAIProvider(
                config=OpenAIGenerationConfig(
                    model_name=(
                        getattr(
                            settings,
                            "openai_model",
                            GPT_5_MINI.model_name,
                        )
                    ),
                    cost_per_input_1m=GPT_5_MINI.cost_per_input_1m,
                    cost_per_output_1m=GPT_5_MINI.cost_per_output_1m,
                ),
            )
        )

    #
    # Claude
    #

    if getattr(
        settings,
        "anthropic_api_key",
        None,
    ):
        providers.append(
            ClaudeProvider(
                config=ClaudeGenerationConfig(
                    model_name=(
                        getattr(
                            settings,
                            "claude_model",
                            CLAUDE_SONNET_4.model_name,
                        )
                    ),
                    cost_per_input_1m=CLAUDE_SONNET_4.cost_per_input_1m,
                    cost_per_output_1m=CLAUDE_SONNET_4.cost_per_output_1m,
                ),
            )
        )

    #
    # Gemini
    #

    if getattr(
        settings,
        "gemini_api_key",
        None,
    ):
        providers.append(
            GeminiProvider(
                config=GeminiGenerationConfig(
                    model_name=(
                        getattr(
                            settings,
                            "gemini_model",
                            GEMINI_2_5_FLASH.model_name,
                        )
                    ),
                    cost_per_input_1m=GEMINI_2_5_FLASH.cost_per_input_1m,
                    cost_per_output_1m=GEMINI_2_5_FLASH.cost_per_output_1m,
                ),
            )
        )

    #
    # Ollama
    #

    if settings.ollama_enabled:
        providers.append(
            OllamaProvider(
                config=OllamaGenerationConfig(
                    host=settings.ollama_base_url,
                    timeout_seconds=settings.ollama_timeout_seconds,
                    model_name=(
                        getattr(
                            settings,
                            "ollama_model",
                            GEMMA_4_12B.model_name,
                        )
                    ),
                    cost_per_input_1m=GEMMA_4_12B.cost_per_input_1m,
                    cost_per_output_1m=GEMMA_4_12B.cost_per_output_1m,
                ),
            )
        )

    registered_providers = [provider.provider.value for provider in providers]

    if not registered_providers:
        logger.warning(
            "generation.registry.empty",
            reason="no_provider_credentials_configured",
        )
    else:
        logger.info(
            "generation.registry.assembled",
            providers=registered_providers,
        )

    return GenerationRegistry(providers=providers)


def create_generation_service() -> GenerationService:
    """
    Create a fully configured GenerationService.
    """

    return GenerationService(
        registry=create_generation_registry(),
        structured_output_registry=get_structured_output_registry(),
        validation_service=get_validation_service(),
        prompt_service=get_prompt_service(),
        routing_service=create_routing_service(),
        caching_service=create_caching_service(),
        guardrail_service=get_guardrail_service(),
        artifact_writer=create_generation_artifact_writer(),
        artifact_policy_service=get_artifact_policy_service(),
        metrics_service=GenerationMetricsService(
            metrics=get_metrics_recorder(),
        ),
        observability_service=get_observability_service(),
        tracer=create_runtime_tracer(),
        usage_service=GenerationUsageService(),
    )

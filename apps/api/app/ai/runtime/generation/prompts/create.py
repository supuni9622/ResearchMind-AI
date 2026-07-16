from __future__ import annotations

from functools import lru_cache

import structlog
from app.ai.runtime.generation.observability.token_counter import (
    TokenCounter,
)
from app.ai.runtime.generation.prompts.registry import (
    PromptRegistry,
)
from app.ai.runtime.generation.prompts.service import (
    PromptService,
)
from app.core.constants import (
    PROMPTS_TEMPLATES_DIRECTORY,
)

logger = structlog.get_logger()


# ==========================================================
# Registry
# ==========================================================


@lru_cache
def get_prompt_registry() -> PromptRegistry:

    registry = PromptRegistry()

    registry.register_all(
        PROMPTS_TEMPLATES_DIRECTORY,
    )

    logger.info(
        "prompt.registry.loaded",
        total_prompts=registry.total_prompts(),
        prompts=registry.dump(),
    )

    return registry


# ==========================================================
# Token Counter
# ==========================================================


@lru_cache
def get_token_counter() -> TokenCounter:

    logger.info(
        "prompt.token_counter.initialized",
    )

    return TokenCounter()


# ==========================================================
# Prompt Service
# ==========================================================


@lru_cache
def get_prompt_service() -> PromptService:

    logger.info(
        "prompt.service.initialized",
    )

    return PromptService(
        registry=get_prompt_registry(),
        token_counter=get_token_counter(),
    )

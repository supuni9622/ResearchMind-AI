from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import structlog
from app.ai.runtime.generation.prompts.registry import (
    PromptRegistry,
)
from app.core.settings import (
    settings,
)

logger = structlog.get_logger()


@lru_cache
def get_prompt_registry() -> PromptRegistry:

    registry = PromptRegistry()

    prompts_path = Path(
        settings.prompts_path,
    )

    registry.register_all(
        prompts_path,
    )

    logger.info(
        "prompt.registry.loaded",
        total_prompts=(registry.total_prompts()),
        prompts=registry.dump(),
    )

    return registry

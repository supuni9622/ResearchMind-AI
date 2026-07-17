from __future__ import annotations

import pytest
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
)


def make_generation_result(**overrides: object) -> GenerationResult:
    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt="hello",
    )

    defaults: dict[str, object] = dict(
        request=request,
        execution=GenerationExecution(),
        statistics=GenerationStatistics(
            provider=GenerationProvider.GROQ,
            model="llama-3.3-70b",
            latency_ms=123.0,
        ),
        provider=GenerationProvider.GROQ,
        model="llama-3.3-70b",
        content="Hello there!",
    )
    defaults.update(overrides)

    return GenerationResult(**defaults)


@pytest.fixture
def generation_result() -> GenerationResult:
    return make_generation_result()

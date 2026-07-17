"""
Shared test factories for Generation Runtime Platform unit tests.

Not a test module itself (no test_ prefix) -- imported by the actual
test files under tests/unit/ai/runtime/generation/orchestration/.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
)
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType


def make_prompt_context(
    *,
    context: str = "The sky is blue during the day.",
) -> PromptContext:
    return PromptContext(
        context=context,
        chunks=[],
        citations=[],
    )


def make_request(
    *,
    user_prompt: str = "What color is the sky?",
    response_format: ResponseFormat = ResponseFormat.TEXT,
    runtime: RuntimeType | None = None,
    session_id: UUID | None = None,
    request_id: UUID | None = None,
) -> GenerationRequest:
    kwargs: dict[str, Any] = {
        "prompt_context": make_prompt_context(),
        "user_prompt": user_prompt,
        "response_format": response_format,
        "runtime": runtime,
        "session_id": session_id,
    }

    if request_id is not None:
        kwargs["request_id"] = request_id

    return GenerationRequest(**kwargs)


def make_result(
    *,
    request: GenerationRequest | None = None,
    content: str = "The sky is blue.",
    metadata: dict[str, Any] | None = None,
) -> GenerationResult:
    return GenerationResult(
        request=request or make_request(),
        execution=GenerationExecution(),
        statistics=GenerationStatistics(
            provider=GenerationProvider.GROQ,
            model="test-model",
        ),
        provider=GenerationProvider.GROQ,
        model="test-model",
        content=content,
        metadata=metadata or {},
    )

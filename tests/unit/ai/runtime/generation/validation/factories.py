"""
Shared test factories for Validation Platform unit tests.

Not a test module itself (no test_ prefix) -- imported by the actual
test files under tests/unit/ai/runtime/generation/validation/.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from app.ai.knowledge.context.citations.models import Citation
from app.ai.knowledge.context.models import ContextChunk, PromptContext
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
)

_DOCUMENT_ID: UUID = uuid4()


def make_chunk(
    *,
    content: str = "The sky is blue during the day.",
    citation_id: str | None = "S1",
    chunk_id: UUID | None = None,
) -> ContextChunk:
    return ContextChunk(
        chunk_id=chunk_id or uuid4(),
        document_id=_DOCUMENT_ID,
        filename="sky.pdf",
        owner_id="owner-1",
        chunk_index=0,
        content=content,
        score=0.9,
        citation_id=citation_id,
    )


def make_citation(
    *,
    citation_id: str = "S1",
) -> Citation:
    return Citation(
        citation_id=citation_id,
        filename="sky.pdf",
        document_id=_DOCUMENT_ID,
    )


def make_prompt_context(
    *,
    context: str = "The sky is blue during the day.",
    chunks: list[ContextChunk] | None = None,
    citations: list[Citation] | None = None,
) -> PromptContext:
    return PromptContext(
        context=context,
        chunks=chunks if chunks is not None else [],
        citations=citations if citations is not None else [],
    )


def make_request(
    *,
    user_prompt: str = "What color is the sky?",
    system_prompt: str | None = None,
    prompt_context: PromptContext | None = None,
    response_format: ResponseFormat = ResponseFormat.TEXT,
    output_schema: dict[str, Any] | None = None,
    max_tokens: int | None = None,
    stream: bool = False,
    tools: list | None = None,
) -> GenerationRequest:
    return GenerationRequest(
        prompt_context=prompt_context or make_prompt_context(),
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        response_format=response_format,
        output_schema=output_schema,
        max_tokens=max_tokens,
        stream=stream,
        tools=tools or [],
    )


def make_result(
    *,
    request: GenerationRequest | None = None,
    content: str = "The sky is blue.",
    parsed_output: Any | None = None,
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
        parsed_output=parsed_output,
    )

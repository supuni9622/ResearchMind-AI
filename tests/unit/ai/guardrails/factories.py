"""
Shared test factories for Guardrails Platform unit tests.

Not a test module itself (no test_ prefix) -- imported by the actual
test files under tests/unit/ai/guardrails/. Self-contained (does not
import from tests/unit/ai/runtime/generation/validation/factories.py)
-- same underlying models, but each platform's test tree owns its own
factories, mirroring how validation/factories.py doesn't import an
even-earlier platform's.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from app.ai.guardrails.enums import (
    GuardrailCategory,
    GuardrailSeverity,
    GuardrailStage,
)
from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.runtime.execution_limits import BudgetPolicy, ExecutionState
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
    metadata: dict[str, Any] | None = None,
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
        metadata=metadata or {},
    )


def make_citation(
    *,
    citation_id: str = "S1",
    chunk_ids: list[UUID] | None = None,
) -> Citation:
    return Citation(
        citation_id=citation_id,
        filename="sky.pdf",
        document_id=_DOCUMENT_ID,
        chunk_ids=chunk_ids or [],
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
) -> GenerationRequest:
    return GenerationRequest(
        prompt_context=prompt_context or make_prompt_context(),
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        response_format=response_format,
        output_schema=output_schema,
        max_tokens=max_tokens,
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


def make_execution_state(
    *,
    tokens_used: int = 0,
    cost_usd: float = 0.0,
    tool_calls_made: int = 0,
    iterations_completed: int = 0,
    elapsed_seconds: float = 0.0,
    visited_state_hashes: list[str] | None = None,
) -> ExecutionState:
    return ExecutionState(
        tokens_used=tokens_used,
        cost_usd=cost_usd,
        tool_calls_made=tool_calls_made,
        iterations_completed=iterations_completed,
        elapsed_seconds=elapsed_seconds,
        visited_state_hashes=visited_state_hashes or [],
    )


def make_budget_policy(
    *,
    max_tokens: int | None = None,
    max_cost_usd: float | None = None,
    max_tool_calls: int | None = None,
    max_iterations: int | None = None,
    max_runtime_seconds: float | None = None,
) -> BudgetPolicy:
    return BudgetPolicy(
        max_tokens=max_tokens,
        max_cost_usd=max_cost_usd,
        max_tool_calls=max_tool_calls,
        max_iterations=max_iterations,
        max_runtime_seconds=max_runtime_seconds,
    )


def make_guardrail_issue(
    *,
    code: str = "test_issue",
    severity: GuardrailSeverity = GuardrailSeverity.WARNING,
    category: GuardrailCategory = GuardrailCategory.PROMPT_INJECTION,
    stage: GuardrailStage = GuardrailStage.INPUT,
    message: str = "test issue",
) -> GuardrailIssue:
    return GuardrailIssue(
        code=code,
        severity=severity,
        category=category,
        stage=stage,
        message=message,
    )


__all__ = [
    "make_budget_policy",
    "make_chunk",
    "make_citation",
    "make_execution_state",
    "make_guardrail_issue",
    "make_prompt_context",
    "make_request",
    "make_result",
]

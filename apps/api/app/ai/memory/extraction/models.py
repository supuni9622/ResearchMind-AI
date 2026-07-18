from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.ai.memory.enums import MemoryType


class _ExtractedMemoryLLM(BaseModel):
    """
    Schema-only twin of `ExtractedMemory`, used exclusively to derive
    `GenerationRequest.output_schema` for the extraction call.

    `ExtractedMemory.importance` isn't reused directly here because its
    `Field(ge=0.0, le=1.0)` emits JSON Schema `minimum`/`maximum`
    keywords that Claude's structured-output schema validation rejects
    outright ("For 'number' type, properties maximum, minimum are not
    supported"). `MemoryExtractionService.extract()` clamps this back
    into `[0, 1]` when converting to the canonical `ExtractedMemory`,
    so the real constraint still holds -- it's just enforced after
    parsing instead of as a schema keyword.
    """

    model_config = ConfigDict(extra="forbid")

    content: str

    type: MemoryType

    importance: float


class ExtractedMemoryBatch(BaseModel):
    """
    Wire shape for the extraction LLM call's structured output
    (`GenerationRequest.output_model`) -- a bare list isn't itself a
    `BaseModel`, so this wraps it for schema derivation.

    `memories` has no default: OpenAI's strict structured-output mode
    requires every schema property to appear in `required`, which
    Pydantic only emits for fields without a default.
    """

    model_config = ConfigDict(extra="forbid")

    memories: list[_ExtractedMemoryLLM]

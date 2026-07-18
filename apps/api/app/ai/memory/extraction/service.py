"""
Memory Extraction (Memory Creation Pipeline, stage 1) -- turns a raw
conversational turn into zero or more `ExtractedMemory` candidates
(content + `MemoryType` + importance) via the Generation Runtime,
rather than requiring every caller to already know what's worth
remembering and how to classify it (PRD §17: "Memory extraction is
performed by LLMs").

Classification is folded into extraction rather than a separate stage:
`ExtractedMemory.type` already carries it, and asking the same LLM
call to both identify a fact and classify it is strictly cheaper than
a second round-trip for something the first call already had to reason
about.

Fails open: any failure (provider error, malformed structured output)
logs and returns an empty list rather than raising -- extraction is a
best-effort enrichment step, and a failure here must never break the
conversation/research turn that triggered it.
"""

from __future__ import annotations

import structlog

from app.ai.knowledge.context.models import PromptContext
from app.ai.memory.enums import MemoryType
from app.ai.memory.extraction.models import ExtractedMemoryBatch
from app.ai.memory.models import ExtractedMemory
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface

logger = structlog.get_logger()

_SYSTEM_PROMPT = """You extract durable memories from a single conversation turn for a \
research assistant.

A memory is worth extracting only if it will still be useful in a future, unrelated conversation:
- explicit user preferences (models, formats, tone, tools)
- stable facts about the user's interests, goals, or research focus
- notable findings, conclusions, or evidence surfaced during research

Do NOT extract:
- the conversation itself, small talk, or one-off clarifying questions
- anything already obvious or generic
- anything you are not confident is durable

For each memory, classify `type` as exactly one of: "user" (a preference or profile fact) or \
"research" (a finding, conclusion, or piece of evidence). Never use "session" or "semantic" -- \
those are assigned elsewhere in the pipeline.

Score `importance` in [0.0, 1.0]: trivial acknowledgements are near 0, strong explicit \
preferences or significant findings are near 1.

Return zero memories when nothing durable is worth keeping -- this is the common case, not \
the exception."""


class MemoryExtractionService:
    def __init__(
        self,
        generation_runtime: GenerationRuntimeInterface,
        *,
        provider: GenerationProvider | None = None,
    ) -> None:
        self._generation_runtime = generation_runtime
        self._provider = provider

    async def extract(
        self,
        *,
        user_message: str,
        assistant_message: str | None = None,
    ) -> list[ExtractedMemory]:
        turn = f"User: {user_message}"

        if assistant_message:
            turn += f"\nAssistant: {assistant_message}"

        request = GenerationRequest(
            # `GenerationService._validate()` rejects both an empty
            # `user_prompt` and an empty `prompt_context.context` -- the
            # turn goes in `context` (with a fixed short instruction as
            # `user_prompt`) rather than the other way around purely to
            # satisfy that; `build_prompt_text`/`build_chat_messages`
            # concatenate `system_prompt` + `context` + `user_prompt`
            # regardless, so the model sees the same text either way.
            prompt_context=PromptContext(context=turn, chunks=[]),
            system_prompt=_SYSTEM_PROMPT,
            user_prompt="Extract memories from the conversation turn above.",
            response_format=ResponseFormat.STRUCTURED,
            output_model=ExtractedMemoryBatch,
            temperature=0.0,
        )

        try:
            result = await self._generation_runtime.execute(request, provider=self._provider)
        except Exception as exc:
            logger.warning(
                "memory.extraction.generation_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return []

        batch = result.parsed_output

        if isinstance(batch, dict):
            try:
                batch = ExtractedMemoryBatch.model_validate(batch)
            except Exception as exc:
                logger.warning(
                    "memory.extraction.parse_failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                return []

        if not isinstance(batch, ExtractedMemoryBatch):
            logger.warning(
                "memory.extraction.no_structured_output",
                parsed_output_type=type(batch).__name__,
            )
            return []

        # Extraction only ever proposes durable, LLM-judged memories --
        # SESSION memory is the raw turn itself, captured unconditionally
        # elsewhere in the pipeline (not gated on this LLM call).
        #
        # `importance` is clamped into [0, 1] here rather than enforced
        # via a schema constraint (see `_ExtractedMemoryLLM`'s docstring
        # for why) -- this is where that guarantee actually gets applied
        # before handing back the canonical, constrained `ExtractedMemory`.
        return [
            ExtractedMemory(
                content=item.content,
                type=item.type,
                importance=max(0.0, min(1.0, item.importance)),
            )
            for item in batch.memories
            if item.type != MemoryType.SESSION
        ]

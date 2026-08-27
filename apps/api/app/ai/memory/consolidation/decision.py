from __future__ import annotations

from uuid import UUID

import structlog

from app.ai.knowledge.context.models import PromptContext
from app.ai.memory.consolidation.models import ConsolidationDecision
from app.ai.memory.models import MemoryRecord
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface

logger = structlog.get_logger()

_SYSTEM_PROMPT = """Classify two durable research-assistant memories. Return exactly one action:
duplicate: same claim/evidence in different words;
mergeable: compatible claims that can be losslessly combined;
contradiction: conflicting, versioned, or superseding claims that must both remain visible;
unrelated: not the same claim.
Embedding similarity only nominated this pair and is not proof. Never merge uncertainty or conflict.
For mergeable, write a concise merged_content preserving every fact. For all other actions return an
empty merged_content. Return only the requested structured JSON."""


class MemoryConsolidationDecisionService:
    def __init__(
        self,
        runtime: GenerationRuntimeInterface,
        *,
        provider: GenerationProvider | None = None,
        fallback_provider: GenerationProvider | None = None,
    ) -> None:
        self._runtime = runtime
        self._provider = provider
        self._fallback_provider = fallback_provider

    async def decide(
        self, *, owner_id: UUID, first: MemoryRecord, second: MemoryRecord
    ) -> ConsolidationDecision | None:
        request = GenerationRequest(
            prompt_context=PromptContext(context="", chunks=[]),
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=f"MEMORY A:\n{first.content}\n\nMEMORY B:\n{second.content}",
            response_format=ResponseFormat.STRUCTURED,
            output_model=ConsolidationDecision,
            temperature=0.0,
            max_tokens=500,
            max_regeneration_attempts=2,
            owner_id=owner_id,
            metadata={"usage_category": "memory_consolidation"},
        )
        providers = [self._provider]
        if self._fallback_provider is not None and self._fallback_provider != self._provider:
            providers.append(self._fallback_provider)
        for provider in providers:
            try:
                result = await self._runtime.execute(request, provider=provider)
                decision = result.parsed_output
                if isinstance(decision, dict):
                    decision = ConsolidationDecision.model_validate(decision)
                if isinstance(decision, ConsolidationDecision):
                    return decision
            except Exception as exc:
                logger.warning(
                    "memory.consolidation.decision_failed",
                    provider=provider.value if provider else None,
                    error_type=type(exc).__name__,
                )
        return None

"""
Generation artifact builder. Pure -- no knowledge of storage.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.artifacts.generation.models import (
    GenerationArtifact,
    GenerationArtifactMetadata,
    GenerationCacheSnapshot,
    GenerationResponseSnapshot,
    GenerationRoutingSnapshot,
)
from app.ai.runtime.generation.models import GenerationResult


class GenerationArtifactBuilder:
    """
    Builds the canonical GenerationArtifact from a completed
    GenerationResult.
    """

    def build(
        self,
        *,
        result: GenerationResult,
        owner_id: UUID | None = None,
    ) -> GenerationArtifact:

        routing_dict = result.metadata.get("routing")
        cache_dict = result.metadata.get("cache")

        return GenerationArtifact(
            metadata=GenerationArtifactMetadata(
                owner_id=owner_id,
                session_id=result.request.session_id,
                generation_id=result.generation_id,
                conversation_id=result.request.conversation_id,
                duration_ms=result.statistics.latency_ms,
                provider=result.provider,
                model=result.model,
                operation=result.execution.operation,
            ),
            request=result.request,
            response=GenerationResponseSnapshot(
                content=result.content,
                parsed_output=result.parsed_output,
                finish_reason=result.finish_reason,
                usage=result.statistics,
            ),
            validation=result.validation,
            guardrails=result.guardrails,
            routing=(GenerationRoutingSnapshot(**routing_dict) if routing_dict else None),
            cache=(GenerationCacheSnapshot(**cache_dict) if cache_dict else None),
        )

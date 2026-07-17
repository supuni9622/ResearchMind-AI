"""
Generation Replay (PRD §21): Stored Prompt -> Stored Context -> Stored
Result.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from app.ai.artifacts.generation.readers import GenerationArtifactReader
from app.ai.runtime.generation.models import GenerationExecution, GenerationResult


class GenerationReplayService:
    """
    Reconstructs a `GenerationResult` from a previously persisted
    `GenerationArtifact` -- everything a caller of `GenerationService.
    generate()` would have received, without re-running the provider.
    """

    def __init__(
        self,
        reader: GenerationArtifactReader,
    ) -> None:
        self._reader = reader

    async def replay(
        self,
        generation_id: UUID,
    ) -> GenerationResult:

        artifact = await self._reader.read(generation_id)

        metadata: dict[str, object] = {}

        if artifact.routing is not None:
            metadata["routing"] = artifact.routing.model_dump(mode="json")

        if artifact.cache is not None:
            metadata["cache"] = artifact.cache.model_dump(mode="json")

        return GenerationResult(
            generation_id=artifact.metadata.generation_id,
            request=artifact.request,
            execution=GenerationExecution(
                operation=artifact.metadata.operation,
                started_at=(
                    artifact.metadata.created_at
                    - timedelta(milliseconds=artifact.metadata.duration_ms)
                ),
                completed_at=artifact.metadata.created_at,
            ),
            statistics=artifact.response.usage,
            provider=artifact.metadata.provider,
            model=artifact.metadata.model,
            content=artifact.response.content,
            finish_reason=artifact.response.finish_reason,
            metadata=metadata,
            parsed_output=artifact.response.parsed_output,
            validation=artifact.validation,
            guardrails=artifact.guardrails,
        )

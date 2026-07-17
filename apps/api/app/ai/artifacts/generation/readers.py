"""
Generation artifact reader -- reconstructs a GenerationArtifact
previously persisted by GenerationArtifactWriter.
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
from app.ai.artifacts.readers.base import BaseArtifactReader
from app.ai.guardrails.models import GuardrailReport
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.validation.models import ValidationReport


class GenerationArtifactReader(BaseArtifactReader):
    async def read(
        self,
        generation_id: UUID,
    ) -> GenerationArtifact:

        base_path = f"artifacts/generations/{generation_id}"

        metadata = await self._read_json(
            key=f"{base_path}/metadata.json",
            model=GenerationArtifactMetadata,
        )
        request = await self._read_json(
            key=f"{base_path}/request.json",
            model=GenerationRequest,
        )
        response = await self._read_json(
            key=f"{base_path}/response.json",
            model=GenerationResponseSnapshot,
        )

        return GenerationArtifact(
            metadata=metadata,
            request=request,
            response=response,
            validation=await self._read_json_optional(
                key=f"{base_path}/validation.json",
                model=ValidationReport,
            ),
            guardrails=await self._read_json_optional(
                key=f"{base_path}/guardrails.json",
                model=GuardrailReport,
            ),
            routing=await self._read_json_optional(
                key=f"{base_path}/routing.json",
                model=GenerationRoutingSnapshot,
            ),
            cache=await self._read_json_optional(
                key=f"{base_path}/cache.json",
                model=GenerationCacheSnapshot,
            ),
        )

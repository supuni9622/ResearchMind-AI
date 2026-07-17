"""
Generation artifact models (PRD §13).

Storage layout:

    artifacts/generations/{generation_id}/
        request.json
        response.json
        metadata.json
        validation.json     (when GenerationResult.validation is set)
        guardrails.json     (when GenerationResult.guardrails is set)
        routing.json        (when GenerationResult.metadata["routing"] is set)
        cache.json          (when GenerationResult.metadata["cache"] is set)
        metrics.json        (Runtime Metrics Integration -- always present)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.artifacts.models import ArtifactMetadata
from app.ai.guardrails.models import GuardrailReport
from app.ai.runtime.generation.enums import GenerationOperation, GenerationProvider
from app.ai.runtime.generation.models import GenerationRequest, GenerationStatistics
from app.ai.runtime.generation.observability.models import GenerationMetricsSnapshot
from app.ai.runtime.generation.validation.models import ValidationReport


class GenerationArtifactMetadata(ArtifactMetadata):
    model_config = ConfigDict(extra="forbid")

    generation_id: UUID

    conversation_id: UUID | None = None

    duration_ms: float

    provider: GenerationProvider

    model: str

    operation: GenerationOperation


class GenerationResponseSnapshot(BaseModel):
    """Maps 1:1 onto PRD §13's `response.json` (`content/parsed_output/usage`)."""

    model_config = ConfigDict(extra="forbid")

    content: str

    parsed_output: Any | None = None

    finish_reason: str | None = None

    usage: GenerationStatistics


class GenerationRoutingSnapshot(BaseModel):
    """1:1 with the dict `GenerationService._routing_metadata()` produces."""

    model_config = ConfigDict(extra="forbid")

    strategy: str

    selected_provider: str

    selected_model: str

    score: float

    reasons: list[str]

    used_fallback: bool


class GenerationCacheSnapshot(BaseModel):
    """1:1 with the dict shape stored at `GenerationResult.metadata["cache"]`."""

    model_config = ConfigDict(extra="forbid")

    hit: bool

    level: str | None = None

    tokens_saved: int | None = None

    cost_saved: float | None = None


class GenerationArtifact(BaseModel):
    """
    Canonical persistence model representing one `generate()` execution.
    """

    model_config = ConfigDict(extra="forbid")

    metadata: GenerationArtifactMetadata

    request: GenerationRequest

    response: GenerationResponseSnapshot

    validation: ValidationReport | None = None

    guardrails: GuardrailReport | None = None

    routing: GenerationRoutingSnapshot | None = None

    cache: GenerationCacheSnapshot | None = None

    metrics: GenerationMetricsSnapshot

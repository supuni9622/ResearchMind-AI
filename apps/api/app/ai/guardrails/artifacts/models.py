"""
Canonical guardrail artifact models.

A GuardrailArtifact represents a complete guardrail evaluation for a
single run. Serialized to S3 under (PRD §16):

    guardrails/{run_id}/{input,retrieval,generation,runtime,report}.json
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.ai.guardrails.models import GuardrailReport
from pydantic import BaseModel, ConfigDict, Field


class GuardrailArtifact(BaseModel):
    """
    Canonical persistence model representing a guardrail evaluation run.
    """

    model_config = ConfigDict(extra="forbid")

    artifact_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier of this guardrail artifact.",
    )

    version: str = Field(
        default="1.0",
        description="Artifact schema version.",
    )

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the artifact was generated.",
    )

    run_id: UUID = Field(
        description="Identifier of the run this evaluation belongs to.",
    )

    report: GuardrailReport

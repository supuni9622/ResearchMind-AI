"""Immutable, compact evidence artifact persistence through the Artifact Platform."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.artifacts.models import JsonDictFile
from app.ai.artifacts.writers.base import write_json_artifact
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.retrieval.models import ResearchTaskResult
from app.infrastructure.storage.interfaces import DocumentStorage


class ResearchEvidenceArtifact(BaseModel):
    """Durable hand-off from retrieval to synthesis after graph state expires."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    research_run_id: UUID
    plan: dict
    task_results: dict[str, ResearchTaskResult]
    evidence_bundle: ResearchEvidenceBundle | None = None


class ResearchEvidenceArtifactWriter:
    """Writes idempotent, versioned evidence artifacts per research run."""

    def __init__(self, storage: DocumentStorage) -> None:
        self._storage = storage

    async def write(self, artifact: ResearchEvidenceArtifact, *, version: int = 1) -> str:
        if version < 1 or version > 2:
            raise ValueError("Evidence artifact version must be between one and two.")
        suffix = "" if version == 1 else f"-{version}"
        key = f"artifacts/research-runs/{artifact.research_run_id}/evidence{suffix}.json"
        if await self._storage.exists(key=key):
            return key
        await write_json_artifact(
            self._storage,
            key=key,
            payload=JsonDictFile(data=artifact.model_dump(mode="json")),
        )
        return key

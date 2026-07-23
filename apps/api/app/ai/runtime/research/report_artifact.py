"""Durable, idempotent final-report artifacts for Research Runtime runs."""

from __future__ import annotations

from io import BytesIO
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.artifacts.models import JsonDictFile
from app.ai.artifacts.writers.base import write_json_artifact
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.reporting.pdf import render_research_report_pdf
from app.ai.runtime.research.review import ResearchReview
from app.ai.runtime.research.synthesis.models import ResearchDraft
from app.infrastructure.storage.interfaces import DocumentStorage


class ResearchFinalReportArtifact(BaseModel):
    """Canonical compact payload accompanying a human-facing PDF."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    research_run_id: UUID
    draft: ResearchDraft
    review: ResearchReview


class ResearchFinalReportReferences(BaseModel):
    """Stable artifact keys; callers may authorize presigned downloads separately."""

    model_config = ConfigDict(extra="forbid")

    report_ref: str
    pdf_ref: str


class ResearchFinalReportArtifactWriter:
    """Writes final report JSON and PDF once per research run."""

    def __init__(self, storage: DocumentStorage) -> None:
        self._storage = storage

    async def write(
        self,
        *,
        research_run_id: UUID,
        draft: ResearchDraft,
        review: ResearchReview,
        evidence: ResearchEvidenceBundle,
    ) -> ResearchFinalReportReferences:
        base_key = f"artifacts/research-runs/{research_run_id}/final-report"
        report_key = f"{base_key}.json"
        pdf_key = f"{base_key}.pdf"
        artifact = ResearchFinalReportArtifact(
            research_run_id=research_run_id,
            draft=draft,
            review=review,
        )
        if not await self._storage.exists(key=report_key):
            await write_json_artifact(
                self._storage,
                key=report_key,
                payload=JsonDictFile(data=artifact.model_dump(mode="json")),
            )
        if not await self._storage.exists(key=pdf_key):
            pdf = render_research_report_pdf(draft=draft, review=review, evidence=evidence)
            await self._storage.upload(
                key=pdf_key,
                file=BytesIO(pdf),
                content_type="application/pdf",
            )
        return ResearchFinalReportReferences(report_ref=report_key, pdf_ref=pdf_key)

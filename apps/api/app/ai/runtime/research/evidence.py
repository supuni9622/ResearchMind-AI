"""Deterministic compact evidence aggregation for later synthesis and review."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.ai.runtime.research.retrieval.models import (
    ResearchEvidenceReference,
    ResearchTaskResult,
    ResearchTaskStatus,
)


class ResearchEvidenceWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    warning_id: str
    kind: str
    task_id: str


class ResearchEvidenceBundle(BaseModel):
    """Citation-safe synthesis input: references/excerpts only, no raw contexts."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    evidence: list[ResearchEvidenceReference] = Field(default_factory=list, max_length=40)
    citation_ids: list[str] = Field(default_factory=list, max_length=40)
    completed_task_count: int = Field(ge=0)
    failed_task_count: int = Field(ge=0)
    warnings: list[ResearchEvidenceWarning] = Field(default_factory=list, max_length=20)


def build_evidence_bundle(
    task_results: dict[str, ResearchTaskResult],
    *,
    max_evidence: int = 40,
) -> ResearchEvidenceBundle:
    """Deduplicate only exact chunk identity; distinct sources remain available.

    Selecting the highest-score duplicate is deterministic. We intentionally do
    not deduplicate by semantic similarity or prose, which could erase evidence
    that disagrees with another source.
    """

    if max_evidence < 1:
        raise ValueError("max_evidence must be at least one.")

    by_chunk: dict[tuple[str, str], ResearchEvidenceReference] = {}
    citations: set[str] = set()
    warnings: list[ResearchEvidenceWarning] = []
    completed = 0
    failed = 0

    for task_id in sorted(task_results):
        result = task_results[task_id]
        if result.status is ResearchTaskStatus.FAILED:
            failed += 1
            warnings.append(
                ResearchEvidenceWarning(
                    warning_id=f"task-failed:{task_id}",
                    kind="task_retrieval_failed",
                    task_id=task_id,
                )
            )
            continue

        completed += 1
        citations.update(result.citation_ids)
        for item in result.evidence:
            key = (item.document_id, item.chunk_id)
            previous = by_chunk.get(key)
            if previous is None or item.score > previous.score:
                by_chunk[key] = item

    evidence = sorted(
        by_chunk.values(),
        key=lambda item: (-item.score, item.document_id, item.chunk_id),
    )[:max_evidence]
    return ResearchEvidenceBundle(
        evidence=evidence,
        citation_ids=sorted(citations)[:max_evidence],
        completed_task_count=completed,
        failed_task_count=failed,
        warnings=warnings,
    )

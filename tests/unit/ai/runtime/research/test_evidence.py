from __future__ import annotations

from app.ai.runtime.research.evidence import build_evidence_bundle
from app.ai.runtime.research.retrieval.models import (
    ResearchEvidenceReference,
    ResearchTaskResult,
    ResearchTaskStatus,
)


def _evidence(*, document_id: str, chunk_id: str, score: float) -> ResearchEvidenceReference:
    return ResearchEvidenceReference(
        document_id=document_id,
        chunk_id=chunk_id,
        filename=f"{document_id}.pdf",
        score=score,
        excerpt="bounded excerpt",
    )


def test_evidence_aggregation_deduplicates_exact_chunks_but_preserves_sources() -> None:
    bundle = build_evidence_bundle(
        {
            "first": ResearchTaskResult(
                task_id="first",
                status=ResearchTaskStatus.COMPLETED,
                citation_ids=["c1"],
                evidence=[
                    _evidence(document_id="document-a", chunk_id="chunk-1", score=0.5),
                    _evidence(document_id="document-b", chunk_id="chunk-1", score=0.4),
                ],
            ),
            "second": ResearchTaskResult(
                task_id="second",
                status=ResearchTaskStatus.COMPLETED,
                citation_ids=["c1", "c2"],
                evidence=[_evidence(document_id="document-a", chunk_id="chunk-1", score=0.9)],
            ),
        }
    )

    assert [(item.document_id, item.score) for item in bundle.evidence] == [
        ("document-a", 0.9),
        ("document-b", 0.4),
    ]
    assert bundle.citation_ids == ["c1", "c2"]
    assert bundle.completed_task_count == 2


def test_evidence_aggregation_makes_partial_failure_explicit() -> None:
    bundle = build_evidence_bundle(
        {
            "failed-task": ResearchTaskResult(
                task_id="failed-task",
                status=ResearchTaskStatus.FAILED,
                error_type="TimeoutError",
            )
        }
    )

    assert bundle.failed_task_count == 1
    assert bundle.warnings[0].warning_id == "task-failed:failed-task"

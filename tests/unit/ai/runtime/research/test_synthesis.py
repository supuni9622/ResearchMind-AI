from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.artifacts.enums import ArtifactRuntime
from app.ai.runtime.generation.caching.enums import CacheRuntime
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.retrieval.models import ResearchEvidenceReference
from app.ai.runtime.research.synthesis.models import ResearchDraft, ResearchDraftSection
from app.ai.runtime.research.synthesis.service import (
    ResearchSynthesisError,
    ResearchSynthesisService,
)


def _evidence() -> ResearchEvidenceBundle:
    return ResearchEvidenceBundle(
        evidence=[
            ResearchEvidenceReference(
                document_id="d",
                chunk_id="c",
                filename="a.pdf",
                citation_id="c1",
                score=1,
                excerpt="e",
            )
        ],
        citation_ids=["c1"],
        completed_task_count=1,
        failed_task_count=0,
    )


@pytest.mark.asyncio
async def test_synthesis_uses_structured_generation_and_accepts_known_citations() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=_draft(citation_ids=["c1"]), generation_id=uuid4()
    )
    draft = await ResearchSynthesisService(runtime).synthesize(
        goal="q", evidence=_evidence(), owner_id=uuid4(), research_run_id=uuid4()
    )
    assert draft.abstract == "Grounded"
    assert runtime.execute.await_args.args[0].output_model is ResearchDraft


@pytest.mark.asyncio
async def test_synthesis_is_never_cached_under_the_shared_research_answer_namespace() -> None:
    """Regression test: synthesis must not share `CacheRuntime.RESEARCH` (AUTO,
    semantic-matched) with Linear Research answers -- a semantic-cache hit
    there would silently substitute report prose written for a *different*
    run's evidence bundle. See PRODUCT_FLOWS_AND_GAPS.md Loophole D1."""

    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=_draft(citation_ids=["c1"]), generation_id=uuid4()
    )
    await ResearchSynthesisService(runtime).synthesize(
        goal="q", evidence=_evidence(), owner_id=uuid4(), research_run_id=uuid4()
    )
    request = runtime.execute.await_args.args[0]
    assert request.cache_runtime == CacheRuntime.REVIEWER
    assert request.cache_runtime != CacheRuntime.RESEARCH


@pytest.mark.asyncio
async def test_synthesis_tags_the_request_for_the_research_artifact_policy() -> None:
    """Regression (Evaluation Platform Gap 1): previously unset, which
    only got persisted by an accidental fallback to ArtifactRuntime.CHAT
    -- explicit now that a (RESEARCH, GENERATION) policy rule exists."""

    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=_draft(citation_ids=["c1"]), generation_id=uuid4()
    )
    await ResearchSynthesisService(runtime).synthesize(
        goal="q", evidence=_evidence(), owner_id=uuid4(), research_run_id=uuid4()
    )
    request = runtime.execute.await_args.args[0]
    assert request.artifact_runtime == ArtifactRuntime.RESEARCH


@pytest.mark.asyncio
async def test_synthesis_rejects_invented_citation_ids() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=_draft(citation_ids=["invented"]).model_dump(), generation_id=uuid4()
    )
    with pytest.raises(ResearchSynthesisError, match="unknown citation"):
        await ResearchSynthesisService(runtime).synthesize(
            goal="q", evidence=_evidence(), owner_id=uuid4(), research_run_id=uuid4()
        )


def _draft(*, citation_ids: list[str]) -> ResearchDraft:
    return ResearchDraft(
        title="RAG report",
        abstract="Grounded",
        methodology="Retrieved and evaluated supplied evidence.",
        findings=[
            ResearchDraftSection(
                heading="Finding",
                content="Evidence-backed finding.",
            )
        ],
        discussion="Discussion of findings.",
        conclusion="Conclusion.",
        citation_ids=citation_ids,
    )

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.research.planner.models import ResearchPlanTask
from app.ai.runtime.research.retrieval.models import ResearchTaskStatus
from app.ai.runtime.research.retrieval.service import ResearchTaskRetrievalService


@pytest.mark.asyncio
async def test_task_retrieval_scopes_owner_and_bounds_checkpoint_evidence() -> None:
    owner_id = uuid4()
    retrieval = AsyncMock()
    retrieval.search_hybrid.return_value = SimpleNamespace(retrieval_id=uuid4())
    context_builder = AsyncMock()
    context_builder.build.return_value = SimpleNamespace(
        prompt_context=SimpleNamespace(
            chunks=[
                SimpleNamespace(
                    document_id=uuid4(),
                    chunk_id=uuid4(),
                    filename="paper.pdf",
                    citation_id="c1",
                    score=0.9,
                    content="x" * 700,
                )
            ],
            citations=[SimpleNamespace(citation_id="c1")],
        )
    )
    service = ResearchTaskRetrievalService(
        retrieval_service=retrieval,
        context_builder=context_builder,
    )

    result = await service.execute_task(
        task=ResearchPlanTask(task_id="research", question="How does RAG work?"),
        owner_id=owner_id,
        filters={"document_type": "pdf", "owner_id": "untrusted"},
        top_k=100,
    )

    query = retrieval.search_hybrid.await_args.kwargs["query"]
    assert query.top_k == 8
    assert query.filters["owner_id"] == str(owner_id)
    assert result.status is ResearchTaskStatus.COMPLETED
    assert len(result.evidence[0].excerpt) == 500
    assert result.citation_ids == ["c1"]


@pytest.mark.asyncio
async def test_task_retrieval_turns_a_task_failure_into_a_partial_result() -> None:
    retrieval = AsyncMock()
    retrieval.search_hybrid.side_effect = TimeoutError()
    service = ResearchTaskRetrievalService(
        retrieval_service=retrieval,
        context_builder=AsyncMock(),
    )

    result = await service.execute_task(
        task=ResearchPlanTask(task_id="research", question="q"),
        owner_id=uuid4(),
        filters={},
        top_k=3,
    )

    assert result.status is ResearchTaskStatus.FAILED
    assert result.error_type == "TimeoutError"

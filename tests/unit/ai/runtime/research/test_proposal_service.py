from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryContext, MemoryRecord
from app.ai.runtime.research.exceptions import ResearchQueueSaturatedError
from app.ai.runtime.research.planner.models import (
    ResearchComplexity,
    ResearchExecutionStrategy,
    ResearchPlan,
    ResearchPlanTask,
)
from app.ai.runtime.research.proposal_service import ResearchProposalService
from app.ai.runtime.research.types import ResearchProposalStatus, ResearchRunStatus
from app.models.research_run import ResearchRun
from langchain_core.messages import AIMessage, HumanMessage


@pytest.mark.asyncio
async def test_proposal_persists_a_plan_without_creating_or_running_research() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=ResearchPlan(
            goal="Compare methods",
            complexity=ResearchComplexity.MODERATE,
            execution_strategy=ResearchExecutionStrategy.DECOMPOSED,
            tasks=[ResearchPlanTask(task_id="compare", question="Compare methods")],
            approval_required=True,
        )
    )

    proposal = await ResearchProposalService(session=session, generation_runtime=runtime).propose(
        query="Compare methods",
        top_k=5,
        filters={},
        owner_id=uuid4(),
        provider=None,
        routing_strategy=None,
        conversation_id=None,
    )

    assert proposal.status == ResearchProposalStatus.AWAITING_APPROVAL.value
    assert proposal.plan is not None
    assert proposal.research_run_id is None
    assert ResearchProposalService.plan(proposal).goal == "Compare methods"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_proposal_persists_the_paper_suggestions_toggle() -> None:
    """Regression coverage for the production bug (2026-07-25): the
    `/research/proposals` route parsed `paper_suggestions_enabled` off the
    request but never forwarded it to `propose()`, and `propose()` never
    wrote it into the persisted `request` dict either -- so the graph
    always read it back as unset, no matter what the toggle was set to.
    Both gaps are covered here: the value must actually reach
    `proposal.request`."""

    session = AsyncMock()
    session.add = MagicMock()
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=ResearchPlan(
            goal="Compare methods",
            complexity=ResearchComplexity.MODERATE,
            execution_strategy=ResearchExecutionStrategy.DECOMPOSED,
            tasks=[ResearchPlanTask(task_id="compare", question="Compare methods")],
            approval_required=True,
        )
    )

    proposal = await ResearchProposalService(session=session, generation_runtime=runtime).propose(
        query="Compare methods",
        top_k=5,
        filters={},
        owner_id=uuid4(),
        provider=None,
        routing_strategy=None,
        conversation_id=None,
        paper_suggestions_enabled=True,
    )

    assert proposal.request["paper_suggestions_enabled"] is True


@pytest.mark.asyncio
async def test_proposal_defaults_the_paper_suggestions_toggle_to_false() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=ResearchPlan(
            goal="Compare methods",
            complexity=ResearchComplexity.MODERATE,
            execution_strategy=ResearchExecutionStrategy.DECOMPOSED,
            tasks=[ResearchPlanTask(task_id="compare", question="Compare methods")],
            approval_required=True,
        )
    )

    proposal = await ResearchProposalService(session=session, generation_runtime=runtime).propose(
        query="Compare methods",
        top_k=5,
        filters={},
        owner_id=uuid4(),
        provider=None,
        routing_strategy=None,
        conversation_id=None,
    )

    assert proposal.request["paper_suggestions_enabled"] is False


@pytest.mark.asyncio
async def test_proposal_folds_retrieved_memory_context_into_the_plan_request() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=ResearchPlan(
            goal="Compare it with QLoRA",
            rewritten_goal="Compare LoRA with QLoRA",
            complexity=ResearchComplexity.SIMPLE,
            execution_strategy=ResearchExecutionStrategy.FOCUSED,
            tasks=[ResearchPlanTask(task_id="compare", question="Compare LoRA with QLoRA")],
        )
    )
    owner_id = uuid4()
    now = datetime.now(UTC)
    memory = AsyncMock()
    memory.get_context.return_value = MemoryContext(
        research_memories=[
            MemoryRecord(
                id=uuid4(),
                owner_id=owner_id,
                type=MemoryType.RESEARCH,
                content="Prior research covered LoRA fine-tuning trade-offs.",
                importance_score=0.8,
                created_at=now,
                updated_at=now,
            )
        ]
    )

    await ResearchProposalService(
        session=session,
        generation_runtime=runtime,
        memory_service=memory,
    ).propose(
        query="Compare it with QLoRA",
        top_k=5,
        filters={},
        owner_id=owner_id,
        provider=None,
        routing_strategy=None,
        conversation_id=None,
    )

    memory.get_context.assert_awaited_once()
    request = runtime.execute.await_args.args[0]
    assert "Prior research covered LoRA fine-tuning trade-offs." in request.user_prompt


@pytest.mark.asyncio
async def test_proposal_folds_prior_conversation_turns_into_the_plan_request() -> None:
    """Regression (2026-08-10): switching from Linear Research to Deep
    Research mid-conversation and asking a context-dependent follow-up
    (e.g. "conduct a literature review" right after asking about
    earthquakes) previously produced a plan with no idea what the request
    was about, since `propose()` never looked at prior turns -- only
    `MemoryService`'s separate long-term memory tier, which isn't
    populated synchronously from the turn that just happened."""

    from app.services.research_conversation import ResearchConversationService

    session = AsyncMock()
    session.add = MagicMock()
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=ResearchPlan(
            goal="conduct a literature review",
            rewritten_goal="Conduct a literature review on earthquakes",
            complexity=ResearchComplexity.MODERATE,
            execution_strategy=ResearchExecutionStrategy.DECOMPOSED,
            tasks=[ResearchPlanTask(task_id="review", question="Literature review on earthquakes")],
        )
    )
    conversation_id = uuid4()
    service = ResearchProposalService(session=session, generation_runtime=runtime)
    service._conversations = AsyncMock(spec=ResearchConversationService)
    service._conversations.load_history.return_value = [
        HumanMessage(content="what causes earthquakes?"),
        AIMessage(content="Tectonic plate movement along fault lines."),
    ]

    await service.propose(
        query="conduct a literature review",
        top_k=5,
        filters={},
        owner_id=uuid4(),
        provider=None,
        routing_strategy=None,
        conversation_id=conversation_id,
    )

    service._conversations.load_history.assert_awaited_once()
    request = runtime.execute.await_args.args[0]
    assert "what causes earthquakes?" in request.user_prompt


@pytest.mark.asyncio
async def test_proposal_creation_survives_a_memory_retrieval_failure() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=ResearchPlan(
            goal="Compare methods",
            complexity=ResearchComplexity.MODERATE,
            execution_strategy=ResearchExecutionStrategy.DECOMPOSED,
            tasks=[ResearchPlanTask(task_id="compare", question="Compare methods")],
        )
    )
    memory = AsyncMock()
    memory.get_context.side_effect = RuntimeError("memory backend unavailable")

    proposal = await ResearchProposalService(
        session=session,
        generation_runtime=runtime,
        memory_service=memory,
    ).propose(
        query="Compare methods",
        top_k=5,
        filters={},
        owner_id=uuid4(),
        provider=None,
        routing_strategy=None,
        conversation_id=None,
    )

    assert proposal.status == ResearchProposalStatus.AWAITING_APPROVAL.value


@pytest.mark.asyncio
async def test_check_escalation_persists_nothing_for_a_simple_plan() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=ResearchPlan(
            goal="How does RAG work?",
            complexity=ResearchComplexity.SIMPLE,
            execution_strategy=ResearchExecutionStrategy.FOCUSED,
            tasks=[ResearchPlanTask(task_id="research", question="How does RAG work?")],
        )
    )

    plan, proposal = await ResearchProposalService(
        session=session, generation_runtime=runtime
    ).check_escalation(
        query="How does RAG work?",
        top_k=5,
        filters={},
        owner_id=uuid4(),
        provider=None,
        routing_strategy=None,
        conversation_id=None,
    )

    assert plan.complexity == ResearchComplexity.SIMPLE
    assert proposal is None
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_escalation_persists_an_approvable_proposal_for_a_moderate_plan() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=ResearchPlan(
            goal="Compare LoRA and QLoRA across three papers",
            complexity=ResearchComplexity.MODERATE,
            execution_strategy=ResearchExecutionStrategy.DECOMPOSED,
            tasks=[
                ResearchPlanTask(task_id="lora", question="Summarize LoRA"),
                ResearchPlanTask(task_id="qlora", question="Summarize QLoRA"),
                ResearchPlanTask(
                    task_id="compare",
                    question="Compare them",
                    dependencies=["lora", "qlora"],
                ),
            ],
        )
    )
    owner_id = uuid4()

    plan, proposal = await ResearchProposalService(
        session=session, generation_runtime=runtime
    ).check_escalation(
        query="Compare LoRA and QLoRA across three papers",
        top_k=5,
        filters={},
        owner_id=owner_id,
        provider=None,
        routing_strategy=None,
        conversation_id=None,
    )

    assert plan.complexity == ResearchComplexity.MODERATE
    assert proposal is not None
    assert proposal.owner_id == owner_id
    assert proposal.status == ResearchProposalStatus.AWAITING_APPROVAL.value
    assert (
        ResearchProposalService.plan(proposal).goal == "Compare LoRA and QLoRA across three papers"
    )
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_approval_creates_and_links_one_durable_run() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=0)))
    owner_id = uuid4()
    proposal_id = uuid4()
    run = ResearchRun(
        id=uuid4(),
        owner_id=owner_id,
        graph_thread_id="thread",
        status=ResearchRunStatus.CREATED.value,
    )
    proposal = SimpleNamespace(
        id=proposal_id,
        owner_id=owner_id,
        conversation_id=None,
        status=ResearchProposalStatus.AWAITING_APPROVAL.value,
        research_run_id=None,
        request={"query": "Compare methods", "top_k": 5, "filters": {}},
    )
    runs = AsyncMock()
    runs.create_or_get.return_value = run
    service = ResearchProposalService(
        session=session,
        generation_runtime=AsyncMock(),
        run_service=runs,
    )
    service.get_for_owner = AsyncMock(return_value=proposal)  # type: ignore[method-assign]

    approved = await service.approve(proposal_id=proposal_id, owner_id=owner_id)

    assert approved is run
    assert proposal.research_run_id == run.id
    assert proposal.status == ResearchProposalStatus.APPROVED.value
    assert run.current_phase == "awaiting_runtime_dispatch"
    runs.create_or_get.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_approval_raises_when_the_dispatch_queue_is_saturated() -> None:
    from app.core.settings import settings

    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(
        return_value=MagicMock(
            scalar_one=MagicMock(return_value=settings.deep_research_max_queued_runs)
        )
    )
    owner_id = uuid4()
    proposal_id = uuid4()
    proposal = SimpleNamespace(
        id=proposal_id,
        owner_id=owner_id,
        conversation_id=None,
        status=ResearchProposalStatus.AWAITING_APPROVAL.value,
        research_run_id=None,
        request={"query": "Compare methods", "top_k": 5, "filters": {}},
    )
    runs = AsyncMock()
    service = ResearchProposalService(
        session=session,
        generation_runtime=AsyncMock(),
        run_service=runs,
    )
    service.get_for_owner = AsyncMock(return_value=proposal)  # type: ignore[method-assign]

    with pytest.raises(ResearchQueueSaturatedError):
        await service.approve(proposal_id=proposal_id, owner_id=owner_id)

    runs.create_or_get.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_approval_is_idempotent_after_a_run_was_linked() -> None:
    session = AsyncMock()
    owner_id = uuid4()
    run_id = uuid4()
    proposal = SimpleNamespace(
        id=uuid4(),
        owner_id=owner_id,
        conversation_id=None,
        status=ResearchProposalStatus.APPROVED.value,
        research_run_id=run_id,
        request={},
    )
    run = SimpleNamespace(id=run_id)
    runs = AsyncMock()
    runs.get_for_owner.return_value = run
    service = ResearchProposalService(
        session=session,
        generation_runtime=AsyncMock(),
        run_service=runs,
    )
    service.get_for_owner = AsyncMock(return_value=proposal)  # type: ignore[method-assign]

    assert await service.approve(proposal_id=proposal.id, owner_id=owner_id) is run
    runs.create_or_get.assert_not_awaited()
    session.commit.assert_not_awaited()

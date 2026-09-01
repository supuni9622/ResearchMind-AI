"""Application service for idempotent Research Runtime lifecycle creation."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.runtime.events.research.models import ResearchEventType
from app.ai.runtime.research.draft_inspection import ResearchDraftInspectionService
from app.ai.runtime.research.event_journal import ResearchRuntimeEventJournal
from app.ai.runtime.research.lifecycle import transition_run
from app.ai.runtime.research.types import TERMINAL_RESEARCH_RUN_STATUSES, ResearchRunStatus
from app.core.settings import settings
from app.models.research_run import ResearchRun
from app.repositories.research_run import ResearchRunRepository
from app.repositories.research_run_dispatch import ResearchRunDispatchRepository
from app.repositories.research_run_event import ResearchRunEventRepository

logger = structlog.get_logger()

# How many times a user may retry a run that ended FAILED, before
# `retry_run` refuses further attempts.
_MAX_RESEARCH_RUN_RETRIES = 2


class ResearchRunService:
    """Owns lifecycle creation; graph nodes do not create run records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = ResearchRunRepository(session)
        self._dispatches = ResearchRunDispatchRepository(session)
        self._event_journal = ResearchRuntimeEventJournal(ResearchRunEventRepository(session))

    async def create_or_get(
        self,
        *,
        owner_id: UUID,
        request_fingerprint: str,
        idempotency_key: str | None = None,
        conversation_id: UUID | None = None,
        parent_research_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> ResearchRun:
        if idempotency_key is not None:
            existing = await self._repository.get_by_idempotency_key(
                owner_id=owner_id,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                if existing.request_fingerprint != request_fingerprint:
                    raise ValueError(
                        "Idempotency key was reused with a different research request."
                    )
                return existing

        try:
            run = await self._repository.create(
                ResearchRun(
                    owner_id=owner_id,
                    conversation_id=conversation_id,
                    project_id=project_id,
                    parent_research_id=parent_research_id,
                    graph_thread_id=str(uuid4()),
                    status=ResearchRunStatus.CREATED.value,
                    idempotency_key=idempotency_key,
                    request_fingerprint=request_fingerprint,
                )
            )
            logger.info(
                "research_runtime.run.created",
                research_run_id=str(run.id),
                owner_id=str(owner_id),
                graph_thread_id=run.graph_thread_id,
            )
            return run
        except IntegrityError:
            # Concurrent requests with the same key race between the lookup
            # above and the unique constraint. The constraint is canonical;
            # after rolling back, replay the run it selected.
            await self._session.rollback()
            if idempotency_key is None:
                raise
            existing = await self._repository.get_by_idempotency_key(
                owner_id=owner_id,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise
            if existing.request_fingerprint != request_fingerprint:
                raise ValueError(
                    "Idempotency key was reused with a different research request."
                ) from None
            return existing

    async def get_for_owner(self, *, run_id: UUID, owner_id: UUID) -> ResearchRun | None:
        """Read a lifecycle record only through the owner-scoped repository."""

        return await self._repository.get_by_id_for_owner(run_id=run_id, owner_id=owner_id)

    async def request_cancellation(self, *, run_id: UUID, owner_id: UUID) -> ResearchRun | None:
        """Flag a non-terminal run for cancellation; the graph observes this cooperatively.

        There is no synchronous abort: the worker checks this flag only at
        bounded points (before a new wave, before a new synthesis attempt),
        so cancellation takes effect on the next such checkpoint, not
        immediately.
        """

        run = await self._repository.get_by_id_for_owner(run_id=run_id, owner_id=owner_id)
        if run is None:
            return None
        if run.status in TERMINAL_RESEARCH_RUN_STATUSES or run.cancellation_requested:
            return run
        run.cancellation_requested = True
        await self._session.commit()
        logger.info(
            "research_runtime.run.cancellation_requested",
            research_run_id=str(run.id),
            owner_id=str(owner_id),
        )
        return run

    async def is_cancellation_requested(self, *, run_id: UUID) -> bool:
        return await self._repository.is_cancellation_requested(run_id=run_id)

    async def record_report_decision(
        self,
        *,
        run_id: UUID,
        owner_id: UUID,
        approved: bool,
        reason: str | None = None,
        edited_draft: Mapping[str, object] | None = None,
        draft_inspection: ResearchDraftInspectionService | None = None,
    ) -> ResearchRun | None:
        """Record the report-approval decision and re-queue the run's dispatch
        in one transaction -- both must land together, or neither does,
        otherwise a committed decision with no dispatch would strand the run
        in `awaiting_approval` forever.

        `edited_draft` (only meaningful when `approved`) carries the
        reviewer's free-text edits (`ResearchDraftEdit.model_dump()`) --
        it's merged onto the original checkpointed draft here (filling in
        `citation_ids`/`schema_version`/`limitations` unchanged) so
        `await_report_approval` can hand the graph a fully valid
        `ResearchDraft` to publish, without the graph node itself needing
        to know how to read a checkpoint.
        """

        run = await self._repository.get_by_id_for_owner(run_id=run_id, owner_id=owner_id)
        if run is None:
            return None
        if run.status != ResearchRunStatus.AWAITING_APPROVAL.value:
            raise ValueError(f"Research run '{run.id}' is not awaiting a report decision.")

        decision: dict[str, object] = {
            "decision": "approved" if approved else "rejected",
            "reason": reason,
        }
        if approved and edited_draft is not None:
            if draft_inspection is None:
                raise RuntimeError("Recording an edited draft requires a draft inspection service.")
            pending = await draft_inspection.get_pending_draft(run)
            original_findings = pending.draft.findings
            edited_findings = cast("list[Mapping[str, Any]]", edited_draft["findings"])
            if len(edited_findings) != len(original_findings):
                raise ValueError(
                    "Edited draft must keep the same number of findings as the original."
                )
            merged = pending.draft.model_copy(
                update={
                    "title": edited_draft["title"],
                    "abstract": edited_draft["abstract"],
                    "methodology": edited_draft["methodology"],
                    "findings": [
                        finding.model_copy(
                            update={"heading": edit["heading"], "content": edit["content"]}
                        )
                        for finding, edit in zip(original_findings, edited_findings, strict=True)
                    ],
                    "discussion": edited_draft["discussion"],
                    "conclusion": edited_draft["conclusion"],
                }
            )
            decision["edited_draft"] = merged.model_dump(mode="json")

        run.budget_usage = {**(run.budget_usage or {}), "report_decision": decision}
        await self._dispatches.reopen(run_id=run.id)
        await self._session.commit()
        logger.info(
            "research_runtime.run.report_decision_recorded",
            research_run_id=str(run.id),
            owner_id=str(owner_id),
            approved=approved,
            edited=edited_draft is not None,
        )
        return run

    async def record_plan_decision(
        self,
        *,
        run_id: UUID,
        owner_id: UUID,
        approved: bool,
        reason: str | None = None,
        edited_goal: str | None = None,
        socratic_response: str | None = None,
    ) -> ResearchRun | None:
        """Record the plan-approval decision and re-queue the run's dispatch
        in one transaction -- mirrors `record_report_decision`'s atomicity
        rationale (a committed decision with no dispatch would strand the
        run at `awaiting_plan_approval` forever).

        `edited_goal` (only meaningful when `approved`) is the reviewer's
        revised `rewritten_goal` -- the only plan field editable at this
        checkpoint, since retrieval for the plan's `tasks` has already run
        by the time evidence exists to review. No merge/validation against
        a checkpointed original is needed here (unlike an edited draft's
        finding-count guard): it's a single free-text field, already
        length-bounded by `ResearchPlanGoalEdit`, that `await_plan_approval`
        substitutes directly onto `state["plan"]`.
        """

        run = await self._repository.get_by_id_for_owner(run_id=run_id, owner_id=owner_id)
        if run is None:
            return None
        if run.status != ResearchRunStatus.AWAITING_PLAN_APPROVAL.value:
            raise ValueError(f"Research run '{run.id}' is not awaiting a plan decision.")

        decision: dict[str, object] = {
            "decision": "approved" if approved else "rejected",
            "reason": reason,
        }
        if approved and edited_goal is not None:
            decision["edited_plan"] = {"rewritten_goal": edited_goal}
        if approved and socratic_response is not None:
            decision["socratic_response"] = socratic_response

        run.budget_usage = {**(run.budget_usage or {}), "plan_decision": decision}
        await self._dispatches.reopen(run_id=run.id)
        await self._session.commit()
        logger.info(
            "research_runtime.run.plan_decision_recorded",
            research_run_id=str(run.id),
            owner_id=str(owner_id),
            approved=approved,
            edited=edited_goal is not None,
        )
        return run

    async def record_web_search_decision(
        self,
        *,
        run_id: UUID,
        owner_id: UUID,
        approved: bool,
        reason: str | None = None,
    ) -> ResearchRun | None:
        """Record the web-search-approval decision and re-queue the run's
        dispatch in one transaction -- mirrors `record_plan_decision`'s
        atomicity rationale (a committed decision with no dispatch would
        strand the run at `awaiting_web_search_approval` forever).

        Unlike a plan/report rejection, a rejected web-search suggestion
        never needs an `edited_*` payload -- the graph's `await_web_search_
        approval` node just falls back to the existing document-only
        gap-research path (`route_after_web_search_approval`), so there is
        nothing here for a caller to edit.
        """

        run = await self._repository.get_by_id_for_owner(run_id=run_id, owner_id=owner_id)
        if run is None:
            return None
        if run.status != ResearchRunStatus.AWAITING_WEB_SEARCH_APPROVAL.value:
            raise ValueError(f"Research run '{run.id}' is not awaiting a web-search decision.")

        decision: dict[str, object] = {
            "decision": "approved" if approved else "rejected",
            "reason": reason,
        }
        run.budget_usage = {**(run.budget_usage or {}), "web_search_decision": decision}
        await self._dispatches.reopen(run_id=run.id)
        await self._session.commit()
        logger.info(
            "research_runtime.run.web_search_decision_recorded",
            research_run_id=str(run.id),
            owner_id=str(owner_id),
            approved=approved,
        )
        return run

    async def retry_run(self, *, run_id: UUID, owner_id: UUID) -> ResearchRun | None:
        """Retry a FAILED run by resuming it from its last LangGraph checkpoint.

        Nothing about the checkpoint itself needs touching here -- it
        already survives a FAILED transition untouched, keyed by the run's
        immutable `graph_thread_id`. This only needs to move the run's
        status back into a status `execution.py::_begin`'s
        `allow_resume_in_progress` branch already treats as resumable
        (`RESEARCHING`), and re-queue its dispatch so the worker picks it
        back up -- the same mechanism already used for crash-resume, just
        triggered explicitly instead of by a dead worker's expired lease.

        Bounded by `_MAX_RESEARCH_RUN_RETRIES` so a run that keeps failing
        can't be retried forever.
        """

        run = await self._repository.get_by_id_for_owner(run_id=run_id, owner_id=owner_id)
        if run is None:
            return None
        if run.status != ResearchRunStatus.FAILED.value:
            raise ValueError(f"Research run '{run.id}' is not in a failed state.")
        if (run.retry_count or 0) >= _MAX_RESEARCH_RUN_RETRIES:
            raise ValueError(f"Research run '{run.id}' has exhausted its retry attempts.")

        transition_run(run, target=ResearchRunStatus.RESEARCHING, phase="runtime_retry")
        run.completed_at = None
        run.terminal_reason = None
        run.error_summary = {}
        run.retry_count = (run.retry_count or 0) + 1
        await self._dispatches.reopen(run_id=run.id)
        await self._session.commit()
        logger.info(
            "research_runtime.run.retry_requested",
            research_run_id=str(run.id),
            owner_id=str(owner_id),
            retry_count=run.retry_count,
        )
        return run

    async def expire_stale_awaiting_approval(self, *, older_than_hours: int | None = None) -> int:
        """Auto-cancel runs left sitting at AWAITING_APPROVAL past the TTL.

        Without this, a run the user never returns to accept/reject stays
        `awaiting_approval` forever -- it has no other expiry path. This is
        a callable-but-unscheduled sweep (mirrors `MemoryLifecycleService.
        sweep_stale()`): wiring a recurring trigger (cron/Celery beat) is an
        operator decision, not something to invent here.

        Auto-*cancel*, not auto-approve: publishing a report the user was
        explicitly asked to review, without them ever reviewing it, is the
        wrong default just because they didn't respond in time.
        """

        ttl_hours = (
            older_than_hours
            if older_than_hours is not None
            else settings.research_runtime_awaiting_approval_ttl_hours
        )
        cutoff = datetime.now(UTC) - timedelta(hours=ttl_hours)
        stale_runs = await self._repository.list_stale_awaiting_approval(older_than=cutoff)

        for run in stale_runs:
            was_awaiting_plan = run.status == ResearchRunStatus.AWAITING_PLAN_APPROVAL.value
            was_awaiting_web_search = (
                run.status == ResearchRunStatus.AWAITING_WEB_SEARCH_APPROVAL.value
            )
            transition_run(run, target=ResearchRunStatus.CANCELLED, phase="terminal")
            run.terminal_reason = (
                "awaiting_plan_approval_expired"
                if was_awaiting_plan
                else "awaiting_web_search_approval_expired"
                if was_awaiting_web_search
                else "awaiting_approval_expired"
            )
            await self._event_journal.publish(
                run_id=run.id, event_type=ResearchEventType.RESEARCH_CANCELLED
            )

        await self._session.commit()
        logger.info(
            "research_runtime.run.awaiting_approval_expired",
            expired_count=len(stale_runs),
            ttl_hours=ttl_hours,
        )
        return len(stale_runs)

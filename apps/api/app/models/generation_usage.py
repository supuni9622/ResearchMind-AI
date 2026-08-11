"""Durable, owner-scoped accounting records for completed generations."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GenerationUsage(Base):
    """One immutable usage record per generation request.

    ``request_id`` is unique so retries, cache replay, and concurrent
    completion handling cannot double-count a user's spend.
    """

    __tablename__ = "generation_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    #
    # This generation's LangSmith trace run id (E21's LangSmith-feedback
    # follow-up) -- null whenever tracing wasn't configured, or for
    # internal-helper generations that predate this column. Looked up by
    # `generation_id` when a user submits feedback well after the trace
    # itself has closed, so FeedbackService can call LangSmith's own
    # create_feedback() against the right run.
    #
    langsmith_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    runtime: Mapped[str | None] = mapped_column(String(50), nullable=True)
    #
    # Config fingerprint (EVALUATION_PLAN.md §5) -- from
    # GenerationRequest.surface/prompt_version/chunking_strategy/
    # embedding_model/reranker/routing_strategy, populated only for
    # answer-producing generations (see `config_fingerprint.py`); null
    # for everything else (memory extraction, planning, review, ...).
    #
    surface: Mapped[str | None] = mapped_column(String(30), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    chunking_strategy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reranker: Mapped[str | None] = mapped_column(String(50), nullable=True)
    routing_strategy: Mapped[str | None] = mapped_column(String(30), nullable=True)
    #
    # `GenerationResult.guardrails.final_action` (E5, EVALUATION_PLAN.md
    # §14) -- already computed on every generation guardrails ran for,
    # never persisted before this. Not just a `blocked` boolean: a
    # `blocked` generation never reaches `record()` at all (guardrails
    # raise before completion), so the values seen here are realistically
    # "allow"/"warn"/"regenerate"/"escalate" -- anything other than
    # "allow" is what EVALUATION_PLAN.md §14 calls "guardrail-flagged".
    # Null when guardrails didn't run for this call (no `GuardrailService`
    # configured) rather than a default of "allow", so a scoring job can
    # tell "known safe" apart from "not evaluated".
    #
    guardrail_final_action: Mapped[str | None] = mapped_column(String(20), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Numeric(14, 8), nullable=False, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    streamed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

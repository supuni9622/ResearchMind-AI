"""Shared, token-budgeted memory prompt formatting for every runtime."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.ai.knowledge.context.models import PromptContext
from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryContext, MemoryRecord
from app.ai.memory.observability import metrics as memory_metrics
from app.core.settings import settings
from app.infrastructure.metrics.interfaces import MetricsRecorder

_PREAMBLE = (
    "Background memory from prior turns (may be unrelated to the current "
    "question -- use only if directly relevant, otherwise ignore it entirely):"
)
_FOOTER = (
    "End of background memory. If anything above conflicts with an explicit "
    "instruction in the user's current question, the current question always "
    "wins. The user's actual question is in the Question section below."
)


@dataclass(frozen=True)
class _MemorySection:
    memory_type: MemoryType
    heading: str
    records: list[MemoryRecord]
    candidate_count: int
    token_share: int


@dataclass(frozen=True)
class FormattedMemoryContext:
    """Rendered prompt block plus the exact logical memories it contains."""

    text: str | None
    memory_ids: tuple[UUID, ...]


def _estimate_tokens(text: str) -> int:
    """Deterministic estimate shared with TokenBudgetValidator."""

    return max(1, int(len(text.split()) * 1.3))


def _entry_text(record: MemoryRecord) -> str:
    # M4 selects whole entries. The former character slice could cut a fact in
    # half and make it misleading; oversized entries are now omitted intact.
    return f"- {record.content.strip()}"


def _candidate_records(
    records: list[MemoryRecord], *, limit: int, keep_newest: bool = False
) -> tuple[list[MemoryRecord], int]:
    nonempty = [record for record in records if record.content.strip()]
    if limit <= 0:
        return [], len(nonempty)
    selected = nonempty[-limit:] if keep_newest else nonempty[:limit]
    return selected, len(nonempty)


def _sections(context: MemoryContext) -> list[_MemorySection]:
    session, session_count = _candidate_records(
        context.session_memories,
        limit=settings.memory_context_session_max_items,
        keep_newest=True,
    )
    user, user_count = _candidate_records(
        context.user_memories, limit=settings.memory_context_user_max_items
    )
    semantic, semantic_count = _candidate_records(
        context.semantic_memories, limit=settings.memory_context_semantic_max_items
    )
    research, research_count = _candidate_records(
        context.research_memories, limit=settings.memory_context_research_max_items
    )
    return [
        _MemorySection(
            MemoryType.SESSION,
            "Active session state:",
            session,
            session_count,
            settings.memory_context_session_token_share,
        ),
        _MemorySection(
            MemoryType.USER,
            "Durable user preferences (defaults, see precedence note below):",
            user,
            user_count,
            settings.memory_context_user_token_share,
        ),
        _MemorySection(
            MemoryType.SEMANTIC,
            "What we know about this user:",
            semantic,
            semantic_count,
            settings.memory_context_semantic_token_share,
        ),
        _MemorySection(
            MemoryType.RESEARCH,
            "Relevant prior research findings:",
            research,
            research_count,
            settings.memory_context_research_token_share,
        ),
    ]


def _resolved_budget(*, total_token_budget: int | None, context_window_tokens: int | None) -> int:
    configured = total_token_budget or settings.memory_context_total_token_budget
    if context_window_tokens is None:
        return max(0, configured)
    model_room = (
        context_window_tokens
        - settings.memory_context_reserved_evidence_tokens
        - settings.memory_context_reserved_output_tokens
    )
    return max(0, min(configured, model_room))


def format_memory_context(
    context: MemoryContext,
    *,
    total_token_budget: int | None = None,
    context_window_tokens: int | None = None,
    metrics: MetricsRecorder | None = None,
) -> str | None:
    """Render whole memory entries within one coordinated token budget.

    Each type first receives its configured share. Unused capacity then falls
    through in priority order (SESSION, USER, SEMANTIC, RESEARCH), while item
    caps preserve the retrieval contract. Headings, precedence instructions,
    and omission counts are included in the same total budget.
    """

    if metrics is None:
        # Lazy import avoids a composition-root cycle while ensuring every
        # existing runtime call records the same budget telemetry.
        from app.ai.memory.create import get_memory_metrics

        metrics = get_memory_metrics()

    sections = _sections(context)
    if not any(section.records for section in sections):
        return None

    budget = _resolved_budget(
        total_token_budget=total_token_budget,
        context_window_tokens=context_window_tokens,
    )
    fixed_tokens = _estimate_tokens(f"{_PREAMBLE}\n\n{_FOOTER}")
    if budget <= fixed_tokens:
        return None

    selected: dict[MemoryType, list[MemoryRecord]] = {
        section.memory_type: [] for section in sections
    }
    deferred: dict[MemoryType, list[MemoryRecord]] = {
        section.memory_type: [] for section in sections
    }
    used = fixed_tokens

    # First pass: honor explicit type shares.
    for section in sections:
        section_used = 0
        heading_tokens = _estimate_tokens(section.heading)
        for record in section.records:
            entry_tokens = _estimate_tokens(_entry_text(record))
            cost = entry_tokens + (heading_tokens if not selected[section.memory_type] else 0)
            if section_used + cost <= section.token_share and used + cost <= budget:
                selected[section.memory_type].append(record)
                section_used += cost
                used += cost
            else:
                deferred[section.memory_type].append(record)

    # Second pass: unused shares become a common pool, preserving type and
    # retrieval priority rather than wasting budget.
    for section in sections:
        heading_tokens = _estimate_tokens(section.heading)
        for record in deferred[section.memory_type]:
            entry_tokens = _estimate_tokens(_entry_text(record))
            cost = entry_tokens + (heading_tokens if not selected[section.memory_type] else 0)
            if used + cost <= budget:
                selected[section.memory_type].append(record)
                used += cost

    omitted = {
        section.memory_type: section.candidate_count - len(selected[section.memory_type])
        for section in sections
    }
    omission_parts = [f"{kind.value}={count}" for kind, count in omitted.items() if count]
    omission_line = (
        f"Omitted by memory token budget: {', '.join(omission_parts)}." if omission_parts else None
    )

    # The omission summary is itself context. Make room by removing the last
    # selected, lowest-priority entry until the complete block fits.
    if omission_line:
        while used + _estimate_tokens(omission_line) > budget:
            removed = False
            for section in reversed(sections):
                if selected[section.memory_type]:
                    removed_record = selected[section.memory_type].pop()
                    used -= _estimate_tokens(_entry_text(removed_record))
                    if not selected[section.memory_type]:
                        used -= _estimate_tokens(section.heading)
                    omitted[section.memory_type] += 1
                    removed = True
                    break
            if not removed:
                return None
            omission_parts = [f"{kind.value}={count}" for kind, count in omitted.items() if count]
            omission_line = f"Omitted by memory token budget: {', '.join(omission_parts)}."

    rendered_sections: list[str] = []
    for section in sections:
        records = selected[section.memory_type]
        if records:
            rendered_sections.append(
                f"{section.heading}\n" + "\n".join(_entry_text(record) for record in records)
            )
    if not rendered_sections:
        return None

    parts = [_PREAMBLE, *rendered_sections]
    if omission_line:
        parts.append(omission_line)
    parts.append(_FOOTER)
    rendered = "\n\n".join(parts)
    rendered_tokens = _estimate_tokens(rendered)

    total_candidate_tokens = fixed_tokens + sum(
        _estimate_tokens(section.heading)
        + sum(_estimate_tokens(_entry_text(record)) for record in section.records)
        for section in sections
        if section.records
    )
    metrics.observe(metric=memory_metrics.CONTEXT_TOKENS_SELECTED, value=rendered_tokens)
    metrics.observe(
        metric=memory_metrics.CONTEXT_TOKENS_DROPPED,
        value=max(0, total_candidate_tokens - rendered_tokens),
    )
    for memory_type, count in omitted.items():
        metrics.increment(
            metric=memory_metrics.CONTEXT_ITEMS_OMITTED,
            value=count,
            labels={"type": memory_type.value},
        )
    metrics.observe(
        metric=memory_metrics.CONTEXT_TOKEN_SHARE,
        value=(rendered_tokens / budget) if budget else 0,
    )

    return rendered


def format_memory_context_with_ids(
    context: MemoryContext,
    *,
    total_token_budget: int | None = None,
    context_window_tokens: int | None = None,
    metrics: MetricsRecorder | None = None,
) -> FormattedMemoryContext:
    """Format memory and retain only IDs whose complete entry was injected.

    The prompt formatter always emits a selected memory as one exact bullet.
    Matching that complete bullet keeps trace correlation aligned with the
    post-budget prompt, rather than incorrectly recording every candidate.
    """

    rendered = format_memory_context(
        context,
        total_token_budget=total_token_budget,
        context_window_tokens=context_window_tokens,
        metrics=metrics,
    )
    if rendered is None:
        return FormattedMemoryContext(text=None, memory_ids=())
    records = (
        *context.session_memories,
        *context.user_memories,
        *context.semantic_memories,
        *context.research_memories,
    )
    selected_ids = tuple(record.id for record in records if _entry_text(record) in rendered)
    return FormattedMemoryContext(text=rendered, memory_ids=selected_ids)


def with_memory_context(
    prompt_context: PromptContext,
    memory_context_text: str | None,
) -> PromptContext:
    if not memory_context_text:
        return prompt_context
    return prompt_context.model_copy(
        update={"context": f"{memory_context_text}\n\n{prompt_context.context}".strip()},
    )


def extract_memory_context_text(prompt_context: str) -> str | None:
    """Extract the formatter-owned memory block from a persisted prompt."""

    if not prompt_context.startswith(_PREAMBLE):
        return None
    footer_end = prompt_context.find(_FOOTER) + len(_FOOTER)
    if footer_end < len(_FOOTER):
        return None
    return prompt_context[:footer_end]

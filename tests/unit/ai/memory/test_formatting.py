from datetime import UTC, datetime
from uuid import uuid4

from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryContext, MemoryRecord
from app.ai.memory.services.formatting import format_memory_context
from app.ai.runtime.generation.validation.input.token_budget import TokenBudgetValidator
from app.core.settings import settings


def _memory(memory_type: MemoryType, content: str) -> MemoryRecord:
    now = datetime.now(UTC)
    return MemoryRecord(
        id=uuid4(),
        owner_id=uuid4(),
        type=memory_type,
        content=content,
        importance_score=1,
        created_at=now,
        updated_at=now,
    )


def test_formatting_caps_entries_and_labels_session_as_state() -> None:
    now = datetime.now(UTC)
    memory = MemoryRecord(
        id=uuid4(),
        owner_id=uuid4(),
        type=MemoryType.SESSION,
        content="Optimize memory latency",
        importance_score=1,
        created_at=now,
        updated_at=now,
    )
    rendered = format_memory_context(MemoryContext(session_memories=[memory]))
    assert rendered is not None
    assert "Active session state" in rendered


def test_formatting_renders_user_preferences() -> None:
    now = datetime.now(UTC)
    memory = MemoryRecord(
        id=uuid4(),
        owner_id=uuid4(),
        type=MemoryType.USER,
        content="Prefers concise answers",
        importance_score=1,
        created_at=now,
        updated_at=now,
    )
    rendered = format_memory_context(MemoryContext(user_memories=[memory]))
    assert rendered is not None
    assert "Durable user preferences" in rendered
    assert "Prefers concise answers" in rendered


def test_formatting_omits_user_preferences_section_when_empty() -> None:
    rendered = format_memory_context(MemoryContext())
    assert rendered is None


def test_formatting_tells_the_model_the_current_question_wins_over_memory() -> None:
    now = datetime.now(UTC)
    memory = MemoryRecord(
        id=uuid4(),
        owner_id=uuid4(),
        type=MemoryType.USER,
        content="Prefers concise answers",
        importance_score=1,
        created_at=now,
        updated_at=now,
    )
    rendered = format_memory_context(MemoryContext(user_memories=[memory]))
    assert rendered is not None
    assert "current question always wins" in rendered


def test_session_cap_keeps_newest_entries_in_chronological_order(monkeypatch) -> None:
    monkeypatch.setattr(settings, "memory_context_session_max_items", 3)
    memories = [_memory(MemoryType.SESSION, f"session state {index}") for index in range(1, 7)]

    rendered = format_memory_context(MemoryContext(session_memories=memories))

    assert rendered is not None
    assert "session state 1" not in rendered
    assert "session state 2" not in rendered
    assert "session state 3" not in rendered
    assert rendered.index("session state 4") < rendered.index("session state 5")
    assert rendered.index("session state 5") < rendered.index("session state 6")


def test_non_session_caps_still_keep_best_first_entries(monkeypatch) -> None:
    monkeypatch.setattr(settings, "memory_context_semantic_max_items", 2)
    memories = [_memory(MemoryType.SEMANTIC, f"ranked fact {index}") for index in range(1, 5)]

    rendered = format_memory_context(MemoryContext(semantic_memories=memories))

    assert rendered is not None
    assert "ranked fact 1" in rendered
    assert "ranked fact 2" in rendered
    assert "ranked fact 3" not in rendered
    assert "ranked fact 4" not in rendered


def test_total_budget_selects_whole_entries_and_exposes_omissions() -> None:
    memories = [
        _memory(MemoryType.RESEARCH, f"complete finding {index} with supporting detail")
        for index in range(1, 6)
    ]

    rendered = format_memory_context(
        MemoryContext(research_memories=memories), total_token_budget=110
    )

    assert rendered is not None
    assert TokenBudgetValidator._estimate_tokens(rendered) <= 110
    assert "Omitted by memory token budget" in rendered
    assert "research=" in rendered
    assert not rendered.rstrip().endswith("supporting")


def test_model_window_reserves_evidence_and_output_space(monkeypatch) -> None:
    monkeypatch.setattr(settings, "memory_context_reserved_evidence_tokens", 40)
    monkeypatch.setattr(settings, "memory_context_reserved_output_tokens", 30)
    memory = _memory(MemoryType.USER, "prefers concise answers")

    rendered = format_memory_context(
        MemoryContext(user_memories=[memory]),
        total_token_budget=100,
        context_window_tokens=75,
    )

    assert rendered is None


def test_unused_type_share_falls_through_to_other_types(monkeypatch) -> None:
    monkeypatch.setattr(settings, "memory_context_research_token_share", 1)
    memories = [_memory(MemoryType.RESEARCH, f"finding {index}") for index in range(3)]

    rendered = format_memory_context(
        MemoryContext(research_memories=memories), total_token_budget=200
    )

    assert rendered is not None
    assert "finding 0" in rendered

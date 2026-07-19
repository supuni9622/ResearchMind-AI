from datetime import UTC, datetime
from uuid import uuid4

from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryContext, MemoryRecord
from app.ai.memory.services.formatting import format_memory_context
from app.ai.memory.session.state import state_from_user_turn


def test_only_explicit_temporary_state_is_persistable() -> None:
    assert state_from_user_turn(user_message="What is RAG?", source_turn_id="turn") is None
    state = state_from_user_turn(
        user_message="Focus on lowering memory latency", source_turn_id="turn"
    )
    assert state is not None
    assert state.kind == "active_goal"


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

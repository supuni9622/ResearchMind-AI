from datetime import UTC, datetime
from uuid import uuid4

from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryContext, MemoryRecord
from app.ai.memory.services.formatting import format_memory_context


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

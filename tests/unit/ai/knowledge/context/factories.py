"""
Shared test factories for Context Platform unit tests.

Not a test module itself (no test_ prefix) -- imported by the actual
test files under tests/unit/ai/knowledge/context/.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.ai.knowledge.context.models import ContextChunk


def make_context_chunk(
    *,
    chunk_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    filename: str = "paper.pdf",
    owner_id: str = "owner-1",
    chunk_index: int = 0,
    content: str = "some chunk text",
    score: float = 0.5,
    metadata: dict[str, Any] | None = None,
    **overrides: Any,
) -> ContextChunk:
    return ContextChunk(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=document_id or uuid.uuid4(),
        filename=filename,
        owner_id=owner_id,
        chunk_index=chunk_index,
        content=content,
        score=score,
        metadata=metadata or {},
        **overrides,
    )

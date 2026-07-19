"""
Shared prompt-injection helpers (Runtime Memory Injection Pipeline) --
used by every runtime that folds a `MemoryContext` into a
`PromptContext` before generation. `PromptContext.chunks`/`citations`
are always left untouched so citation building and guardrails (both
keyed off chunks) are unaffected by memory; only `context` (the
assembled prompt text) gets the memory block prepended.

Used by `ResearchService` and `app/api/v1/chat.py` -- kept here rather
than duplicated per-runtime since the formatting/merge logic has
nothing runtime-specific about it.
"""

from __future__ import annotations

from app.ai.knowledge.context.models import PromptContext
from app.ai.memory.models import MemoryContext


def format_memory_context(context: MemoryContext) -> str | None:
    sections: list[str] = []

    if context.session_memories:
        lines = "\n".join(f"- {m.content}" for m in context.session_memories)
        sections.append(f"Recent conversation:\n{lines}")

    if context.semantic_memories:
        lines = "\n".join(f"- {m.content}" for m in context.semantic_memories)
        sections.append(f"What we know about this user:\n{lines}")

    if context.research_memories:
        lines = "\n".join(f"- {m.content}" for m in context.research_memories)
        sections.append(f"Relevant prior research findings:\n{lines}")

    if not sections:
        return None

    # Explicit framing (not just a heading) so the model doesn't mistake this
    # block for the current question -- it gets merged into the same
    # `{context}` slot as the retrieved document passages via
    # `with_memory_context()`, right before the actual "Question:" section,
    # so without this the model has no other signal that it's background
    # from a different turn rather than what's being asked right now.
    return (
        "Background memory from prior turns (may be unrelated to the "
        "current question -- use only if directly relevant, otherwise "
        "ignore it entirely):\n"
        + "\n\n".join(sections)
        + "\n\nEnd of background memory. The user's actual question is in "
        "the Question section below."
    )


def with_memory_context(
    prompt_context: PromptContext,
    memory_context_text: str | None,
) -> PromptContext:
    if not memory_context_text:
        return prompt_context

    return prompt_context.model_copy(
        update={
            "context": f"{memory_context_text}\n\n{prompt_context.context}".strip(),
        },
    )

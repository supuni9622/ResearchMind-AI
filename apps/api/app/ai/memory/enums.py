from __future__ import annotations

from enum import StrEnum


class MemoryType(StrEnum):
    """
    PRD §11. Each type routes to a different storage backend -- see
    `create.py` and each type's own `service.py` for the mapping.
    """

    SESSION = "session"

    USER = "user"

    RESEARCH = "research"

    SEMANTIC = "semantic"


class MemoryScopeType(StrEnum):
    PERSONAL = "personal"
    PROJECT = "project"
    # Injected into every context (personal and every project) -- see
    # MemoryService.get_context()'s unconditional GLOBAL fetch for
    # USER/SEMANTIC/RESEARCH types. Owner-scoped only, never project-gated.
    GLOBAL = "global"


class MemoryOperation(StrEnum):
    """
    PRD §12/§13 API surface. Used for logging and metrics labeling
    only -- not persisted on `MemoryRecord` itself.
    """

    REMEMBER = "remember"

    RECALL = "recall"

    SEARCH = "search"

    FORGET = "forget"

    UPDATE = "update"

from enum import StrEnum


class IndexType(StrEnum):
    """
    Supported index types within the Knowledge Platform.

    An IndexType represents a searchable index built from the
    canonical knowledge representation.

    Multiple index types may coexist for the same knowledge.

    Examples
    --------
    - Vector index (semantic retrieval)
    - BM25 index (keyword retrieval)
    - Knowledge graph (future)
    """

    VECTOR = "vector"
    BM25 = "bm25"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class IndexStatus(StrEnum):
    """
    Status of an indexing operation.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IndexOperation(StrEnum):
    """
    Supported indexing operations.
    """

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    REINDEX = "reindex"

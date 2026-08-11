from enum import StrEnum


class DocumentUploadStatus(StrEnum):
    """Lifecycle status of an uploaded document."""

    PENDING = "pending"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentProcessingStatus(StrEnum):
    """
    AI document processing lifecycle.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(StrEnum):
    """
    Who authored a chat Message.
    """

    USER = "user"
    ASSISTANT = "assistant"


class FeedbackRating(StrEnum):
    """
    Thumbs up/down on a single generation (EVALUATION_PLAN.md §16 phase 3).
    """

    UP = "up"
    DOWN = "down"


class FeedbackSurface(StrEnum):
    """
    Which product surface a piece of feedback was left on -- matches the
    `workflow` field in EVALUATION_PLAN.md §3's golden-dataset schema, so
    feedback and golden-set examples can eventually be sliced the same way.
    """

    CHAT = "chat"
    LINEAR_RESEARCH = "linear_research"
    DEEP_RESEARCH = "deep_research"


class EvalScoreSource(StrEnum):
    """
    Where an `eval_scores` row came from (EVALUATION_PLAN.md §14/§16 phase
    6). Only `ONLINE_SAMPLED` is produced today (E5) -- `OFFLINE_BENCHMARK`
    and `HUMAN_FEEDBACK` are declared now so E6/E9's later writers use the
    same closed set from day one instead of each inventing their own
    string.
    """

    ONLINE_SAMPLED = "online_sampled"
    OFFLINE_BENCHMARK = "offline_benchmark"
    HUMAN_FEEDBACK = "human_feedback"

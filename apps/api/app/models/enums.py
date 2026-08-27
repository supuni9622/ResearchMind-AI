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


class MemoryFeedbackSignal(StrEnum):
    """Explicit user assessment of memory's effect on one answer."""

    HELPED = "helped"
    WRONG = "wrong"


class CommentClassification(StrEnum):
    """
    Objective/preference split for a feedback comment (E11,
    EVALUATION_PLAN.md §12/1g). Null on `Feedback`/`EvalScore` whenever
    there's no comment to classify at all (rating-only feedback) -- this
    enum only covers the two possible outcomes of an actual
    classification, not "not classified."
    """

    OBJECTIVE = "objective"
    """Factual quality issue -- "this cited the wrong paper." Feeds the
    shared regression gates (E10's promotion loop can promote it into
    `production_failures`)."""

    PREFERENCE = "preference"
    """Stylistic -- "this answer was too formal." Stays owner-scoped,
    per 1g, never contaminates the shared golden set. Also the fail-safe
    default when classification itself fails (see
    `CommentClassificationService`) -- the conservative direction to
    fail toward, since silently contaminating the shared golden set with
    a misclassified stylistic complaint is worse than under-promoting a
    genuine objective one."""


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


class PromotionCandidateSource(StrEnum):
    """
    Where a `PromotionReview` candidate's signal came from (E10,
    EVALUATION_PLAN.md §3/§15). Mirrors §15's loop: "Free/deterministic
    checks... LLM judges... route to the review queue."
    """

    HUMAN_FEEDBACK = "human_feedback"
    """A thumbs up/down (`Feedback`), optionally with a comment already
    classified `objective` by E11."""

    ONLINE_FLAGGED = "online_flagged"
    """An online-sampled `eval_scores` row (E5) that failed a check or
    was guardrail-flagged -- "E5's flagged-but-scored generations" per
    the tracker's own E10 subtask wording."""


class PromotionDirection(StrEnum):
    """
    "Both directions" (E10's own framing, EVALUATION_PLAN.md §3/§15):
    confirmed genuine failures feed `production_failures`; confirmed
    *good* examples feed `rag_answer_gold` directly, not just harvesting
    the negative side of feedback.
    """

    FAILURE = "failure"
    GOOD = "good"


class PromotionCandidateView(StrEnum):
    """
    Which unreviewed-candidate list `GET .../candidates` returns --
    distinct from `PromotionDirection` (what a *confirmed* row actually
    becomes) because `PREFERENCE` never becomes its own dataset: it's
    thumbs-down feedback E11 classified `preference`, surfaced separately
    so a human reviewer can override the classifier's conservative
    default rather than have it silently vanish from the queue forever.
    Overriding one still confirms with `PromotionDirection.FAILURE`, same
    as the `FAILURE` view.
    """

    GOOD = "good"
    FAILURE = "failure"
    PREFERENCE = "preference"


class PromotionStatus(StrEnum):
    """Outcome of a human review (E10) -- a `PromotionReview` row only
    ever exists for something a human has already acted on; there is no
    "pending" state stored here, since unreviewed candidates are derived
    live from `Feedback`/`eval_scores`, not persisted separately."""

    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class FailureCategory(StrEnum):
    """
    §3's failure-category taxonomy (EVALUATION_PLAN.md), assigned by a
    human reviewer confirming a genuine production failure (E10). Feeds
    the future segment-analysis-by-failure-type slice E9's own tracker
    entry left open pending this taxonomy actually being applied to real
    rows.
    """

    WRONG_CITATION = "wrong_citation"
    HALLUCINATION = "hallucination"
    RETRIEVAL_MISS = "retrieval_miss"
    UNNECESSARY_TOOL_USE = "unnecessary_tool_use"
    ABSTENTION_FAILURE = "abstention_failure"
    WORKFLOW_LOOP = "workflow_loop"
    SCHEMA_VIOLATION = "schema_violation"
    INJECTION_SUCCESS = "injection_success"

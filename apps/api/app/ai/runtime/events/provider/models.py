from __future__ import annotations


class ProviderEventMetadataKeys:
    """
    Well-known `StreamEvent.metadata` keys a provider adapter may attach.

    Constants only, not enforced — providers already put ad-hoc keys into
    `StreamChunk.metadata` today. This exists so future metadata (token
    deltas, finish_reason, tool-call ids) has an agreed-upon name instead
    of every call site inventing its own.
    """

    FINISH_REASON = "finish_reason"
    TOKEN_COUNT_DELTA = "token_count_delta"

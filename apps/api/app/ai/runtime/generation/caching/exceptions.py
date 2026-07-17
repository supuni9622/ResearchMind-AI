from __future__ import annotations


class CachingError(Exception):
    pass


class CacheBackendUnavailableError(
    CachingError,
):
    """
    Raised by a provider constructor when a required backend
    (e.g. the semantic cache's embeddings client) could not be
    configured. Never raised from `get`/`set` — those fail open
    (see provider docstrings) so a transient backend outage degrades
    to a cache miss rather than failing generation.
    """

    pass

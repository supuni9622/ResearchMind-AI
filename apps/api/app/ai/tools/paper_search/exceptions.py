"""Canonical Research Intelligence MCP (paper search) exceptions.

Providers must translate SDK/HTTP/MCP errors into these before they cross
the provider-adapter boundary -- callers never see provider stack traces or
secrets (mirrors `app.ai.tools.web_search.exceptions`).
"""

from __future__ import annotations


class PaperSearchError(Exception):
    """Base error for the Research Intelligence MCP paper-search platform."""


class PaperSearchProviderError(PaperSearchError):
    """A configured provider call failed (transport, protocol, malformed payload)."""


class PaperSearchTimeoutError(PaperSearchError):
    """A provider call exceeded its configured timeout."""


class PaperSearchPolicyError(PaperSearchError):
    """A request was rejected by `PaperSearchPolicy` (disabled, etc.)."""


class PaperSearchProviderUnavailableError(PaperSearchError):
    """No provider is configured/registered (e.g. missing server URL)."""

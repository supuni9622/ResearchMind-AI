"""Canonical Web Search Tool Platform exceptions.

Providers must translate SDK/HTTP errors into these before they cross the
provider-adapter boundary -- callers never see provider stack traces or
secrets (web_search_tool_platform_prd.md §30).
"""

from __future__ import annotations


class WebSearchError(Exception):
    """Base error for the Web Search Tool Platform."""


class WebSearchProviderError(WebSearchError):
    """A configured provider call failed (network, auth, malformed payload)."""


class WebSearchTimeoutError(WebSearchError):
    """A provider call exceeded its configured timeout."""


class WebSearchPolicyError(WebSearchError):
    """A request was rejected by `WebSearchPolicy` (domain, disabled, etc.)."""


class WebSearchBudgetExceededError(WebSearchError):
    """A request would exceed the per-run search-call budget."""


class WebSearchProviderUnavailableError(WebSearchError):
    """No provider is configured/registered (e.g. missing API key)."""

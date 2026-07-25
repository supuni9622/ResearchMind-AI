from __future__ import annotations

from app.ai.tools.web_search.policies import WebSearchPolicy


def test_no_domain_lists_allows_everything() -> None:
    policy = WebSearchPolicy()
    assert policy.domain_allowed("anything.example.com") is True


def test_blocked_domain_rejects_exact_and_subdomains() -> None:
    policy = WebSearchPolicy(blocked_domains=["bad.com"])
    assert policy.domain_allowed("bad.com") is False
    assert policy.domain_allowed("sub.bad.com") is False
    assert policy.domain_allowed("good.com") is True


def test_allowed_domains_is_an_allowlist() -> None:
    policy = WebSearchPolicy(allowed_domains=["good.com"])
    assert policy.domain_allowed("good.com") is True
    assert policy.domain_allowed("sub.good.com") is True
    assert policy.domain_allowed("other.com") is False


def test_blocked_takes_priority_over_allowed() -> None:
    policy = WebSearchPolicy(allowed_domains=["good.com"], blocked_domains=["good.com"])
    assert policy.domain_allowed("good.com") is False

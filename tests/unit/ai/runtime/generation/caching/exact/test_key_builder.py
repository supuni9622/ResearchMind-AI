"""
Unit tests for the L1 Exact Cache key builder.

Covers:
- hash_prompt distinguishes system/user splits, not just concatenation
- hash_context is deterministic and content-sensitive
- hash_schema is order-independent and has a stable sentinel for None
- build_exact_cache_key produces a stable, field-sensitive CacheKey
"""

from __future__ import annotations

from app.ai.runtime.generation.caching.exact.key_builder import (
    build_exact_cache_key,
    hash_context,
    hash_prompt,
    hash_schema,
)
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.routing.enums import RoutingStrategy

from tests.unit.ai.runtime.generation.validation.factories import (
    make_prompt_context,
    make_request,
)


def test_hash_prompt_is_deterministic() -> None:
    first = hash_prompt(system_prompt="sys", user_prompt="user")
    second = hash_prompt(system_prompt="sys", user_prompt="user")

    assert first == second


def test_hash_prompt_distinguishes_system_user_split() -> None:
    """
    "a" + "b\nc" must not hash the same as "a\nb" + "c" — a naive
    concatenation without a separator would collide here.
    """

    first = hash_prompt(system_prompt="a", user_prompt="b\nc")
    second = hash_prompt(system_prompt="a\nb", user_prompt="c")

    assert first != second


def test_hash_context_is_content_sensitive() -> None:
    assert hash_context("context A") != hash_context("context B")
    assert hash_context("same") == hash_context("same")


def test_hash_schema_none_uses_stable_sentinel() -> None:
    assert hash_schema(None) == hash_schema(None)
    assert hash_schema(None) != hash_schema({"type": "object"})


def test_hash_schema_is_key_order_independent() -> None:
    first = hash_schema({"a": 1, "b": 2})
    second = hash_schema({"b": 2, "a": 1})

    assert first == second


def test_build_exact_cache_key_is_sensitive_to_every_field() -> None:
    request = make_request(user_prompt="what color is the sky?")

    baseline = build_exact_cache_key(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        routing_strategy=RoutingStrategy.AUTO,
    )

    different_model = build_exact_cache_key(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5",
        routing_strategy=RoutingStrategy.AUTO,
    )

    different_context = build_exact_cache_key(
        request=make_request(
            user_prompt=request.user_prompt,
            prompt_context=make_prompt_context(context="a different document"),
        ),
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        routing_strategy=RoutingStrategy.AUTO,
    )

    assert baseline.redis_key() != different_model.redis_key()
    assert baseline.redis_key() != different_context.redis_key()


def test_build_exact_cache_key_is_stable_for_identical_requests() -> None:
    request = make_request(user_prompt="what color is the sky?")

    first = build_exact_cache_key(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        routing_strategy=RoutingStrategy.AUTO,
    )

    second = build_exact_cache_key(
        request=request,
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        routing_strategy=RoutingStrategy.AUTO,
    )

    assert first.redis_key() == second.redis_key()

from __future__ import annotations

import hashlib
import json

from app.ai.runtime.generation.caching.models import (
    CacheKey,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
)
from app.ai.runtime.generation.routing.enums import (
    RoutingStrategy,
)

_NONE_SCHEMA_SENTINEL = "-"

#
# Separates system_prompt from user_prompt before hashing so that
# e.g. system="a", user="b\nc" doesn't hash identically to
# system="a\nb", user="c".
#

_PROMPT_SEPARATOR = "\x1f"


def hash_prompt(
    *,
    system_prompt: str | None,
    user_prompt: str,
) -> str:

    canonical = f"{system_prompt or ''}{_PROMPT_SEPARATOR}{user_prompt}"

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def hash_context(
    context: str,
) -> str:
    """
    Hashes the fully-rendered `PromptContext.context` string. Used both
    as part of the L1 `CacheKey` and, independently, as the L2
    Semantic Cache's context isolation discriminator (ADR-027).
    """

    return hashlib.sha256(context.encode("utf-8")).hexdigest()


def hash_schema(
    schema: dict[str, object] | None,
) -> str:

    if schema is None:
        return _NONE_SCHEMA_SENTINEL

    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_exact_cache_key(
    *,
    request: GenerationRequest,
    provider: GenerationProvider,
    model: str,
    routing_strategy: RoutingStrategy | None,
) -> CacheKey:

    return CacheKey(
        provider=provider,
        model=model,
        routing_strategy=routing_strategy,
        prompt_hash=hash_prompt(
            system_prompt=request.system_prompt,
            user_prompt=request.user_prompt,
        ),
        context_hash=hash_context(
            request.prompt_context.context,
        ),
        schema_hash=hash_schema(
            request.output_schema,
        ),
        temperature=request.temperature,
        top_p=request.metadata.get("top_p"),
    )

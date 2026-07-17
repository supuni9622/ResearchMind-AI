"""
L2 Semantic Cache, backed by `langchain_redis.RedisSemanticCache`
(ADR-027 — "leverage LangChain, no custom semantic search
infrastructure") against the dedicated `semantic-cache` RediSearch
instance (see docker-compose.yml; plain Valkey has no vector index
support).

`RedisSemanticCache` implements LangChain's generic `BaseCache`
contract: `alookup(prompt, llm_string)` / `aupdate(prompt, llm_string,
return_val)`. It has no notion of a `GenerationResult` — `prompt` is
embedded for similarity search, and `llm_string` is stored as
opaque metadata and used as a post-retrieval equality filter (it is
NOT part of the vector index, so a similarity search can still surface
a candidate from a different `llm_string` — it's just then filtered
out, never returned as a hit). That filter is where ADR-027's
"semantic cache keys must include context_hash" constraint is
enforced: `discriminator` folds in context_hash plus every other
CacheKey field except prompt/context so a hit can never cross a
provider/model/schema/document boundary. One consequence of this
being a post-filter rather than an index-level one: if the nearest
neighbor overall belongs to a different discriminator, this returns a
miss even when a matching-discriminator entry exists slightly further
away — an accepted precision/recall tradeoff of using the library as
provided rather than building custom filtered vector search.

We store the full `GenerationResult` JSON as the `Generation.text`
payload (rather than plain response text) so a hit can be returned
exactly like an L1 hit. The library's `BaseCache` interface doesn't
surface the matched vector distance on a hit, so `CacheResult.similarity`
is left unset here rather than fabricated.
"""

from __future__ import annotations

import structlog
from app.ai.runtime.generation.caching.interfaces import (
    SemanticCacheProviderInterface,
)
from app.ai.runtime.generation.models import (
    GenerationResult,
)
from langchain_core.outputs import Generation
from langchain_redis import RedisSemanticCache

logger = structlog.get_logger()


class RedisSemanticCacheProvider(
    SemanticCacheProviderInterface,
):
    def __init__(
        self,
        cache: RedisSemanticCache,
    ) -> None:
        self._cache = cache

    async def get(
        self,
        *,
        prompt: str,
        context_hash: str,
        discriminator: str,
    ) -> tuple[GenerationResult, float | None] | None:

        llm_string = self._llm_string(
            context_hash=context_hash,
            discriminator=discriminator,
        )

        try:
            entries = await self._cache.alookup(
                prompt,
                llm_string,
            )
        except Exception:
            logger.exception(
                "caching.semantic.read_failed",
            )
            return None

        if not entries:
            return None

        try:
            result = GenerationResult.model_validate_json(
                entries[0].text,
            )
        except Exception:
            logger.warning(
                "caching.semantic.corrupt_entry",
            )
            return None

        return result, None

    async def set(
        self,
        *,
        prompt: str,
        context_hash: str,
        discriminator: str,
        result: GenerationResult,
    ) -> None:

        llm_string = self._llm_string(
            context_hash=context_hash,
            discriminator=discriminator,
        )

        try:
            await self._cache.aupdate(
                prompt,
                llm_string,
                [
                    Generation(
                        text=result.model_dump_json(),
                    ),
                ],
            )
        except Exception:
            logger.exception(
                "caching.semantic.write_failed",
            )

    @staticmethod
    def _llm_string(
        *,
        context_hash: str,
        discriminator: str,
    ) -> str:
        return f"{context_hash}:{discriminator}"

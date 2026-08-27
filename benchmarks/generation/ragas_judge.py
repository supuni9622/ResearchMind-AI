"""
Ragas LLM-judge wiring (EVALUATION_PLAN.md §7/§16 phase 1).

**Compatibility workaround, read before touching this file's import
order:** `ragas` 0.4.3's `ragas/llms/base.py` unconditionally imports
`from langchain_community.chat_models.vertexai import ChatVertexAI` at
module load time. Current `langchain-community` (0.4.2 -- the only
version resolvable alongside this project's already-pinned
`langsmith>=0.9.7`; older `langchain-community` releases require
`langsmith<0.4` and are unresolvable here) removed that submodule
entirely -- Vertex AI support moved to the standalone
`langchain-google-vertexai` package, which this project doesn't use or
need (Gemini is used via the `google-genai` SDK directly, not through a
LangChain Vertex AI integration). Confirmed 2026-08-11 against a real
`uv add ragas` resolution: `import ragas` fails outright with
`ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'`
with no way to avoid it via version pinning, since `ragas` imports it
from its own top-level `__init__.py` regardless of which ragas submodule
a caller actually needs.

The fix below is the standard, narrow workaround for this class of
problem: register a harmless placeholder module in `sys.modules` under
that exact dotted path *before* `ragas` is imported anywhere in the
process, so its unconditional (and, for this project, irrelevant) import
succeeds. This must run before the first `import ragas` anywhere in the
process -- every other module in this codebase that needs `ragas` should
import it (or import types) through this module, not `import ragas`
directly, so the stub is guaranteed to already be registered. Remove
this workaround once a `ragas` release fixes the unconditional import
(tracked nowhere upstream as of this writing -- re-check on any `ragas`
version bump).
"""

from __future__ import annotations

import sys
import types

if "langchain_community.chat_models.vertexai" not in sys.modules:
    _vertexai_stub = types.ModuleType("langchain_community.chat_models.vertexai")

    class _UnusedChatVertexAI:  # pragma: no cover - never instantiated
        """Placeholder only -- this project does not use Vertex AI."""

    _vertexai_stub.ChatVertexAI = _UnusedChatVertexAI  # type: ignore[attr-defined]
    sys.modules["langchain_community.chat_models.vertexai"] = _vertexai_stub

from dataclasses import dataclass  # noqa: E402

from app.core.settings import settings  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from ragas.embeddings.base import BaseRagasEmbedding, embedding_factory  # noqa: E402
from ragas.llms import llm_factory  # noqa: E402
from ragas.metrics.collections import (  # noqa: E402
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

DEFAULT_JUDGE_MODEL = "gpt-4o-mini"
DEFAULT_JUDGE_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_JUDGE_MAX_TOKENS = 2048


@dataclass(frozen=True)
class RagasJudge:
    """The four RAG-suite metrics (EVALUATION_PLAN.md §7), pre-wired to one LLM/embedding client."""

    faithfulness: Faithfulness
    answer_relevancy: AnswerRelevancy
    context_precision: ContextPrecision
    context_recall: ContextRecall


def build_openai_ragas_judge(
    *,
    model: str = DEFAULT_JUDGE_MODEL,
    embedding_model: str = DEFAULT_JUDGE_EMBEDDING_MODEL,
) -> RagasJudge:
    """
    Build a `RagasJudge` backed by OpenAI -- the best-supported ragas
    provider path. Raises if no OpenAI key is configured rather than
    silently falling back to a different provider, since judge identity
    (which model scored an example) matters for reproducibility.
    """

    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required to build the Ragas judge "
            "(EVALUATION_PLAN.md §7 LLM-judge scoring)."
        )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    llm = llm_factory(
        model,
        provider="openai",
        client=client,
        max_tokens=DEFAULT_JUDGE_MAX_TOKENS,
    )
    embeddings = embedding_factory(provider="openai", model=embedding_model, client=client)
    # `embedding_factory` is a unified legacy+modern factory, so its
    # static return type is a union -- passing `client=` always selects
    # the modern interface at runtime (per its own docstring), which is
    # always `BaseRagasEmbedding`. Asserted, not cast, so a future ragas
    # release changing that behavior fails loudly here instead of
    # silently passing a legacy-interface object to `AnswerRelevancy`.
    assert isinstance(embeddings, BaseRagasEmbedding)

    return RagasJudge(
        faithfulness=Faithfulness(llm=llm),
        answer_relevancy=AnswerRelevancy(llm=llm, embeddings=embeddings),
        context_precision=ContextPrecision(llm=llm),
        context_recall=ContextRecall(llm=llm),
    )


__all__ = [
    "DEFAULT_JUDGE_EMBEDDING_MODEL",
    "DEFAULT_JUDGE_MODEL",
    "DEFAULT_JUDGE_MAX_TOKENS",
    "RagasJudge",
    "build_openai_ragas_judge",
]

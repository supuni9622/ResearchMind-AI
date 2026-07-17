"""
LangChain-backed compression provider.

Uses `ContextualCompressionRetriever` + `LLMChainExtractor` to ask an LLM
to extract only the parts of each chunk relevant to the query, dropping
chunks with nothing relevant left. Chunk metadata (citations, scores,
parent links, risk flags) is carried over unchanged -- only `content` is
replaced with the extracted text.
"""

from __future__ import annotations

import asyncio
from time import perf_counter

import structlog
from app.ai.knowledge.context.compression.enums import (
    CompressionStrategy,
)
from app.ai.knowledge.context.compression.exceptions import (
    CompressionProviderError,
    CompressionTimeoutError,
)
from app.ai.knowledge.context.compression.interfaces import (
    CompressionProvider,
)
from app.ai.knowledge.context.compression.models import (
    CompressionRequest,
    CompressionResult,
    CompressionStatistics,
)
from app.ai.knowledge.context.models import (
    ContextChunk,
)
from app.core.settings import (
    settings,
)
from langchain_classic.retrievers import (
    ContextualCompressionRetriever,
)
from langchain_classic.retrievers.document_compressors import (
    LLMChainExtractor,
)
from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import (
    Document,
)
from langchain_core.language_models import (
    BaseLanguageModel,
)
from langchain_core.retrievers import (
    BaseRetriever,
)
from pydantic import ConfigDict

logger = structlog.get_logger()

_METADATA_CHUNK_ID_KEY = "chunk_id"

DEFAULT_MODEL_NAME = "gpt-5-nano"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TIMEOUT_SECONDS = 30.0


class _StaticDocumentRetriever(BaseRetriever):
    """
    Trivial retriever that always returns a fixed set of documents.

    `ContextualCompressionRetriever` wraps a base retriever, but this
    provider receives an already-retrieved/reranked chunk list -- there's
    no retrieval step left to perform. This adapts that fixed list into
    the retriever interface LangChain's compression machinery expects.
    """

    documents: list[Document]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        return self.documents

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        return self.documents


class LangChainCompressionProvider(
    CompressionProvider,
):
    """
    Query-aware compression backed by LangChain's contextual compression
    retriever.
    """

    def __init__(
        self,
        llm: BaseLanguageModel | None = None,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        # Injected explicitly (tests, alternate models) or lazily built
        # from settings on first use -- kept lazy so constructing this
        # provider never requires an API key to be configured.
        self._llm = llm

        self._timeout_seconds = timeout_seconds

    async def compress(
        self,
        request: CompressionRequest,
    ) -> CompressionResult:

        chunks = request.chunks

        if not chunks:
            return CompressionResult(
                strategy=CompressionStrategy.LANGCHAIN_CONTEXTUAL,
                chunks=[],
                statistics=CompressionStatistics(),
            )

        query = (request.query or "").strip()

        if not query:
            raise CompressionProviderError(
                "LangChainCompressionProvider requires CompressionRequest.query -- "
                "ContextualCompressionRetriever is query-aware."
            )

        started = perf_counter()

        logger.info(
            "context.compression.langchain.started",
            provider="langchain",
            strategy=CompressionStrategy.LANGCHAIN_CONTEXTUAL.value,
            documents_before=len(chunks),
        )

        chunks_by_id = {str(chunk.chunk_id): chunk for chunk in chunks}
        documents = self._to_documents(chunks)

        try:
            compressed_documents = await asyncio.wait_for(
                self._compress_documents(query, documents),
                timeout=self._timeout_seconds,
            )

        except TimeoutError as exc:
            logger.warning(
                "context.compression.langchain.failed",
                provider="langchain",
                reason="timeout",
                timeout_seconds=self._timeout_seconds,
            )

            raise CompressionTimeoutError(
                f"LangChain compression exceeded {self._timeout_seconds}s"
            ) from exc

        except CompressionProviderError:
            raise

        except Exception as exc:
            logger.warning(
                "context.compression.langchain.failed",
                provider="langchain",
                reason="provider_error",
                error_type=type(exc).__name__,
                error=str(exc),
            )

            raise CompressionProviderError(str(exc)) from exc

        compressed_chunks = self._restore_chunks(compressed_documents, chunks_by_id)

        duration_ms = (perf_counter() - started) * 1000

        original_tokens = self._estimate_tokens(chunks)
        compressed_tokens = self._estimate_tokens(compressed_chunks)

        statistics = CompressionStatistics(
            original_chunks=len(chunks),
            compressed_chunks=len(compressed_chunks),
            removed_chunks=(len(chunks) - len(compressed_chunks)),
            estimated_saved_tokens=max(original_tokens - compressed_tokens, 0),
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            duration_ms=duration_ms,
        )

        logger.info(
            "context.compression.langchain.completed",
            provider="langchain",
            strategy=CompressionStrategy.LANGCHAIN_CONTEXTUAL.value,
            documents_before=statistics.original_chunks,
            documents_after=statistics.compressed_chunks,
            tokens_saved=statistics.estimated_saved_tokens,
            duration_ms=duration_ms,
        )

        return CompressionResult(
            strategy=CompressionStrategy.LANGCHAIN_CONTEXTUAL,
            chunks=compressed_chunks,
            statistics=statistics,
        )

    # ==================================================================
    # Internals
    # ==================================================================

    async def _compress_documents(
        self,
        query: str,
        documents: list[Document],
    ) -> list[Document]:

        retriever = self._create_contextual_retriever(documents)

        return list(await retriever.ainvoke(query))

    def _create_compressor(self) -> LLMChainExtractor:

        return LLMChainExtractor.from_llm(self._get_llm())

    def _create_contextual_retriever(
        self,
        documents: list[Document],
    ) -> ContextualCompressionRetriever:

        return ContextualCompressionRetriever(
            base_compressor=self._create_compressor(),
            base_retriever=_StaticDocumentRetriever(documents=documents),
        )

    def _get_llm(self) -> BaseLanguageModel:

        if self._llm is None:
            self._llm = self._build_default_llm()

        return self._llm

    @staticmethod
    def _build_default_llm() -> BaseLanguageModel:

        if not settings.openai_api_key:
            raise CompressionProviderError(
                "No LLM injected and OPENAI_API_KEY is not configured -- "
                "LangChainCompressionProvider needs one to build LLMChainExtractor."
            )

        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr

        return ChatOpenAI(
            model=DEFAULT_MODEL_NAME,
            temperature=DEFAULT_TEMPERATURE,
            api_key=SecretStr(settings.openai_api_key),
        )

    @staticmethod
    def _to_documents(
        chunks: list[ContextChunk],
    ) -> list[Document]:

        return [
            Document(
                page_content=chunk.content,
                metadata={_METADATA_CHUNK_ID_KEY: str(chunk.chunk_id)},
            )
            for chunk in chunks
        ]

    @staticmethod
    def _restore_chunks(
        documents: list[Document],
        chunks_by_id: dict[str, ContextChunk],
    ) -> list[ContextChunk]:
        """
        Rehydrate compressed documents back into ContextChunks.

        Every field except `content` -- citations, scores, parent links,
        risk metadata, arbitrary metadata -- is carried over unchanged
        from the original chunk, keyed by chunk_id.
        """

        restored: list[ContextChunk] = []

        for document in documents:
            chunk_id = document.metadata.get(_METADATA_CHUNK_ID_KEY)
            original = chunks_by_id.get(chunk_id) if chunk_id else None

            if original is None:
                continue

            restored.append(
                original.model_copy(
                    update={"content": document.page_content},
                )
            )

        return restored

    @staticmethod
    def _estimate_tokens(
        chunks: list[ContextChunk],
    ) -> int:

        return sum(len(chunk.content) // 4 for chunk in chunks)

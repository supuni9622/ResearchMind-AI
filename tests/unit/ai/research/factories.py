"""
Shared test factories for Research Service unit tests.

Not a test module itself (no test_ prefix) -- imported by the actual
test files under tests/unit/ai/research/.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from app.ai.knowledge.context.citations.models import Citation
from app.ai.knowledge.context.models import (
    ContextChunk,
    ContextResult,
    ContextStatistics,
    PromptContext,
)
from app.ai.knowledge.retrieval.enums import (
    RetrievalOperation,
    RetrievalProvider,
    RetrievalStrategy,
)
from app.ai.knowledge.retrieval.models import (
    RetrievalExecution,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStatistics,
    RetrievedChunk,
)
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
)


def make_retrieved_chunk(
    *,
    document_id: UUID | None = None,
    chunk_id: UUID | None = None,
    filename: str = "paper.pdf",
    owner_id: str = "owner-1",
    score: float = 0.9,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id or uuid4(),
        document_id=document_id or uuid4(),
        filename=filename,
        owner_id=owner_id,
        chunk_index=0,
        content="RAG combines retrieval with generation.",
        score=score,
    )


def make_retrieval_result(
    *,
    query: str = "How does RAG work?",
    chunks: list[RetrievedChunk] | None = None,
) -> RetrievalResult:
    resolved_chunks = chunks if chunks is not None else [make_retrieved_chunk()]

    return RetrievalResult(
        query=RetrievalQuery(query=query, top_k=10, filters={}),
        execution=RetrievalExecution(operation=RetrievalOperation.SEARCH),
        statistics=RetrievalStatistics(
            provider=RetrievalProvider.QDRANT,
            strategy=RetrievalStrategy.HYBRID,
            duration_ms=12.0,
            returned_chunks=len(resolved_chunks),
        ),
        chunks=resolved_chunks,
    )


def make_context_chunk(
    *,
    document_id: UUID | None = None,
    chunk_id: UUID | None = None,
    filename: str = "paper.pdf",
    score: float = 0.9,
    page_numbers: list[int] | None = None,
    citation_id: str | None = "c1",
) -> ContextChunk:
    return ContextChunk(
        chunk_id=chunk_id or uuid4(),
        document_id=document_id or uuid4(),
        filename=filename,
        owner_id="owner-1",
        chunk_index=0,
        content="RAG combines retrieval with generation.",
        score=score,
        page_numbers=page_numbers or [],
        citation_id=citation_id,
    )


def make_citation(
    *,
    citation_id: str = "c1",
    document_id: UUID | None = None,
    filename: str = "paper.pdf",
) -> Citation:
    return Citation(
        citation_id=citation_id,
        filename=filename,
        document_id=document_id or uuid4(),
    )


def make_context_result(
    *,
    chunks: list[ContextChunk] | None = None,
    citations: list[Citation] | None = None,
    context: str = "RAG combines retrieval with generation.",
) -> ContextResult:
    resolved_chunks = chunks if chunks is not None else [make_context_chunk()]
    resolved_citations = citations if citations is not None else [make_citation()]

    return ContextResult(
        prompt_context=PromptContext(
            context=context,
            chunks=resolved_chunks,
            citations=resolved_citations,
        ),
        statistics=ContextStatistics(
            input_chunks=len(resolved_chunks),
            output_chunks=len(resolved_chunks),
        ),
    )


def make_generation_request(*, user_prompt: str = "How does RAG work?") -> GenerationRequest:
    return GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt=user_prompt,
    )


def make_generation_result(
    *,
    content: str = "RAG retrieves relevant context before generating an answer.",
    provider: GenerationProvider = GenerationProvider.GROQ,
    model: str = "test-model",
) -> GenerationResult:
    return GenerationResult(
        request=make_generation_request(),
        execution=GenerationExecution(),
        statistics=GenerationStatistics(provider=provider, model=model),
        provider=provider,
        model=model,
        content=content,
    )

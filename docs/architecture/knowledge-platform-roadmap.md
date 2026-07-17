# Knowledge Platform Roadmap

**Status:** Living Architecture Document

---

# Overview

The Knowledge Platform is the core AI infrastructure of ResearchMind.

Its responsibility is to transform raw documents into high-quality,
retrievable knowledge that powers search, retrieval, reasoning,
question answering, citations, and future AI agents.

The platform is intentionally designed as a collection of independent,
replaceable subsystems connected through canonical ResearchMind models.

Every subsystem owns a single responsibility and communicates using
framework-independent contracts.

---

# Architectural Principles

The Knowledge Platform follows several long-term engineering principles.

## Canonical Models

Every stage produces canonical ResearchMind models.

Examples include:

- ProcessedDocument
- Chunk
- ChunkArtifact
- Embedding
- RetrievalResult

These models are owned by ResearchMind and never expose framework-specific
types.

---

## Provider-Based Architecture

External AI frameworks are implementation details.

Examples include:

- Docling
- LangChain
- LangGraph
- Voyage AI
- OpenAI SDK

Every framework is encapsulated behind providers or adapters.

The remainder of the application communicates exclusively through
ResearchMind models.

---

## Immutable Artifacts

Each platform produces immutable artifacts.

Examples include:

- processed_document.json
- chunks.json
- embeddings.json

Artifacts are versioned and written to Amazon S3.

Artifacts are never modified after creation.

This principle is no longer unique to the ingestion side described in this document. As of Milestone 3.10 (`artifacts_platform_prd.md`), a new centralized Artifact Platform (`apps/api/app/ai/artifacts/`) extends it to the AI Runtime side — canonical, immutable, versioned, policy-gated persistence for Generation, Streaming, and Conversation executions, with Session/Research/Agent/Evaluation artifacts built but not yet wired to a live runtime. See `PROJECT_STATUS.md` Milestone 3.10 for full detail.

---

## Independent Platforms

Each subsystem is independently replaceable.

Examples:

Processing can evolve independently from Chunking.

Chunking can evolve independently from Embeddings.

Embeddings can evolve independently from Retrieval.

---

# Platform Roadmap

The Knowledge Platform is implemented incrementally.

---

# Phase 2.1 — Processing Platform

**Status:** ✅ Completed

Responsibilities

- Parse uploaded documents
- Produce canonical ProcessedDocument
- Extract structured Markdown
- Generate normalized text
- Generate semantic document blocks
- Enrich metadata
- Enrich document statistics
- Persist processing artifacts

Primary Output

```
ProcessedDocument
```

Artifacts

```
processing/

    processed_document.json

    parsed.md

    parsed.txt
```

---

# Phase 2.2 — Chunking Platform

**Status:** 🚧 In Progress

Responsibilities

- Transform processed documents into retrieval-ready chunks
- Preserve provenance
- Generate chunk statistics
- Generate chunk artifacts
- Support multiple chunking strategies

Architecture

```
ChunkingService

↓

ChunkingRegistry

↓

ChunkingProvider

↓

ChunkArtifact
```

Implemented Strategies

- ✅ Fixed Chunking
- ✅ Recursive Chunking (LangChain)
- 🚧 Markdown Chunking

Planned Strategies

- Hierarchical
- Semantic
- LLM
- Adaptive

Artifacts

```
chunking/

    fixed/

        artifact-id/

            chunks.json

    recursive/

        artifact-id/

            chunks.json

    markdown/

        artifact-id/

            chunks.json
```

---

# Phase 2.3 — Embedding Platform

**Status:** Planned

Responsibilities

- Transform chunks into vector embeddings
- Support multiple embedding providers
- Produce canonical embedding artifacts
- Support experimentation
- Remain independent of vector databases

Planned Providers

- Voyage AI
- OpenAI
- Sentence Transformers
- BGE
- Instructor

Artifacts

```
embeddings/

    voyage/

        artifact-id/

            embeddings.json

    openai/

        artifact-id/

            embeddings.json
```

---

# Phase 2.4 — Vector Store Platform

**Status:** Planned

Responsibilities

- Persist embeddings
- Maintain vector indexes
- Support multiple vector stores

Planned Providers

- Qdrant
- pgvector
- Chroma
- Pinecone

---

# Phase 2.5 — Retrieval Platform

**Status:** Planned

Responsibilities

- Semantic retrieval
- Hybrid retrieval
- Metadata filtering
- Citation retrieval

Planned Features

- Top-K Retrieval
- Hybrid Search
- Parent Retrieval
- Context Expansion
- Multi-stage Retrieval

---

# Phase 2.6 — Reranking Platform

**Status:** Planned

Responsibilities

- Improve retrieval quality
- Reorder retrieved chunks
- Support multiple reranking providers

Examples

- Cohere
- Voyage
- Jina

---

# Phase 2.7 — Conversation Memory

**Status:** Planned

Responsibilities

- Conversation history
- Long-term memory
- Session context
- User context

---

# Phase 2.8 — Knowledge Service

**Status:** Planned

Responsibilities

Provide a unified API over the entire Knowledge Platform.

Examples

- Retrieve Knowledge
- Retrieve Context
- Build AI Context
- Citation Resolution

---

# Runtime Evaluation

Runtime Evaluation evolves together with each platform.

Its responsibility is to observe the configured production pipeline.

It never performs experimentation.

As each platform matures, additional runtime metrics become available.

Examples

Processing

- Processing latency
- Parsing statistics

Chunking

- Chunk count
- Average chunk size
- Chunking latency

Embedding

- Embedding latency
- Cost
- Dimensions

Retrieval

- Retrieval latency
- Retrieved chunk count

LLM

- Prompt tokens
- Completion tokens
- Cost
- Groundedness

Runtime Evaluation is always enabled and has minimal overhead.

---

# Experimentation

Experimentation is intentionally separate from the production pipeline.

Purpose

Evaluate alternative AI strategies without affecting users.

Examples

Chunking

- Fixed
- Recursive
- Markdown
- Semantic

Embedding

- Voyage
- OpenAI
- BGE

Retrieval

- Hybrid
- Dense
- Sparse

Experimentation executes asynchronously using background workers.

It may be disabled entirely in production.

---

# Engineering Benchmarks

ResearchMind maintains benchmark datasets inside the repository.

Purpose

- Prevent regressions
- Compare implementations
- Validate new providers

Benchmark datasets include

- Research papers
- Technical documentation
- API documentation
- Markdown-heavy documents

These datasets are used during development and continuous integration.

---

# Long-Term Vision

The Knowledge Platform becomes the foundation for every future AI
capability within ResearchMind.

Future consumers include

- Retrieval-Augmented Generation (RAG)
- AI Research Assistants
- Knowledge Search
- Citation Engine
- Multi-Agent Systems
- Agentic Workflows
- Evaluation Platform
- Experimentation Platform

The platform remains modular, provider-driven, framework-independent,
and fully extensible as new AI technologies emerge.

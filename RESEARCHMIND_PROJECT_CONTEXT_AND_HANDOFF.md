# ResearchMind AI — Project Context & Engineering Handoff

**Version:** 1.0

**Last Updated:** 2026-07-07

---

# Project Vision

ResearchMind is a **production-grade AI Engineering Platform**, not a demo Retrieval-Augmented Generation (RAG) application.

The goal is to build a modular AI platform where every AI capability evolves independently while participating in a stable, production-ready AI pipeline.

The platform is intentionally designed around independent engineering capabilities instead of frameworks.

Frameworks such as LangChain, Docling, Sentence Transformers, Voyage AI, OpenAI, ChromaDB, Qdrant, Pinecone, etc. are treated as implementation details hidden behind provider abstractions.

ResearchMind should remain:

- Production-ready
- Framework independent
- Modular
- Provider driven
- Experimentation friendly
- Maintainable
- Extensible

The long-term vision is to evolve ResearchMind into a complete AI Engineering Platform supporting:

- Enterprise RAG
- Research Assistant
- Agentic AI
- Multi-Agent Workflows
- MCP Ecosystem
- AI Experimentation
- Engineering Observability

---

# Collaboration Philosophy

This project spans many ChatGPT conversations.

Every conversation should continue from the previous milestone without redesigning previously completed architecture.

Implementation should always prioritize production engineering over demonstrations.

---

## Code Generation Rules

Always provide

- Complete files
- Exact file paths
- Production-quality implementations
- No placeholder implementations
- No partial snippets unless explicitly requested

When modifying an existing file:

- Clearly identify the file
- Explain exactly where changes belong
- Preserve existing architecture

If an implementation depends on existing code that has not been shared, request the file before generating code.

---

## Engineering Philosophy

ResearchMind follows several long-term engineering principles.

### Production First

The project is built as if it will eventually be deployed in production.

Avoid demo shortcuts.

---

### Vertical Slice Development

Each milestone is implemented as a complete vertical slice.

Typical workflow:

```
Architecture

↓

Models

↓

Providers

↓

Registry

↓

Factory

↓

Service

↓

Integration

↓

Manual Verification

↓

Documentation
```

A milestone is not considered complete until documentation has been updated.

---

### Avoid Premature Abstractions

Only introduce abstractions when they solve existing duplication or complexity.

Do not introduce architecture based on future speculation.

---

### Framework Independence

External AI frameworks never leak outside provider implementations.

Business services should never depend directly on:

- LangChain
- OpenAI SDK
- Voyage SDK
- ChromaDB SDK
- Sentence Transformers

Instead they depend on canonical interfaces.

---

### Canonical Models

Every AI platform communicates through canonical ResearchMind models.

External SDK objects never leave providers.

---

### Canonical Artifacts

Every AI platform consumes the artifact produced by the previous platform and produces exactly one artifact for downstream platforms.

Example

```
ProcessedDocument

↓

ChunkArtifact

↓

EmbeddingArtifact

↓

VectorStoreArtifact

↓

RetrievalArtifact

↓

RerankingArtifact
```

---

### Documentation First-Class Citizen

Every milestone produces:

- Architecture documentation
- Engineering Journal
- ADRs (only when architecture changes)
- Roadmap updates
- Project Status updates

Documentation is considered part of implementation.

---

# AI Engineering Platform

ResearchMind is composed of several independent platforms.

```
                    AI Engineering Platform

                               │

      ┌────────────────────────┼────────────────────────┐

      │                        │                        │

 Identity Platform     Knowledge Platform     Observability Platform

                               │

                     Processing

                     Chunking

                     Embedding

                     Vector Store

                     Retrieval

                     Reranking

                               │

                     Research API

                               │

                     Chat Platform

                               │

                     Citation Platform

                               │

                     Research Engine

                               │

                     Agentic AI Platform

                               │

                  Experimentation Platform

                               │

                  Engineering Benchmark Platform

                               │

                       MCP Ecosystem
```

Every platform owns one responsibility.

---

# Canonical Knowledge Pipeline

Current pipeline

```
Upload

↓

Processing

↓

ProcessedDocument

↓

Chunking

↓

ChunkArtifact

↓

Embedding

↓

EmbeddingArtifact
```

Future pipeline

```
Upload

↓

Processing

↓

ProcessedDocument

↓

Chunking

↓

ChunkArtifact

↓

Embedding

↓

EmbeddingArtifact

↓

Vector Store

↓

VectorStoreArtifact

↓

Retrieval

↓

RetrievalArtifact

↓

Reranking

↓

RerankingArtifact

↓

Research API

↓

Chat

↓

Citations
```

---

# Core Engineering Patterns

ResearchMind consistently follows these patterns across every platform.

## Provider Pattern

External implementations remain hidden.

Examples

- OpenAI
- Voyage AI
- Sentence Transformers
- ChromaDB

---

## Registry Pattern

Services never instantiate providers directly.

Registries own provider lookup.

---

## Factory Pattern

Factories construct canonical models.

Providers never construct canonical domain models directly.

---

## Builder Pattern

Builders create persistence artifacts.

Examples

- ChunkArtifactBuilder
- EmbeddingArtifactBuilder

---

## Composition Roots

Every platform owns a `create.py`.

Composition roots assemble dependencies.

Business logic never performs dependency construction.

---

## Dependency Injection

Dependencies are injected through constructors.

Avoid service locators and global singletons.

---

# Project Folder Structure

High-level architecture

```
apps/

    api/

        app/

            ai/

                identity/

                knowledge/

                    processing/

                    chunking/

                    embeddings/

                    vector_store/

                    retrieval/

                    reranking/

                observability/

            api/

            core/

            db/

benchmarks/

docs/

tests/
```

The folder structure reflects platform boundaries rather than framework boundaries.

---

# Major Architectural Decisions

Several long-term architectural decisions have been established.

## ADR-008

Canonical AI Platform Pipeline

Every platform consumes exactly one canonical artifact and produces exactly one canonical artifact.

---

## Composition Roots

Platforms are assembled using `create.py`.

Factories construct models.

Composition roots construct applications.

---

## Runtime Metrics

Observability remains separate from business logic.

Business platforms never collect engineering metrics directly.

---

## Multi-Provider Strategy

Every AI capability supports multiple providers behind stable interfaces.

Examples

Embedding Platform

- Sentence Transformers
- Voyage AI
- OpenAI

Future Vector Store Platform

- ChromaDB
- pgvector
- Pinecone
- Qdrant

---

# Current Project Status

Completed

✅ Identity Platform

✅ Upload Platform

✅ Processing Platform

✅ Chunking Platform

✅ Embedding Platform

✅ Runtime Metrics Foundation

Deferred

- Advanced Observability
- Benchmark Expansion
- Experimentation Platform

Current Focus

**Phase 2.5 — Vector Store Platform**

The Embedding Platform is considered stable and frozen unless bugs are discovered.

---

# Platform Status

This section summarizes the implementation status of every major platform within ResearchMind.

---

# Phase 1 — Identity Platform

**Status:** ✅ Complete

## Completed

- Configuration
- Database foundation
- SQLAlchemy models
- Alembic migrations
- Internal User domain
- Repository pattern
- Service layer
- Authentication abstraction
- AWS Cognito integration
- JWT validation
- Authorization foundation
- Current user dependency

The Identity Platform is considered production-ready and stable.

---

# Phase 2 — Knowledge Platform

The Knowledge Platform is responsible for transforming raw documents into structured, searchable knowledge.

---

# Milestone 2.1 — Upload Platform

**Status:** ✅ Complete

## Responsibilities

- Upload documents
- Validate files
- Persist originals
- Generate document metadata
- Store artifacts

## Implemented

- Upload API
- SHA-256 duplicate detection
- Amazon S3 integration
- Storage abstraction
- Upload lifecycle
- Storage key generation

---

# Milestone 2.2 — Processing Platform

**Status:** ✅ Complete

## Responsibilities

Convert uploaded files into canonical processed documents.

## Architecture

```
Upload

↓

ProcessingService

↓

Parser

↓

Metadata

↓

Statistics

↓

ProcessedDocument
```

---

## Processing Foundation

Implemented

- ProcessingService
- DocumentProcessingService
- Queue processing
- Worker
- Retry
- Dead Letter Queue
- Lifecycle management

---

## Parser Platform

Implemented

- Parser abstraction
- Registry
- Docling provider

Future providers can be added without modifying the ProcessingService.

---

## Metadata Platform

Implemented

- Metadata registry
- PDF metadata provider
- Language detection

---

## Statistics Platform

Implemented

- Word count
- Character count
- Paragraph count
- Heading count
- Table count
- Figure count
- Page count

---

## Processing Artifacts

Generated automatically

```
processed_document.json

parsed.md

parsed.txt
```

Artifacts are persisted to Amazon S3.

---

# Milestone 2.3 — Chunking Platform

**Status:** ✅ Complete

The Chunking Platform transforms canonical processed documents into canonical chunks.

---

## Architecture

```
ProcessedDocument

↓

ChunkingService

↓

ChunkingRegistry

↓

ChunkingProvider

↓

ChunkFactory

↓

ChunkArtifactBuilder

↓

ChunkArtifactWriter
```

---

## Providers

Implemented

- Fixed Chunking
- Recursive Chunking
- Markdown Chunking

Future providers

- Semantic
- Hierarchical
- Adaptive
- LLM Chunking

---

## Canonical Models

Implemented

- Chunk
- ChunkMetadata
- ChunkStatistics
- Provenance
- ExperimentMetadata

---

## Artifacts

```
ChunkArtifact

↓

chunks.json
```

---

## Benchmark Platform

Implemented

- Benchmark framework
- Registry
- Runner
- Dataset loader
- Markdown reports
- JSON reports
- Chunking benchmark

The benchmark framework has intentionally been frozen until the core AI platform is completed.

---

# Milestone 2.4 — Embedding Platform

**Status:** ✅ Complete

The Embedding Platform converts canonical chunks into canonical embeddings.

---

## Architecture

```
ChunkArtifact

↓

EmbeddingService

↓

EmbeddingRegistry

↓

EmbeddingProvider

↓

EmbeddingFactory

↓

EmbeddingArtifactBuilder

↓

EmbeddingArtifactWriter
```

---

## Providers

Implemented

### Local

- Sentence Transformers

### Cloud

- Voyage AI
- OpenAI

Future

- BGE
- Instructor
- Nomic

No additional providers are planned until the core RAG pipeline is completed.

---

## Shared Batching

One reusable batching utility was introduced.

```
EmbeddingBatcher
```

Responsibilities

- Stream batches lazily
- Provider-independent batching
- Configurable batch sizes

Default configuration

| Provider | Batch Size |
|-----------|-----------:|
| Sentence Transformers | 64 |
| Voyage AI | 32 |
| OpenAI | 128 |

This batching infrastructure is shared by every embedding provider.

---

## Canonical Models

Implemented

- Embedding
- EmbeddingVector
- ProviderMetadata
- Provenance
- Statistics
- ExperimentMetadata

SDK-specific models never leave providers.

---

## Artifact Platform

Implemented

```
EmbeddingArtifact

↓

embeddings.json
```

Storage layout

```
embeddings/

    {provider}/

        {artifact_id}/

            embeddings.json
```

---

## Processing Integration

Current production pipeline

```
Processing

↓

Chunking

↓

Embedding
```

The ProcessingService orchestrates every AI stage.

Each stage remains independent.

---

## Manual Verification

Successfully verified

- Sentence Transformers
- Voyage AI
- OpenAI
- Shared batching
- Runtime metrics
- Canonical models
- Artifact generation
- Amazon S3 persistence
- Configuration fingerprints
- Provider metadata

The Embedding Platform is considered complete.

---

# Runtime Metrics Foundation

**Status:** ✅ Complete

Rather than implementing a full Observability Platform immediately, the project introduced a lightweight Runtime Metrics Foundation.

Purpose

Provide standardized engineering metrics while avoiding unnecessary complexity.

---

## Architecture

```
RuntimeMetricsCollector

↓

ProcessingService

↓

RuntimeReportGenerator
```

---

## Current Metrics

Every pipeline stage exposes

- Execution duration
- Stage duration
- Peak memory
- Artifact size
- Provider
- Provider version

Example report

```
Processing Pipeline Metrics

Processing

Chunking

Embedding

Peak Memory

Pipeline Duration
```

---

## Why It Exists

Runtime metrics provide immediate engineering visibility while allowing advanced observability to remain a future enhancement.

---

# Observability Platform

**Status:** Deferred

The Runtime Metrics Foundation satisfies current engineering needs.

The remaining Observability Platform will be implemented later.

Planned

- Token tracking
- Cost tracking
- Queue metrics
- GPU metrics
- Distributed tracing
- OpenTelemetry
- Grafana dashboards

---

# Benchmark Platform

**Status:** Foundation Complete

Implemented

- Registry
- Runner
- Benchmark models
- Dataset loader
- Markdown reports
- JSON reports
- Chunking Benchmark

Deferred

- Embedding Benchmark
- Retrieval Benchmark
- Pipeline Benchmark

Reason

Current priority is delivering production AI capabilities rather than engineering tooling.

---

# Documentation Status

The following documentation has been completed.

Architecture

- Processing Platform
- Chunking Platform
- Embedding Platform
- Observability Platform

Engineering Journals

- Processing
- Chunking
- Embedding
- Runtime Metrics
- Multi-provider Embeddings

Architecture Decision Records

- Canonical AI Pipeline
- Queue Abstraction
- Chunk Model
- Chunking Provider Architecture
- Observability Platform

Roadmaps

- Knowledge Platform
- Observability Platform

---

# Lessons Learned

Several architectural improvements emerged during implementation.

## Canonical Artifact Pipeline

Every AI platform consumes the canonical artifact produced by the previous platform.

---

## Composition Roots

Dependency construction belongs in `create.py`.

Business services remain unaware of application wiring.

---

## Multi-provider Architecture

Adding a new provider should require only

- Provider implementation
- Configuration
- Registration inside `create.py`

No business service modifications should be necessary.

---

## Shared Infrastructure

Infrastructure should only be extracted after duplication becomes real.

Examples

- Runtime Metrics
- EmbeddingBatcher

Both were introduced after concrete implementation needs appeared.

---

## Strategic Prioritization

The project intentionally prioritizes implementation of the production AI platform over engineering tooling.

Current focus remains

```
Vector Store

↓

Retrieval

↓

Reranking

↓

Research API

↓

Chat

↓

Citations
```

Engineering platforms such as Observability, Benchmarking, and Experimentation will evolve after the core AI product is complete.

---

# Roadmap & Next Milestones

ResearchMind is developed using a milestone-driven approach. Each milestone is completed as a production-quality vertical slice before moving to the next capability.

The implementation strategy intentionally prioritizes building a complete AI platform over building engineering tooling too early.

---

# Current AI Knowledge Pipeline

The current production pipeline is:

```text
Upload

↓

Processing

↓

ProcessedDocument

↓

Chunking

↓

ChunkArtifact

↓

Embedding

↓

EmbeddingArtifact
```

The next milestones will extend this pipeline until it becomes a complete Retrieval-Augmented Generation (RAG) platform.

Future pipeline

```text
Upload

↓

Processing

↓

ProcessedDocument

↓

Chunking

↓

ChunkArtifact

↓

Embedding

↓

EmbeddingArtifact

↓

Vector Store

↓

VectorStoreArtifact

↓

Retrieval

↓

RetrievalArtifact

↓

Reranking

↓

RerankingArtifact

↓

Research API

↓

Chat

↓

Citations
```

---

# Current Prioritization

To maximize engineering value, portfolio quality, and interview readiness, the project follows a tiered implementation strategy.

---

## Tier 1 — Highest Priority

These milestones directly contribute to the production AI platform and should be completed before expanding engineering infrastructure.

### Phase 2.5 — Vector Store Platform

Responsibilities

- Canonical Vector Store model
- VectorStoreProvider abstraction
- Provider Registry
- Factory
- ChromaDB provider
- VectorStoreArtifact
- Processing integration
- Manual verification
- Architecture documentation

Future providers

- pgvector
- Pinecone
- Qdrant
- Weaviate
- Milvus

---

### Phase 2.6 — Retrieval Platform

Responsibilities

- Dense retrieval
- Top-K search
- Metadata filtering
- Parent retrieval
- Retrieval artifacts

---

### Phase 2.7 — Reranking Platform

Responsibilities

- Reranking abstraction
- Provider pattern
- Registry
- Factory

Future providers

- Voyage AI
- Jina AI
- Cohere
- Cross Encoder

---

### Phase 2.8 — Research API

Responsibilities

- Retrieval orchestration
- Context assembly
- Prompt construction
- Streaming responses
- REST API

---

### Phase 2.9 — Chat Platform

Responsibilities

- Conversational RAG
- Conversation history
- Prompt assembly
- Streaming chat
- Session management

---

### Phase 2.10 — Citation Platform

Responsibilities

- Chunk references
- Source attribution
- Citation formatting
- Grounded responses

---

# Tier 2 — Product Expansion

These capabilities build upon the completed RAG pipeline.

---

## Hybrid Search

Implement

- Dense search
- Keyword search
- Metadata search
- Score fusion

---

## Evaluation Platform

Measure

- Precision
- Recall
- NDCG
- MRR
- Hit Rate

Purpose

Evaluate retrieval quality independently from implementation.

---

## Agent Memory

Implement

- Conversation memory
- Semantic memory
- Long-term memory
- Memory retrieval

---

## Knowledge Service

Provide a unified service over the Knowledge Platform.

Responsibilities

- Retrieval orchestration
- Context assembly
- Citation assembly
- Knowledge APIs

---

## Research Engine

Consumes the Knowledge Platform to generate research-quality outputs.

Features

- Multi-document reasoning
- Report generation
- Research sessions
- Export capabilities

---

## Agentic AI Platform

ResearchMind will eventually support agentic workflows built on top of the Knowledge Platform.

Potential technologies

- LangGraph
- MCP
- Tool Calling
- Planning
- Reflection
- Human-in-the-loop

Potential agents

- Research Agent
- Analysis Agent
- Report Agent
- Workflow Agent

---

# Tier 3 — Engineering Platforms

These improve engineering quality but intentionally do not block delivery of the AI platform.

---

## Observability Platform

Current status

Runtime Metrics Foundation completed.

Future enhancements

- Token tracking
- Cost tracking
- Queue latency
- GPU monitoring
- Distributed tracing
- OpenTelemetry
- Grafana dashboards

---

## Benchmark Platform

Current status

Foundation completed.

Implemented

- Benchmark framework
- Registry
- Runner
- Dataset loader
- Report generation
- Chunking Benchmark

Future benchmarks

- Vector Store Benchmark
- Retrieval Benchmark
- Pipeline Benchmark

Embedding Benchmark has been intentionally postponed because it provides less value than continuing the production AI platform.

---

## Experimentation Platform

Future responsibilities

Compare

- Embedding providers
- Retrieval strategies
- Chunking strategies
- Rerankers
- Complete AI pipelines

Generate

- Engineering reports
- Performance comparisons
- Configuration recommendations

---

# Current Platform Status

| Platform | Status |
|-----------|--------|
| Identity | ✅ Complete |
| Upload | ✅ Complete |
| Processing | ✅ Complete |
| Chunking | ✅ Complete |
| Embedding | ✅ Complete |
| Runtime Metrics Foundation | ✅ Complete |
| Vector Store | ⏳ Next |
| Retrieval | Planned |
| Reranking | Planned |
| Research API | Planned |
| Chat | Planned |
| Citations | Planned |

---

# Immediate Next Milestone

## Phase 2.5 — Vector Store Platform

Objective

Transform canonical embeddings into searchable vector indexes while maintaining the provider-driven architecture established throughout the Knowledge Platform.

The Vector Store Platform should follow the same architectural principles used by previous platforms.

Architecture

```text
EmbeddingArtifact

↓

VectorStoreService

↓

VectorStoreRegistry

↓

VectorStoreProvider

↓

VectorStoreFactory

↓

VectorStoreArtifactBuilder

↓

VectorStoreArtifactWriter
```

The initial provider will be **ChromaDB**.

Additional providers can be introduced later without modifying business services.

---

# Engineering Principles Going Forward

Continue following these principles throughout the remainder of the project.

- Complete vertical slices before introducing new infrastructure.
- Prefer production-ready implementations over demonstrations.
- Every AI platform consumes exactly one canonical artifact.
- Every AI platform produces exactly one canonical artifact.
- Providers remain hidden behind stable interfaces.
- Frameworks remain implementation details.
- Avoid premature abstractions.
- Keep business logic free from engineering instrumentation.
- Documentation is part of implementation.

---

# Current Architectural Decisions

The following decisions should be treated as stable unless a compelling engineering reason emerges.

## Frozen

- Canonical AI pipeline
- Provider Pattern
- Registry Pattern
- Factory Pattern
- Composition Roots (`create.py`)
- Dependency Injection
- Runtime Metrics Foundation
- Shared EmbeddingBatcher
- Multi-provider Embedding Platform

## Deferred

- Advanced Observability
- Embedding Benchmark
- Experimentation Platform

The project is intentionally prioritizing end-user AI capabilities before expanding engineering tooling.

---

# Starting Point for the Next Conversation

Continue from:

**Phase 2.5 — Vector Store Platform**

Implementation order

```text
Models

↓

Interfaces

↓

Provider Abstraction

↓

Registry

↓

Factory

↓

ChromaDB Provider

↓

VectorStoreArtifact

↓

Service

↓

Processing Integration

↓

Manual Verification

↓

Architecture Documentation

↓

Engineering Journal

↓

Roadmap Update
```

The goal is to build the Vector Store Platform using the same engineering standards established by the Chunking and Embedding platforms.

---

# Notes for Future ChatGPT Conversations

This document is the canonical engineering context for the ResearchMind project.

When continuing the project:

- Do not redesign completed architecture without a strong engineering reason.
- Continue milestone by milestone.
- Always provide complete production-ready code with exact file paths.
- Maintain framework independence.
- Follow the established engineering philosophy.
- Update documentation after every completed milestone.
- Keep implementation aligned with the current prioritization.

The Embedding Platform is complete and considered the stable baseline.

The next conversation should begin with the implementation of the **Vector Store Platform**.

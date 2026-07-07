# ResearchMind AI Roadmap

**Last Updated:** 2026-07-07

---

# Vision

Build a production-grade AI Engineering Platform capable of processing, understanding, retrieving, evaluating, and reasoning over enterprise knowledge while remaining modular, provider-independent, and experimentation-friendly.

ResearchMind is **not** a traditional RAG application.

It is an AI Engineering Platform composed of independent but interoperable platforms communicating through canonical ResearchMind artifacts.

Core engineering principles include:

- Clean Architecture
- Dependency Injection
- Provider Pattern
- Registry Pattern
- Factory Pattern
- Canonical Models
- Canonical Artifacts
- Framework Independence
- Production-first Engineering
- Experimentation-first AI Development

Every platform should be independently evolvable while maintaining stable contracts with downstream platforms.

---

# Architectural Philosophy

ResearchMind is composed of multiple independent platforms.

Examples include:

- Identity Platform
- Knowledge Platform
- Observability Platform
- Experimentation Platform
- Benchmark Platform
- Research Engine
- Agentic AI Platform
- MCP Ecosystem

Each platform owns one responsibility.

Each platform consumes the canonical artifact produced by the previous platform.

Each platform produces exactly one canonical artifact for downstream consumers.

---

# Phase 0 — Engineering Foundation

---

## Milestone 0.0 — Repository Foundation

**Status:** ✅ Completed

Completed

- Repository structure
- Engineering conventions
- Project documentation
- Layered architecture
- Modular application layout

---

## Milestone 0.1 — Development Platform

**Status:** ✅ Completed

Completed

- uv
- Docker
- PostgreSQL
- Valkey
- Local development environment
- Amazon S3 integration
- Amazon Cognito integration
- Amazon SQS integration

---

## Milestone 0.2 — Backend Foundation

**Status:** ✅ Completed

Completed

- FastAPI
- Configuration
- Middleware
- Dependency Injection
- Logging
- Lifespan
- API Versioning
- Health Checks
- Exception Handling
- API Contracts

---

## Milestone 0.3 — Engineering Quality

**Status:** 🚧 In Progress

Completed

- Testing foundation
- Benchmark foundation

Planned

- Ruff
- Type Checking
- Coverage
- GitHub Actions
- Pre-commit Hooks

---

# Phase 1 — Identity Platform

---

## 1.1 Configuration

**Status:** ✅ Completed

---

## 1.2 Database Foundation

**Status:** ✅ Completed

Completed

- SQLAlchemy
- Alembic
- Base Models

---

## 1.3 Internal User Domain

**Status:** ✅ Completed

Completed

- User Entity
- Repository Pattern
- Service Layer
- User Synchronization

---

## 1.4 Authentication

**Status:** ✅ Completed

Completed

- Authentication abstraction
- AWS Cognito
- JWT validation
- Current user dependency

---

## 1.5 Authorization

**Status:** Planned

Planned

- Roles
- Permissions
- Resource ownership

---

## 1.6 User Profile

**Status:** Planned

Planned

- Preferences
- AI Settings
- Profile Management

---

# Phase 2 — Knowledge Platform

The Knowledge Platform transforms raw documents into structured, retrieval-ready knowledge.

Every platform consumes the canonical artifact produced by the previous platform and produces a new canonical artifact for downstream AI platforms.

The production pipeline evolves as a sequence of independent, provider-driven platforms.

Observability is intentionally separated into its own platform.

---

# Canonical Knowledge Pipeline

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
```

---

## Milestone 2.1 — Processing Platform

**Status:** ✅ Completed

Responsibilities

- Document parsing
- Metadata enrichment
- Statistics enrichment
- Canonical ProcessedDocument
- Processing artifacts
- Queue processing
- Amazon S3 persistence

Implemented

- ProcessingService
- DocumentProcessingService
- Queue abstraction
- Retry
- Dead Letter Queue
- Docling integration
- Metadata platform
- Statistics platform
- Processing artifacts

Artifacts

- processed_document.json
- parsed.md
- parsed.txt

---

## Milestone 2.2 — Chunking Platform

**Status:** ✅ Completed

Responsibilities

- Transform processed documents into canonical chunks.

Implemented

### Foundation

- Canonical Chunk model
- Provenance
- Statistics
- Experiment metadata
- Chunk metadata

### Architecture

- Provider Pattern
- Registry
- Factory
- ChunkingService

### Providers

- Fixed Chunking
- Recursive Chunking (LangChain)
- Markdown Chunking

Future Providers

- Hierarchical
- Semantic
- LLM
- Adaptive

### Artifact Platform

- ChunkArtifact
- ChunkArtifactBuilder
- ChunkArtifactWriter

Artifacts

```text
chunking/

    {strategy}/

        {artifact_id}/

            chunks.json
```

### Processing Integration

Implemented

Processing

↓

Chunking

↓

Chunk Artifact

---

### Runtime Evaluation

Initial runtime evaluation completed.

Future runtime metrics will migrate to the Observability Platform.

---

### Benchmark Platform

Implemented

- Benchmark framework
- Registry
- Runner
- Dataset Loader
- Markdown Reports
- JSON Reports
- Chunking Benchmark

---

## Milestone 2.3 — Embedding Platform

**Status:** ✅ Completed

Responsibilities

Transform canonical chunks into canonical vector embeddings.

Implemented

### Foundation

- Canonical Embedding model
- Provider metadata
- Experiment metadata
- Statistics
- Provenance

### Architecture

- Provider Pattern
- Registry Pattern
- Factory Pattern
- Composition Root (`create.py`)
- Framework Independence

### Providers

Implemented

Local

- Sentence Transformers

Cloud

- Voyage AI
- OpenAI

Planned

- BGE
- Instructor
- Nomic

No additional providers are planned until the core RAG pipeline is completed.

### Shared Batching

A single reusable batching utility, `EmbeddingBatcher`, is shared by every embedding provider.

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

### Artifact Platform

Implemented

- EmbeddingArtifact
- EmbeddingArtifactBuilder
- EmbeddingArtifactWriter

Artifacts

```text
embeddings/

    {provider}/

        {artifact_id}/

            embeddings.json
```

### Processing Integration

Implemented

```text
Processing

↓

Chunking

↓

Embedding
```

### Verification

Completed

Verified

- Processing
- Chunk generation
- Embedding generation (Sentence Transformers, Voyage AI, OpenAI)
- Shared batching
- Runtime metrics
- Artifact persistence
- Amazon S3 persistence
- Configuration fingerprints
- Provider metadata
- Canonical models

---

### Documentation

Completed

Architecture

- Embedding Platform Architecture

Engineering Journal

- Embedding Platform

ADR

- ADR-008 — Canonical AI Platform Pipeline

---

## Milestone 2.4 — Observability Platform

**Status:** 🚧 Runtime Metrics Foundation Complete — Full Platform Deferred

The Observability Platform provides standardized engineering visibility across every AI platform within ResearchMind.

Unlike the Knowledge Platform, which performs AI operations, the Observability Platform measures, reports, and monitors those operations.

It is intentionally designed as a **cross-cutting platform** rather than a feature inside individual AI platforms.

Rather than implementing the full platform immediately, a lightweight **Runtime Metrics Foundation** was introduced first, providing standardized engineering metrics while avoiding unnecessary complexity. The remaining, more advanced Observability Platform work is intentionally deferred until after the core AI pipeline is complete.

---

### Responsibilities

- Runtime Evaluation
- Stage Metrics
- Pipeline Metrics
- Performance Measurement
- Resource Monitoring
- Cost Tracking
- Token Tracking
- Tracing
- Telemetry

---

### Runtime Metrics Foundation

**Status:** ✅ Completed

```text
RuntimeMetricsCollector

↓

ProcessingService

↓

RuntimeReportGenerator
```

Every pipeline stage exposes:

- Execution duration
- Stage duration
- Peak memory
- Artifact size
- Provider
- Provider version

Metrics include:

Performance

- Execution duration
- Stage latency
- Pipeline duration

Memory

- Peak memory
- Average memory

Artifacts

- Artifact size
- Artifact count

Provider

- Provider
- Provider version

Runtime metrics provide immediate engineering visibility while allowing advanced observability to remain a future enhancement.

---

### Future Scope — Full Observability Platform

**Status:** Deferred

- Provider costs
- Token usage
- Queue latency
- Worker metrics
- GPU utilization
- Distributed tracing
- OpenTelemetry
- Prometheus
- Grafana

---

### Integration

Observability integrates with the production pipeline.

```text
Processing

↓

Chunking

↓

Embedding

↓

Observability

↓

Runtime Metrics

↓

Pipeline Report
```

Business platforms remain unaware of instrumentation.

---

### Documentation

Completed

Architecture

- Observability Platform Architecture

Engineering Journal

- Observability Platform Design

ADR

- ADR-016 — Observability Platform

Roadmap

- Observability Platform Roadmap

---

## Milestone 2.5 — Vector Store Platform

**Status:** ⏳ Next — Immediate Focus

The Vector Store Platform transforms canonical embeddings into searchable vector indexes.

It abstracts vector database providers behind a common interface while exposing canonical persistence artifacts.

---

### Responsibilities

- Vector indexing
- Metadata indexing
- Collection management
- Similarity search abstraction
- Index persistence

---

### Planned Providers

- ChromaDB
- pgvector
- Qdrant
- Pinecone
- Weaviate

---

### Planned Architecture

```text
EmbeddingArtifact

↓

VectorStoreService

↓

VectorStoreRegistry

↓

VectorStoreProvider

↓

VectorStoreArtifactBuilder

↓

VectorStoreArtifact
```

---

### Canonical Artifact

```text
VectorStoreArtifact
```

---

## Milestone 2.6 — Retrieval Platform

**Status:** Planned

The Retrieval Platform retrieves relevant knowledge from vector stores using multiple retrieval strategies.

---

### Responsibilities

- Dense Retrieval
- Hybrid Retrieval
- Metadata Filtering
- Parent Retrieval
- Citation Retrieval

---

### Planned Strategies

- Dense Vector Search
- Hybrid Search
- Metadata Filtering
- Parent Document Retrieval
- Multi-query Retrieval

---

### Planned Architecture

```text
VectorStoreArtifact

↓

RetrievalService

↓

RetrievalRegistry

↓

RetrievalProvider

↓

RetrievalArtifactBuilder

↓

RetrievalArtifact
```

---

### Canonical Artifact

```text
RetrievalArtifact
```

---

## Milestone 2.7 — Reranking Platform

**Status:** Planned

The Reranking Platform improves retrieval quality by reordering retrieved documents before they are supplied to downstream language models.

---

### Responsibilities

- Candidate reranking
- Multi-stage retrieval
- Provider abstraction
- Score normalization

---

### Planned Providers

- Jina AI
- Cohere
- Voyage AI
- Cross Encoders
- BGE Reranker

---

### Planned Architecture

```text
RetrievalArtifact

↓

RerankingService

↓

RerankingRegistry

↓

RerankingProvider

↓

RerankingArtifactBuilder

↓

RerankingArtifact
```

---

### Canonical Artifact

```text
RerankingArtifact
```

---

## Milestone 2.8 — Conversation Memory Platform

**Status:** Planned

Provides conversational memory capabilities for downstream AI systems.

---

### Responsibilities

- Session memory
- Long-term memory
- Context management
- Memory retrieval
- Context compression

---

### Planned Capabilities

- Short-term conversation memory
- Long-term user memory
- Semantic memory retrieval
- Context window optimization

---

## Milestone 2.9 — Knowledge Service

**Status:** Planned

The Knowledge Service provides the unified API that orchestrates every platform inside the Knowledge Platform.

---

### Responsibilities

- Knowledge orchestration
- Context assembly
- Unified retrieval API
- Citation assembly
- Pipeline orchestration

---

### Production Knowledge Flow

```text
Upload

↓

Processing

↓

Chunking

↓

Embedding

↓

Vector Store

↓

Retrieval

↓

Reranking

↓

Knowledge Service
```

---

# Phase 3 — Research Engine

The Research Engine consumes the Knowledge Platform and generates trustworthy research outputs.

Unlike the Knowledge Platform, which prepares knowledge, the Research Engine reasons over that knowledge.

---

## Responsibilities

- Retrieval-Augmented Generation (RAG)
- Context Assembly
- Citation Engine
- Research Sessions
- Report Generation
- Research History

---

## Architecture

```text
Knowledge Service

↓

Research Engine

↓

Prompt Assembly

↓

LLM

↓

Citation Engine

↓

Research Report
```

---

## Planned Features

- Citation-backed responses
- Research sessions
- Report generation
- Multi-document synthesis
- Research history
- Export capabilities

---

## Runtime Metrics

Provided by the Observability Platform.

Examples

- Total pipeline latency
- Prompt tokens
- Completion tokens
- Groundedness
- Citation coverage
- Provider cost
- Total execution time

---

# Phase 4 — Agentic AI Platform

The Agentic AI Platform introduces autonomous reasoning and multi-step execution.

---

## Planned Components

- LangGraph
- Multi-Agent Workflows
- Planning
- Memory
- Checkpointing
- Human-in-the-loop
- Tool Calling
- Reflection
- Self-correction

---

## Planned Agent Types

- Research Agent
- Retrieval Agent
- Analysis Agent
- Report Generation Agent
- Citation Validation Agent
- Workflow Orchestrator

---

## Future Architecture

```text
Research Request

↓

Planner

↓

Multi-Agent Workflow

↓

Knowledge Platform

↓

Tool Execution

↓

Research Report
```

---

# Phase 5 — Experimentation Platform

The Experimentation Platform continuously improves ResearchMind by evaluating alternative AI strategies without impacting production.

Unlike the Observability Platform, which measures production execution, the Experimentation Platform compares competing AI approaches.

Experimentation is:

- Optional
- Configurable
- Asynchronous
- Internal only

Production requests should never wait for experimentation to complete.

---

## Responsibilities

- Strategy comparison
- AI quality evaluation
- Recommendation generation
- Engineering reports
- Offline experimentation
- Architecture migrations

---

## Relationship to Other Platforms

The Experimentation Platform consumes outputs from multiple platforms.

```text
Knowledge Platform

+

Observability Platform

+

Engineering Benchmarks

↓

Experimentation Platform

↓

Evaluation Reports

↓

Engineering Recommendations
```

---

## Chunking Experiments

Compare chunking strategies.

Examples

- Fixed
- Recursive
- Markdown
- Hierarchical
- Semantic
- Adaptive
- LLM Chunking

Outputs

- Comparison reports
- Quality metrics
- Cost comparison
- Recommended strategy

---

## Embedding Experiments

Compare embedding providers.

Examples

- Sentence Transformers
- Voyage AI
- OpenAI
- BGE
- Instructor
- Nomic

Outputs

- Retrieval quality
- Latency
- Cost
- Memory
- Embedding dimensions
- Recommendations

---

## Retrieval Experiments

Compare retrieval strategies.

Examples

- Dense Retrieval
- Hybrid Search
- Parent Retrieval
- Multi-query Retrieval
- Metadata Filtering

Outputs

- Recall
- Precision
- MRR
- NDCG
- Latency

---

## Reranking Experiments

Compare reranking providers.

Examples

- Cohere
- Jina
- Voyage AI
- Cross Encoders

Outputs

- Ranking quality
- Latency
- Cost

---

## Pipeline Experiments

Compare complete AI pipelines.

Example

```text
Pipeline A

↓

Markdown

↓

Voyage

↓

Hybrid Search

↓

Jina

vs

Pipeline B

↓

Recursive

↓

OpenAI

↓

Dense Search

↓

Cohere
```

Outputs

- Engineering recommendations
- Quality reports
- Cost comparison
- Performance comparison

---

# Phase 6 — MCP Ecosystem

The MCP Ecosystem enables ResearchMind to communicate with external tools and services using the Model Context Protocol (MCP).

---

## Responsibilities

- External Tool Integration
- Enterprise Knowledge Integration
- AI Tool Orchestration
- Remote Agent Communication

---

## Planned MCP Servers

- Research MCP
- Climate MCP
- Earthquake MCP
- GitHub MCP
- Slack MCP
- Jira MCP
- Google Drive MCP
- Notion MCP
- Enterprise Knowledge MCP

---

## Future Capabilities

- Dynamic MCP discovery
- MCP registry
- MCP authentication
- Tool permission management
- Multi-MCP orchestration

---

# Phase 7 — Production Platform

The Production Platform provides the operational foundation required to deploy and operate ResearchMind at production scale.

Unlike the Observability Platform, which measures AI execution, the Production Platform manages infrastructure and deployment.

---

## Responsibilities

- CI/CD
- Kubernetes
- Scaling
- Security
- Disaster Recovery
- Infrastructure Automation
- Multi-region deployment
- Production operations

---

## Planned Components

- GitHub Actions
- Docker
- Kubernetes
- Helm
- AWS
- Terraform
- Secrets Management
- Auto Scaling
- Backup & Recovery

---

# Engineering Benchmark Platform

**Status:** ✅ Foundation Complete

Engineering Benchmarks are repository-owned evaluation datasets and an offline benchmarking framework used to compare competing AI implementations.

Unlike tests, benchmarks do **not** verify correctness.

Instead, they help engineers compare engineering trade-offs and produce reproducible reports.

Benchmarks are completely independent from:

- Runtime Observability
- Experimentation Platform

---

## Purpose

- Prevent regressions
- Compare implementations
- Measure quality
- Measure engineering characteristics
- Support architecture decisions

---

## Implemented

Framework

- Benchmark Registry
- Benchmark Runner
- Canonical Benchmark Models
- Dataset Loader
- Markdown Report Generator
- JSON Report Generator

Benchmarks

- Chunking Benchmark
- Embedding Benchmark

Dataset

- Versioned Research Papers Dataset

---

## Planned

- Vector Store Benchmark
- Retrieval Benchmark
- Reranking Benchmark
- End-to-End Pipeline Benchmark


---

## Execution

Benchmarks execute manually.

Example

```bash
uv run python -m benchmarks.runner chunking --dataset datasets/research_papers
```

Benchmarks are intentionally excluded from CI.

---

# Platform Relationships

The major AI Engineering platforms interact as follows.

```text
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

                     Knowledge Service

                               │

                     Research Engine

                               │

                  Agentic AI Platform

                               │

                    Experimentation Platform

                               │

                  Engineering Benchmarks

                               │

                       MCP Ecosystem
```

---

# Current Project Status

| Phase | Status |
|--------|--------|
| Phase 0 — Engineering Foundation | 🚧 In Progress |
| Phase 1 — Identity Platform | ✅ Complete |
| Phase 2.1 — Processing Platform | ✅ Complete |
| Phase 2.2 — Chunking Platform | ✅ Complete |
| Phase 2.3 — Embedding Platform | ✅ Complete |
| Phase 2.4 — Observability Platform (Runtime Metrics Foundation) | 🚧 Runtime Metrics Foundation Complete |
| Phase 2.5 — Vector Store Platform | ⏳ Next |
| Phase 2.6 — Retrieval Platform | ⏳ Planned |
| Phase 2.7 — Reranking Platform | ⏳ Planned |
| Phase 2.8 — Conversation Memory Platform | ⏳ Planned |
| Phase 2.9 — Knowledge Service | ⏳ Planned |
| Phase 3 — Research Engine | ⏳ Planned |
| Phase 4 — Agentic AI Platform | ⏳ Planned |
| Phase 5 — Experimentation Platform | ⏳ Planned |
| Phase 6 — MCP Ecosystem | ⏳ Planned |
| Phase 7 — Production Platform | ⏳ Planned |

---

# Current Focus

## Phase 2.5 — Vector Store Platform

The Embedding Platform is considered stable and frozen unless bugs are discovered. Runtime Metrics Foundation satisfies current observability needs, so the full Observability Platform remains deferred.

Objective: transform canonical embeddings into searchable vector indexes while maintaining the provider-driven architecture established throughout the Knowledge Platform, following the same architectural principles used by the Chunking and Embedding platforms. The initial provider will be **ChromaDB**.

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

---

# Next Major Milestones

This project intentionally prioritizes completing the production AI platform (Tier 1) before expanding engineering tooling (Tier 2/3 — Observability, Benchmarking, Experimentation).

1. Vector Store Platform (Phase 2.5)
2. Retrieval Platform (Phase 2.6)
3. Reranking Platform (Phase 2.7)
4. Research API (Phase 2.8 / Phase 3)
5. Chat Platform
6. Citation Platform
7. Knowledge Service
8. Research Engine
9. Agentic AI Platform
10. Advanced Observability, Embedding Benchmark, Experimentation Platform (deferred until the core RAG pipeline is complete)

---

# Long-Term Architectural Principles

Every platform in ResearchMind follows these principles.

## Canonical Models

Internal data exchanged between platforms uses canonical ResearchMind models.

---

## Canonical Artifacts

Every AI platform consumes the canonical artifact produced by the previous platform and produces exactly one canonical artifact for downstream platforms.

Example

```text
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

## Provider Pattern

External providers remain implementation details hidden behind stable interfaces.

Examples

- OpenAI
- Voyage AI
- Sentence Transformers
- ChromaDB
- Qdrant
- Pinecone

---

## Registry Pattern

Providers are registered through registries rather than directly coupled to services.

---

## Factory Pattern

Factories own construction of canonical domain models.

---

## Builder Pattern

Builders own construction of persistence artifacts.

---

## Composition Roots

Platforms are wired through `create.py` composition roots rather than business factories.

---

## Framework Independence

Frameworks such as LangChain remain implementation details and never leak outside provider implementations.

---

## Observability

Business platforms remain free from instrumentation.

Runtime metrics are collected by the Observability Platform.

---

## Experimentation

Production execution and experimentation remain independent.

Alternative AI strategies execute asynchronously.

---

## Engineering Benchmarks

Benchmarking remains repository-owned and independent from both runtime execution and experimentation.

---

# Long-Term Vision

ResearchMind is evolving into a production-grade AI Engineering Platform.

Rather than centering the architecture around Retrieval-Augmented Generation (RAG), the platform is organized around independent engineering capabilities that can evolve without breaking downstream systems.

By combining canonical artifacts, provider-based architecture, observability, experimentation, and engineering benchmarks, ResearchMind provides a foundation for building trustworthy, maintainable, and continuously improving AI systems suitable for long-term production use.

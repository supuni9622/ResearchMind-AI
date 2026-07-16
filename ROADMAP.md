# ResearchMind AI Roadmap

**Last Updated:** 2026-07-16

**Current Maturity:** NotebookLM++ + Perplexity Foundation. Hybrid Retrieval, Reranking, Parent Expansion, Compression, Guardrails, and strategy-based Prompt Formatting are all in place — beyond a plain NotebookLM clone. Maturity ladder: `NotebookLM++ → Perplexity v1 (almost here) → Open Deep Research → Manus / Glean`.

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

**Status:** ✅ Completed

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

### Providers

Implemented: **Qdrant** (see ADR-017 — Vector Store Platform Architecture). ChromaDB/pgvector/Pinecone/Weaviate were candidates considered but not built.

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

**Status:** ✅ Completed (Foundation + Metadata Filtering + Reranking); advanced strategies still planned

The Retrieval Platform retrieves relevant knowledge from vector stores using multiple retrieval strategies.

---

### Responsibilities

- ✅ Dense Retrieval
- ✅ Hybrid Retrieval (Reciprocal Rank Fusion of dense + sparse)
- ✅ Metadata Filtering (`owner_id`, `document_id`, `filename`, `language`; server-enforced `owner_id` scoping from the authenticated user)
- ✅ Parallel Retrieval (dense + sparse executed concurrently via `asyncio.gather`)
- 🔄 Parent Retrieval — reclassified into the Context Platform (Milestone 2.8) as Parent Expansion + Adjacent Merge; chunk artifacts, not the vector index, are the source of truth for parent resolution
- ✅ Citation Retrieval — implemented as the Context Platform's Citation Platform (Milestone 2.8): citation IDs, pages, headings, chunk IDs

---

### Strategies

- ✅ Dense Vector Search
- ✅ Hybrid Search
- ✅ Metadata Filtering
- ✅ Parallel Retrieval
- 🔄 Parent Document Retrieval — moved to Context Platform
- ❌ Multi-query Retrieval — moved to future Research Runtime (query decomposition)

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

**Status:** ✅ Completed (Foundation)

The Reranking Platform improves retrieval quality by reordering retrieved documents before they are supplied to downstream language models.

---

### Responsibilities

- ✅ Candidate reranking
- ❌ Multi-stage retrieval
- ✅ Provider abstraction (`RerankingProviderInterface`, registry, service)
- ❌ Score normalization

---

### Providers

Implemented

- ✅ Voyage AI (`rerank-2`) — wired into `RetrievalService.search_hybrid(rerank=True)` by default
- ✅ Cross Encoder (local `BAAI/bge-reranker-base`, sentence-transformers)

Future

- Jina AI
- Cohere

**Finding** (see `benchmarks/reranking/`): on the current benchmark corpus, reranking left Recall@5 unchanged (already 1.0) while lifting MRR and NDCG@5 substantially — exactly the effect reranking is expected to have, since it improves ordering rather than recall. The free local CrossEncoder outperformed paid Voyage AI reranking on this small corpus.

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

## Milestone 2.8 — Context Platform

**Status:** 🟡 ~90% Complete

The Context Platform sits between Reranking and Generation. It enriches, deduplicates, compresses, guards, cites, and formats retrieved knowledge before it reaches an LLM. Parent/child expansion was reclassified here from the Retrieval Platform once it became clear that ResearchMind's persisted chunk artifacts — not the vector index — are the source of truth for parent resolution.

---

### Responsibilities

- ✅ Parent Expansion
- ✅ Adjacent Merge
- 🟡 Compression (Token Budget + Embedding done; LangChain + LLM compression remain)
- ✅ Context Guardrails (V1)
- ✅ Citation Building
- ✅ Prompt Formatting (strategy-based)

---

### 2.8.1 Parent Expansion

**Status:** ✅ Complete

- `ChunkArtifactReader` — loads persisted chunk artifacts from storage
- `ParentExpansionService` — resolves `parent_chunk_id` into full parent context
- Vector payload extended with `chunk_artifact_id`, `chunking_strategy`, `parent_chunk_id`

---

### 2.8.2 Adjacent Merge

**Status:** ✅ Complete

- `AdjacentMergeService` — merges adjacent chunks into a single richer context block (NotebookLM-style)

---

### 2.8.3 Compression Platform

**Status:** 🟡 In Progress

Implemented

- ✅ Token Budget Provider (V1) — sort by score, fit into token budget
- ✅ Embedding Compression Provider (V2) — drop chunks above a similarity threshold

Remaining

- ❌ LangChain Provider (V3) — `ContextualCompressionRetriever`
- ❌ LLM Compression Provider (V4) — chunk-level relevant-summary compression

---

### 2.8.4 Context Guardrails

**Status:** ✅ V1 Complete

- Provider architecture
- `RuleBasedGuardrailProvider`
- Risk scoring
- Guardrail statistics

Future: LlamaGuard, NeMo Guardrails, Lakera.

---

### 2.8.5 Citation Platform

**Status:** ✅ Complete

- Citation IDs, page numbers, headings/heading paths, chunk IDs

Future: inline citations, source highlighting, citation evaluation.

---

### 2.8.6 Prompt Formatter

**Status:** ✅ Complete

Strategy-based prompt formatting — different downstream consumers need different knowledge representations. Stays a Context Platform concern, separate from Generation Platform prompt templates.

Providers: `DEFAULT`, `NOTEBOOKLM`, `PERPLEXITY`, `RESEARCH`, `AGENT`.

---

### Exit Criteria

- ✅ Parent Expansion operational
- ✅ Adjacent Merge operational
- 🟡 Compression Platform (2 of 4 providers complete)
- ✅ Guardrails V1 operational
- ✅ Citation Platform operational
- ✅ Prompt Formatter operational

---

## Milestone 2.9 — Conversation Memory Platform

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

## Milestone 2.10 — Knowledge Service

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

Context Assembly and the Citation Engine are already delivered by the Context Platform (Milestone 2.8). The immediate priority inside Phase 3 is the Generation Platform.

---

## Milestone 3.1 — Generation Platform

**Status:** 🟡 ~65% Complete — structured output, a multi-stage Validation
Platform integration (input/output/hallucination, registry, scoring,
`ValidationReport`), regeneration, and prompt-template integration are
done; the `/research` API, streaming chat, capability-based routing,
caching, artifacts, and per-runtime Validation Contracts/Runtime
Validators remain.

### Goal

Own all LLM interactions, consuming the Context Platform's `Prompt Context` output.

### Architecture

```text
generation/

    interfaces.py
    models.py
    service.py
    registry.py
    create.py

    providers/

        groq.py
        openai.py
        claude.py
        gemini.py
        ollama.py

    structured_output/    # registry, parsers, repair — connected end-to-end
    validation/            # ValidationRegistry, ValidationService, scoring, input/output/hallucination validators
    langchain/              # with_structured_output() bridge (4/5 providers)
    prompts/                # template platform (pre-existing), now bridged in
```

### Milestones

- ✅ Generation Core (interfaces, models, service, registry, composition root)
- ✅ Providers — Groq, OpenAI, Claude, Gemini, Ollama
- ✅ Structured Output — native provider decoding (all 5), parser/repair
  fallback, Markdown/XML registry connection, optional LangChain
  `with_structured_output()` path (OpenAI/Claude/Gemini/Ollama — Groq
  excluded, `langchain-groq` incompatible with the pinned `groq` SDK),
  regenerate-on-invalid-output loop with corrective feedback
- 🟡 Validation Platform Integration — input validators (empty prompt,
  token budget, provider limits, context quality), output validators
  (schema via `jsonschema`, JSON parseability, fabricated-citation
  detection), a lightweight no-LLM hallucination/groundedness validator,
  a `ValidationRegistry`, weighted scoring, and a multi-stage
  `ValidationReport` are all implemented; per-runtime Contracts/Runtime
  Validators and a few PRD output checks (completeness/consistency/
  formatting/response-size) remain — see `validation_platform_prd.md`
- ✅ Prompt Templates — bridged via `generate_from_template()`, reusing
  the pre-existing `generation/prompts/` platform (LangChain
  `ChatPromptTemplate`-based)
- ✅ Output Parsers — `PydanticOutputParser`/`JsonOutputParser` (LangChain,
  via `structured_output/parsers/` and the format-instructions step)
- ✅ Streaming — per-provider `stream()`
- ❌ `POST /research` API
- ❌ Streaming Chat API
- ❌ Capability-based provider routing (flags + guard exist, no
  selection engine — `generation/routing/` is empty stubs)
- ❌ Caching, Artifacts

Detail: `docs/architecture/structured-output-platform.md`.

### Deliverable

Provider-independent generation runtime powering the first end-to-end research answers.

---

## Milestone 3.2 — LangChain Adoption for Generation

**Status:** 🟡 Mostly Complete for Structured Output — Prompt Templates,
Output Parsers, and a `with_structured_output()` path are implemented;
LCEL composition and streaming-specific LangChain usage remain.

Introduced:

- ✅ Prompt Templates — `ChatPromptTemplate` (pre-existing Prompt Platform)
- ✅ Output Parsers — `PydanticOutputParser`, `JsonOutputParser`
- ✅ `with_structured_output()` — `generation/langchain/output_parsers.py`
  (OpenAI, Claude, Gemini, Ollama)
- ❌ LCEL — not adopted
- ❌ Streaming — provider streaming is native-SDK-based, not LangChain-based

Frameworks remain implementation details behind the Generation Platform's provider interfaces.

---

## Research Capabilities

**Status:** ❌ Not Started

- Retrieval-Augmented Generation (RAG) — now Generation Platform + Context Platform combined
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
- Retrieval Benchmark (dense vs. sparse vs. hybrid RRF, ADR-020 metrics)
- Metadata Filtering Benchmark (`leakage_rate` correctness signal, unfiltered vs. owner-filtered)
- Reranking Benchmark (hybrid-only vs. +CrossEncoder vs. +Voyage AI; Recall@5, MRR, NDCG@5, latency, cost)
- Pipeline Benchmark (end-to-end ingestion)

Dataset

- Versioned Research Papers Dataset

---

## Planned

- Vector Store Benchmark
- End-to-End Pipeline Benchmark (RAG-level, post Context Building / Generation)


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
| Phase 2.5 — Vector Store Platform | ✅ Complete |
| Phase 2.6 — Retrieval Platform | ✅ Complete (Foundation + Metadata Filtering + Reranking + Parallel Retrieval) |
| Phase 2.7 — Reranking Platform | ✅ Complete (Foundation) |
| Phase 2.8 — Context Platform | 🟡 ~90% Complete (Parent Expansion, Adjacent Merge, Compression V1/V2, Guardrails V1, Citations, Prompt Formatter done; LangChain + LLM compression remain) |
| Phase 2.9 — Conversation Memory Platform | ⏳ Planned |
| Phase 2.10 — Knowledge Service | ⏳ Planned |
| Phase 3.1 — Generation Platform | 🟡 ~65% Complete (structured output, input/output/hallucination validation + scoring, regeneration, prompt bridge done; runtime validators/contracts, routing/caching/artifacts remain) |
| Phase 3.2 — LangChain Adoption for Generation | 🟡 Mostly Complete for structured output (LCEL not adopted) |
| Phase 3 — Research Engine (broader) | ⏳ Planned |
| Phase 4 — Agentic AI Platform | ⏳ Planned |
| Phase 5 — Experimentation Platform | ⏳ Planned |
| Phase 6 — MCP Ecosystem | ⏳ Planned |
| Phase 7 — Production Platform | ⏳ Planned |

---

# Current Focus

## Phase 2.8 — Context Platform (wrapping up) + Phase 3.1 — Generation Platform (~65% complete, in progress)

Vector Store, Retrieval (dense/sparse/hybrid/parallel), Metadata Filtering, and Reranking are all complete (Phases 2.5–2.7). The Context Platform (Phase 2.8) is ~90% complete. The Generation Platform (Phase 3.1) is now ~65% complete: Provider Structured Output Integration (native decoding for all 5 providers, parser/repair fallback, Markdown/XML registry connection, an optional LangChain `with_structured_output()` path), Validation Platform integration (input/output/hallucination validators, a `ValidationRegistry`, weighted scoring, and a multi-stage `ValidationReport`), a regenerate-on-invalid-output loop (now correctly scoped to only the output stage), a provider-capability-mismatch guard, and a Prompt Platform → Generation bridge (`generate_from_template()` with schema-aware format instructions) are all done. Detail: `docs/architecture/structured-output-platform.md`.

Remaining before Phase 3.1 — Generation Platform is complete:

- `POST /research` API and streaming chat API
- Capability-based provider routing/selection (flags + guard exist; `generation/routing/` selection engine does not)
- Caching, generation-level guardrails, artifact persistence
- Per-runtime Validation Contracts/Runtime Validators, and the remaining PRD output checks — completeness/consistency/formatting/response-size (`generation/validation/` — see `validation_platform_prd.md`)
- Test suite for `routing/`, `caching/`, `artifacts/`, generation-level `guardrails/` (`validation/`, `providers/`, `prompts/`, and core `service.py` now have unit test coverage)

Also remaining to close out Phase 2.8 — Context Platform:

- LangChain compression provider (V3) and LLM compression provider (V4)
- Conversation Memory Platform (Phase 2.9)
- Knowledge Service — unified orchestration API (Phase 2.10)
- Forward `HybridRetrieveRequest.rerank` from `/retrieve/hybrid` into `RetrievalService.search_hybrid` (currently always uses the service's `rerank=True` default)
- Multi-query Retrieval (query decomposition moved to the future Research Runtime)

---

# Next Major Milestones

This project intentionally prioritizes completing the production AI platform (Tier 1) before expanding engineering tooling (Tier 2/3 — Observability, Benchmarking, Experimentation).

1. ~~Vector Store Platform (Phase 2.5)~~ ✅
2. ~~Retrieval Platform (Phase 2.6)~~ ✅
3. ~~Reranking Platform (Phase 2.7)~~ ✅
4. ~~Context Platform (Phase 2.8) — Parent Expansion, Adjacent Merge, Guardrails V1, Citations, Prompt Formatter~~ ✅ (~90%, compression V3/V4 remain)
5. **Generation Platform (Phase 3.1) — ~65% complete, highest priority to finish**: `/research` API, streaming chat, capability-based routing, caching, artifacts, per-runtime Validation Contracts/Runtime Validators, remaining output checks (completeness/consistency/formatting/response-size)
6. ~~LangChain Adoption for Generation (Phase 3.2)~~ 🟡 mostly complete for structured output (LCEL not adopted)
7. Conversation Memory Platform (Phase 2.9)
8. Knowledge Service (Phase 2.10)
9. Evaluation Platform expansion (NDCG, Groundedness, Faithfulness, Hallucinations, Citation Accuracy, End-to-End, Security Evaluation)
10. Research Runtime — Query Decomposition, Planner, Research Agents, Reviewer, Summarizer, LangGraph
11. Agentic AI Platform
12. Long-Term Platform — Research Sessions, Memory, MCP, Feedback Learning
13. Advanced Observability, Experimentation Platform (deferred until the core RAG pipeline is complete)

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

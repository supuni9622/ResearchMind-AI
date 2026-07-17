# ResearchMind AI Engineering Roadmap v2

Version: 2.0

Status: Active

**Current Maturity (2026-07-17):** NotebookLM++ + Perplexity Foundation. Hybrid Retrieval, Reranking, Parent Expansion, Compression, Context Guardrails, and strategy-based Prompt Formatting are all implemented — beyond a plain NotebookLM clone and closing in on Perplexity v1. The AI Runtime Platform (Phase 3) is now ~80% complete: Provider Structured Output Integration, a multi-stage Validation Platform integration (input/output/hallucination validators, registry, scoring, `ValidationReport`), regeneration, Prompt Platform bridging, a Routing Platform (scored model catalog, task-based strategies, fallback chains), and a Runtime Caching Platform (L1 exact/L2 semantic/L3 session caching, policy resolution) are done (see Phase 3.1/3.5 below and `docs/architecture/structured-output-platform.md` / `docs/architecture/model-routing-platform.md` / `docs/architecture/runtime-caching-platform.md`). A standalone, platform-wide Guardrails Platform (`app/ai/guardrails/`, see "AI Guardrails" below) is now complete as an MVP foundation. Ladder: `NotebookLM++ → Perplexity v1 (almost here) → Open Deep Research → Manus / Glean`. See `PROJECT_STATUS.md` and `ROADMAP.md` for the authoritative, continuously-updated status; this document tracks the frozen technology decisions and long-range vision.

---

# 1. Vision

## Mission

ResearchMind is a production-grade AI Research & Intelligence Platform designed to demonstrate modern AI Engineering practices while serving as a real-world application for intelligent knowledge discovery.

The project is not simply a RAG chatbot.

It is an engineering platform that combines:

- Knowledge Processing
- Retrieval-Augmented Generation (RAG)
- AI Runtime
- Multi-Agent Systems
- External MCP integrations
- Evaluation
- Observability
- Production Engineering

The long-term goal is to build a modular AI platform that resembles how modern AI systems are designed in industry.

---

# 2. Objectives

ResearchMind has three primary objectives.

## Objective 1

Become an excellent AI Engineer.

The project should teach:

- AI Engineering
- Production AI Systems
- System Design
- Clean Architecture
- Performance Engineering
- Evaluation Driven Development

---

## Objective 2

Build a production-grade AI platform.

Every architectural decision should be made as if ResearchMind will eventually serve real users.

---

## Objective 3

Create an outstanding portfolio project.

The finished system should demonstrate practical experience in:

- RAG
- AI Agents
- LangGraph
- MCP
- Evaluation
- Production AI Infrastructure

---

# 3. Engineering Philosophy

ResearchMind follows several engineering principles.

---

## Build Production Systems

Every implementation should be suitable for production.

Examples:

- structured logging
- configuration management
- testing
- provider abstraction
- documentation

---

## Avoid Premature Abstraction

Abstractions exist only when they simplify the system.

Do not build generic frameworks before real use cases exist.

---

## Vertical Slice Development

Complete one capability end-to-end before introducing supporting infrastructure.

Example:

```
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
```

before introducing:

- queues
- distributed workers
- advanced caching

---

## Provider Independence

External services should never leak into business logic.

Examples:

- LLM providers
- Embedding providers
- Vector databases
- MCP servers

Business code depends only on canonical interfaces.

---

## Evaluation Driven Development

Every AI improvement should be measurable.

Instead of asking:

> Does it work?

We ask:

> Did it improve quality?

---

## Documentation First

Every important architectural decision should be documented.

ResearchMind should explain:

- what was built
- why it was built
- why alternatives were rejected

---

# 4. Architecture Philosophy

ResearchMind is organized around platforms.

Not technologies.

Platforms own business capabilities.

Technologies implement those capabilities.

Example:

```
Knowledge Platform

↓

Embedding Platform

↓

Vector Platform
```

NOT

```
Sentence Transformers

↓

Qdrant

↓

LangChain
```

This makes technologies replaceable.

---

# 5. Frozen Technology Decisions

These decisions are considered stable unless a future ADR replaces them.

## Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic v2

---

## Database

- PostgreSQL

---

## Object Storage

Development

- Local Storage

Production

- Amazon S3

---

## Vector Database

Qdrant

---

## Primary Embedding Provider

Voyage AI

Current model:

```
voyage-3-lite
```

---

## Sparse Embedding Provider

FastEmbed SPLADE

Current model:

```
prithivida/Splade_PP_en_v1
```

Used for Qdrant native hybrid retrieval (ADR-019). No separate BM25 platform.

---

## Primary LLM Provider (Development)

Groq

---

## Primary Workflow Engine

LangGraph

---

## Primary AI Framework

LangChain

---

## Cache

Valkey

---

## Evaluation

LangSmith

DeepEval

Ragas

---

# 6. Development Strategy

The project will be built in four major layers.

```
Layer 1

Knowledge Platform

↓

Layer 2

AI Runtime Platform

↓

Layer 3

Research & Agent Platform

↓

Layer 4

Production & Enterprise Platform
```

Each layer builds upon the previous one.

---

# 7. Platform Overview

ResearchMind consists of ten major platforms.

```
Phase 0

Engineering Foundation

↓

Phase 1

Identity Platform

↓

Phase 2

Knowledge Platform

↓

Phase 3

AI Runtime Platform

↓

Phase 4

Research Platform

↓

Phase 5

Agent Platform

↓

Phase 6

MCP Platform

↓

Phase 7

AI Quality Platform

↓

Phase 8

Production Platform

↓

Phase 9

Enterprise Platform
```

---

# Phase 0 — Engineering Foundation

## Goal

Create a production-ready backend foundation.

---

## Milestones

### 0.1 Project Bootstrap

- Project structure
- Dependency management
- Docker Compose
- Environment configuration
- Local development

Deliverable

Working backend.

---

### 0.2 Backend Foundation

- FastAPI
- Dependency Injection
- Lifespan
- SQLAlchemy
- Exception handling
- Logging
- Health endpoints

Deliverable

Production backend skeleton.

---

### 0.3 Engineering Quality

- Ruff
- MyPy
- Pytest
- Coverage
- Pre-commit
- GitHub Actions

Deliverable

Production engineering workflow.

---

### Exit Criteria

- Local development works
- CI passes
- Testing configured
- Logging configured
- Documentation started

Status

✅ Complete

---

# Phase 1 — Identity Platform

## Goal

Provide secure authentication and user management.

---

## Milestones

### 1.1 Authentication

- Cognito
- JWT Verification
- Protected APIs

---

### 1.2 Identity

- Internal User
- Synchronization
- Identity abstraction

---

### 1.3 User Profile

- Preferences
- Research settings

Deferred

- Organizations
- RBAC
- Billing integration

---

### Exit Criteria

- Secure authentication
- Current user available
- Identity abstraction completed

Status

✅ Complete

---

# Phase 2 — Knowledge Platform

## Goal

Build a production-grade knowledge ingestion and retrieval foundation.

This phase creates the heart of the RAG system.

Everything after this phase depends on the Knowledge Platform.

---

## Phase 2.1 — Upload Platform

### Goal

Accept and store user documents.

### Milestones

- Upload API
- Validation
- Storage abstraction
- Metadata creation
- Duplicate detection hook
- Virus scan hook (future)

### Deliverable

Documents can be uploaded and stored.

### Exit Criteria

- Upload succeeds
- Metadata stored
- File persisted

Status

✅ Complete

---

## Phase 2.2 — Document Intelligence Platform

### Goal

Convert uploaded files into structured knowledge.

### Milestones

- Document parsing
- Text normalization
- Markdown generation
- Plain text generation
- Metadata extraction
- Fingerprinting
- Language detection
- OCR hooks
- Citation mapping
- Page mapping

### Deliverable

Canonical processed document.

### Exit Criteria

- Structured document created
- Processing artifacts generated

Status

✅ Complete

---

## Phase 2.3 — Chunking Platform

### Goal

Transform documents into retrieval-ready chunks.

### Milestones

Current

- Recursive chunking
- Chunk metadata
- Chunk artifacts
- Chunk evaluation foundation

Future

- Semantic chunking
- Parent-child chunking
- Late chunking
- Agentic chunking

### Deliverable

Canonical chunk collection.

### Exit Criteria

- Chunk artifacts generated
- Strategy abstraction completed

Status

✅ Complete

## Phase 2.4 — Embedding Platform

### Goal

Transform knowledge chunks into high-quality semantic vector representations.

The Embedding Platform provides a provider-independent abstraction for
embedding generation while producing canonical embedding artifacts for
downstream platforms.

---

### Milestones

#### 2.4.1 Platform Foundation

- Canonical domain models
- Provider abstraction
- Provider registry
- Provider factory
- Service layer
- Configuration
- Artifact models
- Artifact builder
- Artifact writer

Deliverable

Production-ready embedding platform architecture.

Status

✅ Complete

---

#### 2.4.2 Voyage AI Provider

- Provider implementation
- Batch embedding
- Retry handling
- Error mapping
- Configuration

Deliverable

Primary production embedding provider.

Status

🚧 Current

---

#### 2.4.3 Embedding Cache

Purpose

Avoid generating identical embeddings multiple times.

Features

- Chunk hash
- Cache lookup
- Cache expiration
- Cache invalidation

Storage

Valkey

Deliverable

Production embedding cache.

---

#### 2.4.4 Additional Providers

Future providers

- OpenAI
- BGE
- E5
- Nomic
- Instructor

Purpose

Learning and benchmarking.

---

#### 2.4.5 Embedding Benchmark

Compare providers using

- Latency
- Cost
- Dimensions
- Storage size
- Recall
- Throughput

Deliverable

Embedding comparison framework.

---

### Exit Criteria

- Provider abstraction completed
- Voyage AI operational
- Embedding artifacts generated
- Embedding cache operational

---

## Phase 2.5 — Vector Platform

### Goal

Persist embeddings in a production-grade vector database.

The Vector Platform owns vector indexing and collection management.

It does not perform retrieval.

---

### Milestones

#### 2.5.1 Platform Foundation

- Canonical models
- Provider abstraction
- Registry
- Configuration
- Service
- Interfaces
- Exceptions

Deliverable

Vector Store Platform architecture.

Status

✅ Complete

---

#### 2.5.2 Qdrant Provider

- Collection creation
- Collection management
- Upsert
- Delete
- Count
- Collection metadata

Deliverable

Production Qdrant provider.

Status

✅ Complete

---

#### 2.5.3 Indexing Pipeline

Workflow

```
Embedding Artifact
+
Chunk Artifact

↓

IndexingService

↓

Sparse Embedding (FastEmbed SPLADE)

↓

Collection Definition

↓

VectorStoreRecord (dense + sparse)

↓

Qdrant (named dense + sparse vectors)
```

Tasks

- Build collection definition
- Generate sparse vectors from chunk text (FastEmbed SPLADE)
- Build vector records (dense + sparse)
- Ensure collection exists (named `dense`/`sparse` vector schema)
- Batch indexing
- Statistics generation (incl. sparse vector counts)

Deliverable

Production indexing pipeline.

Status

✅ Complete

---

#### 2.5.4 Vector Store Artifacts

Generate

- indexing.json
- indexing statistics (incl. `indexed_sparse_vectors`)
- execution metadata

Deliverable

Canonical vector indexing artifacts.

Status

✅ Complete

---

### 2.5.5 Indexing Platform

    • Vector Index (dense)
    • Sparse Vector Index (FastEmbed SPLADE, via Qdrant native hybrid — see ADR-019)
    • Index Artifacts

No separate BM25 platform was built. ADR-019 rejected a dedicated BM25 engine in
favor of sparse neural vectors generated by FastEmbed SPLADE and indexed into
the same Qdrant collection as the dense vectors.

Status

✅ Complete

#### 2.5.6 Snapshot Management

Future

- Snapshot creation
- Snapshot restore
- Backup metadata

---

### Exit Criteria

- Embeddings indexed
- Qdrant operational
- Artifacts generated
- End-to-end indexing verified

Status

✅ Complete — verified against real Qdrant + Voyage AI + FastEmbed with a live sparse-vector query

---


## Phase 2.6 — Retrieval Platform

### Goal

Retrieve the most relevant knowledge from indexed vectors.

Retrieval becomes the entry point for every AI workflow.

---

### Milestones

#### 2.6.1 Retrieval Foundation

Workflow

```
Question

↓

Embedding

↓

Qdrant

↓

Top-K Results
```

Features

- Query embedding
- Vector search
- Top-K retrieval

---

#### 2.6.2 Metadata Filtering

**Status:** ✅ Complete (owner_id, document_id, filename, language)

Support filters

- ✅ owner_id — server-enforced from the authenticated user, never trusted from the request body
- ❌ workspace_id
- ✅ document_id
- ✅ filename
- ✅ language
- ❌ tags

Deliverable

Filtered retrieval. Validated by `MetadataFilteringBenchmark` (`benchmarks/retrieval/metadata_filtering_benchmark.py`): `leakage_rate: 0.0` for every filtered candidate (dense/sparse/hybrid) and MRR raised to 1.0. See `docs/architecture/metadata-filtering.md`.

---

#### 2.6.3 Retrieval Strategies

Initial

- Similarity search

Future

- MMR
- Parent retrieval
- Multi-query retrieval
- Contextual compression

---

#### 2.6.4 Retrieval Cache

Purpose

Avoid repeated vector searches.

Storage

Valkey

Deliverable

Production retrieval cache.

---

#### 2.6.5 Retrieval Evaluation

Metrics

- Recall@K
- Precision@K
- MRR
- NDCG
- Latency

Deliverable

Retrieval benchmark suite.

2.6 Retrieval Platform ✅ Complete

    • ✅ Query Processing
    • ✅ Semantic Search (dense)
    • ✅ Sparse Search (Qdrant native sparse vectors, FastEmbed SPLADE — see ADR-019; no separate BM25 engine)
    • ✅ Hybrid Search (Qdrant fusion of dense + sparse)
    • ✅ Parallel Retrieval (dense + sparse via `asyncio.gather`)
    • 🔄 Retrieval Strategies — Parent/Child reclassified into the Context Platform (2.9); multi-query moved to the future Research Runtime
    • ✅ Fusion (Reciprocal Rank Fusion)
    • ✅ Metadata Filtering
    • ✅ Evaluation (Recall@K, Precision@K, MRR, NDCG@K, latency)

2.7 Reranking Platform ✅ Complete (Foundation)

2.8 Knowledge Platform Integration 🚧 In Progress

2.9 Context Platform ✅ Complete (Phase 3.7, `context_platform_complexion_prd.md`)

    • ✅ Parent Expansion (`ChunkArtifactReader`, `ParentExpansionService`)
    • ✅ Adjacent Merge (`AdjacentMergeService`)
    • ✅ Compression — Token Budget (V1), Embedding Redundancy (V2), LangChain (V3, `ContextualCompressionRetriever` + `LLMChainExtractor`, wired into `ContextBuilderService.build()`'s default pipeline behind `settings.enable_langchain_compression`), LLM Compression (V4, per-chunk `GenerationService.generate()` summarization, registered but not part of the default pipeline)
    • ✅ Context Guardrails V1 (`RuleBasedGuardrailProvider`, risk scoring, statistics)
    • ✅ Citation Platform (citation IDs, pages, headings, chunk IDs)
    • ✅ Prompt Formatter (`DEFAULT`, `NOTEBOOKLM`, `PERPLEXITY`, `RESEARCH`, `AGENT`)

    Architectural decision: parent/child retrieval was reclassified out of the
    Retrieval Platform (2.6) into the Context Platform, since ResearchMind's
    persisted chunk artifacts — not the vector index — are the source of
    truth for parent resolution.

---

### Exit Criteria

- ✅ Retrieval operational
- ✅ Metadata filters supported
- ✅ Evaluation completed
- ✅ Cache operational (query embedding cache, Valkey-backed)

---

## Phase 2.7 — Reranking Platform

**Status:** ✅ Complete (Foundation)

### Goal

Improve retrieval quality by reordering retrieved documents.

---

### Milestones

#### 2.7.1 Platform Foundation

**Status:** ✅ Complete

- ✅ Provider abstraction (`RerankingProviderInterface`, `BaseRerankingProvider`)
- ✅ Registry (`RerankingRegistry`, incl. `has()` for optional-provider checks)
- ✅ Service (`RerankingService`)
- ✅ Canonical models (`RerankingRequest`, `RerankedChunk`, `RerankingResult`)

---

#### 2.7.2 Voyage AI Reranker

**Status:** ✅ Complete

`VoyageReranker` (Voyage AI `rerank-2`). Also implemented ahead of schedule:

- ✅ CrossEncoder (`BAAI/bge-reranker-base`, local sentence-transformers, no marginal cost)

Wired into `RetrievalService.search_hybrid(rerank=True)` by default.

Future

- Cohere
- Jina

---

#### 2.7.3 Reranking Evaluation

**Status:** ✅ Complete

Metrics

- ✅ Recall@5 (baseline comparison)
- ✅ MRR improvement
- ✅ NDCG@5 improvement
- ✅ Latency
- ✅ Cost (qualitative cost_model per candidate — no $ pricing engine exists yet)

`RerankingBenchmark` (`benchmarks/reranking/benchmark.py`) compares `hybrid_only` vs. `hybrid_cross_encoder` vs. `hybrid_voyage` on the same hybrid candidate pool per query. **Finding:** Recall@5 was unchanged by reranking (already 1.0), while MRR and NDCG@5 both improved substantially (MRR 0.925 → 1.0 CrossEncoder / → 0.95 Voyage) — confirming reranking's expected effect on ranking quality rather than recall.

---

### Exit Criteria

- ✅ Reranking operational
- ✅ Evaluation completed

---

## Phase 2.8 — Knowledge Platform Integration

### Goal

Integrate every knowledge subsystem into one production RAG pipeline.

Pipeline

```
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
```

Tasks

- End-to-end integration
- Integration tests
- Performance verification
- Failure recovery
- Pipeline documentation

Deliverable

Production-ready RAG engine.

---

### Exit Criteria

- Complete RAG pipeline operational
- Every artifact generated
- Every platform integrated
- Integration tests passing

Status

🚧 In Progress

---

# Phase 3 — AI Runtime Platform

**Status:** 🟡 ~80% Complete — Provider Structured Output Integration,
Validation Platform integration (input/output/hallucination validators,
a `ValidationRegistry`, weighted scoring, and a `ValidationReport`),
regeneration, Prompt Platform bridging, a Routing Platform (scored
model catalog, task-based strategies, capability/policy filtering,
fallback chains), and a Runtime Caching Platform (L1 exact/L2
semantic/L3 session caching, policy resolution — see Phase 3.5 below)
are done. Per-runtime Validation Contracts/Runtime Validators and
artifacts remain. Tracked in day-to-day docs as
the "Generation Platform" (see `ROADMAP.md` Phase 3.1,
`phase-3-ai-runtime-roadmap.md` Phase 3.8,
`docs/architecture/structured-output-platform.md` for Structured
Output/Validation, `docs/architecture/model-routing-platform.md` +
ADR-026 for Routing, `docs/architecture/runtime-caching-platform.md` +
ADR-027 for Caching).

## Goal

Provide a unified runtime for all LLM interactions.

This platform owns generation.

Knowledge retrieval remains inside the Knowledge Platform. Context assembly (compression, guardrails, citations, prompt formatting) remains inside the Context Platform (2.9) and feeds this platform's `Prompt Context` input.

---

## Phase 3.1 — LLM Provider Platform

**Status:** ✅ Provider abstraction, routing, and caching complete; 🟡 structured
output sub-scope at varying completion (see below)

### Goal

Abstract LLM providers.

Implemented (all five, per the current `generation/providers/` architecture)

- ✅ Groq
- ✅ OpenAI
- ✅ Claude
- ✅ Gemini
- ✅ Ollama

Architecture

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

    structured_output/   # registry, parsers, repair
    validation/            # registry, scoring, input/output/hallucination validation
    langchain/              # with_structured_output() (4/5 providers)
    prompts/                 # template platform, bridged in
    catalog/                 # scored ModelMetadata + ModelCatalogRegistry
    routing/                 # RoutingService — strategies, scoring, fallback chains
```

Features

- ✅ Provider registry
- 🟡 Model registry — a scored `ModelMetadata` catalog (`catalog/models.py`)
  and `ModelCatalogRegistry` (`catalog/registry.py`) exist and back the
  Routing Platform; not yet exposed as its own runtime HTTP endpoint
- ✅ Model routing — a scored `ModelCatalogRegistry`, a 15-value
  task-based `RoutingStrategy`, capability/policy filtering, a weighted
  scoring engine with explainable reasons, and a distinct-provider-
  preferred fallback chain (`generation/routing/`); `GenerationService.
  generate()` routes automatically when no `provider` is given — see
  `routing_platform_prd.md`, ADR-026
- ✅ Streaming
- ✅ Retries (request-level, exponential backoff)
- ✅ Timeouts
- ✅ Structured output — native decoding (all 5 providers), parser/repair
  fallback, Markdown/XML parser-registry connection, optional LangChain
  `with_structured_output()` path (OpenAI/Claude/Gemini/Ollama — Groq
  excluded, `langchain-groq` incompatible with the pinned `groq` SDK),
  regenerate-on-invalid-output loop with corrective feedback
- 🟡 Validation Platform integration — input validators (empty prompt,
  token budget, provider limits, context quality), output validators
  (schema, JSON parseability, citation), a lightweight no-LLM
  hallucination/groundedness validator, a `ValidationRegistry`, weighted
  scoring, and a multi-stage `ValidationReport`; per-runtime Contracts/
  Runtime Validators remain (`validation_platform_prd.md`)

Deliverable

Provider-independent LLM runtime.

---

## Phase 3.2 — Prompt Platform

**Status:** ✅ Substantially complete (pre-existing) and now bridged into
Generation. LangChain adoption (Prompt Templates, Output Parsers) is
done; LCEL is not adopted.

Purpose

Treat prompts as production artifacts.

Features

- ✅ Prompt templates — disk-loaded (`prompt.md` + `metadata.yaml` +
  `examples.json`), rendered via LangChain `ChatPromptTemplate`
- ✅ Prompt registry — `PromptRegistry`
- ✅ Versioning — templates carry a `version`; registry resolves by name+version
- ✅ Variables — `{variable}` extraction and validation
- ✅ Generation bridge — `GenerationService.generate_from_template()`
  renders a template, flattens it into `GenerationRequest`, and appends
  schema-aware format instructions (`PydanticOutputParser.get_format_instructions()`)
  when `output_model` is set
- ❌ Evaluation
- ❌ A/B testing

Deliverable

Prompt management platform.

---

## Phase 3.3 — Conversation Platform

Features

- Sessions
- Conversation history
- Context management
- Streaming responses
- Chat titles

Deliverable

Production chat platform.

---

## Phase 3.4 — Memory Platform

Memory types

- Short-term
- Long-term
- User profile
- Research memory
- Semantic memory

Deliverable

Unified memory platform.

---

## Phase 3.5 — Runtime Caching Platform

**Status:** ✅ Complete (per `runtime_caching_platform_prd.md`, ADR-027; see `docs/architecture/runtime-caching-platform.md` and `PROJECT_STATUS.md` Milestone 2.9.9 for full detail)

Implemented (`apps/api/app/ai/runtime/generation/caching/`), wired directly into `GenerationService`

- L1 Exact Cache — Valkey-backed, content-hash keyed (provider/model/routing_strategy/prompt_hash/context_hash/schema_hash/temperature/top_p)
- L2 Semantic Cache — LangChain `RedisSemanticCache` against a dedicated `redis-stack-server` instance (plain Valkey has no vector-search module); context-hash isolated so a hit can never cross a document boundary
- L3 Session Cache — Valkey-backed, general-purpose session-scoped store; implemented and exposed but not yet called by anything (no conversation/research-session runtime exists yet — that's the "Conversation cache" scope originally envisioned here)
- Policy resolution (`CachePolicy`: AUTO/NEVER/EXACT_ONLY/SEMANTIC/SESSION) per `CacheRuntime` (Chat/Research/Benchmark/Planner/Tool Agent/Summarizer/Reviewer/Critic)
- Streaming bypass, in-memory hit/miss/tokens-saved/cost-saved statistics, `GenerationResult.metadata["cache"]` artifact stamping

Purpose

Reduce latency and LLM costs — response caching (L1/L2) is done; the originally-envisioned conversation/response *memory* use case for L3 awaits a session-aware runtime caller.

---

### Exit Criteria

- ✅ Exact Cache operational
- ✅ Semantic Cache operational
- ✅ Session Cache operational (backend done; not yet consumed by a caller)
- ✅ Policy resolution operational
- ❌ Streaming operational — streaming requests bypass the cache by design (PRD), not yet a caching concern themselves

---

# Phase 4 — Research Platform

## Goal

Transform the RAG engine into an intelligent research system.

Workflow

```
Planner

↓

Research

↓

Summarization

↓

Review

↓

Evaluation

↓

Report

↓

Human Feedback
```

---

## Milestones

### 4.1 Planner

- Intent detection
- Task decomposition
- Research planning

---

### 4.2 Research Engine

- Internal RAG
- Knowledge retrieval
- Tool calling
- Evidence collection

---

### 4.3 Summarizer

- Evidence synthesis
- Citation preservation
- Structured summaries

---

### 4.4 Reviewer

- Gap detection
- Fact verification
- Completeness analysis

---

### 4.5 Report Generator

Outputs

- Markdown
- PDF
- Citations
- References

---

### 4.6 Human Review

Features

- Approve
- Reject
- Edit
- Feedback

---

### Exit Criteria

- End-to-end research workflow operational
- Human review integrated
- Report generation completed

# Phase 5 — Agent Platform

## Goal

Build production-grade AI agents capable of planning, reasoning,
executing tools, recovering from failures, and collaborating through
structured workflows.

This platform introduces LangGraph into ResearchMind.

The Agent Platform builds upon:

- Knowledge Platform
- AI Runtime Platform
- Research Platform

---

## Architecture

```
Planner

↓

Workflow Orchestrator (LangGraph)

↓

Agents

↓

Tools

↓

Evaluation

↓

Output
```

Planner decides.

Workflow Orchestrator executes.

Agents perform work.

---

## 5.1 Workflow Engine

### Goal

Build reusable LangGraph workflows.

Features

- Graph construction
- Nodes
- Edges
- State
- Conditional routing
- Parallel execution

Deliverable

Reusable workflow engine.

---

## 5.2 Planner

Purpose

Convert user requests into execution plans.

Responsibilities

- Intent detection
- Task decomposition
- Execution planning
- Agent selection

Deliverable

Planner abstraction.

---

## 5.3 Agent Runtime

Implement agents such as

- Research Agent
- Retrieval Agent
- Summarization Agent
- Review Agent
- Report Agent

Future

- Coding Agent
- Data Analysis Agent

Deliverable

Reusable agent runtime.

---

## 5.4 Workflow State

State management

- Shared state
- Intermediate outputs
- Agent communication
- Context propagation

Deliverable

Production workflow state.

---

## 5.5 Human Interrupts

Support

- Human approval
- Manual correction
- Resume workflow
- Reject workflow

Deliverable

Human-in-the-loop workflows.

---

## 5.6 Checkpointing

Support

- Resume execution
- Failure recovery
- Partial replay

Deliverable

Recoverable workflows.

---

## 5.7 Multi-Agent Collaboration

Support

- Planner
- Researcher
- Reviewer
- Critic
- Writer

Future

Specialized domain agents.

---

## 5.8 Agent Evaluation

Metrics

- Task completion
- Planning quality
- Tool success
- Recovery success
- Execution latency

---

### Exit Criteria

- LangGraph integrated
- Multi-agent workflows operational
- Human interrupts operational
- Checkpointing operational

---

# Phase 6 — MCP Platform

## Goal

Connect ResearchMind to external capabilities using the
Model Context Protocol (MCP).

ResearchMind should never depend directly on external services.

Instead

```
Planner

↓

MCP Manager

↓

Capability Routing

↓

External MCP Servers
```

---

## 6.1 MCP Client

Features

- MCP protocol
- Session lifecycle
- Authentication
- Connection management

Deliverable

Reusable MCP client.

---

## 6.2 MCP Registry

Purpose

Maintain every available capability.

Examples

- Scientific Search
- Climate
- GitHub
- Crypto
- NASA
- Earthquakes

Deliverable

Capability registry.

---

## 6.3 MCP Manager

Responsibilities

- Capability discovery
- Routing
- Health monitoring
- Failover
- Permission checks

Deliverable

Central MCP orchestration.

---

## 6.4 Research MCP

Capabilities

- Academic search
- Paper retrieval
- DOI lookup
- Citation lookup

---

## 6.5 Development MCP

Capabilities

- GitHub
- Documentation
- Package lookup
- API documentation

---

## 6.6 Domain MCPs

Examples

- Climate
- Earthquake
- Space
- Crypto
- Finance
- Healthcare

---

## 6.7 MCP Evaluation

Metrics

- Tool latency
- Success rate
- Failure rate
- Availability

---

### Exit Criteria

- MCP Manager operational
- Capability routing operational
- Multiple MCP servers integrated

---

# Phase 7 — AI Quality Platform

## Goal

Make AI quality measurable.

Nothing AI-related should be considered complete without evaluation.

---

## 7.1 Evaluation Framework

Features

- Evaluation abstraction
- Dataset abstraction
- Benchmark runner
- Experiment runner

Deliverable

Unified evaluation platform.

---

## 7.2 Retrieval Evaluation

Metrics

- Recall@K
- Precision@K
- MRR
- NDCG
- Latency

---

## 7.3 Generation Evaluation

Metrics

- Faithfulness
- Groundedness
- Completeness
- Citation Quality
- Hallucination Detection

---

## 7.4 Prompt Evaluation

Evaluate

- Prompt versions
- Prompt quality
- Prompt regressions

---

## 7.5 Agent Evaluation

Measure

- Planning
- Tool usage
- Reasoning
- Recovery
- Final quality

---

## 7.6 Benchmark Platform

Support

- Golden datasets
- Regression datasets
- Historical benchmarks
- Version comparisons

---

## 7.7 Experiment Tracking

Compare

- Embeddings
- Chunkers
- Retrieval strategies
- Rerankers
- Models
- Prompts

Deliverable

AI experimentation platform.

---

## 7.8 Cost & Token Analytics

Track

- Token usage
- Embedding costs
- LLM costs
- Tool costs
- Runtime costs

Deliverable

Engineering analytics.

---

## 7.9 LangSmith Integration

Use LangSmith for

- Traces
- Prompt debugging
- Chains
- Graphs
- Evaluations

---

### Exit Criteria

- Every AI subsystem measurable
- Historical benchmarks available
- Regression testing operational

---

# Phase 8 — Production Platform

## Goal

Transform ResearchMind into a production-ready AI system.

---

## 8.1 AI Observability

Logging

Metrics

Tracing

Distributed tracing

OpenTelemetry

Prometheus

Grafana

Phoenix

LangSmith

---

## 8.2 Performance Engineering

Optimize

- Latency
- Throughput
- Memory
- Cost
- Startup time

Deliverable

Performance dashboard.

---

## 8.3 Security Platform

Implement

- Authentication
- Authorization
- Prompt Injection Detection
- Jailbreak Detection
- PII Detection
- Tool Policies
- MCP Permissions
- Secret Management

Deliverable

AI security layer.

---

## 8.4 Infrastructure

Production

- Docker
- Kubernetes
- AWS
- API Gateway
- Load Balancer

Deliverable

Cloud deployment.

---

## 8.5 CI/CD

Pipeline

- Build
- Test
- Security scan
- Deployment
- Rollback

---

## 8.6 Production Operations

Support

- Blue/Green Deployment
- Canary Releases
- Feature Flags
- Backup
- Disaster Recovery

---

### Exit Criteria

- Production deployment
- Monitoring operational
- Security validated
- Performance verified

---

# Phase 9 — Enterprise Platform

## Goal

Transform ResearchMind into an enterprise-ready AI platform.

---

## 9.1 Organizations

Support

- Organizations
- Teams
- Workspaces

---

## 9.2 RBAC

Features

- Roles
- Permissions
- Policies

---

## 9.3 Multi-Tenancy

Support

- Tenant isolation
- Resource isolation
- Knowledge isolation

---

## 9.4 Billing

Track

- Usage
- Tokens
- Embeddings
- API calls

Support

- Quotas
- Limits
- Plans

---

## 9.5 Compliance

Prepare for

- GDPR
- Audit Logging
- Data Retention
- Privacy Controls

---

## 9.6 Admin Platform

Provide

- User Management
- System Health
- AI Analytics
- Evaluation Dashboard
- Cost Dashboard

---

## 9.7 Extension Platform

Support

- Plugin Framework
- Custom MCP Registration
- Third-party Extensions
- SDK

---

### Exit Criteria

- Multi-tenant
- Enterprise-ready
- Extensible
- Operational

# 10. Cross-Cutting Capabilities

These capabilities evolve throughout the entire project.

They are **not phases**.

Every platform should contribute to them.

---

## 10.1 Logging

Starts

Phase 0

Matures

Phase 8

Requirements

- Structured logging
- Correlation IDs
- Request IDs
- AI execution IDs
- JSON logs
- Error context
- Performance logs

---

## 10.2 Metrics

Starts

Phase 0

Matures

Phase 8

Collect

- Request latency
- AI latency
- Embedding latency
- Retrieval latency
- Queue latency
- Error rate
- Success rate

---

## 10.3 Tracing

Starts

Phase 2

Matures

Phase 8

Technology

- OpenTelemetry
- LangSmith
- Phoenix

Trace

```
Upload

↓

Processing

↓

Chunking

↓

Embedding

↓

Retrieval

↓

LLM

↓

Response
```

---

## 10.4 Testing

Every platform requires

- Unit Tests
- Integration Tests
- End-to-End Tests

AI Platforms additionally require

- Regression Tests
- Benchmark Tests

---

## 10.5 Documentation

Every platform requires

Architecture

↓

ADR

↓

Concept Documents

↓

Engineering Journal

↓

Implementation Guide

↓

README

---

## 10.6 Performance

Measure

- Memory
- CPU
- Cost
- Latency
- Throughput

before optimization.

---

## 10.7 Security

Introduced gradually.

Examples

- JWT
- Prompt Injection Detection
- Tool Policies
- PII Detection
- Secret Management
- Audit Logs

---

## 10.8 AI Evaluation

Evaluation is continuous.

Examples

- Retrieval quality
- Prompt quality
- Agent quality
- Citation quality
- Hallucination rate

---

## 10.9 Cost Tracking

Measure

- Embedding cost
- LLM cost
- MCP cost
- Infrastructure cost

---

## 10.10 Versioning

Version

- Prompts
- Chunkers
- Embeddings
- Workflows
- Evaluation datasets
- MCP interfaces

Everything important should be versioned.

---

# 11. AI Core Architecture

ResearchMind is organized into one central AI Core.

```
Applications

│

├── REST API

├── Workers

└── Future Web UI

        │

        ▼

AI Core

├── AI Runtime

├── AI Knowledge

├── AI Quality

├── AI Registry

└── AI Guardrails
```

---

## AI Runtime

Responsible for

- Provider Registry
- Model Registry
- Model Routing
- Prompt Registry
- Streaming
- Structured Output
- Function Calling

---

## AI Knowledge

Responsible for

- Upload
- Processing
- Chunking
- Embeddings
- Vector Store
- Retrieval
- Reranking

---

## AI Quality

Responsible for

- Evaluation
- LangSmith
- Benchmarks
- Experiment Tracking
- Regression Testing
- Cost Tracking
- Token Tracking

---

## AI Registry

Central registry of

- Providers
- Models
- Embeddings
- Rerankers
- Prompt Templates
- MCP Servers

---

## AI Guardrails

**Status (2026-07-16):** ✅ Implemented as an MVP foundation at `apps/api/app/ai/guardrails/` — exactly the target placement this document anticipated (sibling of AI Runtime/AI Knowledge/AI Quality/AI Registry), built per `guardrails_platform_prd.md` (PRD Milestone 11.16). See `PROJECT_STATUS.md`/`ROADMAP.md` for full detail.

Responsible for

- ✅ Prompt Injection Detection (input-stage, P0)
- ✅ Jailbreak Detection (folded into prompt injection — multi-trigger/DAN-style escalation)
- ✅ PII Detection (input and generation stages, foundation regex)
- 🟡 Tool Policies (foundation interface, allow-all default — no tool-call tracking exists yet)
- ✅ Safety Policies — `FailPolicy`, `RiskPolicy`, `RegenerationPolicy`, `RuntimePolicy`, weighted risk scoring
- ✅ Also built, beyond this document's original scope: Retrieval Guardrails (Context Sanitization, a new Source Trust Platform, Citation Integrity), Generation Guardrails (Faithfulness Enforcement, Schema Enforcement — both reusing Validation Platform validators), Runtime Guardrails (Budget, Loop Detection), and `GuardrailArtifactWriter` persistence
- ❌ Not yet wired into `GenerationService`, the context builder, or a router; LLM-based classifiers (Llama Guard, Lakera, NeMo Guardrails) explicitly deferred past MVP

---

# 12. Standard Milestone Lifecycle

Every milestone follows the same engineering process.

```
Problem

↓

Requirements

↓

Architecture

↓

ADR

↓

Domain Models

↓

Contracts

↓

Implementation

↓

Testing

↓

Observability

↓

Evaluation

↓

Documentation

↓

Production Review

↓

Commit

↓

Retrospective
```

No milestone is considered complete without finishing every stage.

---

# 13. Standard Platform Architecture

Every major platform follows the same internal structure.

```
Platform

├── Domain Models

├── Configuration

├── Interfaces

├── Base Classes

├── Provider Implementations

├── Registry

├── Factory (only if needed)

├── Service

├── Artifact Builder

├── Artifact Writer

├── Artifacts

├── Exceptions

└── Tests
```

This consistency makes the entire codebase predictable.

---

# 14. Architecture Decision Records (ADR)

Every important architectural decision must have an ADR.

Examples

- Why Qdrant?
- Why Voyage AI?
- Why LangGraph?
- Why canonical models?
- Why provider architecture?
- Why artifacts?
- Why Valkey?
- Why hybrid retrieval?

ADRs document

- Context
- Decision
- Alternatives
- Consequences

---

# 15. Engineering Standards

ResearchMind follows these engineering principles.

## Production First

Every implementation should be suitable for production.

---

## Simplicity First

Choose the simplest solution that satisfies today's requirements.

Avoid speculative abstractions.

---

## Platform Thinking

Build reusable platforms rather than isolated features.

---

## Replaceability

Every provider should be replaceable.

---

## Vertical Slice Development

Complete one capability end-to-end before adding infrastructure.

---

## Provider Independence

External SDKs never leak into business logic.

---

## Canonical Domain Models

Platforms communicate using canonical models.

Never SDK models.

---

## Artifacts as Contracts

Every processing stage produces immutable artifacts.

---

## Evaluation Driven Development

Every AI improvement should be measurable.

---

## Documentation First

Architecture is documented while it evolves.

Not afterwards.

---

# 16. Definition of Done

A milestone is complete only when all of the following are satisfied.

## Engineering

- Code implemented
- Code reviewed
- Clean architecture
- Static analysis passing

---

## Testing

- Unit tests
- Integration tests
- End-to-end tests

---

## Documentation

- ADR updated
- Architecture updated
- README updated
- Engineering Journal updated

---

## Observability

- Logging
- Metrics
- Error handling

---

## AI Quality

Where applicable

- Evaluation completed
- Benchmark updated
- Regression verified

---

## Production

- Configuration reviewed
- Performance reviewed
- Security reviewed

---

# 17. Learning Objectives

Every platform should teach both engineering and AI concepts.

| Platform | Engineering | AI |
|----------|-------------|----|
| Knowledge | Architecture | RAG |
| Runtime | Provider Design | LLMs |
| Research | Workflow Design | Reasoning |
| Agents | State Machines | Agent Systems |
| MCP | Distributed Systems | Tool Calling |
| Quality | Experimentation | AI Evaluation |
| Production | DevOps | AI Operations |

The goal is not simply to build software.

The goal is to become an AI Engineer.

---

# 18. Future Research Topics

These are intentionally deferred.

Knowledge

- GraphRAG
- RAPTOR
- Knowledge Graphs

Retrieval

- Hybrid Search
- Late Interaction
- ColBERT

Embeddings

- Domain Adaptation
- Fine-tuning

LLMs

- Fine-tuning
- Distillation
- Self-hosting
- vLLM

Agents

- Reflection
- Debate
- Self-Improvement

Infrastructure

- Kubernetes
- Service Mesh
- Multi-region Deployment

These topics belong after the core platform reaches production quality.

---

# 19. Roadmap Completion Criteria

ResearchMind v1.0 is complete when:

✓ Knowledge Platform is production-ready.

✓ AI Runtime is provider-independent.

✓ Research workflows are operational.

✓ Multi-agent workflows function reliably.

✓ MCP integrations are available.

✓ AI Quality platform continuously measures performance.

✓ Production infrastructure is operational.

✓ Enterprise features support organizational deployment.

At this point, ResearchMind is no longer a portfolio project.

It is a production-grade AI Engineering Platform.

---

# 20. Final Guiding Principle

ResearchMind exists to answer one question:

> "How do we build production-quality AI systems?"

Every architectural decision should move the project closer to that goal.

Whenever uncertainty arises, choose the solution that best balances:

- Simplicity
- Reliability
- Performance
- Maintainability
- Cost-effectiveness
- Learning value

The project should grow through deliberate engineering decisions rather than unnecessary complexity.

ResearchMind is not built to demonstrate every AI technology.

It is built to demonstrate sound AI engineering.

# Milestone dependency graph
```
Engineering Foundation
          │
          ▼
 Identity Platform
          │
          ▼
  Knowledge Platform
          │
          ▼
     AI Runtime
          │
          ▼
 Research Platform
          │
          ▼
   Agent Platform
          │
          ▼
    MCP Platform
          │
          ▼
  AI Quality Platform
          │
          ▼
 Production Platform
          │
          ▼
 Enterprise Platform

 ```

 ## Knowledge Platform

 ```

 Upload
   │
   ▼
Processing
   │
   ▼
Chunking
   │
   ▼
Embeddings (dense, Voyage AI)
   │
   ▼
Indexing (dense + sparse — FastEmbed SPLADE)
   │
   ▼
Vector Store (Qdrant, native hybrid) ✅
   │
   ▼
Retrieval (dense + sparse + hybrid RRF, metadata-filtered, parallel) ✅
   │
   ▼
Reranking (Voyage AI + CrossEncoder) ✅
   │
   ▼
Context Platform (Parent Expansion, Adjacent Merge, Compression, Guardrails, Citations, Prompt Formatter) 🟡 ~95%
   │
   ▼
Generation Platform (LLM providers, structured output, validation, regeneration, prompt bridge, routing, caching) 🟡 ~80% — /research API, runtime validators/contracts, artifacts remain
   │
   ▼
Guardrails Platform (Input, Retrieval, Generation, Runtime guardrails, Source Trust, policies, scoring, artifacts) ✅ MVP Foundation Complete — standalone, not yet wired into Generation Platform
```

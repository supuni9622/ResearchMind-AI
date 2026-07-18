# ResearchMind AI Roadmap

**Last Updated:** 2026-07-18

**Current Maturity:** NotebookLM++ + Perplexity v1. Hybrid Retrieval, Reranking, Parent Expansion, Compression, Context Guardrails, and strategy-based Prompt Formatting are all in place — beyond a plain NotebookLM clone. A standalone, platform-wide Guardrails Platform (Milestone 11.16 — input/retrieval/generation/runtime stages, Source Trust, policies, scoring, artifacts) is now complete as an MVP foundation, alongside the Validation Platform. The Generation Platform is now fully complete per `generation_platform_complexion_prd.md` — Routing Platform, Runtime Caching Platform (L1 exact/L2 semantic/L3 session caching, policy resolution), five runtime validation contracts (Research/Planner/Reviewer/Agent/MCP), a Validation Policy Layer (Acceptance/Fail-Fast/Runtime Validation), every PRD output validator, and Runtime Metrics Integration are all done. A Generation Runtime Platform (`generation/orchestration/`, `execute_generation()`/`GenerationRuntime.execute()`) now gives every future caller one canonical entrypoint into that stack instead of reaching into `GenerationService` directly, per `generation_runtime_platform_prd.md`. **`POST /research` is now live** — the Research API Platform (`app/ai/research/`) composes Retrieval → Context → Generation Runtime → Streaming → Artifacts into the first complete, end-to-end, cited product answer ResearchMind has ever produced, with `POST /research`, `/research/stream`, `/research/citations`, and `GET /research/{id}` (replay, backed by a new `research_sessions` table). This is deliberately linear — no query decomposition, planning, or agents yet, per `research_api_prd.md`'s own Non-Goals; that broader Research Runtime / Deep Research / Agent Platform work is next. Maturity ladder: `NotebookLM++ → Perplexity v1 (here) → Open Deep Research → Manus / Glean`.

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

**Status:** 🟡 ~95% Complete

The Context Platform sits between Reranking and Generation. It enriches, deduplicates, compresses, guards, cites, and formats retrieved knowledge before it reaches an LLM. Parent/child expansion was reclassified here from the Retrieval Platform once it became clear that ResearchMind's persisted chunk artifacts — not the vector index — are the source of truth for parent resolution.

---

### Responsibilities

- ✅ Parent Expansion
- ✅ Adjacent Merge
- ✅ Compression (Token Budget + Embedding + LangChain + LLM, V1-V4)
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

**Status:** ✅ Complete (V1-V4, Phase 3.7 per `context_platform_complexion_prd.md`)

Implemented

- ✅ Token Budget Provider (V1) — sort by score, fit into token budget
- ✅ Embedding Compression Provider (V2) — drop chunks above a similarity threshold
- ✅ LangChain Provider (V3) — query-aware extraction via `ContextualCompressionRetriever` + `LLMChainExtractor` (`langchain-classic`); wired into `ContextBuilderService.build()`'s default pipeline, gated by `settings.enable_langchain_compression` and gated on a `query` being passed
- ✅ LLM Compression Provider (V4) — per-chunk, query-aware relevant-summary compression via `GenerationService.generate()`; never drops a chunk, falls back per-chunk to original content on failure; registered but not part of `build()`'s default pipeline

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
- 🟡 Compression Platform (3 of 4 providers complete)
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

Context Assembly and the Citation Engine are already delivered by the Context Platform (Milestone 2.8). The Generation Platform (Milestone 3.1) and the Generation Runtime Platform (Milestone 3.3) are both complete. The Research API Platform (Milestone 3.4) now delivers Phase 3's first live, end-to-end research answer — deliberately linear (no decomposition/planning/agents yet); that broader scope remains this phase's next work (see Milestone 3.4's own "Remaining" list).

---

## Milestone 3.1 — Generation Platform

Status: ✅ Complete, per `generation_platform_complexion_prd.md`

Completed

- Provider Platform
- Structured Output Platform
- Validation Platform (incl. all five runtime contracts and every PRD output validator)
- Runtime Validation Platform
- Validation Policy Layer (Acceptance/Fail-Fast/Runtime Validation)
- Prompt Template Integration
- Routing Platform
- Runtime Caching Platform
- Streaming Platform (incl. `POST /api/v1/chat/stream` / `/api/v1/chat/ws`)
- Regeneration Platform
- Runtime Metrics Integration
- Generation Artifacts (incl. `metrics.json`)

Remaining

- None for this milestone — the `POST /research` API that was previously listed here is now delivered by Milestone 3.4 — Research API Platform, calling this platform through Milestone 3.3 — Generation Runtime Platform's canonical entrypoint

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
    validation/            # ValidationRegistry, ValidationService, scoring, input/output/hallucination/runtime validators, 5 runtime contracts
    policies/               # AcceptancePolicy, FailFastPolicy, RuntimeValidationPolicy
    observability/          # GenerationMetricsSnapshot, GenerationMetricsService
    langchain/              # with_structured_output() bridge (4/5 providers)
    prompts/                # template platform (pre-existing), now bridged in
    catalog/                # scored ModelMetadata + ModelCatalogRegistry
    routing/                # RoutingService — strategies, scoring, fallback chains
```

### Milestones

- ✅ Generation Core (interfaces, models, service, registry, composition root)
- ✅ Providers — Groq, OpenAI, Claude, Gemini, Ollama
- ✅ Structured Output — native provider decoding (all 5), parser/repair
  fallback, Markdown/XML registry connection, optional LangChain
  `with_structured_output()` path (OpenAI/Claude/Gemini/Ollama — Groq
  excluded, `langchain-groq` incompatible with the pinned `groq` SDK),
  regenerate-on-invalid-output loop with corrective feedback
- ✅ Validation Platform Integration — Complete

#### Input Validation
- Empty Prompt Validator
- Token Budget Validator
- Provider Limits Validator
- Context Validation Validator

#### Output Validation
- JSON Validator
- Schema Validator
- Formatting Validator
- Completeness Validator
- Consistency Validator
- Response Size Validator
- Citation Validator

#### Hallucination Validation
- Groundedness Validator
- Citation Faithfulness Checks

#### Runtime Validation
- Runtime Validation Stage
- RuntimeRegistry
- RuntimeValidationService
- Runtime Contracts — Research, Planner, Reviewer, Agent, MCP
- Generic Runtime Validators (incl. Dependency Validator)

#### Scoring
- Weighted Validation Scoring
- Overall Validation Score
- ValidationReport Aggregation

#### Validation Policy Layer
- AcceptancePolicy (Accept/Reject/Regenerate)
- FailFastPolicy (pre-flight input-validation gate before the provider call)
- RuntimeValidationPolicy (opt-in runtime-contract regeneration gate)

#### Metrics
- generation.started / generation.completed / generation.failed
- validation.started / validation.completed
- provider.started / provider.completed
- runtime.validation.started / runtime.validation.completed / runtime.validation.failed
- `GenerationMetricsService` — request/execution/token/cost/validation/guardrail metrics, Prometheus-ready counters

#### Testing
- Unit tests
- Integration tests
- Runtime validation tests

- ✅ Prompt Templates — bridged via `generate_from_template()`, reusing
  the pre-existing `generation/prompts/` platform (LangChain
  `ChatPromptTemplate`-based)
- ✅ Output Parsers — `PydanticOutputParser`/`JsonOutputParser` (LangChain,
  via `structured_output/parsers/` and the format-instructions step)
- ✅ Streaming — per-provider `stream()`, plus `POST /api/v1/chat/stream` (SSE) and `/api/v1/chat/ws` (WebSocket)
- ✅ Routing Platform — scored `ModelCatalogRegistry` (12 models), a
  15-value task-based `RoutingStrategy`, capability/policy filtering,
  a weighted scoring engine with explainable reasons, and a
  distinct-provider-preferred fallback chain; `GenerationService.generate()`
  routes automatically (with fallback retry) when no `provider` is given
- ✅ Runtime Caching Platform — L1 Exact Cache (Valkey), L2 Semantic
  Cache (LangChain `RedisSemanticCache` against a dedicated
  `redis-stack-server` instance, context-isolated), L3 Session Cache
  (implemented, not yet wired to a caller), and a `CachePolicyResolver`
  (AUTO/NEVER/EXACT_ONLY/SEMANTIC/SESSION per `CacheRuntime`); wired
  directly into `GenerationService` — see `runtime_caching_platform_prd.md`,
  ADR-027
- ✅ Artifacts — `GenerationArtifact` (request/response/metadata/metrics/
  validation/guardrails/routing/cache.json), persisted on every
  `generate()` call
- ✅ `POST /research` API — delivered by Milestone 3.4 — Research API Platform (below), via Milestone 3.3 — Generation Runtime Platform

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

## Milestone 3.3 — Generation Runtime Platform

Status: ✅ Complete, per `generation_runtime_platform_prd.md`

Completed

- `generation/orchestration/` (`context.py`, `state.py`, `interfaces.py`, `orchestrator.py`, `create.py`)
- Canonical entrypoint — `execute_generation(request, provider=None) -> GenerationResult` and `GenerationRuntime.execute()`
- FastAPI dependency — `get_generation_runtime()`
- 11 new unit tests, all passing

### Goal

Give every future runtime caller (Research/Planner/Reviewer/Agent/MCP) one canonical entrypoint into the Generation Platform instead of each reaching into `GenerationService` directly, tagging `GenerationRequest.runtime` to identify themselves.

### Notes

Deliberately thin — it does not re-implement anything. `GenerationService.generate()` already runs the full frozen ordering (input validation → input guardrails → routing → cache → provider execution → structured outputs → generation guardrails → output validation → runtime validation → metrics → artifacts) delivered by Milestone 3.1; this platform only orchestrates that call. Explicit Non-Goals honored: no state machines, no DAGs, no LangGraph duplication.

### Deliverable

One canonical Generation Runtime entrypoint, now the first real caller of which is Milestone 3.4 — Research API Platform.

---

## Milestone 3.4 — Research API Platform

Status: ✅ Complete, per `research_api_prd.md` — **the first live, end-to-end product surface in ResearchMind.** For the first time, a user can upload documents, ask a question, and get a grounded, cited, streamable answer back — the "NotebookLM + Perplexity" product vision.

Completed

- Routes — `POST /research`, `POST /research/stream` (SSE), `POST /research/citations`, `GET /research/{id}` (replay). All auth-required, all owner-scoped.
- `ResearchService` (`apps/api/app/ai/research/service.py`) — composes, for the first time in one flow, the Retrieval Platform (hybrid search + rerank) → Context Platform (dedup/expand/merge/compress/cite) → Generation Runtime Platform (Milestone 3.3 — its first real caller) → Streaming Platform (for `/research/stream`) → Artifact Platform (best-effort persistence, via the previously-unwired Research artifact writer)
- New Postgres table `research_sessions` (model + repository + Alembic migration `37117c83beb2_create_research_sessions_table`) — the first persistent, replayable Q&A history in the product
- `RuntimeType.RESEARCH` (Runtime Validation Platform) and `ArtifactRuntime.RESEARCH` (Artifact Platform) go from reserved-but-unused enum values to actually-exercised-by-live-code
- 23 new tests (unit + integration), full suite passing, ruff/mypy clean

Remaining

- Query decomposition, research planning/multi-step loops, agents, LangGraph — deliberately out of scope per this milestone's own PRD Non-Goals; named as what comes next: a Research Runtime, a Deep Research Runtime, and an Agent Platform (Phase 4 — Agentic AI Platform, below)

### Goal

Deliver the first complete, grounded, cited question-answering product experience over a user's own documents.

### Deliverable

`POST /research` — a real, authenticated, owner-scoped, citation-backed research answer, streamable and replayable.

---

## Milestone 3.5 — Research Frontend Integration

Status: ✅ Complete — `apps/web`'s Research page now consumes the live Research API instead of a mock.

Completed

- Deleted `apps/web/src/features/research/mock-engine.ts`; added `use-research.ts` (per-turn state machine: `searching` → `generating` → `done`/`error`, `localStorage`-backed history) and `lib/sse.ts` (a `fetch` + `ReadableStream` SSE client — not a bare `EventSource`, since this platform's auth is a bearer token `EventSource` can't attach)
- New `citation-card.tsx`; `research-block`/`research-composer`/`research-sidebar`/`source-card`/`source-panel`/`streaming-status`/`types.ts`/`lib/api.ts` updated to the real API contract

### Findings — three backend bugs found and fixed while validating against live infra

1. `ResearchService.stream_research()` checked only `CoreEventType.COMPLETE` ("complete") to detect "generation finished," but a live (non-cache-hit) provider stream actually emits `StreamEventType.COMPLETED` ("completed") — `CoreEventType.COMPLETE` is cache-hit-replay-only. Every real streamed research turn silently never wrote its `research_sessions` row. Fixed by checking both values.
2. `claude-sonnet-4` and its dated `-20250514` snapshot are fully retired from the configured Anthropic account (confirmed against `GET /v1/models`). Updated every hardcoded reference (`.env`, `.env.example`, `core/settings.py`, `generation/config.py`, `generation/catalog/models.py`, `generation/prompts/service.py`, `generation/observability/token_counter.py`) to `claude-sonnet-5`.
3. `claude-sonnet-5` rejects the `temperature` parameter outright (400, effort-based reasoning model, not classic sampling). `ClaudeProvider` now retries once without `temperature` on that specific error instead of hardcoding a model-name list.

### To-Do / Open Items

- Chat has a complete backend (`/chat/stream`, `/chat/ws`) but zero frontend surface — `apps/web`'s nav is Dashboard/Research/Documents only. Deferred design decision: separate "Chat" nav entry/page (mirrors the backend's already-separate persistence + no-retrieval-grounding) vs. a unified input with a mode toggle.
- `_sse_byte_stream` (`runtime/generation/streaming/transports/sse.py`) only catches `TimeoutError`/`StopAsyncIteration` around `events.__anext__()` — any other exception propagates unhandled and silently kills the SSE connection with no client-visible `error` event. Not yet hardened.
- No automated check for upstream model deprecations — Finding 2 above was only caught via a live 404 during manual testing, not proactively.

---

## Milestone 11.16 — Guardrails Platform

**Status:** ✅ Complete (MVP Foundation, per `guardrails_platform_prd.md`)

A new, standalone, platform-wide package (`apps/api/app/ai/guardrails/`, sibling to `knowledge/`, `runtime/`, `quality/`) answering a different question than the Validation Platform: not "did the system produce a good output?" but "should the system even perform this operation?" Spans Input → Retrieval → Generation → Runtime stages, built to the same conventions as the Validation Platform (deterministic checks, a crash-safe `GuardrailService`, weighted risk scoring, an `@lru_cache` composition root).

```text
User
 ↓
Input Guardrails
 ↓
Planner
 ↓
Retrieval
 ↓
Retrieval Guardrails
 ↓
Context Platform
 ↓
Generation
 ↓
Generation Guardrails
 ↓
Runtime Guardrails
 ↓
Reflection / Evaluation
```

### 11.16.1 Foundation

**Status:** ✅ Complete

- `models.py`/`enums.py`/`interfaces.py` — `GuardrailIssue`, `GuardrailResult`, `GuardrailReport`; one ABC per stage
- `GuardrailRegistry` — per-stage ordered registration, mirrors `ValidationRegistry`
- `GuardrailService` — `evaluate_input()`/`evaluate_retrieval()`/`evaluate_generation()`/`evaluate_runtime()`/`evaluate()`; a crashing guardrail becomes a WARNING issue rather than propagating
- `policies/` — `FailPolicy`, `RiskPolicy`, `RegenerationPolicy`, `RuntimePolicy`
- `scoring/` — weighted `overall_risk` (0.30/0.30/0.20/0.20 input/retrieval/generation/runtime), renormalized over whichever stages scored
- `artifacts/` — `GuardrailArtifactWriter`, persisting `guardrails/{run_id}/{input,retrieval,generation,runtime,report}.json`
- `create.py` — `get_guardrail_service()`, the integration seam for future callers

### 11.16.2 Input Guardrails

**Status:** ✅ Complete (P0 items) / 🟡 Foundation (rate limit, toxicity)

- ✅ Prompt Injection / Jailbreak detection (P0)
- ✅ Scope Validation (off-topic heuristic, WARNING-only by design)
- ✅ PII Detection (foundation regex)
- 🟡 Rate Limiting, Toxicity — foundation interfaces, always-allow (no request-counting state or classifier provider exists yet)

### 11.16.3 Retrieval Guardrails

**Status:** ✅ Complete (P0/P1 items) / 🟡 Foundation (access control)

- ✅ Context Sanitization (P0) — composes the pre-existing `ContextGuardrailService`/`RuleBasedGuardrailProvider` (Milestone 2.8.4) rather than duplicating it
- ✅ Source Trust Platform (P1, new) — `SourceType` enum, `TrustRegistry`, trust policies/scoring; defaults every chunk to `USER_DOCUMENT` since no source-type field exists on `ContextChunk` yet
- ✅ Citation Integrity — deterministic existence check, complementary to the Validation Platform's fabricated-citation-marker check
- 🟡 Access Control — foundation interface, permissive default (no tenant isolation/document ACL model exists yet)

### 11.16.4 Generation Guardrails

**Status:** ✅ Complete (P1 items) / 🟡 Foundation (moderation)

- ✅ Faithfulness Enforcement (P1) — wraps the Validation Platform's `HallucinationValidator`, reinterpreting low groundedness as ERROR (regenerate-worthy) rather than Validation's advisory WARNING
- ✅ Schema Enforcement — wraps `SchemaValidator`/`JsonValidator`, per the PRD's explicit reuse instruction
- ✅ PII Leakage (foundation regex, same table as the input-side check)
- 🟡 Moderation — foundation interface, always-allow (PRD explicitly skips real moderation providers for MVP)

### 11.16.5 Runtime Guardrails

**Status:** ✅ Complete (P1 items) / 🟡 Foundation (tool policy, approval gate)

- ✅ Budget Guardrail (P1, "implement immediately") — max_tokens/max_cost/max_tool_calls/max_iterations/max_runtime_seconds, independent threshold + near-limit warning checks
- ✅ Loop Detection — foundation depth, real algorithm (max-iterations + repeated-execution-state-hash detection)
- 🟡 Tool Policy — foundation interface, allow-all default
- 🟡 Approval Gate — `ApprovalRequest`/`ApprovalResponse` + `ApprovalGateInterface` only, deliberately unimplemented and unregistered (the future LangGraph-interrupt seam, PRD §19)

### Dead Code Removed

Two empty, zero-reference scaffolds discovered during this work: `app/ai/guardrails/{policies.py,scanners.py}` and the entire (all 0-byte) `app/ai/runtime/generation/guardrails/` tree.

### Testing

113 new unit tests under `tests/unit/ai/guardrails/`, mirroring the Validation Platform's test-tree conventions. Full repo suite (744 tests), `ruff format --check`, `ruff check`, and `mypy` all pass clean.

### Not Yet Built (by design — matches PRD MVP scope)

- ❌ LLM-based classifiers (Llama Guard, Lakera, NeMo Guardrails) — explicitly skipped for MVP
- ❌ Wiring into `GenerationService`, the context builder, or a router (PRD's "Phase 6 — Generation Integration", intentionally deferred, same as the Validation Platform)
- ❌ Enterprise ACL / multi-tenant Access Control, real Tool Policy providers, a working Approval Gate implementation (LangGraph interrupts/checkpoints)
- ❌ Security dashboards, attack datasets, red-teaming

### Deliverable

A complete, tested, standalone safety/policy layer ready to be wired into the Generation Platform and future Research Runtime without further architectural refactoring — matches the PRD's explicit goal of shipping interfaces/contracts for Research Runtime, Multi-Agent Runtime, MCP Platform, and Enterprise Multi-Tenancy ahead of those platforms existing.

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
| Phase 2.8 — Context Platform | ✅ Complete (Parent Expansion, Adjacent Merge, Compression V1-V4, Guardrails V1, Citations, Prompt Formatter — Phase 3.7, `context_platform_complexion_prd.md`) |
| Phase 2.9 — Conversation Memory Platform | ⏳ Planned |
| Phase 2.10 — Knowledge Service | ⏳ Planned |
| Phase 3.1 — Generation Platform | ✅ Complete, per `generation_platform_complexion_prd.md` (structured output, input/output/hallucination/runtime validation + scoring, five runtime contracts, Acceptance/Fail-Fast/Runtime Validation policy layer, every PRD output validator, regeneration, prompt bridge, Routing Platform, Runtime Caching Platform, Streaming Platform, Runtime Metrics Integration, Artifact Platform done) |
| Phase 3.2 — LangChain Adoption for Generation | 🟡 Mostly Complete for structured output (LCEL not adopted) |
| Phase 3.3 — Generation Runtime Platform | ✅ Complete, per `generation_runtime_platform_prd.md` (canonical `execute_generation()`/`GenerationRuntime.execute()` entrypoint, `generation/orchestration/`, `get_generation_runtime()` dependency, 11 new tests) |
| Phase 3.4 — Research API Platform | ✅ Complete, per `research_api_prd.md` — first live, end-to-end product surface (`POST /research`, `/research/stream`, `/research/citations`, `GET /research/{id}`; `research_sessions` table; 23 new tests) |
| Milestone 3.5 — Research Frontend Integration | ✅ Complete — `apps/web` wired to the live Research API (real SSE, `mock-engine.ts` removed); 3 backend bugs found + fixed (stream-completion event mismatch, retired Claude model, `temperature` rejected by new model) |
| Milestone 11.16 — Guardrails Platform | ✅ Complete (MVP Foundation — input/retrieval/generation/runtime guardrails, Source Trust, policies, scoring, artifacts; standalone, not yet wired into the generation pipeline) |
| Phase 3 — Research Engine (broader) | 🟡 First live product surface delivered (Phase 3.4); query decomposition, planning, and a multi-step Research Runtime still planned |
| Phase 4 — Agentic AI Platform | ⏳ Planned |
| Phase 5 — Experimentation Platform | ⏳ Planned |
| Phase 6 — MCP Ecosystem | ⏳ Planned |
| Phase 7 — Production Platform | ⏳ Planned |

---

# Current Focus

## Phase 2.8 — Context Platform (✅ complete) + Phase 3.1 — Generation Platform (✅ complete) + Phase 3.4 — Research API Platform (✅ complete)

Vector Store, Retrieval (dense/sparse/hybrid/parallel), Metadata Filtering, and Reranking are all complete (Phases 2.5–2.7). The Context Platform (Phase 2.8) is 100% complete (Phase 3.7, `context_platform_complexion_prd.md`). The Generation Platform (Phase 3.1) is now 100% complete, per `generation_platform_complexion_prd.md`: Provider Structured Output Integration (native decoding for all 5 providers, parser/repair fallback, Markdown/XML registry connection, an optional LangChain `with_structured_output()` path), Validation Platform integration (input/output/hallucination/runtime validators, a `ValidationRegistry`, weighted scoring, a multi-stage `ValidationReport`, and five runtime contracts — Research/Planner/Reviewer/Agent/MCP), a Validation Policy Layer (`AcceptancePolicy`/`FailFastPolicy`/`RuntimeValidationPolicy`, `generation/policies/`), a regenerate-on-invalid-output loop (now policy-driven, still correctly scoped to only the output stage plus an opt-in runtime-stage gate), a provider-capability-mismatch guard, a Prompt Platform → Generation bridge (`generate_from_template()` with schema-aware format instructions), a Routing Platform (scored `ModelCatalogRegistry`, 15-value task-based `RoutingStrategy`, weighted scoring engine, distinct-provider-preferred fallback chains, automatic routing inside `GenerationService.generate()`), a Runtime Caching Platform (L1 Exact/L2 Semantic/L3 Session caching, policy resolution, wired directly into the provider-call path), Runtime Metrics Integration (`GenerationMetricsService`, `generation/observability/`), and Artifact persistence (`GenerationArtifact` incl. a `metrics.json` snapshot) are all done. Detail: `docs/architecture/structured-output-platform.md`, `docs/architecture/model-routing-platform.md` (ADR-026), and `docs/architecture/runtime-caching-platform.md` (ADR-027).

Phase 3.3 — Generation Runtime Platform is now complete, per `generation_runtime_platform_prd.md`: a thin `generation/orchestration/` layer gives every future runtime caller one canonical `execute_generation()`/`GenerationRuntime.execute()` entrypoint into the already-complete Generation Platform stack, instead of reaching into `GenerationService` directly. Phase 3.4 — Research API Platform is now complete, per `research_api_prd.md`: `POST /research`, `/research/stream`, `/research/citations`, and `GET /research/{id}` compose Retrieval → Context → Generation Runtime → Streaming → Artifacts into ResearchMind's first live, end-to-end, cited product answer, backed by a new `research_sessions` table for replay. `RuntimeType.RESEARCH` and `ArtifactRuntime.RESEARCH` go from reserved to actually-exercised.

Only remaining items nearby:

- Query decomposition, research planning/multi-step loops, and agents — deliberately out of scope for Phase 3.4 per its own PRD Non-Goals; this is the future Research Runtime / Deep Research Runtime / Agent Platform work (see item 11 below)
- Adaptive/evaluation-driven and budget-aware routing, A/B experimentation (Routing Platform Phase 2+ — explicitly future work, not MVP scope)
- Wiring Session Cache (L3, implemented) to an actual conversation/research-session caller
- Test suite for `artifacts/` (`validation/`, `providers/`, `prompts/`, `routing/`, `catalog/`, `caching/`, and core `service.py` now have unit test coverage)
- Wiring the now-complete Guardrails Platform (Milestone 11.16 — see above) into `GenerationService`

Phase 2.8 — Context Platform is now complete (compression V1-V4, and the LangChain provider is wired into `ContextBuilderService.build()`'s default pipeline behind `settings.enable_langchain_compression`). Remaining nearby scope:

- Conversation Memory Platform (Phase 2.9)
- Knowledge Service — unified orchestration API (Phase 2.10)
- Forward `HybridRetrieveRequest.rerank` from `/retrieve/hybrid` into `RetrievalService.search_hybrid` (currently always uses the service's `rerank=True` default)
- Multi-query Retrieval (query decomposition moved to the future Research Runtime)

The **Guardrails Platform** (Milestone 11.16, see above) is now complete as a standalone MVP foundation and needs no further work to reach its PRD-defined MVP scope — remaining work on it is entirely the future "Generation Integration" wiring phase, not new guardrail logic.

## Milestone 3.5 — Research Frontend Integration (✅ complete)

`apps/web`'s Research page now calls the live `/research`/`/research/stream` APIs for the first time (real SSE via `use-research.ts`/`lib/sse.ts`, `mock-engine.ts` deleted) — see Milestone 3.5 above for full detail, the three backend bugs found and fixed while validating it end-to-end (a stream-completion event-type mismatch that silently dropped every `research_sessions` row, a fully-retired Claude model, and Claude Sonnet 5 rejecting the `temperature` parameter), and the open to-do list. The most significant open item isn't a bug: **Chat has a complete backend but no frontend surface at all**, and how to present it alongside Research (separate nav/page vs. a unified mode-toggle input) is a deliberately deferred design discussion.

---

# Next Major Milestones

This project intentionally prioritizes completing the production AI platform (Tier 1) before expanding engineering tooling (Tier 2/3 — Observability, Benchmarking, Experimentation).

1. ~~Vector Store Platform (Phase 2.5)~~ ✅
2. ~~Retrieval Platform (Phase 2.6)~~ ✅
3. ~~Reranking Platform (Phase 2.7)~~ ✅
4. ~~Context Platform (Phase 2.8) — Parent Expansion, Adjacent Merge, Compression V1-V4, Guardrails V1, Citations, Prompt Formatter~~ ✅ Complete
5. ~~Generation Platform (Phase 3.1)~~ ✅ Complete, per `generation_platform_complexion_prd.md` — five runtime contracts, validation policy layer, every output validator, runtime metrics, and artifact persistence all done
6. ~~LangChain Adoption for Generation (Phase 3.2)~~ 🟡 mostly complete for structured output (LCEL not adopted)
7. ~~Guardrails Platform (Milestone 11.16) — input/retrieval/generation/runtime guardrails, Source Trust, policies, scoring, artifacts~~ ✅ MVP foundation complete; wiring into `GenerationService` is future work
8. ~~Generation Runtime Platform (Phase 3.3)~~ ✅ Complete, per `generation_runtime_platform_prd.md` — canonical `execute_generation()`/`GenerationRuntime.execute()` entrypoint, `generation/orchestration/`, no state machines/DAGs/LangGraph duplication
9. ~~Research API Platform (Phase 3.4)~~ ✅ Complete, per `research_api_prd.md` — first live, end-to-end product surface: `POST /research`/`/research/stream`/`/research/citations`/`GET /research/{id}`, `research_sessions` table, `RuntimeType.RESEARCH`/`ArtifactRuntime.RESEARCH` now exercised
10. ~~Research Frontend Integration (Milestone 3.5)~~ ✅ Complete — `apps/web` wired to the live Research API; 3 backend bugs found + fixed along the way
11. **Decide Chat vs. Research frontend UX** (deferred design discussion) — separate nav entry/page vs. a unified mode-toggle input; Chat currently has no frontend surface at all
12. Conversation Memory Platform (Phase 2.9)
13. Knowledge Service (Phase 2.10)
14. Evaluation Platform expansion (NDCG, Groundedness, Faithfulness, Hallucinations, Citation Accuracy, End-to-End, Security Evaluation)
15. Research Runtime — Query Decomposition, Planner, Research Agents, Reviewer, Summarizer, LangGraph (builds on the now-complete Research API Platform)
16. Agentic AI Platform
17. Long-Term Platform — Research Sessions, Memory, MCP, Feedback Learning
18. Advanced Observability, Experimentation Platform (deferred until the core RAG pipeline is complete)

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

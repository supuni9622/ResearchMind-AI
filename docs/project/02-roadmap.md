# ResearchMind AI — Project Roadmap

**Version:** 1.0

---

# Purpose

This roadmap defines the implementation plan for ResearchMind AI.

It serves as the single source of truth for project progress, milestone traceability, and implementation order.

The roadmap is intentionally incremental.

Each milestone should produce a working, production-quality capability before progressing to the next.

---

# Project Progress

| Phase                           | Status         |
| ------------------------------- | -------------- |
| Phase 0 — Foundation            | ✅ Complete     |
| Phase 1 — Identity Platform     | ✅ Complete     |
| Phase 2 — Knowledge Platform    | 🟡 In Progress |
| Phase 3 — Conversation Platform | ⏳ Planned      |
| Phase 4 — Research Platform     | ⏳ Planned      |
| Phase 5 — AI Agent Platform     | ⏳ Planned      |
| Phase 6 — MCP Platform          | ⏳ Planned      |
| Phase 7 — Evaluation Platform   | ⏳ Planned      |
| Phase 8 — Production Platform   | ⏳ Planned      |
| Phase 9 — Enterprise Platform   | ⏳ Planned      |

---

# Phase 0 — Foundation ✅

## Goal

Establish the production backend foundation.

### Completed

* FastAPI
* Docker Compose
* PostgreSQL
* Valkey
* Qdrant
* SQLAlchemy
* Alembic
* Structlog
* Configuration
* Middleware
* Health endpoint
* Development tooling
* Testing foundation

### Deliverable

Production-ready backend foundation.

---

# Phase 1 — Identity Platform ✅

## Goal

Implement secure authentication and user management.

### 1.1 Configuration

✅ Completed

### 1.2 Database Foundation

✅ Completed

### 1.3 User Domain

✅ Completed

* User entity
* Repository
* Service

### 1.4 Authentication

✅ Completed

* AWS Cognito
* JWT verification
* Authentication provider
* User synchronization
* Protected endpoints

### Deliverable

Secure production authentication platform.

---

# Phase 2 — Knowledge Platform 🟡

## Goal

Build the complete Retrieval-Augmented Generation (RAG) knowledge pipeline.

---

## 2.1 Document Upload ✅

### Status

Completed

### Engineering

* Document entity
* Upload API
* Validation
* SHA-256 hashing
* S3 integration
* Repository
* Dependency Injection
* Structured logging

### AI Learning

* Document lifecycle
* Cloud object storage
* Upload architecture

### Deliverable

Authenticated document upload pipeline.

---

## 2.2 Document Processing ✅

### Status

Completed

### Engineering

* Processing pipeline
* Processing service
* Parser architecture
* Processing status
* Error handling
* Background processing hooks

### AI Learning

* Document ingestion
* Parsing strategies
* Metadata extraction
* Processing pipelines

### Deliverable

Normalized document content ready for chunking.

---

## 2.3 Chunking Platform ✅

### Engineering

Implemented chunking strategies.

* Fixed
* Recursive
* Markdown

Deferred: Semantic, Parent-child, Agentic chunking.

### AI Learning

* Chunk quality
* Context preservation
* Chunk overlap
* Token optimization

### Evaluation

Chunking Benchmark compares strategies (`benchmarks/chunking/`).

### Deliverable

Modular chunking platform. ✅ Complete

---

## 2.4 Embedding Platform ✅

### Engineering

* Embedding service
* Batching
* Retry handling
* Caching (Valkey-backed, TTL-based)

### Models

Implemented

* Sentence Transformers
* Voyage AI
* OpenAI

Deferred: BGE, E5, Nomic, Instructor.

### AI Learning

* Embedding dimensions
* Similarity search
* Model selection
* Cost vs quality

### Deliverable

Provider-independent embedding platform. ✅ Complete

---

## 2.5 Vector Platform ✅

### Engineering

* Qdrant collections (named dense + sparse vectors, ADR-019)
* Payloads
* Metadata
* Indexes

### AI Learning

* Vector databases
* Filtering
* Indexing
* Similarity search

### Deliverable

Production vector store. ✅ Complete

---

## 2.6 Retrieval Platform ✅

### Status

Complete — see Milestone 2.7 in `PROJECT_STATUS.md` for full detail.

### Query Processing

* ✅ Validation
* ✅ Normalization

### Search Engines

* ✅ Semantic (dense) search
* ✅ Sparse search
* ✅ Hybrid search

### Retrieval Strategies

* ✅ Standard retrieval
* ✅ Parallel retrieval (dense + sparse via `asyncio.gather`)
* 🔄 Parent/Child retrieval — reclassified into the Context Platform (2.9), implemented as Parent Expansion + Adjacent Merge
* ❌ Query decomposition — moved to the future Research Runtime

### Result Processing

* ✅ RRF fusion
* ✅ Metadata filtering (`owner_id`, `document_id`, `filename`, `language`; server-enforced `owner_id`)
* ✅ Voyage reranking
* ✅ CrossEncoder reranking
* ✅ Top-K selection

### Performance

* ✅ Query embedding cache
* ❌ Retrieval cache

### Evaluation

* ✅ Recall@K
* ✅ Precision@K
* ✅ MRR
* ✅ NDCG@K
* ✅ Latency
* ✅ Cost (qualitative)

### Research APIs

* ✅ `POST /retrieve`
* ✅ `POST /retrieve/sparse`
* ✅ `POST /retrieve/hybrid`
* ❌ `POST /research` — Generation Platform is now complete (see Phase 3 note below, and `generation_platform_complexion_prd.md`); `/research` itself is still pending a Research Runtime
* ✅ Streaming chat — `POST /api/v1/chat/stream` (SSE) and `/api/v1/chat/ws` (WebSocket)
* ✅ Citations — delivered by the Context Platform's Citation Platform (2.9)

### AI Learning

* Recall
* Precision
* Retrieval quality
* Reciprocal Rank Fusion

### Deliverable

Production retrieval engine. ✅ Complete — dense/sparse/hybrid/parallel search, metadata filtering, reranking, and evaluation all done.

---

## 2.7 Reranking ✅

### Engineering

* ✅ Voyage AI (`rerank-2`)
* ✅ Cross Encoder (local `BAAI/bge-reranker-base`)
* Late Interaction / ColBERT — future research topic, not started

### AI Learning

* Reranking quality
* Precision improvements

### Deliverable

Production reranking pipeline. ✅ Complete — wired into `RetrievalService.search_hybrid(rerank=True)` by default.

---

## 2.8 Knowledge Evaluation 🟡

### Engineering

Evaluate

* ✅ Precision
* ✅ Recall
* ✅ NDCG
* ✅ MRR
* ✅ Latency
* ✅ Cost (qualitative)

Retrieval and reranking metrics are implemented via the Retrieval and
Reranking Benchmarks (`benchmarks/retrieval/`, `benchmarks/reranking/`,
ADR-020). Generation and end-to-end pipeline evaluation
(Groundedness, Faithfulness, Hallucinations, Citation Accuracy,
Security Evaluation) are not yet started — see Phase 7 below.

### Deliverable

Evaluation-driven RAG platform. 🟡 In Progress — retrieval and reranking evaluation done; generation-side evaluation pending the Generation Platform.

---

## 2.9 Context Platform 🟡

### Status

~90% Complete

### Engineering

* ✅ Parent Expansion (`ChunkArtifactReader`, `ParentExpansionService`)
* ✅ Adjacent Merge (`AdjacentMergeService`)
* 🟡 Compression — Token Budget (V1) ✅, Embedding Redundancy (V2) ✅, LangChain (V3) ❌, LLM Compression (V4) ❌
* ✅ Context Guardrails V1 — provider architecture, `RuleBasedGuardrailProvider`, risk scoring, statistics
* ✅ Citation Platform — citation IDs, pages, headings, chunk IDs
* ✅ Prompt Formatter — strategy-based (`DEFAULT`, `NOTEBOOKLM`, `PERPLEXITY`, `RESEARCH`, `AGENT`)

A key architectural decision this milestone: parent/child retrieval was
reclassified out of the Retrieval Platform (2.6) into the Context
Platform, since ResearchMind's persisted chunk artifacts — not the
vector index — are the source of truth for parent resolution.

### AI Learning

* Context assembly
* Compression trade-offs
* Guardrail risk scoring
* Prompt strategy design

### Deliverable

Production context-building pipeline feeding the Generation Platform. 🟡 In Progress — LangChain and LLM compression remain before this milestone closes.

---

## 2.10 Guardrails Platform ✅

### Status

Complete (MVP Foundation, per `guardrails_platform_prd.md` — Milestone 11.16 in `PROJECT_STATUS.md`/`ROADMAP.md`)

### Engineering

* ✅ New standalone package (`apps/api/app/ai/guardrails/`, sibling to `knowledge/`, `runtime/`, `quality/`) — a different question than Validation ("should we do this?" vs. "did it work?")
* ✅ Input Guardrails — prompt injection/jailbreak detection, scope validation, PII detection; rate limit/toxicity are foundation interfaces (always-allow)
* ✅ Retrieval Guardrails — Context Sanitization (composes the existing `ContextGuardrailService` from 2.9 rather than duplicating it), a new Source Trust Platform, Citation Integrity; Access Control is a foundation interface
* ✅ Generation Guardrails — Faithfulness Enforcement and Schema Enforcement (both wrap the Validation Platform's validators), PII Leakage; Moderation is a foundation interface
* ✅ Runtime Guardrails — Budget Guardrail, Loop Detection (real algorithm); Tool Policy and Approval Gate are foundation interfaces only, deliberately unimplemented (the future LangGraph-interrupt seam)
* ✅ `GuardrailService` (crash-safe aggregation), `GuardrailRegistry`, weighted risk scoring, fail/risk/regeneration/runtime policies, `GuardrailArtifactWriter`
* ✅ 113 new unit tests; two dead, zero-reference scaffolds removed
* ❌ Wiring into `GenerationService`, the context builder, or a router — intentionally deferred, same posture the Validation Platform shipped with

### AI Learning

* Policy layer design distinct from quality validation
* Deterministic guardrail scoring vs. LLM-based classifiers
* Reuse vs. duplication trade-offs across sibling platforms

### Deliverable

Complete, tested, standalone safety/policy layer ready to be wired into the Generation Platform and future Research Runtime without further architectural refactoring.

---

# Phase 3 — Conversation Platform

**Note:** The **Generation Platform** (multi-provider LLM runtime — Groq, OpenAI, Claude, Gemini, Ollama; prompt templates; validation; streaming) is now complete, per `generation_platform_complexion_prd.md` — only a `/research` API remains, blocked on a Research Runtime that doesn't exist yet. It is the direct consumer of the Context Platform's `Prompt Context` output; status is tracked in `phase-3-ai-runtime-roadmap.md` (Phase 3.8) and `ROADMAP.md` (Phase 3.1), both more current than this file.

## Goal

Build a production conversational AI platform.

### Milestones

* Conversation management
* Session management
* Streaming responses
* Conversation memory
* Semantic cache
* Conversation evaluation

### Deliverable

Production chat platform.

---

# Phase 4 — Research Platform

## Goal

Transform ResearchMind into a research assistant.

### Milestones

* Planner
* Research agent
* Summarizer
* Reviewer
* Report generator
* Human feedback
* Research sessions

### Deliverable

End-to-end research workflow.

---

# Phase 5 — AI Agent Platform

## Goal

Introduce production-grade agent orchestration.

### Milestones

* LangGraph
* Workflow engine
* Checkpointing
* Interrupts
* Multi-agent collaboration
* Agent memory
* Agent evaluation

### Deliverable

Production multi-agent platform.

---

# Phase 6 — MCP Platform

## Goal

Consume external capabilities through Model Context Protocol.

### Milestones

* MCP client
* Registry
* Manager
* Research MCP
* Climate MCP
* Earthquake MCP
* Future domain MCPs

### Deliverable

Domain-independent AI orchestration platform.

---

# Phase 7 — Evaluation Platform

## Goal

Build evaluation into every AI subsystem.

### Milestones

### Retrieval

* Precision
* Recall
* NDCG
* MRR

### Generation

* Faithfulness
* Groundedness
* Citation quality

### Agents

* Planning quality
* Tool success
* Completion rate

### Platform

* LangSmith
* Phoenix
* Benchmark datasets
* Regression testing

### Deliverable

Evaluation-driven AI engineering platform.

---

# Phase 8 — Production Platform

## Goal

Prepare ResearchMind for production deployment.

### Milestones

* Docker
* Kubernetes / ECS
* CI/CD
* OpenTelemetry
* Prometheus
* Grafana
* Performance optimization
* Security
* Cost optimization

### Deliverable

Production deployment platform.

---

# Phase 9 — Enterprise Platform

## Goal

Enterprise readiness.

### Milestones

* RBAC
* Multi-tenancy
* Billing
* Compliance
* Admin portal
* Plugin framework

### Deliverable

Enterprise AI platform.

---

# Cross-Cutting Engineering Capabilities

These capabilities evolve continuously throughout the roadmap.

| Capability            | Starts  | Matures    |
| --------------------- | ------- | ---------- |
| Structured Logging    | Phase 0 | Phase 8    |
| Metrics               | Phase 0 | Phase 8    |
| Tracing               | Phase 2 | Phase 8    |
| AI Evaluation         | Phase 2 | Phase 7    |
| Testing               | Phase 0 | Continuous |
| Security              | Phase 0 | Phase 9    |
| Performance           | Phase 0 | Phase 8    |
| Cost Tracking         | Phase 2 | Phase 8    |
| Engineering Analytics | Phase 2 | Phase 8    |
| LangSmith             | Phase 2 | Continuous |

---

# AI Learning Roadmap

Every milestone should strengthen knowledge in four dimensions.

| Dimension    | Focus                                          |
| ------------ | ---------------------------------------------- |
| Engineering  | Architecture, clean code, testing, scalability |
| AI           | RAG, embeddings, retrieval, prompting, agents  |
| Production   | Docker, AWS, observability, deployment         |
| Architecture | Trade-offs, ADRs, system design                |

The project should not only produce working software but also develop practical AI engineering expertise through real-world implementation and experimentation.

---

# Roadmap Rules

* Complete one milestone before starting the next.
* Every milestone ends with testing and documentation.
* Freeze architectural decisions once implemented.
* Prioritize implementation over redesign.
* Compare AI approaches using evaluation rather than opinion.
* Keep the project focused on becoming a production-grade AI engineering platform.

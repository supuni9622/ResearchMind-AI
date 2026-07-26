# ResearchMind AI — Roadmap

**Version:** 3.0 (Unified)
**Last Updated:** 2026-07-26
**Status:** Living document — single source of truth for project progress, milestone traceability, and implementation order.

**2026-07-26 note:** Phase 5 gained a Research Intelligence MCP paper-search
platform (ADR-037) — see below. This is ResearchMind's first MCP **client**
integration (one external server, one tool, two call sites), not the
general-purpose Phase 6 (Agentic AI) / Phase 7 (MCP Ecosystem) work, both of
which remain unstarted and deferred per ADR-033 exactly as before. Do not
read Phase 5's new MCP-client work as progress on Phase 6/7.

---

## About this document

This roadmap replaces four previously-parallel roadmap files that had drifted out of sync with each other and with the codebase:

| Superseded file | Moved to | Was |
|---|---|---|
| `docs/project/02-roadmap.md` (v1.0, undated) | `docs/archive/02-roadmap.md` | Oldest; predates the Guardrails, Artifact, Observability, Memory, and Research Runtime platforms entirely |
| `ResearchMind-Roadmap-v2.md` (v2.0, 2026-07-18/19/23) | `docs/archive/ResearchMind-Roadmap-v2.md` | Vision/architecture doc; self-corrected once (2026-07-23 banner) but left contradicting body text below the correction |
| `phase-3-ai-runtime-roadmap.md` (v2.0, "Frozen" 2026-07-19) | `docs/archive/phase-3-ai-runtime-roadmap.md` | Explicitly self-declared frozen; accurate for its date, stale by design after |
| `ROADMAP.md` (2026-07-23) | *(this file, rewritten)* | Most current of the four; became the backbone of this document |

They're kept under `docs/archive/` for history, not deleted — do not treat them as current.

### What changed in this unification pass

1. **Phase numbering was reorganized** by actual delivery order. The four source files disagreed on where Agent/MCP/Research-Runtime work sits (Phase 4, 5, or 6 depending on the file), and the most-current source file (`ROADMAP.md`) assigned **Phase 6 to two different things** (Research Runtime Platform in its status table, MCP Ecosystem in its body) — an internal collision. This document assigns each shipped or planned capability exactly one phase number, in the order it was actually (or will be) delivered.
2. **Two claims that had gone stale in three of the four source files were corrected against the live codebase**, not just against the newest doc:
   - **Guardrails wiring** — two source files claimed `GuardrailService` was still unwired into `GenerationService`/`ContextBuilderService`. Verified false: `apps/api/app/ai/runtime/generation/service.py` and `apps/api/app/ai/knowledge/context/service.py` both import and call it (input-stage, generation-stage, and retrieval-stage enforcement all present). Marked ✅ here.
   - **Context Platform compression V3/V4** — one source file claimed the LangChain (V3) and LLM (V4) compression providers were still unbuilt (~90% complete). Verified false: both `providers/langchain.py` and `providers/llm.py` exist under `apps/api/app/ai/knowledge/context/compression/`, and `settings.enable_langchain_compression` gates V3 into the default pipeline. Marked ✅ here.
   - **Research Runtime / Deep Research** — two source files still show this entirely unstarted. Verified built: `apps/api/app/ai/runtime/research/` contains real `planner/`, `decomposition/`, `retrieval/`, `synthesis/`, `reporting/`, `workflows/` packages, plus a dedicated worker (`apps/worker/research_runtime_worker.py`, `research_runtime_main.py`). Marked ✅ here, per the most-current source file's account.
3. **Nothing marked "not started" or "future" in any source file was deleted.** Where sources disagreed on *status* of a shipped thing, the codebase was the tiebreaker (above). Where sources agreed something isn't built yet, it's retained here as ❌/⏳ — see the "Not Yet Built" callouts throughout.
4. PRD filenames are cited as they appear in the source roadmaps (e.g. `generation_platform_complexion_prd.md`) for historical traceability. Most PRD files at repo root are being reorganized/removed as of this pass (only `prds/research_runtime_prd.md` currently survives) — treat these as historical citations, not live file paths.
5. **Uncommitted work as of 2026-07-24** (staged, not yet committed): refinements to the Research Runtime planner/prompts, `run_service.py`, worker bootstrap, and structured-output helpers, with new/updated tests. This is incremental hardening of the already-shipped Phase 5 (Research Runtime), not a new capability — noted under Phase 5 below, not yet reflected as its own milestone.

### Status legend

| Symbol | Meaning |
|---|---|
| ✅ | Complete and verified against the codebase |
| 🟡 | Partially complete — some sub-items done, some not |
| ⏳ | Planned, not started |
| ❌ | Explicitly not built (used inline for sub-items within an otherwise-✅/🟡 milestone) |
| 🚧 | Actively in progress |

---

## Project Progress at a Glance

| # | Phase | Status | Summary |
|---|---|---|---|
| 0 | Engineering Foundation | ✅ Complete | FastAPI, Docker Compose, Postgres, Valkey, Qdrant, SQLAlchemy, Alembic, structured logging |
| 1 | Identity Platform | ✅ Complete | Cognito auth, JWT verification, user sync, protected endpoints |
| 2 | Knowledge Platform | ✅ Complete | Upload → Processing → Chunking → Embedding → Vector Store → Retrieval → Reranking → Context |
| 3 | AI Runtime / Generation Platform | ✅ Complete | Multi-provider LLM runtime, structured output, validation, guardrails, routing, caching, observability |
| 4 | Research API (Linear) | ✅ Complete | `POST /research` — first live, cited, end-to-end product surface |
| 5 | Research Runtime (Deep Research) | ✅ Complete | Single-agent LangGraph: proposal → plan → approval → multi-wave graph → report approval → PDF; web search (Tavily, 3rd checkpoint) and paper search (Research Intelligence MCP client, non-blocking post-report event) both also reachable from Chat |
| 6 | Agentic AI Platform | ⏳ Planned | General-purpose (non-Research-scoped) agents; deferred per ADR-033 |
| 7 | MCP Ecosystem | ⏳ Planned | External tool/capability integration via Model Context Protocol — the *ecosystem* (registry, manager, multi-server routing) is still unstarted; a narrow, single-server/single-tool MCP client now exists via Phase 5's ADR-037 (paper search), see below |
| 8 | AI Quality / Evaluation Platform | 🟡 Partial | Retrieval + generation benchmarks done; Experimentation Platform not started |
| 9 | Production Platform | ⏳ Planned | Kubernetes/ECS, CI/CD, OpenTelemetry, Prometheus, Grafana |
| 10 | Enterprise Platform | ⏳ Planned | RBAC, multi-tenancy, billing, compliance, admin portal |

Maturity ladder (informal, cross-cutting): `NotebookLM++ → Perplexity v1 → Open Deep Research → Manus / Glean`. As of 2026-07-23, the Deep Research path (Phase 5) reaches "Open Deep Research" territory; Chat and Linear Research remain at "NotebookLM++ + Perplexity v1."

---

## Phase 0 — Engineering Foundation ✅

**Goal:** Production-ready backend foundation.

| Item | Status |
|---|---|
| FastAPI, Dependency Injection, Lifespan | ✅ |
| SQLAlchemy, Alembic | ✅ |
| PostgreSQL, Valkey, Qdrant | ✅ |
| Structured logging (structlog) | ✅ |
| Configuration, middleware, health endpoints | ✅ |
| Ruff, MyPy, Pytest, coverage, pre-commit | ✅ |
| GitHub Actions CI | 🟡 — testing/benchmark foundations done; full CI pipeline maturity ongoing (cross-cutting, see below) |

**Deliverable:** Production-ready backend skeleton. ✅

---

## Phase 1 — Identity Platform ✅

**Goal:** Secure authentication and user management.

| Milestone | Status |
|---|---|
| 1.1 Configuration | ✅ |
| 1.2 Database Foundation (SQLAlchemy, Alembic, base models) | ✅ |
| 1.3 Internal User Domain (entity, repository, service, sync) | ✅ |
| 1.4 Authentication (AWS Cognito, JWT verification, protected endpoints) | ✅ |
| 1.5 Authorization | ✅ — delivered as the Memory Platform's owner-scoping, wired into Chat and Research |
| 1.6 User Profile (preferences, AI settings) | ⏳ Planned — not started |
| Organizations / RBAC / billing | ⏳ Deferred to Phase 10 (Enterprise) |

**Deliverable:** Secure production authentication platform. ✅

---

## Phase 2 — Knowledge Platform ✅

**Goal:** Production-grade RAG knowledge ingestion and retrieval pipeline — everything downstream depends on this.

### Canonical pipeline

```text
Upload → Processing → Chunking → Embedding → Vector Store → Retrieval → Reranking → Context Building
```

### 2.1 Upload Platform ✅

Document entity, Upload API, validation, SHA-256 hashing, S3 integration, repository, DI, structured logging.

### 2.2 Document Processing / Intelligence Platform ✅

Parsing (Docling), text normalization, markdown/plain-text generation, metadata + statistics enrichment, fingerprinting, processing status, error handling, queue processing (incl. DLQ), S3 persistence.

### 2.3 Chunking Platform ✅

| Strategy | Status |
|---|---|
| Fixed | ✅ |
| Recursive (LangChain) | ✅ |
| Markdown | ✅ |
| Hierarchical (`HierarchicalChunkingProvider`) | ✅ — two-pass LangChain `RecursiveCharacterTextSplitter`; parent sections + child chunks, children carry `structure.parent_chunk_id`; producer for Context Platform's Parent Expansion (2.9) |
| Semantic | ❌ Not started |
| Late chunking | ❌ Not started |
| Agentic chunking | ❌ Not started |

Evaluation: Chunking Benchmark (`benchmarks/chunking/`). **Deliverable:** ✅ Complete.

### 2.4 Embedding Platform ✅

| Provider | Status |
|---|---|
| Sentence Transformers (local) | ✅ |
| Voyage AI (primary — `voyage-3-lite`) | ✅ |
| OpenAI | ✅ |
| BGE / E5 / Nomic / Instructor | ❌ Not started (deferred, no urgency) |

Shared `EmbeddingBatcher` across providers. Valkey-backed embedding cache (TTL-based). **Deliverable:** ✅ Provider-independent embedding platform.

### 2.5 Vector Platform ✅

Qdrant, named dense + sparse vector schema (ADR-019 — no separate BM25 engine; FastEmbed SPLADE `prithivida/Splade_PP_en_v1` sparse vectors instead). Collections, payloads, metadata, indexing pipeline, `indexing.json` artifacts. Verified end-to-end against live Qdrant + Voyage AI + FastEmbed. **Deliverable:** ✅ Complete.

Snapshot management (backup/restore): ❌ Not started.

### 2.6 Retrieval Platform ✅

| Capability | Status |
|---|---|
| Dense (semantic) search | ✅ |
| Sparse search (FastEmbed SPLADE) | ✅ |
| Hybrid search (RRF fusion) | ✅ |
| Metadata filtering (`owner_id` server-enforced, `document_id`, `filename`, `language`) | ✅ |
| Metadata-only retrieval (`search_metadata()`, filter-only Qdrant `scroll()`) | ✅ |
| Parallel retrieval — 3-way `asyncio.gather()` (dense + sparse + metadata) | ✅ |
| Parent/Child retrieval | ✅ — reclassified into Context Platform (2.9); chunking-side producer (2.3 Hierarchical) + expansion-side consumer both exist, genuinely end-to-end |
| Query decomposition / multi-query retrieval | ✅ for Deep Research (Phase 5's planner does real dependency-wave decomposition) / ❌ for Linear Research (`/research` stays one retrieval + one generation call, by design) |
| Retrieval cache (Valkey) | ❌ Not started — only the query-embedding cache exists |
| Evaluation (Recall@K, Precision@K, MRR, NDCG@K, latency, cost) | ✅ |

**Deliverable:** ✅ Production retrieval engine.

### 2.7 Reranking Platform ✅

| Provider | Status |
|---|---|
| Voyage AI (`rerank-2`) | ✅ |
| CrossEncoder (local `BAAI/bge-reranker-base`) | ✅ |
| Cohere / Jina | ❌ Not started |
| Late Interaction / ColBERT | ❌ Future research topic |

Wired into `RetrievalService.search_hybrid(rerank=True)` by default. **Finding** (Reranking Benchmark): Recall@5 unchanged (already 1.0); MRR and NDCG@5 both improved substantially (MRR 0.925 → 1.0 CrossEncoder / → 0.95 Voyage). **Deliverable:** ✅ Complete.

### 2.8 Knowledge Evaluation 🟡

| Metric | Status |
|---|---|
| Precision@K, Recall@K, NDCG, MRR, latency (retrieval + reranking) | ✅ |
| Cost (qualitative, then real `$` via benchmarks) | ✅ |
| Generation-side evaluation (Groundedness, Faithfulness, Hallucinations, Citation Accuracy) | ✅ — delivered under Phase 8 (Evaluation Platform), not this milestone originally, see below |
| Security Evaluation | ❌ Not started |

### 2.9 Context Platform ✅

Sits between Reranking and Generation — enriches, deduplicates, compresses, guards, cites, and formats retrieved knowledge. Parent/child expansion reclassified here from Retrieval since ResearchMind's persisted chunk artifacts, not the vector index, are the source of truth for parent resolution.

| Sub-capability | Status |
|---|---|
| Deduplication | ✅ |
| Parent Expansion (`ChunkArtifactReader`, `ParentExpansionService`) | ✅ — genuinely end-to-end (producer via 2.3 Hierarchical Chunking) |
| Adjacent Merge (`AdjacentMergeService`) | ✅ |
| Compression V1 — Token Budget | ✅ |
| Compression V2 — Embedding Redundancy | ✅ |
| Compression V3 — LangChain (`ContextualCompressionRetriever` + `LLMChainExtractor`) | ✅ — **corrected**: wired into `ContextBuilderService.build()`'s default pipeline behind `settings.enable_langchain_compression`; verified present in code (one source file incorrectly listed this as ❌) |
| Compression V4 — LLM (per-chunk query-relevant summarization) | ✅ — **corrected**: registered, not part of default pipeline by design (one source file incorrectly listed this as ❌) |
| Context Guardrails V1 (`RuleBasedGuardrailProvider`, risk scoring) | ✅ |
| Guardrails V2 (LlamaGuard, NeMo Guardrails, Lakera) | ❌ Not started |
| Citation Platform (IDs, pages, headings, chunk IDs) | ✅ |
| Inline citations / source highlighting / citation evaluation | ❌ Not started |
| Prompt Formatter (`DEFAULT`, `NOTEBOOKLM`, `PERPLEXITY`, `RESEARCH`, `AGENT` strategies) | ✅ |

**Deliverable:** ✅ Complete — production context-building pipeline feeding the Generation Platform.

### 2.10 Conversation Memory Platform ✅

| Sub-capability | Status |
|---|---|
| Session, user, semantic, and research memory | ✅ |
| Conversation transcript/history + memory-context injection | ✅ |
| Owner-scoped Chat history/replay | ✅ |
| Cost-aware, versioned extraction policy (Groq primary, OpenAI fallback) | ✅ |
| Explicit-interest immediate promotion; generic topics need two sessions + one bounded LLM validation | ✅ |
| Compact session state, durable-memory short-circuit, shared query embedding, concurrent semantic/research retrieval | ✅ |
| Chat context-window compaction (cursor-paginated replay, persisted deterministic summary + newest 12 messages, ADR-030) | ✅ |
| Research conversation-thread history (`research_conversations`) | ✅ |
| Representative live-traffic validation of skip rate / empty-extraction rate / P50-P95 latency / cost per 100 turns | 🟡 Remaining operational follow-up, not yet executed |

### 2.11 Knowledge Service (unified orchestration API) ⏳

Planned — not started. Would provide one unified API orchestrating every Knowledge Platform sub-service (currently each is called individually by upstream services).

---

## Phase 3 — AI Runtime / Generation Platform ✅

**Goal:** Own all LLM interactions; provider-independent runtime consuming the Context Platform's `Prompt Context` output.

### 3.1 Provider Platform ✅

| Provider | Status |
|---|---|
| Groq (primary, dev) | ✅ |
| OpenAI | ✅ |
| Claude | ✅ |
| Gemini | ✅ |
| Ollama | ✅ |

Streaming, retries (exponential backoff), timeouts — all ✅.

### 3.2 Structured Output Platform ✅

Native decoding (all 5 providers), parser/repair fallback, Markdown/XML parser registry, optional LangChain `with_structured_output()` path (OpenAI/Claude/Gemini/Ollama — Groq excluded, `langchain-groq` incompatible with pinned `groq` SDK), regenerate-on-invalid-output loop with corrective feedback. ✅ Complete. See `docs/architecture/structured-output-platform.md`.

### 3.3 Validation Platform ✅

| Layer | Status |
|---|---|
| Input validators (empty prompt, token budget, provider limits, context quality) | ✅ |
| Output validators (JSON, schema, formatting, completeness, consistency, response size, citation) | ✅ |
| Hallucination/groundedness validator (no-LLM, deterministic) | ✅ |
| Runtime contracts (Research, Planner, Reviewer, Agent, MCP) | ✅ registered — Research contract now actively exercised by Phase 4/5; Planner/Reviewer/Agent/MCP remain registered-but-dormant pending real callers |
| `ValidationRegistry`, weighted scoring, `ValidationReport` | ✅ |
| Validation Policy Layer (Acceptance / Fail-Fast / Runtime Validation) | ✅ |

### 3.4 Routing Platform ✅

Scored `ModelCatalogRegistry`, 15-value task-based `RoutingStrategy`, capability/policy filtering, weighted scoring engine with explainable reasons, distinct-provider-preferred fallback chain. `GenerationService.generate()` auto-routes when no provider given. See `docs/architecture/model-routing-platform.md`, ADR-026.

Adaptive/evaluation-driven and budget-aware routing, A/B experimentation: ❌ explicitly future work, not MVP scope.

### 3.5 Runtime Caching Platform ✅

| Layer | Status |
|---|---|
| L1 Exact Cache (Valkey, content-hash keyed) | ✅ |
| L2 Semantic Cache (LangChain `RedisSemanticCache`, context-hash isolated) | ✅ |
| L3 Session Cache (Valkey-backed, general-purpose) | ✅ implemented — 🟡 not yet consumed by any caller (no session-aware runtime existed at build time; Phase 5's Research Runtime is a candidate future caller, not yet wired) |
| Policy resolution (`CachePolicy`: AUTO/NEVER/EXACT_ONLY/SEMANTIC/SESSION) | ✅ |
| Streaming cache | ❌ Streaming bypasses cache by design (PRD), not a gap |

See `docs/architecture/runtime-caching-platform.md`, ADR-027.

### 3.6 Guardrails Platform ✅

Standalone package (`apps/api/app/ai/guardrails/`), sibling to `knowledge/`, `runtime/`, `quality/`. Answers "should the system do this?" vs. Validation's "did it work?"

| Stage | Status |
|---|---|
| Input Guardrails — prompt injection/jailbreak (P0), scope validation, PII detection | ✅ |
| Input Guardrails — rate limiting, toxicity | 🟡 Foundation interfaces only (always-allow, no request-counting state or classifier provider yet) |
| Retrieval Guardrails — Context Sanitization, Source Trust Platform, Citation Integrity | ✅ |
| Retrieval Guardrails — Access Control | 🟡 Foundation interface, permissive default (no tenant ACL model yet) |
| Generation Guardrails — Faithfulness Enforcement, Schema Enforcement | ✅ |
| Generation Guardrails — Moderation | 🟡 Foundation interface, always-allow |
| Runtime Guardrails — Budget Guardrail, Loop Detection (real algorithm) | ✅ |
| Runtime Guardrails — Tool Policy, Approval Gate | 🟡 Foundation interfaces only, deliberately unimplemented (future LangGraph-interrupt seam) |
| **Wiring into `GenerationService` (input + generation stage gates)** | ✅ — **corrected**: two source files claimed this was still unwired; verified present in `apps/api/app/ai/runtime/generation/service.py` |
| **Wiring into `ContextBuilderService` (retrieval-stage gate)** | ✅ — **corrected**: verified present in `apps/api/app/ai/knowledge/context/service.py` |
| Wiring into a router/agent runtime for `evaluate_runtime()` | 🟡 Needs a genuine agent-runtime caller — partially addressed by Phase 5's Deep Research graph, not fully exercised yet |
| LLM-based classifiers (Llama Guard, Lakera, NeMo Guardrails) | ❌ Explicitly deferred past MVP |

113+ unit tests. Two dead scaffolds removed during the build.

### 3.7 Generation Runtime Platform ✅

Thin orchestration layer (`generation/orchestration/`: `context.py`, `state.py`, `interfaces.py`, `orchestrator.py`, `create.py`) giving every runtime caller (Research/Planner/Reviewer/Agent/MCP) one canonical entrypoint — `execute_generation(request, provider=None) -> GenerationResult` / `GenerationRuntime.execute()` — instead of reaching into `GenerationService` directly. No reimplementation, no state machines, no DAGs, no LangGraph duplication. First real caller: Phase 4 (Research API).

### 3.8 Prompt Platform ✅

Disk-loaded templates (`prompt.md` + `metadata.yaml` + `examples.json`), `ChatPromptTemplate` rendering, `PromptRegistry`, versioning, variable extraction/validation. Bridged via `GenerationService.generate_from_template()`.

Prompt evaluation / A/B testing: ❌ Not started.

### 3.9 Artifact Platform 🟡

Canonical, immutable, policy-gated persistence for AI Runtime executions.

| Artifact type | Status |
|---|---|
| Generation Artifacts (`GenerationArtifact`) | ✅ |
| Streaming Artifacts (`StreamArtifact`) | ✅ |
| Conversation Artifacts (`ConversationTurnArtifact`) | ✅ |
| Replay services (Generation/Stream) | ✅ real, reconstruct from persisted artifacts |
| Session / Research / Agent / Evaluation Artifacts | 🟡 built + unit-tested, deliberately unwired at time of original build (`ResearchReplayService` was a `NotImplementedError` stub) — **note:** Research-side wiring has since progressed via Phase 4/5's `research_sessions`/`research_runs` persistence; full replay parity not independently re-verified in this pass |
| Automated retention/expiry enforcement | ❌ Informational-only |

### 3.10 Observability Platform ✅

Real LangSmith tracing + metrics/statistics/report/artifact layer, wired into both Generation entry points (`generate()` and `stream_generate()` — so Research and Chat both get it) and the Knowledge Processing pipeline. Live-verified against a real LangSmith account/S3 bucket; found and fixed 3 real bugs (streaming path completely dark, missing artifact-policy rule silently dropped research artifacts, tracer never sent real input/output) plus a follow-up (streamed generations never scored for post-generation validation/guardrails — now do, informationally).

Advanced observability (OpenTelemetry, Prometheus, Grafana, Phoenix): ⏳ Deferred to Phase 9.

**Phase 3 Deliverable:** ✅ Provider-independent generation runtime powering every downstream product surface (Chat, Linear Research, Deep Research).

---

## Phase 4 — Research API (Linear) ✅

**Goal:** First live, end-to-end, grounded, cited product answer over a user's own documents — deliberately linear (one retrieval + one generation call), ahead of and simpler than the full Deep Research workflow (Phase 5).

| Item | Status |
|---|---|
| `POST /research` | ✅ |
| `POST /research/stream` (SSE) | ✅ |
| `POST /research/citations` | ✅ |
| `GET /research/{id}` (replay) | ✅ |
| All routes auth-required, owner-scoped | ✅ |
| `ResearchService` — composes Retrieval → Context → Generation Runtime → Streaming → Artifacts | ✅ |
| `research_sessions` Postgres table (replay) | ✅ |
| `RuntimeType.RESEARCH` / `ArtifactRuntime.RESEARCH` exercised by live code | ✅ |
| Research frontend integration (`apps/web`, real SSE, `mock-engine.ts` removed) | ✅ — 3 backend bugs found + fixed live (stream-completion event name mismatch, retired Claude model, `temperature` rejected by newer Claude model) |

**Explicitly out of scope for this milestone** (delivered instead by Phase 5): query decomposition/research planning, multi-step research loops, tool calling, evidence synthesis across sub-queries, gap detection/fact verification, report generation, human-in-the-loop approve/reject, LangGraph orchestration.

**Deliverable:** ✅ `POST /research` — authenticated, owner-scoped, citation-backed, streamable, replayable.

---

## Phase 5 — Research Runtime / Deep Research ✅

**Goal:** A third, deliberately separate product path alongside Chat (fast, ungrounded) and Linear Research (fast, one-shot, cited): **proposal → approval → asynchronous multi-step LangGraph investigation → human-reviewed report.** `POST /research`/`/research/stream` (Phase 4) remain architecturally untouched — no runtime flag routes either through LangGraph.

### Flow

```text
POST /research/escalation-check          → optional; classifies a query, suggests Deep
                                             Research only when it's actually worth it
POST /research/proposals                  → memory-aware planner (query rewriting via
                                             `rewritten_goal`); no run/retrieval cost yet
POST /research/proposals/{id}/approve     → idempotent; creates ResearchRun + outbox dispatch
  dedicated worker process (apps/worker/research_runtime_worker.py)
    → Postgres-checkpointed LangGraph:
        planner → dependency-wave retrieval (Send fan-out)
        → evidence aggregation → synthesis → deterministic+model review → bounded repair
        → report-approval interrupt() — a real second human checkpoint
POST /research/runs/{id}/report-decision  → approve (resumes → report + PDF) or reject
GET  /research/runs/{id}/events (SSE)     → live-consumed by the Research UI
GET  /research/runs/{id}/report           → presigned PDF download URL
```

### What shipped

| Item | Status |
|---|---|
| Memory-aware planning with query rewriting | ✅ |
| Dependency-wave parallel retrieval (LangGraph `Send` fan-out) | ✅ |
| Synthesis, deterministic + model review, bounded repair | ✅ |
| Report-approval `interrupt()` (genuine 2nd human-in-the-loop checkpoint) | ✅ |
| Checkpoint provisioning, budget enforcement, cancellation, crash-resume, logging | ✅ — closed in a same-day readiness-audit pass |
| Real per-owner rate limiting across all three product paths (Chat / Linear Research / Deep Research) | ✅ — was previously a total no-op app-wide |
| Cross-run cache-leakage fix in synthesis/review | ✅ |
| Research UI Deep Research destination (mode toggle, escalation suggestion, plan review, live SSE progress, report-approval, PDF download) | ✅ |
| Worker session-staleness bugs (long-lived `AsyncSession` poisoning, stale cached `report_decision` on resume) | ✅ found via manual browser verification (2026-07-23) and fixed, regression-tested |
| Plan-approval `interrupt()` — second human checkpoint between evidence aggregation and synthesis, view/edit-goal/reject-with-reason | ✅ (2026-07-24) |
| Web Search Tool Platform — third human checkpoint (`await_web_search_approval`), Tavily-backed, AUTO/REQUIRED/DISABLED modes + pre-authorize toggle | ✅ (2026-07-25, ADR-036) — see subsection below |
| Research Intelligence MCP Paper Search Platform — ResearchMind's first MCP client, non-blocking post-report suggestion node (not a checkpoint) | ✅ (2026-07-25/26, ADR-037) — see subsection below |
| Session-state pronoun-resolution fix (Memory Platform, benefits Chat too) | ✅ (2026-07-25/26) — see subsection below |

### Web Search Tool Platform ✅ (2026-07-25, ADR-036)

A framework-independent search platform (`app/ai/tools/web_search/` — canonical models, provider interface/registry, Tavily provider over raw `httpx`, no new SDK dependency) reused by two runtimes:

| Consumer | Approval model | Status |
|---|---|---|
| Deep Research (`multi_wave_research.py`) | Third `interrupt()` checkpoint (`await_web_search_approval`), mirroring the plan-approval pattern; reused inside the existing bounded gap-research loop. `AUTO` asks unless `web_search_auto_approve` is set; `REQUIRED` never asks; `DISABLED` never searches. | ✅ |
| Chat (`app/ai/runtime/chat/web_search.py`) | No checkpoint — Chat has no interrupt/resume mechanism, so a single `web_search_enabled` toggle on `ChatStreamRequest` *is* the approval, once, per turn. Reuses the same `WebSearchService`/`WebSearchNecessityService`/evidence normalizer unchanged; best-effort (any failure degrades to no search for that turn). | ✅ (2026-07-25, same day, later) |
| Linear Research (`/research`, `/research/stream`) | — | ❌ Explicitly excluded per product decision; request/response schemas untouched |

The necessity decision (does this task need the web?) is a small structured-output call pinned to a cheap OpenAI/Claude model via a dedicated registry, deliberately separate from the shared `GenerationRegistry`. Its default OpenAI model was swapped from `gpt-5-nano` to `gpt-5-mini` after production logs showed `gpt-5-nano` unreliably following the structured-output contract, silently failing AUTO mode closed to "no search needed" every time.

Frontend: Deep Research composer gained an Off/Auto/Required toggle + "skip approval" checkbox (labeled "Web search" as of 2026-07-25) and an approval card; Chat composer gained its own toggle plus a "Searching the web…"/"Searched the web" status chip with source pills in the message bubble. Citation chips across both surfaces (sidebar Citations panel, plan-review "Sources found so far," report draft "Sources," inline `[S1]`/`[W1-1]` answer markers) now visually distinguish web-sourced citations from document ones, derived client-side from the `S{n}`/`W{round}-{n}` citation-ID prefix already set server-side — no new backend field needed.

Not built this pass (deferred, see ADR-036): the standalone SSRF-hardened Web Fetch Platform (Tavily already extracts page content server-side, so there's no new SSRF surface yet), multi-provider fallback (Exa/Brave/MCP), org-wide domain policy management, the full evaluation/benchmark harness.

### Research Intelligence MCP Paper Search Platform ✅ (2026-07-25/26, ADR-037)

ResearchMind's **first MCP client** integration — narrowly scoped to one
external "Research Intelligence MCP" server, one tool (`search_papers`),
two call sites. This is explicitly **not** the general-purpose Phase 6/7
MCP Ecosystem work (a client-agnostic MCP manager/registry, multiple
servers, planner-driven capability routing) — that remains fully
unstarted, per the Phase 6/7 tables below.

| Consumer | Approval model | Status |
|---|---|---|
| Chat (`app/ai/runtime/chat/paper_search.py`) | Toggle-only (`ChatStreamRequest.paper_search_enabled`), no necessity-decision call — deliberately simpler than Web Search's AUTO mode. | ✅ |
| Deep Research (`multi_wave_research.py`'s `suggest_related_papers` node) | **Not** an `interrupt()` checkpoint — a plain sequential node between `persist_final_report` and `END`, since the report is already durably persisted by the time it runs. Any failure degrades to a `SKIPPED` event; the run reaches `END` exactly as it would without the feature. | ✅ |
| Linear Research | — | ❌ Excluded, same as Web Search |

`app/ai/tools/paper_search/` mirrors `app/ai/tools/web_search/`'s file
layout exactly (canonical models, provider interface/registry, a
Valkey-backed TTL cache, a composition root that degrades `.available` to
`False` when unconfigured). `ResearchIntelligenceMCPProvider` uses the
official `mcp` SDK's `streamablehttp_client`, a fresh connection per call,
optional static bearer-token auth — explicitly not the fuller
JWT-service-token/retry-with-backoff/9-category-error-taxonomy spec in
`prds/1.researchmind_mcp_integration_prd.md`, which is deferred as a later
hardening pass. Both call sites distill the search query through
`PaperQueryExtractionService` first (a raw prompt or `rewritten_goal`
sentence returns zero results from the paper-search backend).

Same session, a real bug fix in the Memory Platform (not paper-search-
specific, but shipped alongside it): a `SessionStateUpdaterService`
(`app/ai/memory/session/state_updater.py`) now maintains one evolving
SESSION-memory summary of "what this session is about" after every turn,
fixing pronoun follow-ups ("how is magma related to *it*?") that previously
had nothing to resolve against.

See ADR-037 for the full decision record.

### Not yet built (explicitly retained, not dropped)

| Item | Status |
|---|---|
| Plan edits/rejection before approval | ✅ Done — `await_plan_approval` interrupt (2026-07-24), see above |
| Horizontal worker scaling | ✅ Done — in-process worker concurrency + global load-shedding (2026-07-24), see above. Still static config, not autoscaling |
| Expiry/auto-reject for a run stuck awaiting report approval | ✅ Done (2026-07-24, commit `95a6c8c` — missed in earlier passes of this document, corrected now) — `ResearchRunService.expire_stale_awaiting_approval()` auto-cancels runs stuck at any of the three approval pauses (report/plan/web-search) past a 72h TTL (`research_runtime_awaiting_approval_ttl_hours`), scheduled via `ResearchRuntimeWorker`'s own poll loop rather than a separate cron process |
| General-purpose MCP manager/registry, multi-agent integration into this runtime | ❌ Deferred per ADR-033 until the single-agent design proves a limitation it can't address. Distinct from the narrow, single-tool MCP client added by ADR-037 above, which does not count toward this. |
| Chat → Deep Research escalation | ❌ **Explicitly out of scope, will not be built** — Chat stays a standalone fast conversational surface. (Do not confuse with the Research-interface Linear → Deep escalation, which *is* built.) |

**In progress, uncommitted as of 2026-07-24:** refinements to the planner/prompts, `run_service.py`, worker bootstrap, `research_run` repository, and structured-output helpers, with new/updated unit tests — incremental hardening, not a new capability.

See `docs/archive/` source files' equivalent sections, and `PRODUCT_FLOWS_AND_GAPS.md` / `PROJECT_STATUS.md` (if present) for full narrative detail.

---

## Phase 6 — Agentic AI Platform ⏳

**Goal:** General-purpose (non-Research-scoped) agent orchestration — distinct from Phase 5's Deep Research, which is a single, purpose-built agent.

| Milestone | Status |
|---|---|
| Workflow engine (reusable LangGraph graphs beyond Deep Research) | ⏳ Planned |
| Planner abstraction (general-purpose, not Research-specific) | ⏳ Planned |
| Agent runtime (Research/Retrieval/Summarization/Review/Report agents as reusable units) | ⏳ Planned |
| Workflow state management | ⏳ Planned |
| Human interrupts (generalized beyond Phase 5's report-approval seam) | ⏳ Planned |
| Checkpointing (generalized) | ⏳ Planned |
| Multi-agent collaboration (Planner/Researcher/Reviewer/Critic/Writer) | ⏳ Planned |
| Agent evaluation (task completion, planning quality, tool success, recovery) | ⏳ Planned |
| Coding Agent, Data Analysis Agent | ⏳ Future |

**Status note:** Deliberately deferred (ADR-033) until Phase 5's single-agent Research Runtime design proves a limitation it can't address on its own.

---

## Phase 7 — MCP Ecosystem ⏳

**Goal:** Connect ResearchMind to external capabilities via the Model Context Protocol — ResearchMind should never depend directly on external services.

```text
Planner → MCP Manager → Capability Routing → External MCP Servers
```

**2026-07-26 note:** the *ecosystem* this phase describes — a reusable,
client-agnostic MCP manager that discovers/routes/fails-over across
*multiple* external servers on a planner's behalf — is still entirely
unstarted, exactly as before. What changed is narrower: Phase 5 shipped a
single, hand-wired MCP client (`app/ai/tools/paper_search/`,
ADR-037) that talks to exactly one external server for exactly one tool
(`search_papers`), with no manager, registry, discovery, routing, or
failover of any kind — it's a point integration, not an instance of this
phase's architecture. The two milestones below it's directly relevant to
are marked 🟡 Partial rather than ✅ for that reason; every other milestone
here (registry, manager, the other domain MCPs, evaluation) is unaffected
and remains ⏳ Planned. See Phase 5's "Research Intelligence MCP Paper
Search Platform" subsection and ADR-037 for what actually shipped.

| Milestone | Status |
|---|---|
| MCP client (protocol, session lifecycle, auth, connection management) | 🟡 Partial — a single-server, single-tool client exists (ADR-037, official `mcp` SDK's `streamablehttp_client`, fresh connection per call, optional static bearer token); no reusable/generalized client abstraction, no persistent session management, no cached/refreshed service-token auth (deferred per ADR-037, see `prds/1.researchmind_mcp_integration_prd.md`) |
| MCP registry | ⏳ Planned — no registry of any kind; the one configured server is wired by direct construction, not looked up |
| MCP manager (discovery, routing, health monitoring, failover, permissions) | ⏳ Planned — not started; ADR-037's client has no discovery, routing, health checks, or failover |
| Research MCP (academic search, paper retrieval, DOI/citation lookup) | 🟡 Partial — academic search (`search_papers`) is live (ADR-037), reachable from Chat and Deep Research; paper retrieval, citation lookup, DOI lookup, and the other 5 tools the server exposes (`get_paper`, `get_paper_citations`, etc.) are explicitly out of scope for this pass |
| Development MCP (GitHub, docs, package lookup) | ⏳ Planned |
| Domain MCPs (Climate, Earthquake, Space, Crypto, Finance, Healthcare) | ⏳ Planned |
| MCP evaluation (tool latency, success/failure rate, availability) | ⏳ Planned — ADR-037's paper search has no dedicated evaluation/benchmark harness either |

---

## Phase 8 — AI Quality / Evaluation Platform 🟡

**Goal:** Make AI quality measurable across every subsystem.

### Engineering Benchmark Platform ✅ Foundation Complete

Repository-owned, offline (`benchmarks/`), independent from runtime Observability and the not-yet-built Experimentation Platform.

| Benchmark | Status |
|---|---|
| Chunking Benchmark | ✅ |
| Embedding Benchmark | ✅ |
| Retrieval Benchmark (dense/sparse/hybrid RRF, incl. NDCG@5/10) | ✅ |
| Metadata Filtering Benchmark (`leakage_rate` correctness signal) | ✅ |
| Reranking Benchmark (Recall@5, MRR, NDCG@5, latency, cost) | ✅ |
| Pipeline Benchmark (end-to-end ingestion) | ✅ |
| Generation Benchmark — deterministic no-LLM scoring (faithfulness, groundedness, relevance, completeness, citation accuracy, hallucination rate, cost) | ✅ — live-verified against Groq/OpenAI/Claude; found + fixed a real citation-accuracy bug (model never given the filename it was asked to cite); found a real ~24x cost spread between Claude and Groq per 1k queries |
| Regression Detection (`--check-regression`, threshold-based, incl. cost thresholds) | ✅ |
| Vector Store Benchmark | ⏳ Planned |
| End-to-End Pipeline Benchmark (RAG-level, post Context/Generation) | ⏳ Planned |

**Reconciliation note:** a proposed standalone `app/ai/evaluation/` platform (per one source PRD) was **not** built literally — it was reconciled against the already-real Benchmark Platform (`benchmarks/`) and the already-live Observability Platform (Phase 3.10) rather than duplicated. "Runtime Evaluation" = Observability Platform; "Experiment runner" = the still-not-built Experimentation Platform below.

### Experimentation Platform ⏳ Not Started

Would compare competing AI strategies offline/asynchronously (chunking, embedding, retrieval, reranking, pipeline-level experiments) without affecting production. Distinct from Benchmarks (which don't verify correctness, just compare trade-offs).

### Agent Evaluation ⏳ Not Started

Planning quality, tool success, completion rate — blocked on Phase 6/7 actually existing.

### Security Evaluation ❌ Not started

Attack datasets, red-teaming — not begun.

---

## Phase 9 — Production Platform ⏳

**Goal:** Prepare ResearchMind for production deployment.

| Milestone | Status |
|---|---|
| Docker | ✅ (dev; production-grade multi-stage not verified) |
| Kubernetes / ECS | ⏳ Planned |
| CI/CD (build/test/security-scan/deploy/rollback) | 🟡 GitHub Actions foundation only |
| OpenTelemetry, Prometheus, Grafana, Phoenix | ⏳ Planned — explicitly deferred by the Observability Platform's own non-goals |
| Performance optimization (latency, throughput, memory, cost, startup) | ⏳ Planned |
| Security Platform (prompt-injection/jailbreak/PII detection exist at the Guardrails layer already; tool policies, MCP permissions, secret management) | 🟡 Partial — see Phase 3.6 Guardrails for what already exists |
| Blue/green deploy, canary releases, feature flags, backup/DR | ⏳ Planned |

---

## Phase 10 — Enterprise Platform ⏳

**Goal:** Enterprise readiness.

| Milestone | Status |
|---|---|
| Organizations, teams, workspaces | ⏳ Planned |
| RBAC (roles, permissions, policies) | ⏳ Planned |
| Multi-tenancy (tenant/resource/knowledge isolation) | ⏳ Planned |
| Billing (usage/token/embedding/API-call tracking, quotas, plans) | ⏳ Planned |
| Compliance (GDPR, audit logging, data retention, privacy controls) | ⏳ Planned |
| Admin portal (user mgmt, system health, AI/cost dashboards) | ⏳ Planned |
| Plugin framework, custom MCP registration, SDK | ⏳ Planned |

---

## Cross-Cutting Engineering Capabilities

These evolve continuously across every phase rather than belonging to one.

| Capability | Starts | Matures | Current State |
|---|---|---|---|
| Structured Logging | Phase 0 | Phase 9 | ✅ Live everywhere |
| Metrics | Phase 0 | Phase 9 | ✅ `GenerationMetricsService`, Prometheus-ready counters |
| Tracing | Phase 2 | Phase 9 | ✅ Real LangSmith tracing (Phase 3.10) |
| AI Evaluation | Phase 2 | Phase 8 | 🟡 Retrieval + generation done; agent/security eval pending |
| Testing | Phase 0 | Continuous | ✅ Real pytest suite, ~1000+ tests, fakes/mocks over live services |
| Security | Phase 0 | Phase 10 | 🟡 Guardrails MVP live; enterprise ACL/tool policy pending |
| Performance | Phase 0 | Phase 9 | 🟡 Measured ad hoc; no dedicated dashboard |
| Cost Tracking | Phase 2 | Phase 9 | ✅ Real per-model `$` cost accounting (generation + memory extraction) |
| Engineering Analytics | Phase 2 | Phase 9 | 🟡 Benchmark reports; no unified dashboard |
| LangSmith | Phase 2 | Continuous | ✅ Live |

---

## AI Learning Dimensions

Every milestone is expected to strengthen four dimensions simultaneously:

| Dimension | Focus |
|---|---|
| Engineering | Architecture, clean code, testing, scalability |
| AI | RAG, embeddings, retrieval, prompting, agents |
| Production | Docker, AWS, observability, deployment |
| Architecture | Trade-offs, ADRs, system design |

---

## Roadmap Rules

- Complete one milestone before starting the next.
- Every milestone ends with testing and documentation.
- Freeze architectural decisions once implemented (see ADRs, e.g. ADR-019 sparse vectors, ADR-026 routing, ADR-027 caching, ADR-030 chat compaction, ADR-033 deferred agent/MCP integration).
- Prioritize implementation over redesign.
- Compare AI approaches using evaluation rather than opinion.
- Keep the project focused on becoming a production-grade AI engineering platform, not a demo of every possible AI technology.
- Canonical models and canonical artifacts between platforms — never leak SDK models or provider types across platform boundaries.
- Frameworks (LangChain, LangGraph) remain implementation details behind provider/service interfaces.

---

## Open Items Carried Forward From This Reconciliation

Things noted during this consolidation that don't have a clean answer yet and may need a follow-up pass:

1. **Artifact Platform Research-side wiring** (Phase 3.9) — the original build left Session/Research/Agent/Evaluation artifact writers scaffold-only with a stub `ResearchReplayService`. Phase 4/5 have since added real `research_sessions`/research-run persistence, but this document does not assert full replay parity was re-verified against the original Artifact Platform design — worth an explicit check.
2. **PRD file reorganization** — most PRDs cited throughout this roadmap (`generation_platform_complexion_prd.md`, `guardrails_platform_prd.md`, `research_api_prd.md`, etc.) are being removed from the repo root as of this session, with only `prds/research_runtime_prd.md` surviving. If historical PRD content should be preserved, consider archiving rather than deleting the rest.
3. **Runtime Caching L3 (Session Cache)** — implemented and tested but has never had a real caller. Phase 5's Research Runtime is the most plausible consumer; not yet wired.
4. **Uncommitted Phase 5 refinements** (staged as of 2026-07-24, not yet committed) — planner/prompts, `run_service.py`, worker bootstrap, and structured-output helper changes with new tests. Recommend committing with a clear message once verified, so this roadmap's "✅ Complete" for Phase 5 stays anchored to a real commit.

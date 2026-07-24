# ResearchMind AI — Roadmap
## Retrieval, Context, Generation & Research Runtime

**Status:** Frozen (v2.0)

**Last Updated:** 2026-07-19

---

# ResearchMind Maturity Vision

```text
NotebookLM++
      ↓
Perplexity v1
      ↓
Open Deep Research
      ↓
Manus / Glean
```

Current State:

```text
NotebookLM++
    +
Perplexity Foundation
```

Hybrid Retrieval, Reranking, Parent Expansion, Compression, Context Guardrails, and strategy-based Prompt Formatting are all implemented — beyond a plain NotebookLM clone and closing in on Perplexity v1. A platform-wide Guardrails Platform (Milestone 3.13 below — input/retrieval/generation/runtime stages, Source Trust, policies, scoring, artifacts) is now complete as an MVP foundation and wired directly into both the Generation Platform and the Context Building Platform (per `guardrail_integration_prd.md`). A new, centralized Artifact Platform (Milestone 3.14 below — canonical, immutable, policy-gated persistence for AI Runtime executions) is now also complete for generation/streaming/conversation, per `artifacts_platform_prd.md`. A Generation Runtime Platform (Milestone 3.15 below — a thin orchestration layer giving every future runtime one canonical `execute_generation()` entrypoint) is now complete, per `generation_runtime_platform_prd.md`. And the Research API (Milestone 3.9 below) is now complete too, per `research_api_prd.md` — ResearchMind's first live, end-to-end product surface: a user can upload documents, ask a question, and get a grounded, cited, streamable answer back.

**Chat runtime growth-control update (2026-07-19):** Chat now cursor-pages
canonical conversation/message replay and compacts only its **prompt** history:
the newest 12 messages remain verbatim and older content is retained as a
persisted deterministic summary. This is a Chat-only additive capability
(ADR-030), not a substitute for the future Research Runtime's compact
checkpoint state or its own context policy.

Current Focus:

```text
Phase 3.7
Context Building Platform (✅ Complete)
    ↓
Phase 3.8
Generation Platform (✅ Complete — structured output, input/output/
hallucination/runtime validation + scoring, all five runtime contracts
(Research/Planner/Reviewer/Agent/MCP), the Acceptance/Fail-Fast/Runtime
Validation policy layer, every PRD output validator (completeness/
consistency/formatting/response-size), regeneration, prompt bridge,
Routing Platform, Runtime Caching Platform, Streaming Platform, Runtime
Metrics Integration, and Artifact Platform (incl. metrics.json) done —
per `generation_platform_complexion_prd.md`)
    ↓
Phase 3.15
Generation Runtime Platform (✅ Complete — thin orchestration layer,
`runtime/generation/orchestration/`, canonical `execute_generation()` /
`GenerationRuntime.execute()` entrypoint + `get_generation_runtime()`
FastAPI dependency, per `generation_runtime_platform_prd.md`; no
reimplementation of the frozen Generation Platform ordering, no state
machines, no DAGs, no LangGraph duplication)
    ↓
Phase 3.9
Research APIs (✅ Complete — `POST /research`, `/research/stream`,
`/research/citations`, `GET /research/{id}`, per `research_api_prd.md`;
first real caller of the Generation Runtime Platform above; deliberately
linear — no query decomposition, no planning/multi-step loops, no agents,
no LangGraph, all of which remain future work under Milestone 3.11
Research Runtime and Phase 5 AI Agent Platform)
```

---

# Purpose

The Knowledge Ingestion Platform is now complete.

```text
Upload
↓
Processing
↓
Chunking
↓
Embeddings
↓
Indexing
↓
Vector Store
```

ResearchMind now transitions into an AI Research Platform.

The next stages focus on consuming, enriching, reasoning over, and generating knowledge.

---

# Engineering Principles

- Build complete vertical slices.
- Every platform owns one business capability.
- Canonical domain models only.
- Provider independence.
- Production-first engineering.
- Evaluation-driven development.
- Documentation-first.
- Freeze architecture after validation.
- Frameworks remain implementation details.

# Overall AI Pipeline

```text
                    Upload Platform
                          │
                          ▼
                 Processing Platform
                          │
                          ▼
                 Chunking Platform
                          │
                          ▼
                Embedding Platform
                          │
                          ▼
               Vector Store Platform
                          │
                          ▼
                Retrieval Platform
                          │
                          ▼
               Reranking Platform
                          │
                          ▼
             Context Building Platform
                          │
                          ▼
                Generation Platform
                          │
                          ▼
                Evaluation Platform
                          │
                          ▼
                Research Runtime
                          │
                          ▼
                 Long-Term Platform
```

# Phase 3.4 — Retrieval Strategies

**Status:** ✅ Complete (Parallel Retrieval 3-way; Parent/Child genuinely end-to-end; Query Decomposition explicitly moved to the future Research Runtime, out of this phase's scope)

---

## Parallel Retrieval

### Status: ✅ Complete (3-way)

Implemented:

```python
asyncio.gather(
    dense_search(),
    sparse_search(),
    metadata_search(),
)
```

Current workflow:

```text
Dense Retrieval
        │
Sparse Retrieval
        │
Metadata Retrieval
        │
        ▼
Parallel Execution
        │
        ▼
Fusion
```

The metadata branch (`QdrantRetrievalProvider.search_metadata()`) is a pure filter-only Qdrant `scroll()` lookup — no vector similarity, no query embedding needed. It short-circuits to an empty result when no filters are present, since an unfiltered scroll would ignore `owner_id` tenant scoping and could leak chunks across owners. `RetrievalStatistics.metadata_latency_ms` tracks its latency alongside the pre-existing `dense_latency_ms`/`sparse_latency_ms`, and its results are fused in by RRF (`ReciprocalRankFusion.fuse()`'s new optional `metadata` parameter) alongside dense and sparse.

---

## Parent / Child Retrieval

### Status: ✅ Complete (Reclassified into Context Platform, now genuinely end-to-end)

Originally planned under Retrieval.

After architecture validation, Parent/Child retrieval has been moved into the Context Platform.

Reason:

ResearchMind persists canonical chunk artifacts.

Retrieval should find knowledge.

Context Building should enrich knowledge.

Workflow:

```text
Parent Documents
      ↓
Child Chunks
      ↓
Retriever
      ↓
Retrieved Child Chunks
      ↓
Parent Expansion
      ↓
Prompt Context
```

Implemented Foundations:

- ChunkArtifactReader
- ParentExpansionService
- AdjacentMergeService

**Producer (new):** the workflow above previously started at "Retriever" — nothing upstream of it ever produced a `parent_chunk_id`, so `ParentExpansionService` was live-wired but never actually triggered. `HierarchicalChunkingProvider` (Chunking Platform, Milestone 2.2) now closes that gap: a two-pass LangChain `RecursiveCharacterTextSplitter` first splits documents into parent sections, then splits each parent into child chunks. Children carry `structure.parent_chunk_id`; parent sections are tagged `is_parent` and excluded from embedding/indexing by `EmbeddingService`, but persist in the `ChunkArtifact` for `ParentExpansionService` to resolve against.

---

## Query Decomposition

### Status: ❌ Not Started

Moved to:

### Research Runtime Platform

Workflow:

```text
Question
      ↓
Planner
      ↓
Sub Questions
      ↓
Parallel Retrieval
      ↓
Merge
```

Likely Framework:

- LangGraph

---

## Deliverables

### Complete

- ✅ Parallel Retrieval (3-way: dense + sparse + metadata)

### Context Platform

- ✅ Parent Expansion (genuinely end-to-end — producer now exists via Hierarchical Chunking)

### Runtime Platform

- ❌ Query Decomposition

# Phase 3.7 — Context Building Platform

**Status:** 🟡 ~90% Complete

---

## Goal

Prepare retrieved knowledge for LLM consumption.

---

## Architectural Decision

Retrieval finds knowledge.

Context Building prepares knowledge.

---

## Responsibilities

### Implemented

- ✅ Deduplication
- ✅ Parent Expansion
- ✅ Adjacent Chunk Merge
- ✅ Compression Platform Foundation
- ✅ Token Budget Compression (V1)
- ✅ Embedding Redundancy Compression (V2)
- ✅ LangChain Contextual Compression (V3) — `ContextualCompressionRetriever` + `LLMChainExtractor` (`langchain-classic`); wired into `ContextBuilderService.build()`'s default pipeline, gated by `settings.enable_langchain_compression` and gated on a `query` being passed
- ✅ LLM Compression (V4) — per-chunk, query-aware relevant-summary compression via `GenerationService.generate()`; registered in `create_compression_service()` but intentionally not part of `build()`'s default pipeline
- ✅ Context Guardrails (V1) — provider architecture, `RuleBasedGuardrailProvider`, risk scoring, statistics
- ✅ Citation Platform — citation IDs, pages, headings, chunk IDs
- ✅ Prompt Formatter — strategy-based (`DEFAULT`, `NOTEBOOKLM`, `PERPLEXITY`, `RESEARCH`, `AGENT`)

### Future

- Inline citations, source highlighting, citation evaluation
- LlamaGuard, NeMo Guardrails, Lakera (Guardrails V2)

---

## Workflow

```text
Retrieved Chunks
        ↓
Deduplicate
        ↓
Parent Expansion
        ↓
Adjacent Merge
        ↓
Ordering
        ↓
Compression (Token Budget + Embedding; LangChain implemented, not yet wired in)
        ↓
Guardrails
        ↓
Citation Building
        ↓
Prompt Formatting
        ↓
Prompt Context
```

---

## Compression Roadmap

### V1

```text
Top 20
↓
Sort by score
↓
Fit token budget
↓
Top 5-10
```

Status:

✅ Complete

---

### V2

```text
Chunk similarity > 0.95
↓
Drop duplicate chunks
```

Status:

✅ Complete

---

### V3

LangChain

```text
ContextualCompressionRetriever
```

Status:

✅ Complete — `ContextualCompressionRetriever` + `LLMChainExtractor` (`langchain-classic`); registered in `create_compression_service()` and wired into `ContextBuilderService.build()`'s default pipeline, gated by `settings.enable_langchain_compression` and gated on a `query` being passed

---

### V4

LLM Compression

```text
Chunk
↓
Relevant Summary
↓
Compressed Chunk
```

Status:

✅ Complete — `LLMCompressionProvider` calls `GenerationService.generate()` once per chunk (never a direct provider call), asking for a concise, query-relevant summary; never drops a chunk, falls back per-chunk to original content on failure. Registered in `create_compression_service()` but intentionally not part of `build()`'s default pipeline (unlike V3)

---

## Deliverables

### Complete

- ✅ Context Models
- ✅ ChunkArtifactReader
- ✅ ParentExpansionService
- ✅ AdjacentMergeService
- ✅ Compression Platform (Token Budget + Embedding + LangChain + LLM, V1-V4)
- ✅ Context Guardrails (V1)
- ✅ Citation Platform
- ✅ Prompt Formatter
- ✅ LangChain Compression Provider (V3) wired into `ContextBuilderService.build()`'s default pipeline

# Phase 3.8 — Generation Platform

**Status:** ✅ Complete, per `generation_platform_complexion_prd.md` —
structured output, a multi-stage Validation Platform integration
(input/output/hallucination/runtime validators, registry, scoring,
`ValidationReport`), five runtime contracts (Research, Planner,
Reviewer, Agent, MCP — all registered), the Acceptance/Fail-Fast/
Runtime Validation policy layer (`generation/policies/`), every PRD
output validator (JSON/Schema/Formatting/Completeness/Consistency/
Response Size/Citation, in pipeline order), regeneration,
prompt-template integration, a Routing Platform (scored model catalog,
task-based strategies, capability/policy filtering, fallback chains), a
Runtime Caching Platform (L1/L2/L3), Runtime Metrics Integration
(`GenerationMetricsService`, Prometheus-ready counters via
`infrastructure/metrics/generation.py`, `generation.started/failed`/
`validation.started/completed`/`provider.started/completed` events),
and an Artifact Platform (canonical `GenerationArtifact` persistence
including a `metrics.json` snapshot — Milestone 3.14 below) are all
done. Input validation now runs pre-flight (before guardrails/routing/
provider execution), gated by `FailFastPolicy`. The five runtime
contracts remain registered-but-dormant until a `/research` API sets
`GenerationRequest.runtime` — a scope decision the PRD itself accepts,
not a gap in this milestone. Generation-level guardrails are no longer
part of this gap — see Milestone 3.13 (Guardrails Platform) below, now
complete and wired directly into this service (input gate before every
provider call, full `evaluate()` report on `GenerationResult.guardrails`).

---

## Goal

Generate answers from prepared context.

---

## Responsibilities

- ✅ Prompt templates — `generation/prompts/` (pre-existing, substantial:
  disk-loaded templates, variable rendering, few-shot examples,
  versioning) now bridged into Generation via
  `GenerationService.generate_from_template()`
- ✅ Prompt registry — `PromptRegistry` (pre-existing)
- ✅ LLM provider abstraction — all five providers implemented
- ✅ Streaming — per-provider `stream()`
- ✅ Structured output — native decoding (all 5 providers) + parser/repair
  fallback + Markdown/XML registry + optional LangChain
  `with_structured_output()` path (4/5 providers) + regenerate-on-invalid
  loop with corrective feedback
- ✅ Validation Platform integration — input validators (empty prompt,
  token budget, provider limits, context quality), output validators
  (JSON parseability, schema via `jsonschema`, formatting, completeness,
  consistency, response size, fabricated-citation detection — full PRD
  pipeline order), a lightweight no-LLM hallucination/groundedness
  validator, five runtime contracts (Research/Planner/Reviewer/Agent/
  MCP), a `ValidationRegistry`, weighted scoring, and a multi-stage
  `ValidationReport` all implemented — see `validation_platform_prd.md`,
  `generation_platform_complexion_prd.md`
- ✅ Routing — scored `ModelCatalogRegistry`, a 15-value task-based
  `RoutingStrategy`, capability/policy filtering, a weighted scoring
  engine with explainable reasons, and a distinct-provider-preferred
  fallback chain; `GenerationService.generate()` routes automatically
  (with fallback retry) when no `provider` is given — see
  `routing_platform_prd.md`, ADR-026
- ✅ Caching — Runtime Caching Platform (L1 exact/L2 semantic/L3
  session, policy resolution), wired into `GenerationService` — see
  `runtime_caching_platform_prd.md`, ADR-027
- ✅ Artifacts — canonical `GenerationArtifact` persistence (Artifact
  Platform, Milestone 3.14 below), wired into `GenerationService.generate()`
  — see `artifacts_platform_prd.md`
- ✅ Validation Policy Layer — `AcceptancePolicy`/`FailFastPolicy`/
  `RuntimeValidationPolicy` (`generation/policies/`), wired into
  `GenerationService`'s regeneration decision and a pre-flight
  input-validation gate — see `generation_platform_complexion_prd.md`
- ✅ Runtime Metrics Integration — `GenerationMetricsService`
  (`generation/observability/`), request/execution/token/cost/
  validation/guardrail metrics, Prometheus-ready counters
- ❌ Research chains — not started

---

## Supported Providers

- Groq
- OpenAI
- Claude
- Gemini
- Ollama

---

## Architecture

```text
generation/

    models.py
    interfaces.py
    service.py
    registry.py
    create.py

    providers/

        groq.py
        openai.py
        claude.py
        gemini.py
        ollama.py

    structured_output/      # registry, parsers, repair — connected end-to-end
    validation/              # ValidationRegistry, ValidationService, scoring, input/output/hallucination/runtime validators, 5 runtime contracts
    policies/                 # AcceptancePolicy, FailFastPolicy, RuntimeValidationPolicy
    observability/            # GenerationMetricsSnapshot, GenerationMetricsService
    langchain/                # with_structured_output() bridge (4/5 providers)
    prompts/                  # pre-existing template platform, now bridged in
    catalog/                  # scored ModelMetadata + ModelCatalogRegistry
    routing/                  # RoutingService — strategies, scoring, fallback chains
```

---

## Workflow

```text
Prompt Context (+ optional PromptService template rendering)
        ↓
Generation Service
        ↓
LLM Provider — native structured output → parser fallback
        ↓
Validation (input + output + hallucination stages → ValidationReport)
        ↓
Regeneration (opt-in, corrective feedback) if parsing failed or the output stage is invalid
        ↓
Generated Answer
```

See `docs/architecture/structured-output-platform.md` for the detailed,
continuously-updated breakdown of this subsystem.

---

## LangChain Usage (Implemented)

- `with_structured_output()` — `generation/langchain/output_parsers.py`,
  a standalone alternative to the native-SDK path for OpenAI, Claude,
  Gemini, and Ollama (not Groq — `langchain-groq` has no release
  compatible with the pinned `groq>=1.5.0` SDK floor)
- `PydanticOutputParser` / `JsonOutputParser` — power the Structured
  Output Platform's `PydanticParser`/`JsonParser` and the
  `generate_from_template()` format-instructions step
- `ChatPromptTemplate` / few-shot prompt templates — power the
  pre-existing Prompt Platform

Still potential future usage: LCEL composition.

Frameworks remain implementation details.

---

## Deliverables

- ✅ Generation service
- ✅ Provider abstraction
- ✅ Prompt platform (bridged in)
- ✅ Streaming support
- ✅ Structured output (native + fallback + registry + LangChain + regeneration)
- ✅ Validation Platform integration (input/output/hallucination/runtime validators, registry, scoring, `ValidationReport`, five runtime contracts, completeness/consistency/formatting/response-size all done)
- ✅ Validation Policy Layer (Acceptance/Fail-Fast/Runtime Validation policies)
- ✅ Routing Platform (scored catalog, task-based strategies, fallback chains)
- ✅ Runtime Caching Platform (L1 exact/L2 semantic/L3 session, policy resolution)
- ✅ Runtime Metrics Integration (`GenerationMetricsService`, Prometheus-ready counters)
- ✅ Artifact Platform (`GenerationArtifact` incl. `metrics.json`, persisted on every `generate()` call)

# Phase 3.9 — Research APIs

**Status:** ✅ Complete, per `research_api_prd.md` — ResearchMind's first live, end-to-end product surface: upload a document, ask a question, get a grounded, cited, streamable answer back, replayable later (the "NotebookLM + Perplexity" product vision).

---

## Goal

Give ResearchMind a single question-answering surface, composing the already-complete Retrieval, Context, Generation Runtime, Streaming, and Artifact Platforms into one product loop.

---

## Responsibilities

- ✅ `POST /research` — ask a question, get `{research_id, query, answer, citations, sources, duration_ms}`
- ✅ `POST /research/stream` — the same, over SSE
- ✅ `POST /research/citations` — citation-panel preview, no generation
- ✅ `GET /research/{id}` — replay a past research session
- ✅ All routes auth-required and owner-scoped
- ✅ New `ResearchService` (`apps/api/app/ai/research/service.py`) — composes the Retrieval Platform (hybrid search + rerank) → Context Platform (dedup/expand/merge/compress/cite) → Generation Runtime Platform (3.15 below, its first real caller) → Streaming Platform (streaming route) → Artifact Platform (best-effort persistence via the Research artifact writer, previously unwired scaffolding)
- ✅ New Postgres `research_sessions` table (model + repository + Alembic migration) for session replay
- ✅ First real exercise of `RuntimeType.RESEARCH` (Runtime Validation Platform) and `ArtifactRuntime.RESEARCH` (Artifact Platform) — both go from reserved-but-unused to live
- ❌ Query decomposition, research planning/multi-step loops, agents, LangGraph — explicitly out of scope per the PRD's Non-Goals; see Milestone 3.11 (Research Runtime) and Phase 5 (AI Agent Platform)

---

## Deliverables

- ✅ 23 new tests, full suite passing (1068 tests), ruff/mypy clean
- ✅ Deliberately linear/simple per the PRD's own Non-Goals — no Research Runtime, no Deep Research Runtime, no Agent Platform, no LangGraph; all remain future roadmap items

---

# Phase 3.13 — Guardrails Platform

**Status:** ✅ Complete (MVP Foundation, per `guardrails_platform_prd.md`) — ✅ Integrated into the Generation Platform and Context Building Platform (per `guardrail_integration_prd.md`)

---

## Goal

Answer a different question than Validation: not "did the system produce a good output?" but "should the system even perform this operation?"

---

## Responsibilities

- ✅ Input Guardrails — prompt injection/jailbreak detection (P0), scope validation, PII detection (foundation); rate limit/toxicity are foundation interfaces (always-allow)
- ✅ Retrieval Guardrails — Context Sanitization (composes the pre-existing `ContextGuardrailService`, does not duplicate it), a new Source Trust Platform (P1), Citation Integrity; Access Control is a foundation interface (permissive default)
- ✅ Generation Guardrails — Faithfulness Enforcement and Schema Enforcement (both wrap the Validation Platform's validators per the PRD's explicit reuse instruction), PII Leakage; Moderation is a foundation interface (always-allow)
- ✅ Runtime Guardrails — Budget Guardrail (P1, "implement immediately"), Loop Detection (real algorithm); Tool Policy and Approval Gate are foundation interfaces only, deliberately unimplemented (the future LangGraph-interrupt seam)
- ✅ `GuardrailService`, `GuardrailRegistry`, weighted risk scoring, fail/risk/regeneration/runtime policies, `GuardrailArtifactWriter`
- ✅ Wiring into `GenerationService` (input gate before every provider call + full report on `GenerationResult.guardrails`) and `ContextBuilderService` (retrieval-stage gate before context building) — per `guardrail_integration_prd.md`
- ❌ Wiring into a router or agent runtime for `evaluate_runtime()` — needs a `/research` API first, same gap as the Runtime Validation Platform

---

## Deliverables

- ✅ `apps/api/app/ai/guardrails/` package, 113 unit tests from the original build + 14 more from the integration pass, full repo suite/ruff/mypy clean
- ✅ Two dead, zero-reference scaffolds removed (`app/ai/guardrails/{policies,scanners}.py`, all of `app/ai/runtime/generation/guardrails/`)
- ✅ Wired into the live generation pipeline (`GenerationService`) and the Context Building Platform (`ContextBuilderService`), plus artifact persistence and metrics/logging on `GuardrailService.evaluate()` itself
- ❌ LLM-based classifiers (Llama Guard, Lakera, NeMo Guardrails) — explicitly skipped for MVP
- ❌ Wiring into a router/agent runtime for the runtime stage — needs `/research` first

# Phase 3.14 — Artifact Platform

**Status:** ✅ Complete for Generation/Streaming/Conversation (per `artifacts_platform_prd.md`) — 🟡 Session/Research/Agent/Evaluation built but scaffold-only, unwired

Numbered 3.14 here (next free slot after Guardrails' 3.13) rather than the PRD's own self-declared "Milestone 3.10" — that number is already taken in this roadmap's table by the Evaluation Platform. `PROJECT_STATUS.md` uses the PRD's own "Milestone 3.10" label instead, since its numbering scheme doesn't collide.

---

## Goal

Canonical, immutable, versioned, policy-gated persistence for AI Runtime executions — the foundation for replay, debugging, evaluation datasets, and future observability, extending to the runtime side the same "artifacts are the source of truth" principle the ingestion side (Knowledge Platform) has always followed.

---

## Responsibilities

- ✅ Foundation — `ArtifactPolicy`/`ArtifactCategory`/`ArtifactRuntime` enums, `ArtifactMetadata`, `ArtifactPolicyService.should_persist(runtime, category)`, shared `BaseArtifactWriter`/`BaseArtifactReader`
- ✅ Generation Artifacts — `GenerationArtifact` (request/response/metadata/validation/guardrails/routing/cache.json), wired into `GenerationService.generate()`
- ✅ Streaming Artifacts — `StreamArtifact` (events/timeline/stream/metrics.json), wired into `StreamingService._stream_live()`
- ✅ Conversation Artifacts — `ConversationTurnArtifact` (one immutable file per turn) + `ConversationIdentity`, wired into `chat.py`
- ✅ Replay Platform — `GenerationReplayService`/`StreamReplayService` (real, reconstruct from persisted artifacts)
- 🟡 Session/Research/Agent/Evaluation Artifacts — fully built and unit-tested, deliberately unwired (no session concept, Research Runtime, Agent Runtime, or evaluation harness exists yet); `ResearchReplayService` is a `NotImplementedError` stub
- ❌ Automated retention/expiry enforcement — informational-only in this pass

---

## Deliverables

- ✅ New centralized `apps/api/app/ai/artifacts/` package, 39 unit tests, full repo suite (931 tests)/ruff clean
- ✅ Old dead, zero-reference scaffold removed (`app/ai/runtime/generation/artifacts/`, 4 empty files)
- ✅ `DocumentStorage.list_keys(*, prefix)` added to `infrastructure/storage/` — required for `ConversationArtifactReader`
- ✅ Wired into the live Generation, Streaming, and Conversation paths, best-effort (storage failures are caught/logged, never fail the run that already succeeded)
- ❌ Session/Research/Agent/Evaluation wiring — needs a real session concept, `/research` API, Agent Runtime, and evaluation harness respectively

# Final MVP Pipeline

```text
                    User Query
                         │
          ┌──────────────┴──────────────┐
          │                             │
     Sparse Search               Dense Search
          │                             │
       Top 50                        Top 50
          └──────────────┬──────────────┘
                         │
                  Parallel Execution
                         │
                  Reciprocal Rank Fusion
                         │
                     Top 20 Results
                         │
                     Reranker
                         │
                      Top 5 Results
                         │
                  Context Builder
                         │
                  Parent Expansion
                         │
                  Adjacent Merge
                         │
               Token Budget Compression
                         │
                  Citation Builder
                         │
                  Prompt Formatter
                         │
                 Generation Platform
                         │
                    Final Answer
                    + Citations
```

Milestone	Platform	Deliverables	Status
3.1	Retrieval Foundation	Query processing, dense retrieval	✅ Complete
3.2	Sparse Retrieval	SPLADE, sparse search	✅ Complete
3.3	Hybrid Retrieval	Dense + Sparse + RRF	✅ Complete
3.4	Retrieval Strategies	Parallel Retrieval, Parent/Child Retrieval, Runtime Query Decomposition	✅ Parallel Retrieval complete (3-way: dense+sparse+metadata) + ✅ Parent/Child Retrieval complete (genuinely end-to-end now — producer added via Hierarchical Chunking) (Query Decomposition moved to 3.11)
3.5	Result Processing	Metadata filtering, Top-K	✅ Complete
3.6	Reranking Platform	Voyage, CrossEncoder	✅ Complete
3.7	Context Building Platform	Parent Expansion, Merge, Compression, Guardrails, Citations, Prompt Formatter	✅ Complete (Compression V1-V4, LangChain wired into default pipeline)
3.8	Generation Platform	Multi-provider LLM runtime, structured output, validation, policy layer, regeneration, routing, caching, streaming, metrics, artifacts	✅ Complete, per `generation_platform_complexion_prd.md` — runtime contracts registered but dormant pending a /research API
3.9	Research APIs	/research, streaming, citations	✅ Complete (row stale below — this file is frozen/not continuously updated; see PROJECT_STATUS.md/ROADMAP.md for authoritative status), per `research_api_prd.md`
3.10	Evaluation Platform	Groundedness, Hallucinations, Citation Accuracy	🟡 Retrieval evaluation complete + ✅ Generation evaluation (Groundedness/Faithfulness/Relevance/Completeness/Citation Accuracy/Hallucination Rate/Cost) + ✅ Regression Detection (incl. cost thresholds), both built into repo-root `benchmarks/` rather than a new `app/ai/evaluation/` (`evaluation_platform_prd.md` was reconciled against the already-live Observability Platform and the already-real Benchmark Platform rather than implemented literally — see PROJECT_STATUS.md). Runtime Evaluation (Layer 2) is the already-complete Observability Platform (3.16 below); Experimentation Platform (Layer 3) remains not started
3.11	Research Runtime	Planner, Query Decomposition, Agents	❌ Not Started — Research now has persisted thread history and cost-aware Memory Platform context; the future graph must reuse the final-turn extraction orchestrator rather than extracting from planner/tool/reviewer nodes. Query decomposition/rewriting, planning, and agents remain future work
3.12	Long-Term Platform	Research Sessions, Memory, MCP	🟡 Memory Platform is complete and wired into Chat/Research: compact session state, policy-gated extraction, bounded interest promotion, parallel durable retrieval, and separate memory-cost accounting are live. MCP and broader long-term-platform work remain not started
3.13	Guardrails Platform	Input/Retrieval/Generation/Runtime guardrails, Source Trust, policies, scoring, artifacts	✅ MVP Foundation Complete + ✅ Integrated into Generation Platform and Context Building Platform (runtime stage still needs a router/agent runtime caller)
3.14	Artifact Platform	Canonical persistence/replay for Generation/Streaming/Conversation, policy-gated, S3-backed	✅ Complete for Generation/Streaming/Conversation + 🟡 Session/Research/Agent/Evaluation built but scaffold-only
3.15	Generation Runtime Platform	execute_generation()/GenerationRuntime.execute() canonical entrypoint	✅ Complete, per `generation_runtime_platform_prd.md` (referenced in this doc's own summary paragraph above; row was missing from this table until now)
3.16	Observability Platform	Metrics/statistics/reports/artifacts (Generation, Streaming, Chat, Processing) + real LangSmith tracing	✅ Complete, per `oberservability_platform_prd.md` (self-numbered "Phase 3.9" in its own PRD header — collides with this table's pre-existing 3.9, so numbered 3.16 here instead). Three real bugs found + fixed via live verification against an actual LangSmith account/S3 bucket (streaming path completely dark, missing artifact-policy rule silently ate research artifacts, tracer never sent real input/output), plus a follow-up closing a real gap (streamed generations never ran post-generation validation/guardrail scoring). See PROJECT_STATUS.md for full detail

# Architecture Principles

- Retrieval is responsible only for finding knowledge.
- Reranking improves ordering.
- Context Building prepares knowledge for LLM consumption.
- Generation owns all LLM interactions.
- Evaluation measures every improvement.
- Runtime owns planning and reasoning.
- Artifacts remain the source of truth.
- Vector databases are acceleration mechanisms only.
- Frameworks remain implementation details.
- Provider SDKs never leak outside provider implementations.

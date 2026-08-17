# ResearchMind AI — Project Status

**Current reconciliation:** 2026-08-17 — see the current addendum below; the
long `Last Updated` entry is retained as historical build-log context.

**Last Updated:** 2026-08-12 (+ The Evaluation Platform reached full production maturity per `docs/PRIORITIZED_ROADMAP.md` Wave 0/Wave 1, items E1–E23: a 115-example golden dataset with Ragas scoring, CI regression gates (including a manual-dispatch live-service suite covering all 3 absolute gates — fabricated-citation, schema-validity, abstention-pass rates), a cross-surface citation validator, an online risk-weighted scoring job, a feedback loop (`POST /feedback`, thumbs up/down on all 3 surfaces, mirrored into LangSmith's own `create_feedback()`), an internal eval dashboard with owner/segment/promotion-review drill-down, an LLM-as-judge rubric metric, latency-SLO alerts across Chat/Linear Research/Deep Research, cost forecasting, an 18-case adversarial dataset, and a tool-invocation-rate metric. This entry supersedes the "Evaluation Platform Expansion" line further down this file, which predates all of the above — see `docs/EVALUATION_IMPLEMENTATION_TRACKER.md` for full task-level detail. This doc itself otherwise remains a dated build log rather than a living doc; only this header and the superseded-entry note were added, historical entries below are left as originally written.) Prior update, 2026-07-26: + ResearchMind became an MCP **client** for the first time — a narrow, single-tool "Research Intelligence MCP" paper-search platform (`app/ai/tools/paper_search/`, ADR-037) reachable from both Chat (toggle-gated, query-distilled) and Deep Research (a non-blocking post-report suggestion, not a 4th approval checkpoint). This is a scoped-down MCP **client** integration for one external capability, not the general-purpose Phase 6/7 Agentic/MCP Ecosystem — that remains explicitly out of scope, deferred per ADR-033, and unaffected by this work; see the new "2026-07-25/26 Research Intelligence MCP Paper Search Platform" section under Phase 6 below. Same session: a real production bug fix in the Memory Platform — Deep Research/Chat follow-ups using a pronoun ("so how is magma related to it?") had nothing to resolve the pronoun against, since no session-level "what is this about" state was ever persisted; a new `SessionStateUpdaterService` (`app/ai/memory/session/state_updater.py`, replacing the old narrow-trigger-phrase `state_from_user_turn`) now maintains one evolving, upserted-in-place SESSION memory summary per session after every turn. Also (uncommitted as of 2026-07-26): Chat, Research, and Deep Research answers now render as real Markdown (`apps/web/src/components/ui/markdown.tsx`, `react-markdown`+`remark-gfm`+`remark-breaks`) instead of raw `whitespace-pre-wrap` text — lists/headings/bold/tables/code blocks now format correctly, and citation badges (`[S1]`/`[W1-1]`) are now produced by a remark plugin operating on the parsed markdown tree rather than a hand-rolled string-splitting regex, fixing a real bug where a web-citation marker embedded in a rejected-report's fallback answer rendered as plain unstyled text. Prior update, 2026-07-25: + Chat gained web search — toggle-gated, no approval, reusing the Deep Research Web Search Tool Platform unchanged — and citation chips across both surfaces now visually distinguish web-sourced citations from document ones. See the "AUTO model swap + Chat web search" and "Citation web-source UI + composer label" sections under Phase 6 below. Prior update, 2026-07-24: + A user-driven testing pass against the real, working Deep Research frontend surfaced six concrete UX/correctness gaps in the flow verified end-to-end the day before — all six are now fixed: the progress-step log no longer disappears once a run reaches report-review/done/failed, PDF citation references resolve to filenames instead of raw document UUIDs, Linear and Deep Research turns now correctly share one conversation instead of forking a new one per Deep Research call, a Deep Research run now survives a page refresh (conversation replay reconstructs its live/paused/completed state, not just Linear turns), rejecting a report no longer discards the synthesized content as a terminal `failed` run — it now still publishes as a plain answer, just without the PDF — and the report-approval step is no longer blind: a new `GET /research/runs/{id}/draft` endpoint reads the pending draft straight out of the paused run's LangGraph checkpoint, and the frontend now shows (and lets a reviewer edit, citation-safely) the report before deciding. See Phase 6's new "2026-07-24 UX/reliability pass" section below and `PRODUCT_FLOWS_AND_GAPS.md` for the code-verified detail. + Prior update, 2026-07-23: Deep Research became a complete, working, end-to-end single-agent workflow with a real frontend — memory-aware planning, a second human checkpoint via a real LangGraph report-approval `interrupt()`, real per-owner rate limiting across all three product paths, a fixed cross-run cache-leakage risk in synthesis/review, a full Research-UI Deep Research destination consuming live SSE progress events for the first time, and a same-day manual browser click-through that surfaced and fixed two worker session-staleness bugs — see Phase 6's "2026-07-23 verification pass" below.)

**Current addendum (2026-08-17):** M9-M10 USER-preference quality is implemented; M11 adds scheduled bounded PostgreSQL/Qdrant inventory and operations dashboards/alerts. M12 completes the scope-aware management API: safe durable-memory projections and filters, authorized mutations, explicit audited edits, confirmed moves, independent capture/retrieval settings, and real two-user/two-project isolation tests. Memory M0-M2/M4-M12 are implemented; M3 production rollout, M6-M10 calibration, and M13 Project UI remain. The same verification pass fixed Linear Research false relevance: owner-only metadata scrolling no longer injects arbitrary chunks, reranking evaluates the expanded pool, an absolute configurable relevance gate can return zero documents, and the UI no longer labels every weak best match as 100%.

**Scope-framing correction (2026-07-26, not a code change):** several historical entries below (and in `AI_ENGINEERING_AUDIT.md`) describe Chat having no retrieval/RAG wiring using "❌"/"gap" language. That description of current behavior is accurate, but the framing was wrong — Chat's lack of document grounding is the deliberate three-surface product design (Chat fast/conversational/NOT document-grounded; Linear Research and Deep Research document-grounded), confirmed with the user 2026-07-26, not an unfinished feature. Historical entries are left as-written since this file is a dated build log, not a living doc; read any "Chat has no retrieval/RAG" mention below as a scope note, not an open defect. See `PRODUCT_FLOWS_AND_GAPS.md`'s Chat section for the current framing.

**Current Maturity:** NotebookLM++ + Perplexity Foundation — Hybrid Retrieval, Reranking, Parent Expansion, and Context Guardrails are all in place, putting the platform ahead of NotebookLM and closing in on a Perplexity v1 experience. The Context Platform's Compression stage is now complete end to end (V1-V4 — Token Budget, Embedding Redundancy, LangChain Contextual, and LLM per-chunk summarization — per `context_platform_complexion_prd.md`), with LangChain compression wired into `ContextBuilderService.build()`'s default pipeline behind an opt-in `settings.enable_langchain_compression` flag. A platform-wide Guardrails Platform (input/retrieval/generation/runtime stages, Source Trust, policies, scoring, artifacts) now sits alongside the Validation Platform as a completed foundation layer, and — per `guardrail_integration_prd.md` — is wired directly into both `GenerationService` (input gate before every provider call, full evaluate() report attached to `GenerationResult.guardrails`) and `ContextBuilderService` (retrieval-stage gate before context building). The Generation Platform is now fully complete, per `generation_platform_complexion_prd.md`: Routing Platform (model/provider selection, scored catalog, strategy-weighted fallback chains), Runtime Caching Platform (L1 exact/L2 semantic/L3 session caching, policy resolution, wired into `GenerationService`), Streaming Platform (canonical event protocol, SSE + WebSocket transports, `stream_generate()`, cache-hit replay), five per-runtime Validation Contracts (Research/Planner/Reviewer/Agent/MCP), a Validation Policy Layer, every PRD output validator, and Runtime Metrics Integration are all done. Critically, the Generation Platform is now reachable over HTTP for the first time — `POST /api/v1/chat/stream` (SSE) and `/api/v1/chat/ws` (WebSocket) are live, backed by a new minimal Conversation/Message persistence layer. A new, centralized Artifact Platform (`app/ai/artifacts/`, per `artifacts_platform_prd.md`) now persists every generation call, completed stream, and conversation turn as an immutable, versioned, policy-gated artifact in S3 — the canonical execution history layer the ingestion side has always had, now extended to the runtime side. A thin Generation Runtime Platform (`app/ai/runtime/generation/orchestration/`, per `generation_runtime_platform_prd.md`) then gave every future caller one canonical entrypoint, `execute_generation()`, into that already-complete `GenerationService.generate()` flow instead of reaching into `GenerationService` directly — and that entrypoint now has its first real caller: the new Research API Platform (Phase 4, per `research_api_prd.md`) is ResearchMind's **first live, end-to-end product surface** — `POST /api/v1/research` (plus `/research/stream`, `/research/citations`, `GET /research/{research_id}`) lets a user upload documents, ask a question, and get back a grounded, cited, streamable answer, via a new `ResearchService` composing Retrieval (hybrid search + rerank) + Context (dedup/expand/merge/compress/cite) + Generation Runtime + Streaming + best-effort Artifact persistence. This is also the first live code exercising `RuntimeType.RESEARCH` and `ArtifactRuntime.RESEARCH` — previously reserved-but-unused enum values — and the first live caller of the previously scaffold-only Research Artifact writer. Session/Agent/Evaluation artifacts remain built but scaffold-only, since those runtimes still don't exist yet. Most recently, an **AI Runtime Observability Platform** (`oberservability_platform_prd.md`, Phase 3.9) shipped and was hardened through several rounds of real-world verification against a live LangSmith account and S3 bucket: canonical metrics/statistics/report-builder subpackages under a new `app/ai/observability/`, real (not stubbed) LangSmith tracing + artifact persistence wired into **both** Generation entry points — `generate()` and, after a bug found via live testing, `stream_generate()` too (meaning Research, Chat, and any future streaming caller all get it "for free") — plus the Knowledge Processing pipeline (parse/chunk/embed/index, no LLM call, so metrics/report only, no trace). Three real bugs were found and fixed by testing against the actual frontend rather than trusting the initial implementation: (1) tracing/artifacts were wired into `generate()` only, silently dark for every streamed request; (2) a missing `(RESEARCH, OBSERVABILITY)` artifact policy rule silently skipped every research artifact write even with tracing working; (3) the tracer only ever sent metadata tags as LangSmith's "input" and never sent an "output" at all. A follow-up closed a real product gap surfaced by the same verification: streamed generations never ran post-generation validation/guardrail scoring at all (only pre-generation input checks) — `GenerationService.score_completed_stream()` now runs the same checks `generate()` does, informationally, never blocking (there's nothing left to stop once tokens reached the client). Separately, verifying the Research feature surfaced an unrelated, real product gap: **Research has no multi-turn conversation memory at all** — every query is a fully standalone retrieval + generation call with no history, no query rewriting, and no session continuity, unlike Chat (which has persisted history, just flattened at the provider boundary). See `AI_ENGINEERING_AUDIT.md` for the full write-up. Most recently, `evaluation_platform_prd.md` (Phase 4.1 in its own header, a number already taken in this file by Research Frontend Integration) asked for a full new Evaluation Platform — datasets/evaluators/benchmarks/experiments/regression/reports under a new `app/ai/evaluation/`. Investigation found that would have duplicated two things that already exist under different names: the "Engineering Benchmarks" layer described in `docs/architecture/evaluation-strategy.md` is already real, working code at repo-root `benchmarks/` (not the empty `app/ai/quality/` scaffold the PRD's folder layout would have paralleled), and the "Runtime Evaluation" layer described in `docs/architecture/evaluation-platform.md` is already implemented as the AI Runtime Observability Platform above — confirmed by `STRUCTURE.md`'s own annotation on that doc's sibling. The PRD's Experiment Platform section was also deferred, since it would have forked the separately-designed, not-yet-built async Experimentation Platform before it exists. What was real and missing — Generation evaluation and Regression Detection — was built directly into `benchmarks/` instead; see the Engineering Benchmark Platform section below for detail, including a real citation-accuracy bug found and fixed via live verification against Groq/OpenAI/Claude. Since then, the Retrieval Platform closed its last two tracked gaps (see "Recently Completed" below): **Parent/Child Retrieval** now has a real producer (`HierarchicalChunkingProvider`) feeding the previously-orphaned `ParentExpansionService`, and **Parallel Retrieval** grew from a dense+sparse 2-way `asyncio.gather()` to a 3-way one with a new filter-only Metadata branch. Most recently, a new **Memory Platform** (`app/ai/memory/`, per `memory_platform_prd.md`) closed the multi-turn conversation memory gap flagged earlier in this file — SESSION (Valkey)/USER+SEMANTIC+RESEARCH (Postgres+Qdrant) storage, a `MemoryService` orchestrator, and a new `/memory` API, extended same-session against a follow-up 5-pipeline architecture review (Reciprocal Rank Fusion search, LLM-driven extraction, a lifecycle sweep), then wired into **both** live surfaces via Runtime Memory Injection — `ResearchService` first, then `chat.py` in a further follow-up. Wiring Chat to memory surfaced that `chat.py` was actually crashing on **every single message, unconditionally** (`GenerationService._validate()` hard-rejected the empty `PromptContext.context` every unretrieval-backed chat request always had) — fixed, along with a second, independent latent bug where `GenerationRequest.output_model` couldn't be serialized for artifact persistence. Separately, the Routing Platform's `AUTO` strategy now hard-defaults to Groq instead of the scoring engine's own top pick (previously claude-sonnet-5 essentially always), per explicit request. See Milestone 12 and the Milestone 2.9.7 Addendum below for full detail. Most recently, **Chat got its own frontend surface** (Phase 4.2, `apps/web`'s new `/chat` page) — closing the product-IA gap flagged at the end of Phase 4.1: Chat (user knows the question — fast, interactive, ungrounded) and Research (user knows the goal — slow, cited, report-generating) are now two visibly separate surfaces instead of Chat existing only as a backend API with no way to reach it. This needed one small but load-bearing backend fix first: `chat.py` never populated `GenerationRequest.session_id`, so a client starting a new conversation had no way to learn the server-assigned `conversation_id` from the stream after turn 1 (`ConversationService.get_or_create()` 404s on an unknown client-supplied id rather than creating one, so the frontend can't just mint its own) — permanently blocking multi-turn chat from a fresh session. Fixed with `session_id=conversation_id`, the exact pattern `ResearchService` already used for the same reason. See Phase 4.2 below for full detail. Maturity ladder: `NotebookLM++ → Perplexity v1 (reached) → Open Deep Research → Manus / Glean`.

---

# Phase 1 — Identity Platform

## Milestone 1.1 — Configuration

**Status:** ✅ Complete

---

## Milestone 1.2 — Database Foundation

**Status:** ✅ Complete

---

## Milestone 1.3 — Internal User Domain

**Status:** ✅ Complete

### Completed

- Internal User entity
- SQLAlchemy ORM model
- Alembic migration
- Repository pattern
- Service layer
- User synchronization
- Application exception handling

---

## Milestone 1.4 — Authentication & Authorization

**Status:** ✅ Complete

### Completed

- AWS Cognito authentication
- JWT validation
- Authorization foundation
- Protected API endpoints

---

# Phase 2 — Knowledge Platform

---

# Milestone 2.1 — Document Upload Platform

**Status:** ✅ Complete

### Completed

- Document upload API
- Upload validation
- Storage abstraction
- Amazon S3 integration
- SHA-256 hashing
- Duplicate detection
- Upload lifecycle

---

# Milestone 2.2 — Processing Platform

**Status:** ✅ Complete

## Processing Foundation

Implemented

- ProcessingService
- DocumentProcessingService
- Queue processing
- Worker
- Retry
- Dead Letter Queue
- Processing lifecycle

---

## Parser Platform

Implemented

- Parser abstraction
- Parser registry
- Docling provider
- Canonical ProcessedDocument

---

## Metadata Platform

Implemented

- Metadata registry
- Metadata enrichment
- PDF metadata
- Language detection

---

## Statistics Platform

Implemented

- Statistics registry
- Statistics enrichment

Extracted

- Pages
- Words
- Characters
- Paragraphs
- Headings
- Tables
- Figures

---

## Processing Artifacts

Generated

- processed_document.json
- parsed.md
- parsed.txt

Persisted automatically to Amazon S3.

---

## AWS Integrations

Implemented

- Amazon Cognito
- Amazon S3
- Amazon SQS

---

# Milestone 2.3 — Chunking Platform

**Status:** ✅ Complete

## Foundation

Implemented

- Canonical Chunk model
- Provenance
- Statistics
- Experiment metadata
- Metadata
- Provider abstraction
- Registry
- Factory
- ChunkingService

---

## Providers

Implemented

- Fixed Chunking
- Recursive Chunking
- Markdown Chunking
- Hierarchical (Parent/Child) Chunking — `HierarchicalChunkingProvider`, two-pass LangChain `RecursiveCharacterTextSplitter` (parent sections, then child chunks per parent). Children carry `structure.parent_chunk_id`; parent sections are tagged `is_parent` in `experiment.additional_metadata` and excluded from embedding/indexing by `EmbeddingService`, but persisted in the `ChunkArtifact` so the Context Platform's `ParentExpansionService` (Milestone 2.8.1) can resolve a retrieved child back into its full parent section — this is the producer half of Parent/Child Retrieval that was previously missing

---

## Artifact Platform

Implemented

- ChunkArtifact
- ChunkArtifactBuilder
- ChunkArtifactWriter

Artifacts

```
chunking/

    {strategy}/

        {artifact_id}/

            chunks.json
```

---

## Processing Integration

Implemented

```
Processing

↓

Chunking

↓

ChunkArtifact
```

---

## Benchmark Platform

Implemented

- Benchmark framework
- Registry
- Runner
- Dataset loader
- Markdown report generator
- JSON report generator
- Chunking Benchmark

---

# Milestone 2.4 — Embedding Platform

**Status:** ✅ Complete

## Foundation

Implemented

- Canonical Embedding model
- Provenance
- Statistics
- Provider metadata
- Experiment metadata

---

## Architecture

Implemented

- Provider Pattern
- Registry Pattern
- Factory Pattern
- Composition Root (`create.py`)
- Framework-independent canonical models

---

## Providers

Implemented

- ✅ Sentence Transformers
- ✅ Voyage AI
- ✅ OpenAI

Future

- BGE
- Instructor
- Nomic

---

## Shared Batching

Implemented

- EmbeddingBatcher
- Streaming batch processing
- Provider-specific batch configuration

Default batch sizes

| Provider | Batch Size |
|-----------|-----------:|
| Sentence Transformers | 64 |
| Voyage AI | 32 |
| OpenAI | 128 |

---

## Artifact Platform

Implemented

- EmbeddingArtifact
- EmbeddingArtifactBuilder
- EmbeddingArtifactWriter

Artifacts

```
embeddings/

    {provider}/

        {artifact_id}/

            embeddings.json
```

---

## Processing Integration

Implemented

```
Processing

↓

Chunking

↓

Embedding

↓

EmbeddingArtifact
```

---

## Manual Verification

Completed

Verified

- Sentence Transformers
- Voyage AI
- OpenAI
- Batch embedding
- Artifact generation
- Amazon S3 persistence
- Provider metadata
- Configuration fingerprints
- Canonical models
- Runtime metrics

---

## Documentation

Completed

Architecture

- Embedding Platform Architecture

Engineering Journals

- Embedding Platform
- Multi-provider Embeddings & Shared Batching

ADR

- ADR-008 — Canonical AI Platform Pipeline

---

# Phase 2.4.4 — Runtime Metrics Foundation

**Status:** ✅ Complete

The initial Runtime Metrics Foundation has been implemented as the first vertical slice of the Observability Platform.

Implemented

- RuntimeMetricsCollector
- Stage metrics
- Pipeline metrics
- Runtime report generation
- Memory measurement
- Artifact size measurement
- ProcessingService integration

Collected Metrics

- Execution duration
- Stage duration
- Pipeline duration
- Peak memory
- Artifact size
- Provider
- Provider version

Example

```
Processing Pipeline Metrics

Processing

Chunking

Embedding

Peak Memory

Pipeline Duration
```

---

# Phase 2.4.5 — Observability Platform

**Status:** 🚧 Deferred

The Runtime Metrics Foundation has been completed.

The remaining Observability Platform capabilities have been intentionally postponed in favor of delivering core AI functionality.

Future scope

- Cost tracking
- Token usage
- Queue latency
- GPU monitoring
- Tracing
- Telemetry
- OpenTelemetry
- Grafana dashboards

---

# Milestone 2.5 — Vector Store Platform

**Status:** ✅ Complete

Implemented

- Canonical models (`VectorStoreRecord`, `SparseVector`, `VectorPayload`, `CollectionDefinition`, `CollectionMetadata`, `IndexStatistics`)
- Provider abstraction (`VectorStoreProviderInterface`)
- Registry Pattern
- Composition Root (`create.py`)
- Qdrant provider — collection create/exists, batched upsert, delete-by-document, count, collection info

Documentation

- ADR-017 — Vector Store Platform Architecture

---

# Milestone 2.6 — Indexing Platform (Hybrid Retrieval)

**Status:** ✅ Complete

ResearchMind now indexes both a dense and a sparse vector for every chunk into the same Qdrant collection, enabling native hybrid retrieval without a separate BM25 platform.

Implemented

- `IndexingService` — orchestrates dense+sparse record building, collection creation, upsert, statistics, artifact persistence
- `FastEmbedSparseEmbeddingProvider` — SPLADE sparse vectors (`prithivida/Splade_PP_en_v1`), generated off the event loop via `asyncio.to_thread`
- Qdrant collection schema migrated from a single unnamed vector to named `dense` + `sparse` vectors per point
- `IndexingRequest` extended to carry the source `ChunkArtifact` (sparse generation needs raw chunk text)
- `IndexingArtifact` / `indexing.json`, `IndexStatistics.indexed_sparse_vectors`
- Fixed a latent bug: `VectorPayload.chunk_index` was hardcoded to `0` for every chunk; now reflects the real chunk position

Manual Verification

- Dropped and recreated the dev `researchmind_knowledge` Qdrant collection (old single-vector schema → new dense+sparse schema)
- Ran the real pipeline end-to-end (Voyage AI dense + FastEmbed SPLADE sparse + Qdrant), confirmed both named vectors present
- Issued a real sparse-vector query — the keyword-relevant chunk scored 17.15 vs. 0.66 for an unrelated chunk, confirming lexical matching works
- Full test suite (234 tests), ruff, and mypy pass

Documentation

- ADR-018 — Knowledge Indexing and Retrieval Architecture
- ADR-019 — Qdrant Native Hybrid Retrieval
- `docs/architecture/hybrid-retrieval-indexing.md` — complete ingestion pipeline flow diagram, schema before/after, verification results

---

# Milestone 2.7 — Retrieval Platform

**Status:** ✅ Complete (Foundation + Metadata Filtering + Reranking + 3-way Parallel Retrieval)

ResearchMind can now query the hybrid Qdrant index built in Milestone 2.6. Dense, sparse, and hybrid (RRF-fused) retrieval are implemented, benchmarked, and exposed via API. Metadata filtering and reranking are implemented end-to-end. Parent/Child retrieval is now genuinely end-to-end too (chunking-side producer added this session, see below); only query decomposition/multi-query and a retrieval result cache remain open.

## Query Processing

Implemented

- Query validation — empty/whitespace query, max length, `top_k` bounds
- Query normalization — whitespace collapsing
- Dense query embedding (Voyage AI), Valkey-backed cache with TTL and settings-gated enable/disable
- Sparse query embedding (FastEmbed SPLADE)

## Search Engines

- ✅ Semantic (dense) search
- ✅ Sparse search
- ✅ Hybrid search — Reciprocal Rank Fusion of dense + sparse (`k=60`, matching Elasticsearch/Azure AI Search defaults)

## Retrieval Strategies

- ✅ Standard retrieval (top-k similarity search)
- ✅ Metadata retrieval — `QdrantRetrievalProvider.search_metadata()`, a pure filter-only `scroll()` lookup with no vector similarity; short-circuits to an empty result when no filters are present (an unfiltered scroll would ignore tenant/`owner_id` scoping)
- ✅ Parallel retrieval — dense + sparse + metadata search all executed concurrently via a single `asyncio.gather()` in `search_hybrid()` (was 2-way dense+sparse; metadata added this session), then fused together by RRF. `RetrievalStatistics.metadata_latency_ms` added alongside `dense_latency_ms`/`sparse_latency_ms`
- ✅ Parent/Child retrieval — reclassified out of the Retrieval Platform into the Context Platform (see Milestone 2.8 below); implemented there as Parent Expansion + Adjacent Merge. Now genuinely end-to-end: the Chunking Platform's new `HierarchicalChunkingProvider` (Milestone 2.2/2.3) is the producer that was previously missing — it generates parent sections + child chunks (children carry `structure.parent_chunk_id`; parents are excluded from embedding/indexing by `EmbeddingService` but persisted in the `ChunkArtifact` for Parent Expansion to resolve against)
- ✅ Query decomposition — moved to the Research Runtime (Phase 6, see below); implemented there as DAG-validated dependency-wave scheduling, not in this Milestone 2.7 retrieval path

## Result Processing

- ✅ Reciprocal Rank Fusion (RRF)
- ✅ Top-K selection
- ✅ Metadata filtering — `QdrantRetrievalProvider._build_filter` supports `owner_id`, `document_id`, `filename`, `language`; enforced across dense, sparse, and hybrid search
- ✅ Voyage AI reranking — `VoyageReranker` (Voyage AI `rerank-2`), wired into `RetrievalService.search_hybrid(rerank=True)` by default
- ✅ CrossEncoder reranking — `CrossEncoderReranker` (local `BAAI/bge-reranker-base`, sentence-transformers)

## Metadata Filtering

**Status:** ✅ Complete

Implemented

- `QdrantRetrievalProvider._build_filter` — translates canonical `RetrievalQuery.filters` into Qdrant payload filters (`owner_id`, `document_id`, `filename`, `language`); unsupported keys and falsy values are ignored rather than raising
- Applied uniformly across dense, sparse, and hybrid search
- `owner_id` is always injected server-side from the authenticated user (`current_user.id`), never trusted from the request body — see APIs section below

Validated

- Unit tests (`tests/unit/ai/knowledge/retrieval/providers/test_qdrant_filters.py`) — empty/single/multiple filters, `document_id` UUID coercion, unsupported/falsy values ignored
- Integration tests (`tests/api/test_retrieval_filters.py`) — 401 without auth, retrieval scoped to the authenticated user, a spoofed `owner_id` in the request body is ignored
- `MetadataFilteringBenchmark` (`benchmarks/retrieval/metadata_filtering_benchmark.py`) — assigns each benchmark document a distinct synthetic owner and compares unfiltered vs. owner-filtered dense/sparse/hybrid search against a dedicated `benchmark_retrieval_filtering` Qdrant collection

**Finding:** filtering eliminates cross-owner leakage entirely (`leakage_rate: 0.0` for every filtered candidate, down from 0.16–0.21 unfiltered) and raises MRR to a perfect 1.0 across dense, sparse, and hybrid (up from 0.925–0.975 unfiltered) — narrowing the candidate pool to the correct owner means the relevant document always ranks first. Precision@5/10 show no delta, which is a metric-definition artifact of this benchmark corpus (one relevant document per query, so precision@k is capped at `1/k` regardless of filtering) rather than a filtering weakness.

Documentation

- `docs/architecture/metadata-filtering.md`

## Reranking

**Status:** ✅ Complete (Foundation)

Implemented

- Provider abstraction (`RerankingProviderInterface`, `BaseRerankingProvider`), registry, service (`RerankingService`), composition root (`app/ai/knowledge/reranking/create.py`)
- `VoyageReranker` — Voyage AI `rerank-2`
- `CrossEncoderReranker` — local `BAAI/bge-reranker-base` via sentence-transformers, no marginal cost
- Wired into `RetrievalService.search_hybrid(rerank=True)` (default): fuses dense+sparse down to `top_k`, then reranks via Voyage AI before returning
- `HybridRetrieveRequest.rerank` field exists on the API schema, though the `/retrieve/hybrid` endpoint does not yet forward it to the service (always uses the service's `rerank=True` default) — small follow-up item

Validated

- `tests/unit/ai/knowledge/reranking/test_registry.py`
- `RerankingBenchmark` (`benchmarks/reranking/benchmark.py`) — compares `hybrid_only` vs. `hybrid_cross_encoder` vs. `hybrid_voyage` on the *same* hybrid candidate pool per query, reporting Recall@5, MRR, NDCG@5, latency, and a qualitative cost model

**Finding (updated on the 50-document, 160-query corpus):** reranking now has real room to move — `hybrid_only`'s Recall@5 dropped off its old 1.0 ceiling to 0.9583, and both rerankers lift it back up (CrossEncoder 0.9703, Voyage 0.9688) plus improve MRR (0.9552 → 0.9719 CrossEncoder, → 0.976 Voyage) and NDCG@5 (0.943 → 0.9582, tied). Unlike the earlier 5-document finding, **Voyage now edges out the free local CrossEncoder on MRR** (0.976 vs. 0.9719) at the cost of being slower (860ms vs. 603ms avg latency) — the "free CrossEncoder wins outright" conclusion from the small-corpus run doesn't hold up on real data; it's now a genuine quality-vs-latency tradeoff, not a free win.

Documentation

- ADR-022 — Reranking Platform
- `docs/architecture/reranking-platform.md`

## Performance

- ✅ Query embedding cache — Valkey-backed, TTL-based expiry, toggleable via `QUERY_EMBEDDING_CACHE_ENABLED`
- ❌ Retrieval result cache

## APIs

- ✅ `POST /api/v1/retrieve` — dense
- ✅ `POST /api/v1/retrieve/sparse` — sparse
- ✅ `POST /api/v1/retrieve/hybrid` — hybrid (RRF), reranks via Voyage AI by default
- ✅ All three endpoints now require authentication (`Depends(get_current_user)`) and force `owner_id` from the authenticated user, never from the request body — closes a gap where an unauthenticated or spoofed request could read another user's documents
- ✅ `POST /research` (+ `/research/stream`, `/research/citations`, `GET /research/{id}`) — Phase 4, per `research_api_prd.md`
- ❌ Streaming chat
- ❌ Citations

## Retrieval Evaluation

Implemented

- `RetrievalBenchmark` — evaluates dense, sparse, and hybrid against a dedicated, reproducible Qdrant collection (`benchmark_retrieval`, dropped/recreated every run, never touches production data)
- Metrics: Recall@5/10/20, Precision@5/10, MRR, avg/P95/P99 latency, qualitative cost model — matches the ADR-020 required metric set
- 160-query hand-curated ground-truth dataset (`benchmarks/datasets/research-papers/retrieval_queries.json`), document-level relevance, 4 query categories (semantic, acronym, exact-keyword, code-entity)
- ✅ NDCG — `ndcg_at_k` implemented in `benchmarks/retrieval/metrics.py` (binary relevance, standard DCG/IDCG), used by the Reranking Benchmark below

**Finding (updated on the 50-document corpus, up from 5):** dense, sparse, and hybrid now genuinely separate instead of tying at a Recall@5/10/20 = 1.0 ceiling. Recall@5: dense 0.9667, sparse 0.9906, hybrid **0.9953** (best). Per-category Recall@10 shows dense is specifically weak on `acronym` queries (0.9615 vs. 1.0 for sparse/hybrid) — the exact failure mode ADR-020 predicted for dense embeddings. Hybrid is now tied-best or outright best in every query category, real evidence RRF fusion is adding value rather than just latency. Sparse alone is worth noting too: ~30x lower latency than dense/hybrid (12ms vs. ~360-420ms avg) for nearly the same recall. Document-level relevance (not chunk-level) is still the main remaining gap — see the chunk-level-relevance TODO in `README.md`.

Documentation

- ADR-020 — Retrieval Evaluation First Development
- `docs/architecture/retrieval-benchmarking-strategy.md` — benchmark methodology, query categories, decision gate

---

# Milestone 2.8 — Context Platform

**Status:** 🟡 ~90% Complete

The Context Platform sits between Retrieval/Reranking and Generation. It enriches, deduplicates, compresses, guards, cites, and formats retrieved knowledge before it reaches an LLM. A key architectural realization this milestone: parent/child expansion was reclassified out of the Retrieval Platform and into the Context Platform, since ResearchMind's persisted chunk artifacts (not the vector index) are the source of truth for parent resolution.

Pipeline

```
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
Compression (Token Budget / Embedding)
        ↓
Guardrails
        ↓
Citation Building
        ↓
Prompt Formatting
        ↓
Prompt Context
```

## 2.8.1 Parent Expansion

**Status:** ✅ Complete — now genuinely end-to-end (producer + consumer)

Implemented

- `ChunkArtifactReader` — loads persisted `ChunkArtifact`s from storage so parent chunks can be resolved without S3 object listing
- `ParentExpansionService` — resolves `parent_chunk_id` from retrieved child chunks into full parent context
- Vector payload extended with `chunk_artifact_id`, `chunking_strategy`, `parent_chunk_id`
- **Producer (new):** until this session, nothing ever set `structure.parent_chunk_id`, so this service was live-wired but never actually triggered by real data. `HierarchicalChunkingProvider` (Milestone 2.3) now produces parent sections + child chunks, closing that gap — see Milestone 2.3's Providers section above

## 2.8.2 Adjacent Merge

**Status:** ✅ Complete

Implemented

- `AdjacentMergeService` — merges adjacent chunks (e.g. chunk 15/16/17) into a single richer context block, NotebookLM-style

## 2.8.3 Compression Platform

**Status:** ✅ Complete (V1-V4, per `context_platform_complexion_prd.md`)

Implemented

- Provider architecture (`context/compression/interfaces.py`, `models.py`, `enums.py`, `exceptions.py`, `service.py`, `registry.py`, `create.py`)
- ✅ Token Budget Provider — sorts by score, fits into token budget (V1)
- ✅ Embedding Compression Provider — drops redundant chunks by embedding similarity (V2)
- ✅ LangChain Provider — query-aware extraction via `ContextualCompressionRetriever` + `LLMChainExtractor` (V3, `langchain-classic` — these classes moved out of core `langchain` in the 1.x split). A `_StaticDocumentRetriever` adapts the already-retrieved chunk list into the retriever interface `ContextualCompressionRetriever` expects; chunks the LLM extracts nothing relevant from are dropped, and every field but `content` (citations, scores, parent links, risk metadata) survives via `chunk.model_copy()`. The LLM is DI'd via constructor, lazily defaulting to `ChatOpenAI(gpt-5-nano)` off `settings.openai_api_key`. `CompressionStatistics` gained `original_tokens`/`compressed_tokens`/`duration_ms`. `CompressionService.compress()` now catches `CompressionError` from any provider and falls back to the original, uncompressed chunks (an unregistered strategy still raises `ValueError`, unchanged) — compression can no longer break generation. **Now wired into `ContextBuilderService.build()`'s default pipeline**: `build()` takes an optional `query: str | None = None`, threaded into every `CompressionRequest` (embedding-redundancy, the new LangChain stage, token-budget). The LangChain stage itself only runs when both `settings.enable_langchain_compression` is `True` (currently defaults to `True`, but stays a flag rather than unconditional since it's an LLM call requiring an API key) and a `query` was passed; it runs between embedding-redundancy and token-budget, so query-aware extraction shrinks chunks before the final hard token cap. 12 unit tests (`FakeListChatModel`-faked, no network calls), plus a fallback test in `test_service.py` and an exception-hierarchy test
- ✅ LLM Compression Provider — per-chunk, query-aware relevant-summary compression via the Generation Platform (V4). `LLMCompressionProvider` calls `GenerationService.generate()` once per chunk (never a direct provider call), asking for a concise, query-relevant summary; unlike the LangChain provider, it never drops a chunk — every field but `content` survives via `chunk.model_copy()`, and a chunk falls back to its own original content (not the whole batch) if its summarization call fails, returns empty, or the chunk itself is blank. `LLMCompressionConfig` (`provider: GenerationProvider = GROQ`, `max_tokens: int = 300`, `temperature: float = 0`) controls the call. Its `GenerationService` dependency is lazily constructed on first use (mirrors `LangChainCompressionProvider`'s lazily-built LLM) rather than eagerly at `create_compression_service()` time — eager construction was tried first and surfaced a latent, pre-existing bug: `TokenCounter.__init__` (`generation/observability/token_counter.py`) unconditionally builds a `genai.Client()`, which raises without `GEMINI_API_KEY` configured; no code path had called `create_generation_service()` directly before, so this was previously dormant. Registered in `create_compression_service()` but **not** part of `ContextBuilderService.build()`'s default pipeline — the PRD scopes V4 to "provider implemented," not wired in by default, unlike V3. 13 new unit tests (mocked `GenerationService.generate()`, no network calls)

## 2.8.4 Context Guardrails

**Status:** ✅ V1 Complete

Implemented

- Provider architecture for retrieved-context guardrails
- `RuleBasedGuardrailProvider`
- Risk scoring
- Guardrail statistics

Future

- LlamaGuard
- NeMo Guardrails
- Lakera

## 2.8.5 Citation Platform

**Status:** ✅ Complete

Implemented

- Citation IDs
- Page numbers
- Headings / heading paths
- Chunk IDs

Future

- Inline citations
- Source highlighting
- Citation evaluation

## 2.8.6 Prompt Formatter

**Status:** ✅ Complete

Implemented — strategy-based prompt formatting, since different downstream consumers need different knowledge representations. Prompt formatting is a Context Platform concern and intentionally stays separate from Generation Platform prompt templates.

Providers

- `DEFAULT`
- `NOTEBOOKLM`
- `PERPLEXITY`
- `RESEARCH`
- `AGENT`

## Context Platform Status

✅ 100% complete (Phase 3.7, per `context_platform_complexion_prd.md`).

---

# Milestone 2.9 — Generation Platform

**Status:** ✅ Complete, per `generation_platform_complexion_prd.md` (see Milestone 2.9.11 below)

The Generation Platform owns all LLM interactions, consuming the Context Platform's `Prompt Context` output. Provider abstraction (all five providers), Structured Output Integration, a multi-stage Validation Platform integration (input/output/hallucination/runtime validators, a `ValidationRegistry`, weighted scoring, a `ValidationReport`, and five runtime contracts), a Validation Policy Layer, a regenerate-on-invalid-output loop, a Prompt Platform bridge, a Routing Platform (model/provider selection with fallback chains), a Runtime Caching Platform (L1/L2/L3 caching with policy resolution), a Streaming Platform (canonical event protocol + SSE/WebSocket transports, wired into a new `POST /api/v1/chat/stream` / `/api/v1/chat/ws`), Runtime Metrics Integration, and Artifact persistence are all implemented. Detail: `docs/architecture/structured-output-platform.md` (Structured Output/Validation), `docs/architecture/model-routing-platform.md` + ADR-026 (Routing), `docs/architecture/runtime-caching-platform.md` + ADR-027 (Caching), and `docs/architecture/streaming-platform.md` + ADR-028 (Streaming).

Pipeline

```
GenerationRequest (+ optional PromptService template rendering)
        ↓
GenerationService — resolves a provider explicitly, or via RoutingService from routing_strategy (falls back across the decision's fallback_models on failure)
        ↓
GenerationService — routes to generate_structured() when a schema/JSON/STRUCTURED response is requested
        ↓
Provider (Groq, OpenAI, Claude, Gemini, Ollama) — native structured decoding
        ↓
Parser Fallback (json.loads → StructuredOutputRepair) / Markdown-XML Parser Registry
        ↓
Validation (input + output + hallucination stages → ValidationReport, weighted overall_score)
        ↓
Regeneration (opt-in, corrective feedback) if parsing failed or the output stage is invalid
        ↓
GenerationResult (content, parsed_output, validation: ValidationReport, regeneration_attempts)
```

## 2.9.1 Provider Abstraction

**Status:** ✅ Complete

Implemented

- `GenerationProviderInterface`, `BaseGenerationProvider`, `GenerationRegistry`, composition root (`generation/create.py`)
- Five providers: Groq, OpenAI, Claude, Gemini, Ollama
- Per-provider `generate()`, `generate_structured()`, `stream()`
- Request-level retry with exponential backoff (`_execute_with_retry`)
- `ProviderCapabilities` flags (`structured_output`, `json_mode`, `tool_calling`, `streaming`, `reasoning`, `vision`, ...) and `supports_*` accessors — pre-date this milestone
- Per-model catalog with capabilities + cost (`catalog/models.py`)

## 2.9.2 Provider Structured Output Integration

**Status:** ✅ Complete

Implemented

- Native schema-constrained decoding for all five providers: OpenAI (`text.format` json_schema), Gemini (`response_json_schema` — not `response_schema`, which expects Gemini's restricted OpenAPI-subset type), Claude (`output_config.format`, the modern Structured Outputs API — supersedes the older tool-calling-only approach), Groq (`response_format.json_schema`), Ollama (schema-constrained `format`)
- Parser/repair fallback (`BaseGenerationProvider.parse_structured_output` — `json.loads` → `StructuredOutputRepair`) used consistently across all providers
- `GenerationRequest.output_model` — convenience field; auto-derives `output_schema` via `model_json_schema()`, and `GenerationService` validates `parsed_output` back into the Pydantic instance
- Markdown/XML response formats routed through the (pre-existing but previously disconnected) `StructuredOutputRegistry` (`MarkdownParser`/`XMLParser`) via `GenerationService._parse_via_registry`
- `ResponseFormat.XML` added — previously there was no way to request XML output at all

## 2.9.3 LangChain `with_structured_output()` Integration

**Status:** ✅ Complete (4 of 5 providers)

Implemented

- `generation/langchain/output_parsers.py` — standalone alternative to the native-SDK path, for callers who want LangChain's one-call provider-formatting + parsing + validation without the full platform's routing/observability
- Supported: OpenAI (`ChatOpenAI`), Claude (`ChatAnthropic`), Gemini (`ChatGoogleGenerativeAI`), Ollama (`ChatOllama`, added `langchain-ollama` dependency)
- Not supported: Groq — no released `langchain-groq` version (including pre-releases) is compatible with the pinned `groq>=1.5.0` SDK floor the native `GroqProvider` requires; adding it would force a downgrade risking the native integration

## 2.9.4 Validation Platform Integration

**Status:** ✅ Complete (Input/Output/Hallucination/Runtime stage validators, a `ValidationRegistry`, weighted scoring, a multi-stage `ValidationReport`, all five runtime contracts, and the Acceptance/Fail-Fast/Runtime Validation policy layer all done — see Milestone 2.9.11 below)

Implemented (`generation/validation/` — a narrow slice of `validation_platform_prd.md`'s full target design, still living inside the Generation Platform rather than as its own top-level platform; see that PRD's Implementation Status note and `docs/architecture/structured-output-platform.md` → "Validation Platform Integration" for full detail)

- `ValidationRegistry` — dynamic per-stage validator registration (input/output/hallucination)
- `ValidationService` — per-stage (`validate_input()`/`validate_output()`/`validate_hallucination()`) and full (`validate()`) flows; a crashing validator becomes a WARNING issue rather than failing the whole check
- `ValidationReport` — replaces the old single-stage `ValidationResult` on `GenerationResult.validation`: one `ValidationResult` per stage plus a renormalized `overall_score` (`validation/scoring.py`, weighted per the PRD's §15 formula)
- Input validators — `EmptyPromptValidator` (empty/whitespace prompts, unrendered `{placeholder}` template variables), `TokenBudgetValidator` (estimated tokens vs. context window — a cheap deterministic word-count estimate, not `TokenCounter`'s real provider API calls, to stay deterministic per the PRD's Principle 2), `ProviderLimitsValidator` (streaming/structured_output/json_mode/tool_calling requested vs. the resolved provider's capabilities), `ContextValidator` (empty/duplicate chunks, orphaned citation references)
- Output validators — `SchemaValidator` (`parsed_output` vs. `request.output_schema` via `jsonschema`, added `jsonschema` + `types-jsonschema` dependencies), `JsonValidator` (new — is `content` itself valid/repairable/unparseable JSON, independent of `SchemaValidator`'s shape check), `CitationValidator` (bracketed `[S1]`-style markers vs. `request.prompt_context.citations`/`chunks`, catching fabricated citations)
- Hallucination validator — `HallucinationValidator` (new — deterministic lexical-overlap groundedness score against retrieved context, no LLM judge, WARNING-only to keep the false-positive rate low)
- Regeneration only reacts to `output_validation.valid` — input-stage issues (token budget, missing capability) describe the request, not the response, so re-generating with the same request wouldn't fix them; hallucination issues are WARNING-only and never gate it either
- Runtime Validators + Contracts layer (`generation/validation/runtime/`, per `runtime_validation_prd.md`) — a fourth `ValidationStage.RUNTIME` stage, resolved from a new `GenerationRequest.runtime: RuntimeType | None` field: `RuntimeRegistry` (per-`RuntimeType` contract/validator lookup) and `RuntimeValidationService` (crash-safe execution + aggregation, composed into `ValidationRegistry`/`ValidationService`), six generic reusable validators (`CompletenessValidator`, `ConsistencyValidator`, `ConfidenceValidator`, `EvidenceValidator`, `RuntimeCitationValidator`, and — new, per `generation_platform_complexion_prd.md` — `DependencyValidator`), and — per that same PRD — all five concrete contracts: `ResearchRuntimeContract` (summary/≥2 sections/≥1 citation/≥1 evidence/confidence in `[0,1]`), `PlannerRuntimeContract` (plan/≥1 steps/acyclic step dependencies), `ReviewerRuntimeContract` (critique/confidence/≥1 recommendations), `AgentRuntimeContract` (reasoning/completion_state/≥1 tool_trace entries), `MCPRuntimeContract` (≥1 tool_outputs/execution_metadata/tool_references referential integrity) — each merged into one `ValidatorOutcome` tagged with its own contract name. `compute_overall_score()` already had a `runtime_score` weight (0.20) reserved for this. Nothing in the request path sets `GenerationRequest.runtime` yet, so the stage stays a no-op (`None`/trivially valid) until a caller (e.g. a future `/research` API) does — all five contracts are registered and ready for that day. See Milestone 2.9.11 below for full detail on this session's additions

## 2.9.5 Regeneration Strategy

**Status:** ✅ Complete

Implemented

- `GenerationRequest.max_regeneration_attempts` — opt-in, default preserves prior behavior
- `GenerationService` regenerates (up to the budget) when the latest attempt's `parsed_output` is `None` for a structured request, or `ValidationReport.output_validation.valid` is `False` (input-stage and hallucination-stage issues do not trigger regeneration — see Milestone 2.9.4)
- Each retry appends corrective feedback to `system_prompt`, built fresh from the latest failure only (not accumulated) — combines JSON-formatting guidance and specific validation-issue messages when both apply, rather than picking one
- `GenerationResult.regeneration_attempts` records how many extra calls were made; exhausting the budget is not an error — the last attempt is returned as-is

## 2.9.6 Provider Capability Flags

**Status:** ✅ Complete

- `ProviderCapabilities` and `supports_*` accessors pre-date this milestone
- `GenerationService._check_capability_support()` — a best-effort guard that logs `generation.capability_mismatch` when the caller's explicitly-chosen provider doesn't declare support for what the request needs; never blocks the call
- Capability-based provider *selection* (as opposed to this after-the-fact guard) is now implemented — see Milestone 2.9.8 below

## 2.9.7 Routing Platform

**Status:** ✅ Complete (per `routing_platform_prd.md`, ADR-026)

The Routing Platform is the decision layer between callers (agents, planners, runtime services) and the Generation Platform's providers: it decides which model and provider to use, why, and what the fallback chain is. It does not execute prompts or perform generation itself — see `docs/architecture/model-routing-platform.md`.

Implemented (`generation/catalog/` + `generation/routing/`)

- **Model Catalog** — `ModelMetadata` extended with per-task 0-1 scores (planning, reasoning, coding, review, summarization, classification, extraction, speed, reliability, quality), `average_latency_ms`, and policy flags (`priority`, `enabled`, `experimental`, `local`) for all 12 known models; `ModelCatalogRegistry` (`all()`/`enabled()`/`by_provider()`/`get()`/`local_models()`) with a cached factory
- **Routing Strategies** — a 15-value task-based `RoutingStrategy` enum (`AUTO`, `FAST`, `CHEAP`, `QUALITY`, `REASONING`, `CODING`, `LONG_CONTEXT`, `STRUCTURED_OUTPUT`, `SUMMARIZATION`, `CLASSIFICATION`, `EXTRACTION`, `VALIDATION`, `PLANNING`, `REVIEW`, `LOCAL`); six of these (planning, summarization, review, validation, coding, research/reasoning) carry dedicated weight profiles plus their own capability/context requirements in `routing/strategies/`, the rest use generic weight profiles
- **Scoring Engine** — `ScoringService` blends weighted per-task scores into a single ranking; cost and context-window are normalized relative to the candidate set (cheapest/largest scores 1.0), boolean capabilities score 0/1; produces a 0-10 score plus explainable `reasons` (top contributing dimensions, e.g. "highest planning score", "supports long context")
- **Routing Service** — capability filter → policy filter (disabled models always excluded; experimental/local models excluded unless requested or the `LOCAL` strategy explicitly opts in) → strategy resolution → scoring → primary selection → fallback chain (prefers a distinct provider per fallback slot before repeating one, so a single provider outage can't take out the whole chain); every decision is logged via structlog (`routing.decision` — strategy, selected model, fallbacks, score, reasons, latency)
- **Generation Integration** — `GenerationRequest` gained `routing_strategy`/`required_capabilities`; `GenerationService.generate()`'s `provider` argument is now optional — when omitted, it routes via the strategy (defaulting to `AUTO`), tries the selected model, and automatically retries through the decision's fallback chain on execution failure, stamping a compact routing summary (`strategy`, `selected_provider`/`model`, `score`, `reasons`, `used_fallback`) onto `GenerationResult.metadata["routing"]`
- 44 new unit tests (catalog registry, scoring engine, routing service filtering/fallback, generation-service routing integration); full repo suite (746 tests), `ruff format --check`, `ruff check`, and `mypy` all pass clean

Not built (explicitly out of scope per the PRD's Non-Goals — routing only decides, it doesn't execute)

- ❌ Adaptive/evaluation-driven routing, A/B experimentation, budget-aware routing, multi-model ensembles (PRD Phases 2-5, future work)
- ❌ Per-request model switching *within* a single provider — a provider instance is still configured with one model at composition time (`create.py`); routing selects the provider, not a specific model override mid-request

## 2.9.8 Prompt Platform Integration

**Status:** ✅ Complete

- `generation/prompts/` (template loading from disk, `ChatPromptTemplate` rendering, few-shot examples, versioning) pre-dates this milestone and was previously fully disconnected from Generation
- `GenerationService.generate_from_template()` — renders a named template via `PromptService`, flattens the resulting messages into `GenerationRequest.system_prompt`/`user_prompt`, and — when `output_model` is set — appends schema-aware format instructions (`PydanticOutputParser(pydantic_object=output_model).get_format_instructions()`) that reinforce (not replace) native provider structured output
- Composition root (`generation/create.py`) now wires `structured_output_registry`, `validation_service`, and `prompt_service` together into `GenerationService`

## 2.9.9 Runtime Caching Platform

**Status:** ✅ Complete (per `runtime_caching_platform_prd.md`, ADR-027)

The Runtime Caching Platform reduces provider costs, latency, and duplicate execution by caching `GenerationResult`s. It is a standalone platform (`generation/caching/`) wired directly into `GenerationService._generate_with_provider`: a cache lookup runs right after a candidate model is resolved (before the provider call), and a store runs after generation — including any regeneration attempts — completes.

Implemented (`generation/caching/`)

- **L1 Exact Cache** — Valkey-backed, keyed on `provider`/`model`/`routing_strategy`/`prompt_hash`/`context_hash`/`schema_hash`/`temperature`/`top_p` (`exact/key_builder.py`); `ValkeyExactCacheProvider` stores/retrieves full `GenerationResult` JSON, fails open on backend errors
- **L2 Semantic Cache** — wraps LangChain's `langchain_redis.RedisSemanticCache` (per the ADR's "leverage LangChain" directive) against a **dedicated** `redis-stack-server` instance (see Infra below), embedding prompts via a thin `Embeddings` adapter over OpenAI; `context_hash` plus every other non-prompt `CacheKey` field is folded into the library's `llm_string` post-retrieval filter so a hit can never cross a provider/model/schema/document boundary (ADR-027's isolation constraint)
- **L3 Session Cache** — Valkey-backed, general-purpose session-scoped store (`get_session`/`set_session`/`invalidate_session`/`clear_session`); implemented and exposed on `CachingService` but not yet called from anywhere — no conversation/research-session runtime exists yet to call it (PRD Phase 3 territory)
- **Policy Resolution (FR-4)** — `CachePolicy` (`AUTO`/`NEVER`/`EXACT_ONLY`/`SEMANTIC`/`SESSION`) resolved per `CacheRuntime` (Chat/Research/Benchmark/Planner/Tool Agent/Summarizer/Reviewer/Critic) via `CachePolicyResolver`, with an explicit `GenerationRequest.cache_policy` override always winning; `GenerationRequest` gained `cache_runtime`/`cache_policy` fields, mirroring how `routing_strategy` already lives directly on the request
- **Statistics (FR-5)** — in-memory `CacheStatistics` (exact/semantic/session hits, misses, hit ratio, tokens saved, cost saved) plus a structured `caching.lookup` log line per call (`cache_hit`, `cache_level`, `cache_latency_ms`, `tokens_saved`, `cost_saved`)
- **Streaming integration** — originally `request.stream` skipped lookup/store entirely per the PRD; corrected in Milestone 2.9.10 so streaming requests participate in caching identically to non-streaming ones, with `StreamingService` (not `CachingService`) deciding to replay a hit as a synthetic token stream
- **Artifact shape** — `GenerationResult.metadata["cache"]` populated with `{hit, level, tokens_saved, cost_saved}` on every call (hit or miss), mirroring the existing `metadata["routing"]` pattern; at the time this milestone shipped, the Artifacts platform itself (`generation/artifacts/`) was still an empty scaffold with no persistence layer to consume this — since corrected by Milestone 3.10 (Artifact Platform, below), whose `GenerationArtifact.cache` field now persists exactly this shape
- Null-object providers (`exact/null.py`, `semantic/null.py`, `session/null.py`) back each layer's `settings.*_cache_enabled` flag, so a disabled layer no-ops instead of every call site needing an `is not None` check
- 22 new unit tests (`tests/unit/ai/runtime/generation/caching/`) — key builder determinism/sensitivity, policy resolution precedence, `CachingService` policy branching (AUTO/EXACT_ONLY/SEMANTIC/NEVER/streaming), statistics, session cache independence

Infra decisions (flagged during implementation, not silent)

- ADR-027 mandates LangChain's `RedisSemanticCache`, but the existing `valkey:8-alpine` docker-compose service has no RediSearch/vector-index module. Added a **second**, dedicated `redis/redis-stack-server:7.4.0-v6` service (`semantic-cache`, port 6380) rather than modifying the app's main `valkey` service, so L1/L3 traffic and data are unaffected
- `langchain-redis`'s dependency (`redisvl`) caps `redis<8.0`, conflicting with the previously-pinned `redis>=8.0.1`. Downgraded to `redis>=5.0.1,<8.0` — verified safe, every existing redis call in the codebase (`get`/`set`/`mget`/`pipeline`/`lpush`/`rpop`/`ping`) is basic and has no 8.x-specific dependency. This did surface redis-py 7.x stub regressions in the pre-existing `ValkeyQueue` (`infrastructure/queue/providers/valkey.py`) — fixed with scoped `# type: ignore[misc]` comments (a stub-quality issue, not a runtime bug)
- `CacheKey` uses the PRD/architecture-doc's 8-field key rather than ADR-027's slightly larger one (which adds `prompt_version`/`validation_version`/`guardrail_version` — concepts that don't exist anywhere else in the codebase yet)

Documentation

- ADR-027 — Runtime Caching Platform
- `docs/architecture/runtime-caching-platform.md`

## 2.9.10 Streaming Platform

**Status:** ✅ Complete (per `streaming_platform_prd.md`, ADR-028)

The Streaming Platform is the canonical event infrastructure for real-time execution, built as two independent layers per the ADR: a Runtime Event Platform (`runtime/events/`) providing a provider-independent `StreamEvent` protocol reusable by any future runtime, and a Generation Streaming Platform (`generation/streaming/`) providing SSE/WebSocket transport, cache-aware orchestration, and lifecycle management on top of it. This is also the milestone that first put a live HTTP surface in front of `GenerationService` — `chat.py` was a 0-byte, unregistered file before this work.

Implemented (`runtime/events/` + `generation/streaming/`)

- **Runtime Event Platform** — `StreamEvent` (`event_id`, `session_id`, `request_id`, `parent_event_id`, `category: EventCategory`, `type: str`, `timestamp`, `content`, `metadata`); `type` is a plain string rather than one shared enum, so each future runtime (Research/Agent/Tool — reserved under `runtime/events/{research,agent,tool}/models.py`) owns its own event vocabulary without ever touching this shared model. One `GenericStreamChunkAdapter` (not five duplicated per-provider adapters) converts every provider's already-normalized `StreamChunk` into a `StreamEvent`, since Layer-1 SDK-specific normalization already happens inside each provider's `stream()`
- **`GenerationService.stream_generate()`** (R2) — streaming counterpart to `generate()`; resolves a provider explicitly or via the Routing Platform's top candidate (no mid-stream fallback, unlike `generate()`'s retry loop), then yields directly from `generation_provider.stream()`. `GenerationService.registry`/`resolve_streaming_provider()` are now public so `StreamingService` can reuse the same registered provider instances
- **`StreamingService`** (`generation/streaming/service.py`) — orchestrates cache lookup, live streaming, and cache store. On a cache hit, replays the cached content as synthetic `TOKEN` events (character-chunked) rather than skipping streaming's contract entirely; on a miss, streams live and stores the assembled full result once the stream reaches `COMPLETE` (best-effort token statistics via `count_tokens()`, since today's provider `stream()` implementations don't surface real usage mid-stream)
- **Transports** — `transports/sse.py` (`StreamingResponse`, heartbeat comment lines on an idle interval to survive load-balancer/proxy timeouts, a hard max-duration ceiling, `X-Accel-Buffering: no`); `transports/websocket.py` (JSON frames over an accepted `WebSocket`, disconnect cancels the underlying generation)
- **API wiring** — `POST /api/v1/chat/stream` (SSE, `Authorization` header via `get_current_user` — deliberately a `POST` consumed via `fetch`/`ReadableStream`, not a bare `EventSource`, since browsers can't attach custom headers to an `EventSource`/WebSocket handshake) and `/api/v1/chat/ws` (WebSocket, `?token=` query-param auth through a new shared `authenticate_token()` helper in `auth/dependencies.py`)
- **New Conversation persistence** (not part of the original PRD's scope, added because chat needed history) — `Conversation`/`Message` SQLAlchemy models, `ConversationRepository`, `ConversationService` (multi-turn history folded into `user_prompt` as a text transcript, since `BaseGenerationProvider.build_messages` only builds a single system+user pair today, not a message array), and a new Alembic migration

Runtime Caching Platform correction made as part of this work: `CachingService.lookup()`/`store()` previously bypassed caching entirely whenever `request.stream` was set (see Milestone 2.9.9). That blanket bypass has been removed — streaming requests are looked up/stored identically to non-streaming ones; only `StreamingService`, not `CachingService`, decides to replay a hit as a synthetic stream. `docs/adrs/ADR-027-runtime-caching-platform.md` and its architecture doc were updated to match.

Also corrected: the PRD/ADR-028/architecture docs contained a self-contradiction (a flat `StreamEventType` enum mixing generation/research/agent/validation values, despite the platform's own Non-Goals excluding agents/research) and two inconsistent `StreamEvent` shapes (5 vs. 8 fields) across the three documents. All three were reconciled in place before implementation.

Testing: unit tests for `runtime/events/adapters`, `StreamingService` (cache-hit replay, live-stream store-on-complete, error path), `GenerationService.stream_generate()` (provider resolution, capability check), plus an integration test exercising `POST /api/v1/chat/stream` end-to-end (SSE frame order, persisted turn). Full repo suite (828 tests), ruff, and mypy all pass clean.

Known gaps (deliberate, documented)

- Cache-hit replay chunks by fixed character count, not real token boundaries — a documented approximation, not a faithful stream replay
- No rate limiting / per-user concurrent-stream cap yet, despite being called out in the docs' "Production Considerations"
- Multi-turn history is a text transcript prefix, not a real langchain message array — blocked on providers gaining a multi-message API

Documentation

- ADR-028 — Streaming Platform Architecture
- `docs/architecture/streaming-platform.md`
- `streaming_platform_prd.md`

## 2.9.11 Generation Platform Completion

**Status:** ✅ Complete (per `generation_platform_complexion_prd.md`) — closes out the Generation Platform at 100%

This milestone closes out every remaining gap Milestone 2.9's earlier sub-milestones had flagged: Planner/Reviewer/Agent/MCP runtime contracts, the Acceptance/Fail-Fast policy layer, the remaining PRD output validators, and metrics/observability integration. Six deliverables:

1. **Runtime Contract Expansion** — four new contracts alongside the pre-existing `ResearchRuntimeContract` (Milestone 2.9.4): `PlannerRuntimeContract`, `ReviewerRuntimeContract`, `AgentRuntimeContract`, `MCPRuntimeContract` (`generation/validation/runtime/contracts/`), all registered in `validation/create.py`. A new generic validator, `DependencyValidator` (`runtime/validators/dependency.py`), backs Planner's dependency-graph check — DFS cycle detection (white/gray/black coloring) plus unknown-dependency detection, configurable `list_field`/`id_keys`/`dependency_key`. `ConsistencyValidator` (`runtime/validators/consistency.py`) was generalized to take configurable `list_field`/`id_keys`/`ref_list_field`/`ref_key` (defaults preserve Research's original `sections`/`evidence`/`section_id` behavior unchanged) so MCP's contract could reuse it for `tool_outputs`/`tool_references` instead of a bespoke check. All five contracts remain registered-but-dormant in production — nothing sets `GenerationRequest.runtime` yet, same accepted gap as before — but are fully built and tested for the day a `/research` API (or Planner/Reviewer/Agent/MCP runtime) starts issuing requests with `runtime` set.
2. **Validation Policy Layer** — new `generation/policies/{acceptance,fail_fast,runtime}.py`: `AcceptancePolicy` (Accept/Reject/Regenerate, decided from a `ValidationReport` + parse-failure flag — default behavior unchanged from the pre-existing hard-coded logic), `FailFastPolicy` (should an input-stage failure stop generation before the provider call — default `stop_on_error=True`), `RuntimeValidationPolicy` (should a failed runtime contract also gate regeneration — default `block_on_error=False`, since nothing sets `request.runtime` in production yet). Wired into `GenerationService` as optional constructor params defaulting to permissive instances; `_needs_regeneration` (now an instance method, was a classmethod) delegates to these instead of inlined booleans. `GenerationService._enforce_fail_fast_input_validation()` runs `ValidationService.validate_input()` pre-flight — before guardrails, routing, and any provider call — gated by `FailFastPolicy`, so a request already known to be invalid never pays for that work. In practice this is a safety net today, not a behavior change: every input validator's ERROR-severity paths need either `context_window` (unavailable before a provider is resolved) or an empty `user_prompt` (already hard-rejected earlier by the pre-existing `_validate()` check) — but the ordering hook now exists for when that changes.
3. **Remaining Output Validators** — `generation/validation/output/{formatting_validator,response_size_validator,completeness_validator,consistency_validator}.py`. `FormattingValidator` checks balanced Markdown code fences and parseable XML (with a wrap-in-`<root>` fallback for multi-root content); JSON/STRUCTURED is left to the pre-existing `JsonValidator`. `ResponseSizeValidator` checks configurable min/max character bounds and flags a likely-truncated response via `finish_reason` in `{"length", "max_tokens"}` (OpenAI/Groq/Claude's markers — Gemini/Ollama don't populate `finish_reason` yet). The top-level `CompletenessValidator`/`ConsistencyValidator` are thin delegating wrappers around the existing generic `runtime/validators/{completeness,consistency}.py` classes (re-tagging `issue.validator` to their own name) rather than duplicated logic — `CompletenessValidator` self-configures from `request.output_schema`'s own `required`/`properties` (array-typed required fields become `list_minimums`) instead of needing per-caller setup. All seven output validators now run in the PRD's specified pipeline order: JSON → Schema → Formatting → Completeness → Consistency → Response Size → Citation.
4. **Runtime Metrics Integration** — populated the previously-empty `generation/observability/{models,service}.py`: `GenerationMetricsSnapshot` (request/execution/token/cost/validation/guardrail fields) + a pure `build_generation_metrics_snapshot(result)` function, and `GenerationMetricsService` (mirrors the Guardrails Platform's `MetricsRecorder`/`NoOpMetricsRecorder` pattern — new counters in `infrastructure/metrics/generation.py`: `generation_requests_total`, `generation_failures_total`, `generation_retries_total`, `generation_regenerations_total`, `generation_cache_hits_total`, `generation_validation_failures_total`, `generation_hallucination_flags_total`, `generation_runtime_validation_failures_total`). Unlike every other optional `GenerationService` collaborator (`artifact_writer`/`caching_service`/`guardrail_service` — `None` skips them entirely), `metrics_service` always defaults to a real `GenerationMetricsService` instance, so every `generate()` call gets metrics captured (as a structured log event, zero-cost) whether or not a real recorder is wired in. `cost_tracker.py`/`latency_tracker.py`/`metrics_collector.py`/`token_tracker.py` remain deliberately empty scaffolds — token/cost accounting already lives on `GenerationResult.statistics`, nothing left to independently track. New structlog events round out the pipeline: `generation.started`/`generation.failed` (wraps the provider-dispatch path in `generate()`), `provider.started`/`provider.completed` (around the actual provider call in `_execute_once`), `validation.started`/`validation.completed` (bracketing `ValidationService.validate()`).
5. **Artifact Completion** — `GenerationArtifact` gained a required `metrics: GenerationMetricsSnapshot` field, always persisted as `metrics.json` alongside the existing request/response/metadata/validation/guardrails/routing/cache files (builder/writer/reader all updated).
6. **Full Generation Flow Activation** — the target execution flow (Input Validation → Input Guardrails → Routing → Cache → Provider → Structured Parsing → Output/Hallucination/Runtime Validation → Metrics → Artifacts) is now fully realized: metrics recording runs before artifact persistence in `generate()`, and input validation runs before guardrails/routing/provider per deliverable 2 above.

A real bug was caught and fixed along the way: `artifacts/writers/base.py::write_json_artifact` serializes with `exclude_none=True`, so a Pydantic field typed `X | None` **without an explicit `= None` default** is still required on read-back (Pydantic v2 treats a bare `Optional[X]` as nullable-but-required) — a `None` value gets stripped on write and then fails `model_validate_json` on read. Hit this with the first draft of `GenerationMetricsSnapshot` (5 fields); fixed by adding explicit `= None` defaults. Any future artifact-persisted Pydantic model needs the same check.

~40 new test files/cases across `policies/`, `observability/`, the new contracts, the new output validators, and `GenerationService` integration; full repo suite (1034 tests), `ruff format --check`, `ruff check`, and `mypy` all pass clean.

## 2.9.12 Generation Runtime Platform

**Status:** ✅ Complete (per `generation_runtime_platform_prd.md`) — thin orchestration layer, no new generation behavior

This milestone does not re-implement anything: `GenerationService.generate()` already runs the full frozen ordering (input validation → input guardrails → routing → cache → provider → structured outputs → generation guardrails → output/hallucination validation → runtime validation → metrics → artifacts) from every prior Generation Platform milestone. What was missing was a single canonical entrypoint that future runtimes call instead of reaching into `GenerationService` directly. New `apps/api/app/ai/runtime/generation/orchestration/`:

- `context.py` — `GenerationExecutionContext` (trace id minted fresh per call, request/session/runtime ids, provider/routing/cache/validation/guardrail summaries, reserved `langsmith_trace_id`/`langgraph_run_id` fields for future integrations), built via `for_request()` and mutated in place by `finalize()` once `GenerationService.generate()` returns
- `state.py` — `GenerationExecutionState` (context + request + result/failed/exception), a single object a future LangGraph node can hold and inspect across the call
- `interfaces.py` — `GenerationRuntimeInterface` ABC (`execute()`), the contract Research/Planner/Reviewer/Agent/MCP runtimes depend on instead of `GenerationService` directly
- `orchestrator.py` — `GenerationRuntime`, deliberately thin: mints a context, delegates to `GenerationService.generate()`, folds the result (or exception) back into the state, logs `generation_runtime.started/completed/failed`. Owns only what the PRD assigns to the runtime layer (tracing/timing) and explicitly not provider execution, planning, workflows, agent state, retrieval, reasoning loops, or checkpoints
- `create.py` — composition root: `create_generation_runtime()` (wraps `create_generation_service()`), `@lru_cache`'d `get_generation_runtime()`, and the module-level `execute_generation(request, *, provider=None) -> GenerationResult` — the canonical entrypoint the PRD names in §11

New `get_generation_runtime()` FastAPI dependency added to `dependencies/generation.py`. 11 new unit tests under `tests/unit/ai/runtime/generation/orchestration/` (`factories.py`, `test_context.py`, `test_state.py`, `test_orchestrator.py`, `test_create.py`). This platform had no real caller until the Research API Platform below — see Phase 4.

## Not Yet Built

- ❌ Adaptive/evaluation-driven routing, budget-aware routing, A/B experimentation (Routing Platform Phase 2+ — see Milestone 2.9.7)
- ❌ Session Cache wiring — implemented and available (Milestone 2.9.9) but nothing calls it yet
- ❌ Streaming rate limiting / per-user concurrent-stream cap, real multi-message chat history (Milestone 2.9.10)
- 🟡 Test suite — `validation/`, `policies/`, `observability/`, `providers/`, `prompts/`, `routing/`, `catalog/`, `caching/`, `streaming/`, `runtime/events/`, `orchestration/`, and core `service.py` all have unit test coverage now; `artifacts/` (the old empty in-package scaffold) is gone — see Milestone 3.10 below

Generation-level guardrails, previously listed here as a gap, are now implemented and wired into `GenerationService` — see Milestone 11.16 below. Artifact persistence, also previously listed here as a gap, is now implemented — see Milestone 3.10 below. The `POST /research` API, previously listed here as the only remaining Generation Platform gap, is now closed — see Phase 4 — Research API Platform below.

---

# Milestone 3.10 — Artifact Platform

**Status:** ✅ Complete (Generation/Streaming/Conversation/Research live and wired, per `artifacts_platform_prd.md`) — 🟡 Session/Agent/Evaluation built but scaffold-only (no runtime exists yet to call them)

The Artifact Platform provides canonical, immutable, versioned, policy-gated persistence for AI Runtime executions — the same "artifacts are the source of truth" principle the ingestion side (`chunking/`, `embeddings/`, `indexing/`, `processing/`) has always followed, now extended to the runtime side (generation calls, streams, conversations). It is a new, centralized, cross-cutting package (`apps/api/app/ai/artifacts/`, sibling to `knowledge/`, `runtime/`, `guardrails/`, `quality/`) — deliberately *not* nested inside `runtime/generation/`, since it spans multiple runtimes (generation, streaming, conversation, and eventually research/agent) rather than being owned by a single one. Supersedes and deletes the old empty 4-file scaffold that previously sat at `runtime/generation/artifacts/`.

Pipeline (PRD §10)

```
Runtime
      ↓
Artifact Builder
      ↓
Artifact Policy
      ↓
Artifact Writer
      ↓
Storage
      ↓
Artifact Reader
      ↓
Replay / Evaluation / Observability
```

## Foundation

Implemented

- `models.py` — `ArtifactMetadata` (`artifact_id`/`version`/`created_at`/`owner_id`/`session_id`), `JsonDictFile` (generic single-object wrapper so the scaffold-only domains' loosely-typed `dict[str, Any]` fields can still go through the shared JSON writer)
- `enums.py` — `ArtifactPolicy` (`never`/`session`/`short_term`/`long_term`/`permanent`, PRD §8 verbatim), `ArtifactCategory` (mirrors the PRD §12 S3 prefixes), `ArtifactRuntime` (`internal_helper`/`chat`/`research`/`agent`/`benchmark`/`evaluation`) — a new, dedicated runtime enum rather than reusing `caching.enums.CacheRuntime` or `validation.runtime.enums.RuntimeType`, matching this codebase's established convention that each platform owns its own runtime concept (confirmed twice already by those two prior platforms)
- `policies/` — `ArtifactPolicyService.should_persist(runtime, category)` / `resolve_policy()`, `DEFAULT_ARTIFACT_POLICY_RULES` encoding PRD §8's example table; unmapped combinations fail safe to `NEVER`
- `writers/base.py` / `readers/base.py` — `write_json_artifact()`/`BaseArtifactWriter` and `BaseArtifactReader._read_json()`/`_read_json_optional()`, extracted from `guardrails/artifacts/writers.py`'s pattern so the upload/parse boilerplate isn't re-declared per runtime
- `create.py` — composition root: `create_artifact_storage()`, `get_artifact_policy_service()`, and per-category writer factories, imported into each live platform's own `create.py`
- Infra: `DocumentStorage.list_keys(*, prefix) -> list[str]` added to `infrastructure/storage/` (S3 `list_objects_v2` paginator) — a hard dependency for `ConversationArtifactReader`, which has no mutable index file to consult

## Generation Artifacts (PRD §13) — Live

- `GenerationArtifact` — `request.json`/`response.json`/`metadata.json` always written; `validation.json`/`guardrails.json`/`routing.json`/`cache.json` written only when the corresponding `GenerationResult` field is set
- `GenerationArtifactBuilder`/`GenerationArtifactWriter`/`GenerationArtifactReader` under `artifacts/generation/`
- Wired into `GenerationService.generate()` (new optional `artifact_writer`/`artifact_policy_service` constructor params) — persists after every successful call, gated by policy, best-effort (a storage failure is caught/logged as `artifacts.generation.failed`, never fails the generation that already succeeded, mirroring `GuardrailService._persist_artifact`)
- New `GenerationRequest.artifact_runtime: ArtifactRuntime | None` field — defaults to `ArtifactRuntime.CHAT` at the policy-lookup call site when unset, since 100% of live `generate()` traffic today is chat traffic; `chat.py` sets it explicitly

## Streaming Artifacts (PRD §14) — Live

- `StreamArtifact` — `events.json` (every emitted `StreamEvent`), `timeline.json` (`generation_started`/`first_token`/`completion` entries derived from the event list), `stream.json` (= metadata), `metrics.json` (`first_token_latency_ms`, `stream_duration_ms`, `tokens_per_second` — a documented character-count approximation, same shape of gap as the Streaming Platform's own cache-hit-replay/statistics approximations, since provider `stream()` implementations don't surface real token counts)
- Wired into `StreamingService._stream_live()` — now accumulates `emitted_events`/`started_at` alongside the pre-existing `content_parts`; the old `if self._caching_service is None: return` early-exit was restructured so artifact persistence runs independently of whether caching is wired

## Conversation Artifacts (PRD §15, adapted) — Live

- Diverges from the PRD's literal fixed `messages.json`: overwriting one file on every turn would violate the platform's own immutability principle (PRD §5), so each completed turn instead writes a fresh, never-overwritten `artifacts/conversations/{conversation_id}/turns/{turn_id}/turn.json` (`turn_id` a new UUID every call) — satisfies both "immutable" and "append-only" literally. `conversation.json` (`ConversationIdentity`) is written once, guarded by an `exists()` check
- `summary.json` from the PRD is intentionally not built — no summarization component exists anywhere in this codebase to produce one
- Wired into `chat.py` (`_persist_on_complete()`), covering both `/chat/stream` (SSE) and `/chat/ws` (WebSocket) through the one shared hook; new `get_conversation_artifact_writer()`/`get_artifact_policy_service_dependency()` singletons in `dependencies/generation.py`

## Research Artifacts (PRD §17) — Live (as of Phase 4 — Research API Platform)

`ResearchArtifact` (`plan`/`queries`/`retrievals`/`citations`/`report`/`evaluation`, loosely-typed `dict[str, Any]` via `JsonDictFile` since no `ResearchPlan`-shaped type exists yet) is no longer scaffold-only. `ResearchService._persist_artifact()` calls the pre-existing `ResearchArtifactBuilder`/`ResearchArtifactWriter` after every completed `/research`(`/stream`) call, best-effort and policy-gated exactly like `GenerationService`/`StreamingService`/`chat.py` already do. `plan`/`queries` are written empty (this milestone is deliberately linear — no planning/decomposition, per `research_api_prd.md`'s Non-Goals) and the answer is folded into `report` rather than a separate file. `runtime/research/{decomposition,planner,workflows}/` remain empty directories. See Phase 4 below for the full Research API Platform writeup.

## Session / Agent / Evaluation Artifacts (PRD §16, §18-19) — Scaffold-only, unwired

Built (models/builders/writers/readers, unit-tested with a fake `DocumentStorage`) but deliberately not wired to any live caller, matching this codebase's repeated, established pattern of building the platform layer ahead of the API surface (see the Streaming Platform's reserved `AgentEventType`):

- `session/` — `SessionArtifact` (`session.json`/`timeline.json`/`statistics.json`); no session concept distinct from `Conversation` exists today (`GenerationRequest.session_id`/`StreamEvent.session_id` are real fields but nothing populates them)
- `agent/` — `AgentArtifact` (`state`/`tools`/`execution_graph`/`events`/`memory`); `ai/agents/*` are still empty directories
- `evaluation/` — `EvaluationArtifact` (`dataset`/`results`/`metrics`/`comparison`); still unwired, and deliberately staying that way — `benchmarks/` (see the Engineering Benchmark Platform section below) now has a real Generation + Regression evaluation harness, but its own README explicitly forbids depending on S3/production infrastructure, so it writes local `report.json`/`report.md` only. This artifact layer remains reserved for a future online/API-triggered evaluation surface (`api/v1/evaluation.py` is still an empty file); `quality/{evaluation,regression}/` are still empty `__init__.py`s, present since the very first commit and never filled in

## Replay Platform (PRD §21)

- `GenerationReplayService` / `StreamReplayService` / `ResearchReplayService` (`artifacts/replay/`) — all real and unit-tested, reconstruct a `GenerationResult`, re-emit a stored `StreamEvent` sequence in order, or reconstruct a `ResearchArtifact`, all from persisted artifacts; no API route added for any of the three, just the services. (`ResearchReplayService` was a `NotImplementedError` stub with a stale justifying docstring until 2026-08-12 — fixed to read through `ResearchArtifactReader` like its two siblings, since both the Research API Platform and Deep Research Runtime now persist real `ResearchArtifact` records; see `docs/IMPLEMENTATION_GAP_CROSSCHECK_2026-08-12.md` Table C.)

## Testing

39 unit tests under `tests/unit/ai/artifacts/`, following the `_FakeDocumentStorage`/fixture pattern already established by `tests/unit/ai/guardrails/artifacts/`. Full repo suite (931 tests), ruff, and composition-root smoke construction (`create_generation_service()`, `create_streaming_service()`) all pass clean.

## Not Yet Built (by design)

- ❌ Wiring for Session/Agent/Evaluation artifacts — needs a real session concept, an Agent Runtime, and an evaluation harness respectively, none of which exist yet (Research artifacts are now wired — see Phase 4 — Research API Platform)
- ❌ Automated retention/expiry enforcement for the PRD §23 retention table — informational only in this pass, no deletion job
- ❌ A local S3/MinIO dev stack — `docker-compose.yml` has no S3-compatible service, so a true storage round-trip smoke test needs real AWS credentials; unit tests use a fake `DocumentStorage` instead

---

# Phase 4 — Research API Platform

**Status:** ✅ Complete (per `research_api_prd.md`) — **ResearchMind's first live, end-to-end product surface**: a user can upload documents, ask a question, and get a grounded, cited, streamable answer back

Everything before this milestone was platform-layer work — Retrieval, Context, Generation, Guardrails, Validation, Caching, Streaming, Artifacts — with no single API tying them together into a product experience. This milestone adds exactly one thing on top: an orchestration layer that composes those already-complete platforms in the PRD's specified linear order (retrieve → build context → generate through the Generation Runtime → persist), and adds no new retrieval/context/generation logic of its own (PRD §4 Non-Goals — no query decomposition, no research planning or multi-step loops, no agents, no LangGraph; those are explicitly named as future milestones — a Research Runtime, a Deep Research Runtime, and an Agent Platform).

New files

- `apps/api/app/api/v1/research.py` — `POST /research`, `POST /research/stream`, `POST /research/citations`, `GET /research/{research_id}` (all auth-required via `get_current_user`, owner-scoped)
- `apps/api/app/ai/research/service.py` — `ResearchService`: `research()` (full linear flow through the Generation Runtime), `stream_research()` (the streaming counterpart, going through `StreamingService` directly per the PRD's own `/research/stream` flow diagram, distinct from `/research`), `citations_only()` (retrieval + context building only, no generation, no persistence — powers the citation-panel preview)
- `apps/api/app/ai/research/models.py` — internal DTOs `ResearchSource` (built from a `ContextChunk`, not the raw retrieved chunk, since `page` only becomes available after parent expansion) and `ResearchOutcome`
- `apps/api/app/models/research.py` — `ResearchSession` (new Postgres table `research_sessions`: `query`/`answer`/`citations`/`sources`/`runtime_metadata` as JSONB) — Postgres is the live read path for `GET /research/{id}`, storing the answer directly rather than reconstructing it from the best-effort, write-only Research Artifact, mirroring the existing Conversation/Chat precedent
- `apps/api/app/repositories/research.py` — `ResearchRepository` (`create()`, `get_by_id_for_owner()` — owner-scoped so a caller can never load another user's session by id)
- `apps/api/app/schemas/research.py` — `ResearchRequest`/`ResearchStreamRequest`/`ResearchCitationsRequest` and `ResearchResponse`/`ResearchSessionResponse`/`ResearchCitationsResponse`
- `apps/api/app/dependencies/research.py`, `apps/api/app/dependencies/context.py` — new FastAPI dependency wiring (`get_research_service()`, `get_research_repository()`, `get_context_builder()`)
- `alembic/versions/37117c83beb2_create_research_sessions_table.py` — new migration, verified to round-trip cleanly

Every `GenerationRequest` this service builds sets `runtime=RuntimeType.RESEARCH` and `artifact_runtime=ArtifactRuntime.RESEARCH` — the first live code to exercise either enum value, previously reserved-but-unused. That means the pre-existing `ResearchRuntimeContract` (Runtime Validation Platform, Milestone 2.9.4) now actually runs against real traffic for the first time, and the previously scaffold-only Research Artifact writer (Artifact Platform, Milestone 3.10) now actually gets called — see "Research Artifacts" above.

`research()` and `stream_research()` both call `RetrievalService.search_hybrid()` (owner_id always injected server-side into filters, never trusted from the request body, mirroring `api/v1/retrieval.py`) and `ContextBuilderService.build()`, then persist a `ResearchSession` row and a best-effort `ResearchArtifact` (a storage failure is caught/logged as `artifacts.research.persist_failed`, never fails the request/stream — the same pattern `chat.py::_persist_on_complete` already established).

## Testing

23 new tests: `tests/unit/ai/research/` (`factories.py`, `test_service.py`), `tests/integration/test_research_repository.py`, `tests/integration/ai/test_research_api.py`. Full repo suite (1068 tests), `ruff format --check`, `ruff check`, and `mypy` all pass clean; migration verified to round-trip.

## Not Yet Built (by design — PRD §4 Non-Goals)

- ❌ Query decomposition, research planning, multi-step/agentic loops, LangGraph — explicitly out of scope for this milestone
- ❌ Guardrails runtime stage (`evaluate_runtime()`) still has no live caller — this service has no reasoning loop for it to guard
- ❌ Session/Agent/Evaluation artifacts remain scaffold-only (see Milestone 3.10 above)

---

# Phase 4.1 — Research Frontend Integration

**Status:** ✅ Complete — `apps/web`'s Research page is now wired to the live `/research`/`/research/stream` APIs above instead of a mock

`apps/web/src/features/research/mock-engine.ts` (the placeholder that previously faked streaming/citations/sources for UI development) is deleted. In its place: a new `use-research.ts` hook driving per-turn state (`searching` → `generating` → `done`/`error`), a new `lib/sse.ts` client for consuming the backend's `text/event-stream` responses via `fetch` + `ReadableStream` (not a bare `EventSource`, matching `chat.py`'s own documented reasoning — `EventSource` can't attach a custom bearer `Authorization` header), and a new `citation-card.tsx` component. `research-block`/`research-composer`/`research-sidebar`/`source-card`/`source-panel`/`streaming-status`/`types.ts`/`lib/api.ts` all updated to match the real API contract (citations, sources, `research_id`, replay-by-id) instead of mocked shapes. Initial history was client-side by `research_id`; a later follow-up replaced that with server-backed research conversation history via `/research/conversations`, while keeping `GET /research/{id}` as the single-turn replay path.

## Findings (bugs discovered turning this on against live infra, all fixed)

1. **Live-streamed research turns silently never persisted.** `ResearchService.stream_research()` only treated `CoreEventType.COMPLETE` (`"complete"`) as "generation finished," but `StreamingService`'s live-provider path (`_stream_live`) actually emits `StreamEventType.COMPLETED` (`"completed"`) — `CoreEventType.COMPLETE` is only ever emitted on the cache-hit-replay path. Every real (non-cache-hit) research stream finished, showed an answer in the UI, and then `GET /research/{id}` 404'd, because `_persist_session`/`_persist_artifact` were never reached. Fixed in `apps/api/app/ai/research/service.py` by checking both event-type values.
2. **`claude-sonnet-4` (bare, and its dated `-20250514` snapshot) has been fully retired** from the configured Anthropic account — confirmed directly against `GET /v1/models`, which no longer lists either. Every hardcoded reference (`.env`, `.env.example`, `core/settings.py`, `generation/config.py`, `generation/catalog/models.py`, `generation/prompts/service.py`, `generation/observability/token_counter.py`) updated to `claude-sonnet-5`; one test assertion (`tests/unit/ai/runtime/generation/prompts/test_service.py`) updated to match the new default.
3. **`claude-sonnet-5` rejects the `temperature` sampling parameter outright** (400 `invalid_request_error`, `` `temperature` is deprecated for this model``) — it's an "effort"-based reasoning model, not a classic sampling-temperature one. Rather than hardcoding a model-name list that would rot as Anthropic ships new snapshots, `ClaudeProvider.stream()`/`_create_message()` (`generation/providers/claude.py`) now attempt the call with `temperature` first and, on that specific error, retry once without it.

## To-Do / Open Items

- ~~Chat has no frontend surface yet~~ — **resolved, see Phase 4.2 below.** The design discussion (separate nav/page vs. unified mode-toggle) was settled in favor of a separate "Chat" page — matches the backend's own already-separate persistence/retrieval-grounding split.
- **SSE error path is not fully hardened.** `_sse_byte_stream` (`runtime/generation/streaming/transports/sse.py`) only catches `TimeoutError`/`StopAsyncIteration` around `events.__anext__()` — any other exception raised deeper in a route's stream generator (e.g. a future DB/commit failure) propagates unhandled and silently kills the SSE connection with no client-visible `error` event, rather than converting cleanly like the existing `CoreEventType.ERROR` path does. Noticed while investigating Finding 1 above, though Finding 1's actual root cause was the event-type mismatch, not this gap — still worth hardening defensively.
- **No automated check for upstream model deprecations.** Finding 2 was only caught by a live 404 during manual testing, not proactively. Worth a periodic (manual or CI) cross-check of `generation/catalog/models.py` model names against `GET /v1/models` so a provider-side retirement doesn't silently break generation again.

---

# Phase 4.2 — Chat Surface Frontend Integration

**Status:** ✅ Complete — `apps/web` now has a separate `/chat` page wired to the live `POST /api/v1/chat/stream` SSE endpoint, alongside (not merged into) the Research page from Phase 4.1

Implements the two-surface product IA explicitly requested: **Chat** (user knows the question — fast, interactive, multi-turn, no citations) vs **Research** (user knows the goal, the system discovers/synthesizes — slow, cited, report-generating). These are now genuinely separate pages with separate visual languages, not a mode toggle on one input.

## Backend fix required first

`app/api/v1/chat.py::_build_request` set `GenerationRequest.conversation_id` but never `session_id`. `ConversationService.get_or_create()` only fetches-by-id-or-creates-fresh — it 404s if given a client-supplied id it doesn't recognize, it does not create a row with that exact id. So a frontend cannot pre-generate a `conversation_id` for a new chat; the server must mint one on turn 1. But since `session_id` was never set, `StreamEvent.session_id` (carried on every SSE/WS event) was always `null` for chat, so the client had no way to *learn* that server-minted id either — multi-turn chat from a fresh session was structurally impossible from the frontend. Fixed by adding `session_id=conversation_id` to the `GenerationRequest(...)` construction, mirroring the exact pattern `ResearchService` already uses (`session_id=research_id`) for the identical reason. The expanded focused chat suite now covers this flow alongside history persistence and title generation.

## Frontend additions (`apps/web/src`)

- `lib/api.ts` — renamed `ResearchStreamEvent` → `RuntimeStreamEvent` (kept as a type alias for existing call sites) since the canonical `StreamEvent` shape is shared by Research and Chat; added `api.chat.stream()` (SSE POST to `/api/v1/chat/stream`, same `fetch`+`ReadableStream` approach as `lib/sse.ts` already used for Research — `EventSource` still can't send a Bearer header). Moved `PROVIDER_OPTIONS` here from `features/research/types.ts` (re-exported from there for backward compatibility) since it's runtime-agnostic.
- `features/chat/{types.ts,use-chat.ts,components/}` — `use-chat.ts` now mirrors Research's server-replay shape: `GET /chat/conversations` loads account-scoped summaries and `GET /chat/conversations/{conversation_id}` replays a selected thread. The server is the source of truth; the client retains only immediate in-flight streaming state.
- `app/(app)/chat/page.tsx` — "AI Assistant" page with a server-backed conversation sidebar, ChatGPT-style message bubbles (user right-aligned, sage-tinted; assistant left-aligned, plain), and the shared provider picker. Sidebar entries expose the complete generated title with a native tooltip and accessible label. It deliberately has no source/citation panel: Chat still has no retrieval/RAG wired server-side.
- Nav: added a "Chat" entry to `components/layout/sidebar.tsx`, positioned between Dashboard and Research. Dashboard's `RecentQuestions` mock component now links to `/chat` instead of `/research` (quick Q&A maps to Chat in the new IA); `RecentSessions`/`SuggestedResearch` still point at `/research`, since their copy ("draft a synthesis report," "compare methodology") is report-flavored, not quick-question-flavored.

## Not Yet Built (known, documented gaps)

- ❌ Citations/sources panel on Chat — blocked on Chat getting retrieval/RAG wired server-side (a separate, already-tracked gap, not new to this milestone).
- ❌ Routing-strategy picker in the Chat composer — `ChatStreamRequest.routing_strategy` exists on the backend contract but isn't exposed in the UI yet (Research's composer doesn't expose it either, for the same reason: kept to provider-only for now).

## Verification

Follow-up verification: focused chat integration tests (5) pass, as do `ruff`, repository/service `mypy`, and frontend `tsc --noEmit`. Did **not** verify via live Cognito login or a real LLM provider call.

---

# Milestone 11.16 — Guardrails Platform

**Status:** ✅ Complete (MVP Foundation, per `guardrails_platform_prd.md`) — ✅ Integrated into `GenerationService` and `ContextBuilderService` (per `guardrail_integration_prd.md`)

The Guardrails Platform answers a different question than the Validation Platform: not "did the system produce a good output?" but "should the system even perform this operation?" It is a platform-wide package (`apps/api/app/ai/guardrails/`, sibling to `knowledge/`, `runtime/`, `quality/`) spanning Input → Retrieval → Generation → Runtime stages, built to the same conventions as the Validation Platform (deterministic checks, a crash-safe `GuardrailService`, a `GuardrailRegistry`, weighted risk scoring, an `@lru_cache` composition root). It shipped standalone first (this milestone's original scope), then was wired into the two live composition roots in a follow-up integration pass — see the new "Integration" subsection below.

Pipeline

```
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

## Foundation

Implemented

- `models.py` / `enums.py` / `interfaces.py` — `GuardrailIssue`, `GuardrailResult`, `GuardrailReport`; `GuardrailSeverity`/`GuardrailStage`/`GuardrailCategory`/`GuardrailAction`; one ABC per stage
- `GuardrailRegistry` — per-stage ordered registration, mirrors `ValidationRegistry`
- `GuardrailService` — `evaluate_input()` / `evaluate_retrieval()` / `evaluate_generation()` / `evaluate_runtime()` / `evaluate()`; a crashing guardrail becomes a WARNING issue rather than propagating (mirrors `ValidationService`); `FailPolicy` (open/closed) governs whether a crash blocks
- `policies/` — `FailPolicy`, `RiskPolicy`, `RegenerationPolicy`, `RegenerationPolicy`-driven REGENERATE on faithfulness/schema errors, `RuntimePolicy`-driven BLOCK on budget/loop errors
- `scoring/` — weighted `overall_risk` (input 0.30 / retrieval 0.30 / generation 0.20 / runtime 0.20), renormalized over whichever stages actually scored
- `artifacts/` — `GuardrailArtifact`/`GuardrailArtifactBuilder`/`GuardrailArtifactWriter`, persisting `guardrails/{run_id}/{input,retrieval,generation,runtime,report}.json` to the same storage abstraction as `ChunkArtifactWriter`
- `reports/` — `summarize_report()`, `stage_summaries()`, issue grouping helpers
- `create.py` — `get_guardrail_service()`; now injected into both `create_generation_service()` and `create_context_builder()` (see "Integration" below) — a router/agent-runtime caller remains future work

## Input Guardrails

- ✅ Prompt Injection / Jailbreak detection (P0) — regex against `user_prompt`/`system_prompt`; single trigger warns, multiple/jailbreak-specific triggers error
- ✅ Scope Validation — deterministic off-topic (creative-writing/hacking) heuristic, WARNING-only by design
- ✅ PII Detection (foundation) — email/credit-card/API-key/token regex
- 🟡 Rate Limiting, Toxicity (foundation interfaces, always-allow — no request-counting state or classifier provider exists yet)

## Retrieval Guardrails

- ✅ Context Sanitization (P0) — composes the pre-existing `ContextGuardrailService`/`RuleBasedGuardrailProvider` (Milestone 2.8.4) rather than duplicating it
- ✅ Source Trust Platform (P1, new) — `SourceType` enum, `TrustRegistry` (static trust-score-by-source-type table), `trust_policies`/`scoring`; defaults every chunk to `USER_DOCUMENT` since no source-type field exists on `ContextChunk` yet
- ✅ Citation Integrity — deterministic existence check (every citation's chunks resolve, every chunk's citation resolves), complementary to the Validation Platform's fabricated-citation-marker check
- 🟡 Access Control (foundation interface, permissive default — no tenant isolation/document ACL model exists yet)

## Generation Guardrails

- ✅ Faithfulness Enforcement (P1) — wraps the Validation Platform's `HallucinationValidator`, reinterpreting low groundedness as ERROR (regenerate-worthy) rather than Validation's advisory WARNING
- ✅ Schema Enforcement — wraps `SchemaValidator`/`JsonValidator`, per the PRD's explicit reuse instruction
- ✅ PII Leakage (foundation) — same regex table as the input-side check, applied to generated content
- 🟡 Moderation (foundation interface, always-allow — PRD explicitly skips real moderation providers for MVP)

## Runtime Guardrails

- ✅ Budget Guardrail (P1, "implement immediately") — `BudgetPolicy`/`ExecutionState` models; checks max_tokens/max_cost/max_tool_calls/max_iterations/max_runtime_seconds independently, warns near the limit
- ✅ Loop Detection (foundation depth, real algorithm) — max-iterations check plus repeated-execution-state-hash detection
- 🟡 Tool Policy (foundation interface, allow-all default)
- 🟡 Approval Gate — `ApprovalRequest`/`ApprovalResponse` models + `ApprovalGateInterface` only, deliberately unimplemented and unregistered (the future LangGraph-interrupt seam, PRD §19)

## Dead Code Removed

Two empty, zero-reference scaffolds discovered during this work were deleted: `app/ai/guardrails/{policies.py,scanners.py}` and the entire (all 0-byte) `app/ai/runtime/generation/guardrails/` tree.

## Integration (per `guardrail_integration_prd.md`)

A follow-up pass wired the already-complete platform above into the two live composition roots, introducing no new registries/interfaces/services (per the PRD's own Non-Goals):

- `GenerationService` (`runtime/generation/service.py`) takes an optional `guardrail_service: GuardrailService | None`. `evaluate_input()` runs once at the top of both `generate()` and `stream_generate()`, before any provider call — a blocked result raises `GuardrailViolationError` (a `generation/exceptions.py` exception that pre-dated this wiring, unused until now) and generation never starts. The full `evaluate()` (input + retrieval + generation, reusing `request.prompt_context.chunks/citations`) runs inside `_execute_once()` after structured-output post-processing but before `ValidationService`, populating a new `GenerationResult.guardrails: GuardrailReport | None` field and raising on block.
- `ContextBuilderService` (`knowledge/context/service.py`) takes an optional `guardrail_platform_service: GuardrailService | None`, distinct from the pre-existing required `guardrail_service: ContextGuardrailService` (the Milestone 2.8.4 regex sanitizer, which the platform's own `ContextSanitizationGuardrail` already composes rather than duplicates). `evaluate_retrieval()` runs on the raw retrieved chunks before dedup/expansion/merge/compression — a blocked result raises a new `GuardrailBlockedError` (`guardrails/exceptions.py`), stopping downstream context building and generation.
- `GuardrailService.evaluate()` now persists a `GuardrailArtifact` via the pre-existing `GuardrailArtifactBuilder`/`GuardrailArtifactWriter` when an `artifact_writer` is configured (best-effort — a storage failure is caught/logged, never fails the run) and emits `guardrails.started`/`guardrails.completed`/`guardrails.blocked`/`guardrails.failed` structlog events plus `guardrail_checks_total`/`guardrail_failures_total`/`guardrail_blocks_total`/`prompt_injection_attempts`/`pii_detections`/`policy_violations` metrics via a new `MetricsRecorder` (`infrastructure/metrics/guardrails.py`, same not-yet-Prometheus-backed interface the Upload platform already used).
- Both composition roots (`guardrails/create.py`, `runtime/generation/create.py`, `knowledge/context/create.py`) wire this together automatically — no other caller needs to change.
- 14 new unit tests covering the block/allow paths on both integration points plus the new metrics/artifact behavior; full repo suite (854 tests), `ruff format --check`, `ruff check`, and `mypy` all pass clean.

## Testing

113 unit tests under `tests/unit/ai/guardrails/` from the original platform build, mirroring the Validation Platform's test-tree conventions (shared `factories.py`, local `_Fake...` doubles, real-dependency composition tests for the reuse points), plus 14 more from the Integration pass above (see "Integration").

## Not Yet Built (by design — matches PRD §21/§22 MVP scope, plus `guardrail_integration_prd.md`'s own Phase 5)

- ❌ LLM-based classifiers (Llama Guard, Lakera, NeMo Guardrails) — explicitly skipped for MVP
- ❌ A router/agent-runtime caller for `evaluate_runtime()` — the new `/research` API (Phase 4) is deliberately linear with no reasoning/tool loop, so it still has nothing to drive this stage; needs a future Research/Agent Runtime instead
- ❌ Post-generation guardrails on the streaming path (`stream_generate()` only gets the pre-provider input gate — buffering a full streamed response to evaluate it wasn't in scope)
- ❌ Enterprise ACL / multi-tenant Access Control, real Tool Policy providers, a working Approval Gate implementation (LangGraph interrupts/checkpoints)
- ❌ Security dashboards, attack datasets, red-teaming (PRD's Phase 2-4 future roadmap)

---

# Engineering Benchmark Platform

**Status:** ✅ Foundation Complete, incl. Generation Evaluation + Regression Detection (per the `evaluation_platform_prd.md` reconciliation below)

Implemented

- Benchmark framework
- Registry
- Runner
- Dataset loader
- Markdown reports
- JSON reports
- Chunking Benchmark
- Embedding Benchmark
- Pipeline Benchmark — end-to-end ingestion benchmark (real Chunking → Embedding → Indexing), now reports dense + sparse vector counts per document; re-run after the hybrid indexing change confirmed indexing (SPLADE inference) is the new dominant per-document latency cost, ahead of embedding
- Retrieval Benchmark — benchmarks dense, sparse, and hybrid (RRF) retrieval against a dedicated, reproducible Qdrant collection (`benchmark_retrieval`, dropped/recreated per run, never touches production data); reports Recall@5/10/20, Precision@5/10, **NDCG@5/10 (new — wired the pre-existing but previously-unused `ndcg_at_k` into the candidate metrics table, confirmed with real values via Qdrant/Voyage)**, MRR, avg/P95/P99 latency, and a qualitative cost model per ADR-020
- Metadata Filtering Benchmark — validates `owner_id` filtering against a dedicated `benchmark_retrieval_filtering` collection with a distinct synthetic owner per document; reports Recall@K/Precision@K/MRR plus a `leakage_rate` correctness signal (0.0 for every filtered candidate)
- Reranking Benchmark — compares `hybrid_only` vs. `hybrid_cross_encoder` vs. `hybrid_voyage` on the same hybrid candidate pool per query against a dedicated `benchmark_reranking` collection; reports Recall@5, MRR, NDCG@5, latency, and a qualitative cost model
- **Generation Benchmark (new)** — `benchmarks/generation/`, scores every configured `GenerationProvider` (Groq/OpenAI/Claude/Gemini/Ollama — whichever have credentials, mirroring how `create_generation_registry()` already scopes itself for "benchmark environments") against a hand-curated 13-query dataset (`benchmarks/datasets/research-papers/generation_queries.json`, query/context/expected_answer/citations, context supplied directly rather than retrieved live so generation quality is isolated from retrieval quality). Deterministic, no-LLM lexical-overlap scoring (`benchmarks/generation/metrics.py`), mirroring the exact convention already established by `hallucination_validator.py` — faithfulness (sentence-level claim support), groundedness (token-level bag-of-words containment), relevance (query-term coverage), completeness (expected-answer coverage), citation accuracy, and a derived hallucination rate. Verified live against real providers: Groq/OpenAI/Claude all completed 13/13 queries with distinct, sensible scores; Gemini/Ollama failed for legitimate external reasons (free-tier quota, no local server) and degraded gracefully per-candidate without aborting the run — same isolation pattern `RetrievalBenchmark._evaluate()` already uses. **Found and fixed a real bug during verification**: `citation_accuracy` was structurally 0.0 for every candidate on the first live run, because the benchmark instructed the model to cite a source filename it was never actually given anywhere in its input — fixed by tagging the context with `[Source: <filename>]`; a second live run confirmed `citation_accuracy` correctly moved to 1.0 for every working candidate. **Cost metrics (new)** — `avg_cost_usd`, `cost_per_query`, `cost_per_1k_queries`, read directly off the already-existing `GenerationResult.statistics.estimated_cost_usd` (real per-model pricing from `catalog/models.py`, previously computed but never surfaced by any benchmark); verified live — Claude came out ~24x pricier than Groq per 1k queries for this dataset ($3.76 vs. $0.16), giving the provider comparison table a real cost column alongside quality and latency.
- **Regression Detection (new)** — `benchmarks/regression/` (`models.py`/`thresholds.py`/`detector.py`/`report_generator.py`), compares a fresh `BenchmarkReport` against the previously stored `report.json` for the same benchmark and flags any metric that crossed its configured threshold (PRD §18: 0.05 absolute drop for retrieval quality metrics, 0.03 for generation quality metrics, 0.03 absolute increase for hallucination rate, 25% relative increase for latency **and cost**). Wired into `benchmarks/runner.py` via a new `--check-regression` flag — writes `regression.json`/`regression_report.md` alongside the benchmark's own reports and exits non-zero on failure, satisfying PRD Goal 5 ("Enable CI quality gates") without any CI infrastructure of its own. Verified both directions live: caught a real regression (relevance/completeness/latency shifts from the citation-instruction prompt change above, with correct per-metric messages) and passed cleanly on an unchanged retrieval rerun. **Follow-up finding:** a later live diff of two ad-hoc Generation Benchmark dev runs (no code change between them) tripped several false "regressions" — traced to LLM sampling non-determinism and provider-side latency jitter, not a real defect; the stale `regression.json`/`regression_report.md` artifacts from that comparison were deleted and replaced with a clean baseline `report.json`. The mechanism itself is sound (confirmed working correctly on the deterministic Retrieval Benchmark); it just needs a frozen, CI-committed baseline rather than consecutive dev-loop runs to be a trustworthy signal for Generation.
- `mypy`/`ruff` clean across all 35 files in `benchmarks/` after these additions.

## Evaluation Platform PRD Reconciliation

`evaluation_platform_prd.md` (repo root) proposed a new, monolithic `app/ai/evaluation/` platform — datasets/evaluators/benchmarks/experiments/regression/reports/artifacts/langsmith — self-labeled "Phase 4.1" (a number already taken in this file by Research Frontend Integration). Investigation before writing any code found the PRD would have duplicated two systems that already exist under different names, and forked a third that's separately designed but not yet built:

1. **"Engineering Benchmarks"** (`docs/architecture/evaluation-strategy.md` Layer 1) — already real, working code at repo-root `benchmarks/`, not the empty `app/ai/quality/{evaluation,benchmarks,experiments,regression,telemetry,tracing}/` scaffold (present since the very first commit, confirmed dead by `docs/evaluation/strategy.md`'s own "Current Status: Not Implemented" note) that the PRD's proposed `app/ai/evaluation/` folder layout would have paralleled a third time.
2. **"Runtime Evaluation"** (`docs/architecture/evaluation-platform.md`, and Layer 2 of the strategy doc) — already implemented as the **AI Runtime Observability Platform** above. `STRUCTURE.md` independently confirms this on the sibling doc `docs/architecture/observability-platform.md`: *"Phase 1 (Runtime Evaluation) ... now implemented ... through the newer AI Runtime Observability Platform ... rather than a new module under this document's own proposed folder structure."*
3. **"Experiment Platform"** (PRD §17) — would have forked the separately-designed, not-yet-built async Experimentation Platform (`docs/architecture/experimentation-platform.md`, Layer 3: background queue/worker, per-document strategy comparison) before it exists, with a materially different synchronous Candidate-A/B/C shape. Deferred — the PRD's own roadmap (§23) places Experimentation at Phase 5, after Regression.

What was real and missing — Generation evaluation (PRD §15, nothing existed; `tests/evaluation/{test_faithfulness,test_groundedness}.py` confirmed empty stubs) and Regression Detection (PRD §18) — was built directly into the already-working `benchmarks/` package instead, described above. LangSmith dataset/experiment sync (PRD §21 "Future") stayed out of scope per the PRD's own Non-Goal #3. The S3-backed Evaluation Artifact layer (`app/ai/artifacts/evaluation/`, already built, scaffold-only) was deliberately left unwired — `benchmarks/README.md` explicitly states the Benchmark Platform must stay independent of production infrastructure and never depend on S3.

---

# Milestone 12 — Memory Platform

**Status:** ✅ Complete (per `memory_platform_prd.md`, Phase 11.23), extended same-session against a follow-up 5-pipeline architecture review, then wired into **both** live product surfaces (Research and Chat) in a further same-day follow-up

A new top-level `app/ai/memory/` package gives Research and Chat persistence between turns/sessions — distinct from the Artifact Platform (write-only execution history) and the Context Platform (per-request retrieval only). Four memory types, each routed to whichever backend fits its access pattern: **SESSION** → Valkey only (`ValkeySessionStore`, TTL-bound scratch, keyed by `owner_id`+`id` for O(1) recall); **USER** → Postgres only (preferences — not semantically searched, no embedding); **SEMANTIC**/**RESEARCH** → Postgres (canonical row/ownership) + a dedicated Qdrant collection (`researchmind_memory`, search-index only, not source of truth) via a shared `VectorBackedMemoryService` base, reusing the Knowledge Platform's `QueryEmbeddingService` (Voyage AI) rather than the document-oriented `EmbeddingService`. A `MemoryService` orchestrator exposes `remember()`/`recall()`/`search()`/`forget()`/`update_memory()`/`get_context()`, dispatching generically across types via `Protocol`-typed structural typing (`_MemoryBackend`/`_RememberableBackend`) rather than `Any`. New `/memory` API: `POST /memory` (remember — returns `null`, not an error, below the importance threshold), `POST /memory/search`, `GET /memory/context`, `GET`/`PUT`/`DELETE /memory/{id}`. New `memories` Postgres table (migration `9ab1f891554a`).

Importance scoring (`importance.py`) is a cheap rule-based heuristic (`score_importance()` — signal-phrase regex, not LLM-driven); `remember()` silently skips persistence below `settings.memory_importance_threshold` (default 0.1).

## Pipeline Alignment Pass

The user supplied a detailed 5-pipeline target architecture (Creation/Retrieval/Consolidation/Lifecycle/Runtime Injection) and asked for a gap review. Rather than a full type→stage folder rewrite of already-verified working code, the genuinely missing *behaviors* were added as new stage-named modules alongside the existing type-based ones (`session/`, `profile/`, `semantic/`, `research/`):

- **`retrieval/fusion.py`** — fixed a real bug: `MemoryService.search()` used to concatenate per-type result lists and sort purely by `importance_score`, silently discarding Qdrant's own relevance ranking. Now runs Reciprocal Rank Fusion (`k=60`, same algorithm/constant as the Knowledge Platform's `RetrievalFusionService`) across each already-ranked per-type list; dedup falls out of keying by id.
- **`extraction/service.py`** — new `MemoryExtractionService`, LLM-driven via `GenerationRuntimeInterface`, turns a conversation turn into `ExtractedMemory` candidates (USER/RESEARCH only — SESSION is never proposed by extraction, it's captured unconditionally instead). Classification is folded into extraction rather than a separate stage, since `ExtractedMemory.type` already carries it. Hit two cross-provider structured-output incompatibilities fixed via a schema-only `_ExtractedMemoryLLM` twin (`extraction/models.py`): Claude rejects `ge=0.0, le=1.0` constraints in JSON Schema (`minimum`/`maximum` unsupported), and OpenAI's strict mode rejects a field with a Pydantic default (silently absent from `required`) — importance is clamped back to `[0,1]` in code after parsing.
- **`lifecycle/service.py` + worker entrypoint** — `MemoryLifecycleService.sweep_stale()` deletes low-importance USER/SEMANTIC/RESEARCH rows (+ their Qdrant point) past configurable per-type thresholds. `apps.worker.memory_lifecycle_main` now runs it recurringly with a Valkey singleton lock, dry-run by default, bounded batches, row-level failure isolation, and registered Prometheus metrics.
- **Runtime Memory Injection wired into `ResearchService`** — `get_context()` runs before retrieval and is prepended to `PromptContext.context` (never `chunks`/`citations`, so citations/guardrails are unaffected); after generation, the raw turn is unconditionally stored as SESSION memory and `MemoryExtractionService` proposes USER/RESEARCH memories from it. New `ResearchRequest.session_id` (optional, defaults to a fresh one-off) lets callers link multiple `/research` calls into one continuing thread — this didn't exist at all before.
- Consolidation (PRD §26 / the follow-up doc's own "Future" section) stays deferred, matching both docs' own guidance.

## Chat Wired to Memory Too, Plus Two Generation Platform Bugs Fixed

A further same-day follow-up request: *"Chat runtime is still not wired to memory — only research is, since that's the only live surface"* — plus two explicit bug-fix asks. Fixing the second bug turned out to be a prerequisite for the memory wiring actually working at all.

**Bug 1 — latent artifact-serialization crash, fails open.** `GenerationRequest.output_model: type[BaseModel] | None` had no `exclude`, so `GenerationArtifactBuilder`'s `model_dump_json()` of `GenerationResult.request` crashed with `PydanticSerializationError: Unable to serialize unknown type: ModelMetaclass` whenever structured output was used. The crash was itself caught and logged (`artifacts.generation.failed`), never raised — no request ever failed from this, but the whole generation artifact silently never persisted. Fixed with `output_model: type[BaseModel] | None = Field(default=None, exclude=True)` in `runtime/generation/models.py` — one line; `output_schema` (the JSON-serializable derived schema) is unaffected and still persists.

**Bug 2 — blanket empty-`prompt_context.context` rejection: a total, unconditional outage of Chat, not an edge case.** Originally described (and initially assumed by this project) as "a brand-new account with zero documents gets rejected regardless of memory." Investigating it directly for this fix revealed it was far worse: `GenerationService._validate()` (`runtime/generation/service.py`) required `prompt_context.context` to be non-empty in addition to `user_prompt` — and `chat.py` has never wired retrieval, so `_build_request()` always built `PromptContext(context="", chunks=[])`. That means **every `/chat/stream` and `/chat/ws` call, on every account, was unconditionally crashing** with `GenerationValidationError: Prompt context cannot be empty`, confirmed by direct reproduction before the fix. The softer `ContextValidator` (`validation/input/context_validation.py`) already documented this exact tension in its own docstring, treating empty chunks as WARNING-only, "not generation-time failures" — this was a known, never-reconciled design conflict between two validators, not a fresh regression. Fixed by removing the `prompt_context.context` check from `_validate()` entirely; `user_prompt`'s own non-empty check (unchanged) is a complete, valid request on its own. Verified via direct reproduction that the exact request shape `chat.py` builds now succeeds end-to-end, then again via the full test suite (see "Testing" below).

**Chat memory wiring** (`api/v1/chat.py`) mirrors `ResearchService`'s pattern exactly: `_retrieve_memory_context()`/`_build_request()` fetch `MemoryService.get_context()` before generation and prepend it via `with_memory_context()`; `_extract_and_store_memory()`, called from `_persist_on_complete()` right after the turn is appended to `ConversationService`, stores the raw turn as SESSION memory and runs `MemoryExtractionService.extract()` for USER/RESEARCH candidates. `conversation_id` doubles as the session id — a more natural boundary than Research's synthetic one, since a conversation already persists across turns via `ConversationService.get_or_create()`. Both `/chat/stream` (HTTP, `Depends(get_memory_service)`/`Depends(get_memory_extraction_service)`) and `/chat/ws` (WebSocket, via two new plain-Python factories in `ai/memory/create.py` — `build_memory_service(session)`/`build_memory_extraction_service()`, needed since that route manages its own `AsyncSession` outside FastAPI's DI graph) are covered. The formatting/injection logic (`format_memory_context()`, `with_memory_context()`) was extracted out of `ResearchService` into a shared `ai/memory/services/formatting.py` so Chat and Research don't duplicate it.

## Testing

Verifying this against the repo's actual `tests/` suite (not live smoke scripts — see the note below) surfaced 3 failures, all fixed:

- `tests/integration/ai/test_chat_stream.py` — two tests broke because the route now resolves real `MemoryService`/`MemoryExtractionService` via `Depends(...)` when not overridden, and the real ones need provider credentials the test environment doesn't have. Fixed by adding `_FakeMemoryService`/`_FakeMemoryExtractionService` and wiring them into the file's existing `app.dependency_overrides` fixture pattern, alongside the pre-existing streaming/conversation fakes.
- `tests/unit/ai/runtime/generation/test_service.py::test_generate_raises_validation_error_for_empty_prompt_context` — this test asserted the *old* behavior Bug 2's fix intentionally removed. Replaced with `test_generate_allows_empty_prompt_context`, asserting the new behavior actually completes a full `generate()` call end-to-end.

Full repo suite (1160 tests) passes clean after both fixes; `ruff`/`mypy` clean.

## Memory Optimization Hardening (2026-07-19)

The approved `memory_platform_optimization_plan.md` core optimization is now implemented without changing public Memory API contracts:

- Durable-memory availability is cached per owner in Valkey; new users skip query embedding and Qdrant memory searches while SESSION state still loads. Store/cache failures are fail-open and do not break the Chat or Research response.
- One query embedding is shared by concurrent semantic and research memory searches. A failure in one branch is separately logged and preserves the other branch's results.
- Post-turn extraction is governed by a versioned deterministic policy, skips trivial/generic turns, uses a shared Chat/Research orchestrator, records a structured outcome, and uses canonical Chat assistant-message IDs (or research IDs) for Redis idempotency.
- Explicit learning/research-interest statements are eligible for LLM validation immediately. Generic questions remain inexpensive lexical candidates; a topic must recur in two distinct sessions before one LLM validation can promote it to a USER interest. Per-user/topic Valkey keys are hashed and claimed once for 90 days, preventing repeat promotion cost. Assistant inferences are never supplied as evidence for profile writes.
- Raw `Q/A` SESSION copies are disabled by default. Canonical conversation/research persistence owns transcript history; SESSION memory now stores only compact, explicitly detected temporary state with source-turn provenance. Formatting has configurable category counts and per-item caps.
- Exact normalized extracted-memory duplicates are updated with latest provenance rather than inserted repeatedly. Broad semantic supersession remains intentionally deferred until there is an explicit subject/version model.
- Named memory counters/durations emit as structured metric events now; existing `generation_usage` owner summaries expose memory-extraction requests, cost, answer turns, and extraction cost per 100 answer turns.
- Dedicated unit tests cover policy, availability fail-open behavior, no-memory short-circuiting, branch isolation, compact state, de-duplication, outcome handling, and idempotency. Focused Memory + Chat + Research regression suite: **30 passed**. The full repository suite now passes: **1,183 passed**. Backend formatting/lint and `mypy apps/api/app` pass; frontend type check passes.

### Cost-Aware Interest Promotion (2026-07-19)

The initial optimized policy was extended so cost control does not remove useful long-term interest capture:

- `memory_extraction_policy_version` is now `v2`. Explicit learning or research-interest language is LLM-eligible immediately; ordinary one-off questions remain normal conversational history, not a profile write.
- Generic questions contribute at most three bounded lexical topic candidates. Valkey records distinct server-side Chat/Research session IDs under hashed owner/topic keys. The second distinct session makes a topic eligible for one LLM validation; a separate 90-day hashed claim prevents repeat promotion spend in later sessions.
- The LLM remains the final gate: it may create/update a canonical PostgreSQL `USER` memory or return no durable memory. Assistant-generated inference is never promotion evidence. Extracted durable `USER`/`RESEARCH` memory continues to use PostgreSQL as canonical storage; only RESEARCH is Qdrant-indexed for semantic recall.
- Live local diagnosis confirmed the mechanism is not a PostgreSQL write regression: the API and infrastructure were healthy, durable `memories` rows remained present, and a repeated RAG candidate with only one newly observed server-side session correctly did not trigger `memory_extraction`. Historical conversations are deliberately not backfilled into the candidate counter.
- Added `docs/adrs/ADR-029-cost-aware-memory-promotion.md` and appended §26, “Memory Optimization Architecture,” to `docs/architecture/memory-platform.md`. The original architecture remains preserved as the baseline; the new section documents the optimized flow, storage responsibilities, safeguards, and staged validation.
- Latest verification: Memory unit suite **19 passed**; Chat + Research regression suite **16 passed**; focused Ruff, mypy, and `git diff --check` pass.

Live rollout remains a separate operational verification step: collect staging/production traffic and inspect the structured metrics plus `/usage/summary` before marking target percentages and P50/P95 values as achieved. No synthetic production rows or provider calls were created during implementation.

**Process note:** initial verification for the Memory Platform build (this milestone and the Pipeline Alignment Pass above) used ad hoc scripts hitting live dev Postgres/S3/Qdrant/LangSmith and real LLM/embedding providers instead of this repo's actual `tests/` suite, under the mistaken premise that no test suite existed (only `apps/api/` had been searched for `test_*.py`, missing the real one at repo-root `tests/`, ~1150+ tests). This left stray rows/artifacts/traces in the dev environment that had to be traced back and explained after the fact. Corrected going forward — see the "Not Yet Built" note below.

## Not Yet Built (by design, or deferred)

- ❌ Evaluation harness (Recall@K/Precision@K) — PRD §23, not in the PRD's own Deliverables checklist
- ❌ Memory consolidation, decay staging (hot/warm/cold), reflection memories, agent-shared memory — both the PRD (§26) and the follow-up architecture doc explicitly frame these as future work pending real usage data
- ❌ Wiring into an Agent Runtime — none exists yet
- ⚠️ Memory lifecycle worker rollout — recurring execution is implemented and safe-by-default in dry-run mode; production must review candidate counts and explicitly enable deletion
- ⚠️ Dedicated Memory unit coverage now exists; the older `tests/integration/test_memory.py` stub remains unimplemented, so a full infrastructure-backed Memory integration suite is still a future hardening item
- ❌ Chat still has no retrieval/RAG wired at all — a separate, pre-existing gap independent of memory; memory injection works, but Chat answers still aren't grounded in uploaded documents

---

# Milestone 2.9.7 Addendum — Routing Platform AUTO Default Changed to Groq

**Status:** ✅ Complete — explicit user request, 2026-07-18, same session as the Memory Platform follow-up work above

`RoutingStrategy.AUTO` (the strategy every request without an explicit `provider` or `routing_strategy` resolves to) previously picked whichever model the scoring engine ranked highest under AUTO's default weights (quality 0.30 / reliability 0.25 / reasoning 0.20 / speed 0.15 / cost 0.10) — in practice claude-sonnet-5 essentially every time (~8.52 vs. groq's ~7.50). The user asked for groq to be the default instead. Added `RoutingService._select_for_strategy()` (`routing/service.py`): for `AUTO` specifically, scans the already-scored, already-sorted-descending candidate list for the first groq entry and selects that instead of `scored[0]`, falling back to `scored[0]` only if no groq candidate survived capability/policy filtering for that request (e.g. a `RequiredCapability.TOOL_CALLING` requirement groq's catalog models don't support) — groq not fitting a request never raises `NoEligibleModelsError` on its own. The remaining scored candidates (minus the selection) still feed the existing `_build_fallback_chain()` unchanged, so multi-provider fallback diversification and graceful degradation if groq's API key isn't configured both work exactly as before. Every other named strategy (`FAST`, `CHEAP`, `QUALITY`, `REASONING`, ...) and any explicit `provider=` argument bypass this entirely and are unaffected — verified directly against `create_routing_service()` (no live calls): AUTO now selects `groq/deepseek-r1-distill-llama-70b`, fallbacks `claude-sonnet-5` → `gpt-5`; `QUALITY` unchanged, still `claude-opus-4`. `ruff`/`mypy` clean.

---

# Phase 6 — Research Runtime Platform

**Status:** ✅ Complete, working, end-to-end single-agent Deep Research workflow
— backend *and* a real frontend, clickable start to finish (proposal → plan
review → approval → live-streamed multi-wave run → report preview/edit →
approval-or-non-destructive-rejection → PDF-or-plain-answer). User-tested
2026-07-24, six real gaps found and fixed the same day — see "2026-07-24
UX/reliability pass" below.

**Source docs:** `researchmind_research_runtime_implementation_plan.md`, `research_runtime_prd.md`, tracked milestone-by-milestone in `RESEARCH_RUNTIME_IMPLEMENTATION_TRACKER.md`. Architecture decisions in ADR-031 (runtime boundary), ADR-032 (checkpointing/events), ADR-033 (single-agent vs. multi-agent — single-agent chosen), ADR-034 (product routing — the proposal/approval/dispatch flow below). **Code-verified flow-by-flow reference (Chat/Linear/Deep, with a real loophole/gap audit)**: `PRODUCT_FLOWS_AND_GAPS.md` — check that file before this one for anything performance/cost/correctness-related; it's re-verified against the current code on every change, this section is a higher-level summary.

Phase 1 (the disabled `START → initialize → complete → END` walking skeleton this file previously described under the Memory Platform roadmap stub) has grown into a real, additive Deep Research product surface, built in an uncommitted session and then hardened in a same-day follow-up. The three product paths stay deliberately separate, verified by direct code read, not just design intent:

```text
Chat            → fast conversation, ungrounded
Linear Research → POST /research, /research/stream — fast, cited, never touches LangGraph
Deep Research   → proposal → approval → asynchronous multi-step investigation → report
```

`POST /research` and `POST /research/stream` are architecturally untouched: no runtime flag ever routes either through LangGraph, and the one DI provider that could (`get_research_runtime_execution_service`) has zero route callers.

## What works end to end today

```text
POST /research/escalation-check                 → optional; classifies a query, persists a
                                                    proposal only if it's worth suggesting
POST /research/proposals                        → planner-only (memory-aware, query-rewriting),
                                                    no run/retrieval cost
POST /research/proposals/{id}/approve            → idempotent; creates ResearchRun + outbox dispatch
  dedicated worker (apps/worker/research_runtime_main.py, own process)
    → Postgres-checkpointed LangGraph: planner → dependency-wave retrieval (Send fan-out)
      → evidence aggregation → synthesis → deterministic+model review → bounded repair
      → report-approval interrupt() — graph pauses for a real human checkpoint
GET  /research/runs/{id}/draft                   → owner-scoped read of the pending draft
                                                    (title/abstract/findings/citations/review),
                                                    read straight out of the paused run's
                                                    LangGraph checkpoint -- added 2026-07-24
POST /research/runs/{id}/report-decision         → approve (optionally with edited draft text,
                                                    citation-safe -- resumes -> final report + PDF)
                                                    or reject-with-reason (as of 2026-07-24: the
                                                    run still completes and publishes the
                                                    synthesized draft as a plain answer, just
                                                    without the PDF -- no longer a terminal failure
                                                    that discards the content)
GET  /research/runs/{id}                         → owner-scoped lifecycle status
GET  /research/runs/{id}/events                  → owner-scoped SSE progress replay (live-
                                                    consumed by the Research UI, not just API)
GET  /research/runs/{id}/report                  → owner-scoped 5-minute presigned PDF URL
POST /research/runs/{id}/cancel                  → cooperative cancellation (not rate-limited —
                                                    a safety valve)
```

**Frontend** (`apps/web/src/features/research/`, `apps/web/src/app/(app)/research/page.tsx`) —
a real, working state machine, not a stub: Linear/Deep mode toggle (Linear default) →
optional escalation suggestion banner → plan review card (goal/tasks/complexity/budget) →
live SSE-streamed progress card (the actual "Planning research" / "Searching selected
sources" / "Analyzing evidence" / etc. labels below, not polled — and, as of 2026-07-24,
still visible after the run leaves `running`, instead of disappearing) → report-review
card (as of 2026-07-24, shows the actual draft — title/abstract/findings/citations/review
scores — with an in-place edit mode, not just blind approve/reject+reason buttons) →
completed card with either a PDF download link, or (if the report was rejected) the
synthesized answer shown inline instead. Known, disclosed scope trim: the citations/
sources side panel is still Linear-Research-only (the report-review card now shows its
own resolved citations inline, but the separate side panel doesn't pick up Deep Research
turns). **Resolved 2026-07-24:** conversation-history replay now does reconstruct the
Deep Research card treatment (including a still-running or awaiting-approval run's live
state) for past conversations, not just completed-and-flattened answer turns.

- **Memory-aware planning** (`proposal_service.py`) — best-effort session/semantic/research memory retrieval feeds the planner, which can emit a `rewritten_goal` resolving references like "compare it with X" using that context. Fail-open: a memory outage never blocks planning.
- **Planner** (`runtime/research/planner/`) — Generation Runtime-only structured planning, complexity classification (SIMPLE/MODERATE/COMPLEX), per-complexity policy ceilings (task count, review iterations, duration, cost).
- **Decomposition** (`runtime/research/decomposition/`) — DAG validation, topological dependency-wave scheduling.
- **Multi-wave graph** (`runtime/research/workflows/multi_wave_research.py`) — `StateGraph` with `Send()`-based parallel fan-out per wave, bounded concurrency (semaphore on the retrieval service itself), evidence aggregation, synthesis, deterministic + model-based review, decision-specific bounded repair (one synthesis revision, one targeted gap-research round — budget-enforced per plan complexity, not hardcoded), and a real `interrupt()` before the final report is ever persisted.
- **Report-approval checkpoint** — the graph pauses (LangGraph `interrupt()`) after review passes, publishing `RESEARCH_AWAITING_APPROVAL`; a fresh dispatch (`ResearchRunDispatchRepository.reopen`) wakes the worker once a decision is recorded, resuming the *same* graph thread via `Command(resume=...)` rather than restarting. As of 2026-07-24, the reviewer can also read (and citation-safely edit) the pending draft before deciding (`GET /research/runs/{id}/draft`, reading directly off the paused run's checkpoint), and rejection is no longer a terminal `failed` state that discards the work — `route_after_report_approval` routes straight to `END`, skipping only the PDF-writing node, so the run still completes (`COMPLETED_WITH_LIMITATIONS`, `terminal_reason="report_rejected_returned_as_answer"`) and the already-synthesized draft still gets published as a plain answer.
- **Run lifecycle** (`lifecycle.py`) — a validated status state machine (`created → planning → researching → reviewing → synthesizing → awaiting_approval → completed/completed_with_limitations/cancelled/failed`), persisted on `research_runs`, distinct from the completed-turn `research_sessions` table.
- **Dispatch** (`repositories/research_run_dispatch.py`, `apps/worker/research_runtime_worker.py`) — a PostgreSQL transactional outbox (`SELECT ... FOR UPDATE SKIP LOCKED`, leased claims with expiry-based re-delivery), run by a worker process dedicated to Research Runtime — never the document-processing worker, never FastAPI background tasks. Single process by default (see Not Yet Built).
- **Cancellation and crash-resume** — cooperative cancellation checked at bounded graph checkpoints (before each wave, before each synthesis attempt, and before resuming from the report-approval pause); a run interrupted mid-execution (worker crash, OOM) resumes from its last LangGraph checkpoint rather than restarting, gated to the outbox-protected worker path only.
- **Budgets** — real, not aspirational: per-complexity max tasks/review-iterations/duration/cost, an explicit graph `recursion_limit`, and a real (ledger-backed, not estimated) running-cost check before allowing another repair loop.
- **Rate limiting** — real, Valkey-backed, per-owner: proposals + escalation-checks share a 5 req/60s bucket, approvals get their own stricter 5 req/600s bucket (the most expensive action in the product). Same mechanism now also covers Chat and Linear Research.
- **Reports** — final report JSON + rendered PDF, idempotent per run, downloadable via a short-lived owner-scoped presigned URL.

## 2026-07-23 hardening pass

A same-day readiness audit (before enabling `research_runtime_v1_graph_enabled` for real) found and fixed a batch of real gaps — full detail in `AI_ENGINEERING_AUDIT.md` §0.0.0 and ADR-034's "Resolved since first written" section:

- Postgres checkpoint tables didn't exist in the real database (only ever provisioned against a separate test DB) — added a one-time `scripts/provision_research_runtime_checkpoints.py`, run against dev.
- A disabled-flag misconfiguration produced a silently stuck run instead of a visible failure — fixed.
- `max_review_iterations` was computed per plan complexity but never actually enforced by the graph (hardcoded to allow 1 regardless) — now wired through.
- No duration or cost ceiling existed — added real ones (`asyncio.wait_for` + a `generation_usage`-ledger cost check).
- No explicit `recursion_limit` — added (`Settings.research_runtime_graph_recursion_limit`).
- A declared retrieval concurrency cap was dead code (never actually called) — fixed.
- A single malformed synthesis response killed the whole run instead of using the existing repair-loop machinery — fixed with one bounded inline retry.
- No cancellation or crash-resume existed despite `cancellation_requested` being a real, API-visible column — both added.
- The SSE progress endpoint shared chat/generation's 5-minute ceiling, too short for a real research run — given its own 30-minute ceiling.
- Near-zero operational logging across the whole runtime — added throughout.

Verified: full repo suite **1247 passed**, ruff/mypy clean across `apps`, worker starts/stops cleanly with no orphaned processes or connections.

## 2026-07-23 completion pass (same day, later) — memory, human checkpoints, rate limiting, frontend

Follow-up work that took this from "hardened backend slice" to "complete, working,
end-to-end single-agent workflow with a real frontend." Full detail and severity-rated
remaining gaps in `PRODUCT_FLOWS_AND_GAPS.md`.

- **Memory Platform wired into planning** — `ResearchProposalService` now retrieves
  session/semantic/research memory (best-effort, fail-open) and feeds it to the planner,
  which can emit a `rewritten_goal`. Previously the Deep Research planner received the raw
  query string only, despite the Memory Platform being live for Chat/Linear Research since
  Phase 11.23. Also fixed the actual root cause: the worker's own composition root
  (`bootstrap/worker.py`) was constructing `MemoryService` via FastAPI `Depends`-only
  factories called outside FastAPI's resolution, silently producing broken sentinel
  objects — memory extraction from completed Deep Research runs had never actually worked.
- **Report-approval interrupt** — a real second human checkpoint, not just plan approval:
  the graph now pauses via LangGraph `interrupt()` after review passes, before the report
  is persisted. `POST /research/runs/{id}/report-decision` resumes (approve) or terminally
  fails (reject-with-reason) the *same* graph thread — no re-planning, no lost work.
  Required one lifecycle-FSM transition addition and a dispatch-outbox `reopen()` method
  (1:1 run↔dispatch invariant, so re-queuing reuses the existing row).
- **Rate limiting, all three paths** — previously `RateLimitGuardrail` was a permanent
  no-op (confirmed by reading it, not inferred) and nothing else in the app throttled
  anything. Added a real Valkey-backed per-owner limiter (`ValkeyRateLimiter`, fixed-window
  `INCR`+`EXPIRE`) in front of every cost-generating route: Chat (20/60s), Linear Research
  (15/60s, shared across `/research`+`/stream`+`/citations`), Deep Research proposals +
  escalation-checks (5/60s), Deep Research approvals (5/600s — the single most expensive
  action in the product). `GET` routes, cancel, and report-decision stay unlimited on
  purpose.
- **Escalation-check + Deep Research frontend** — `POST /research/escalation-check`
  classifies a query without committing to it (persists a proposal only when the plan
  comes back `MODERATE`/`COMPLEX`, so accepting costs no second planner call). The Research
  UI got a full Deep Research destination: mode toggle, suggestion banner, plan review,
  live SSE-streamed progress (the canonical safe labels — "Planning research," "Searching
  selected sources," etc. — defined earlier but never actually consumed by any UI until
  now), report-approval, PDF download.
- **Cache-leakage fix** — synthesis and review generation calls were tagged
  `CacheRuntime.RESEARCH` (same `AUTO`/semantic-matched namespace as ordinary Linear
  Research answers), so a semantic-cache hit could have silently substituted report content
  generated for a *different* run's evidence bundle. Moved both to `CacheRuntime.REVIEWER`
  (`CachePolicy.NEVER`), regression-tested.

Verified: full repo suite **1286 passed**, ruff/mypy clean; frontend `tsc --noEmit`/
`next lint`/`next build` clean, plus an HTTP smoke test of the built page. **Not
verified at the time**: no browser automation was available in this environment, so
no actual manual click-through of the frontend flow had been performed — disclosed,
not hidden. **Superseded below** — a manual click-through was completed the same day.

## 2026-07-23 verification pass — browser click-through + worker session-staleness fixes

The manual click-through flagged as outstanding above was performed by hand at
`localhost:3000/research`: DEEP mode toggle → submitting a COMPLEX query → live
SSE progress through every canonical stage → the report-approval card → a
completed run with a working PDF download. The golden path works end to end in
a real browser, not just via API/test coverage.

This surfaced two real bugs invisible to the existing test suite (which always
constructs a fresh session per test), both stemming from
`apps/worker/research_runtime_main.py` holding one `AsyncSession` open for the
worker's **entire process lifetime**, combined with `SessionFactory`'s
`expire_on_commit=False` (`db/session.py`):

- **Aborted-transaction poisoning.** Any dispatch failure that aborted the
  session's transaction *before* its first commit (e.g. the disabled-V1-graph
  `RuntimeError` from the hardening pass above) left every subsequent dispatch
  on that same session failing silently — the worker had to be manually
  restarted to recover. Fixed: `ResearchRuntimeWorker.run_once` now calls
  `session.rollback()` in its failure path (`research_runtime_worker.py`,
  `bootstrap/worker.py`).
- **Stale identity-mapped `report_decision` read.** `execute_approved_run`'s
  resume-after-approval branch read `run.budget_usage` off a `ResearchRun`
  object the worker's session had already loaded earlier in that same run's
  lifecycle — before a separate, short-lived API-request session committed the
  approval decision. Since nothing ever invalidates a cached object under
  `expire_on_commit=False`, the resume attempt saw the pre-decision snapshot
  and failed with "awaiting a report decision that was never recorded," even
  immediately after approving. This is the same staleness hazard
  `ResearchRunRepository.is_cancellation_requested` was already written to
  guard against, just not applied here too. Fixed with
  `await self._session.refresh(run)` immediately after the worker loads the
  run, before any branch reads its fields (`execution.py`) — refreshing the
  object in place rather than a column-only re-read, since a later
  read-modify-write on `run.budget_usage` in the same method would otherwise
  silently re-drop the decision on its next commit.

Both fixes are regression-tested (`test_research_runtime_worker.py`,
`test_execution.py`), including a test that fakes `session.refresh` to
simulate a real DB refresh picking up the decision, proving the resume only
succeeds because that refresh happens. Full repo suite **1212 passed** after
these fixes. The underlying single-session-per-process design is a known,
tracked limitation (see "Not Yet Built" below, horizontal worker scaling) —
these are correctness fixes within that design, not a redesign of it.

## 2026-07-24 UX/reliability pass — visibility, citation accuracy, conversation
## continuity, refresh durability, non-destructive rejection, report preview/edit

The user hand-tested the Deep Research frontend verified end-to-end the day
before and reported seven concrete issues from actually using it. Six were
real gaps in the shipped flow (root-caused against the current code, not
assumed) and are now fixed; the seventh (Deep Research's synthesis/review
calls not being cached) turned out to already be the deliberate, correct
design from the 2026-07-23 cache-leakage fix above, and was left unchanged
with the reasoning explained back to the user rather than "fixed."

- **Progress-step log disappearing.** `DeepResearchBlock` only rendered the
  ordered event log while `stage === 'running'` — the moment a run reached
  `report_review`, `done`, or `failed`, the whole step history vanished from
  the UI even though the data was still there client-side. Fixed by
  rendering it (as a completed, non-pulsing log) in every post-`running`
  stage too. Frontend-only, `deep-research-block.tsx`.
- **PDF citations showing raw document UUIDs.** `_append_references` in
  `reporting/pdf.py` rendered `item.document_id` instead of `item.filename`
  in the References section — the two sibling call sites (the synthesis and
  review prompts) already used `.filename` correctly; this one node was the
  outlier. One-line fix, regression-tested (`test_report_artifact.py` now
  asserts a real filename appears in the extracted PDF text, not just a
  citation token — the old test's evidence bundle had no `evidence` items,
  so it couldn't have caught this).
- **Linear and Deep Research never sharing one conversation; History showing
  one row per question.** Root cause: `activeConversationId` lived only in
  `use-research.ts` and was only ever learned from *Linear* Research stream
  events — `useDeepResearch()` had no way to learn or contribute a
  `conversation_id`, so every Deep Research call (proposal, approval, or
  report-decision) that could reveal one just started a new
  `ResearchConversation` server-side, even though `ResearchRun`/
  `ResearchProposal`/`ResearchSession` all already FK to the same
  `research_conversations` table and always could mix freely. Fixed
  frontend-only: `useDeepResearch()` now accepts an `onConversationLearned`
  callback, invoked whenever a proposal/run response reveals a
  `conversation_id`, wired in `page.tsx` to the same `setActiveConversationId`
  Linear Research already used. No backend change was needed — the schema
  already supported this.
- **Deep Research state lost on refresh.** `GET /research/conversations/{id}`
  only ever returned `ResearchSession` rows (Linear turns) — a Deep Research
  run only produces one of those once it *completes*; an in-flight or
  awaiting-approval run had no representation there at all. Fixed: the
  response now also carries `deep_research_runs` (new
  `ResearchRunRepository.list_for_conversation` + a proposal lookup per run),
  and the frontend's new `hydrateFromConversation` reconstructs every Deep
  Research turn from it, re-subscribing non-terminal runs to the live event
  stream from cursor 0 (which replays full persisted history before
  following live, so the step log comes back too). The active conversation
  is now also synced into the page URL so a plain refresh — not just an
  explicit `?conversation=` link — finds its way back.
- **Report rejection destroying the synthesized content.** Previously,
  rejecting a report raised `ResearchReportRejectedError` inside the graph,
  which the execution service caught and marked the whole run `FAILED`,
  discarding a report that had already passed review. Fixed at the graph
  level: `await_report_approval` no longer raises on rejection — it returns
  a `report_decision`/`report_rejection_reason` state update, and a new
  `route_after_report_approval` conditional edge sends that straight to
  `END`, skipping only `persist_final_report` (the PDF-writing node).
  `draft`/`evidence_bundle`/`review` are plain, unreduced state channels
  already set by earlier nodes, so they survive regardless of which node the
  graph terminates at — `_finalize_or_pause`'s normal-completion path still
  runs, still calls `publish_runtime_report`. The run now lands on
  `COMPLETED_WITH_LIMITATIONS` with `terminal_reason=
  "report_rejected_returned_as_answer"` (new field on `ResearchRunResponse`),
  and the frontend renders the plain-text answer inline instead of a red
  "failed" card.
- **Report approval was blind.** There was no way to see, let alone edit,
  the report before approving or rejecting it — the draft only ever existed
  inside the LangGraph Postgres checkpoint while `AWAITING_APPROVAL`, with no
  endpoint exposing it. Added a new `ResearchDraftInspectionService` that
  reads a paused run's checkpoint directly (`channel_values["draft"]`/
  `["evidence_bundle"]`/`["review"]`) and a new `GET /research/runs/{id}/draft`
  endpoint built on it, resolving citations to filenames the same way the
  PDF fix above does. `ResearchReportDecisionRequest` gained an optional
  `edited_draft` (title/abstract/methodology/findings/discussion/conclusion
  only — citation ids/schema version/limitations are carried over from the
  original untouched, so an edit can never introduce an unsupported
  citation and needs no re-validation against the evidence bundle). On
  approval, `await_report_approval` overwrites `state["draft"]` with the
  merged edit before `persist_final_report`/`publish_runtime_report` read
  it, so an edit applies uniformly to both the PDF and the plain-answer
  path. The report-review card now shows the real draft with an in-place
  edit toggle instead of blind approve/reject buttons.
- **Caching in Deep Research (explained, not changed).** The user asked why
  Deep Research doesn't seem to cache. Confirmed by reading the code: this
  is the 2026-07-23 cache-leakage fix (D1) working as intended — synthesis
  and review calls deliberately use `CacheRuntime.REVIEWER`
  (`CachePolicy.NEVER`) specifically so a semantic-cache hit can never
  substitute prose written for a *different* run's evidence bundle into this
  run's report. Only Linear Research's answer generation is cached
  (`CacheRuntime.RESEARCH`, `AUTO`). No code change made.

Verified: full repo suite **1334 passed** (`pytest tests/`, no `-x` failures),
ruff clean across every touched backend path, frontend `tsc --noEmit`,
`eslint`, and a full production `next build` all clean. New backend tests
cover the citation-filename fix, the graph's new rejection routing (both the
happy path and the still-raising malformed-payload defensive case),
`record_report_decision` merging an edited draft (including the
same-finding-count guard), `ResearchDraftInspectionService`, and the new
`/draft` and extended `/conversations` endpoints (including the 409-when-
not-awaiting-approval case). The user then manually re-tested the full flow
in the browser and confirmed all six fixes work correctly.

## 2026-07-24 plan-approval interrupt — the same view/edit/reject-with-reason
## treatment report approval got, now for the earlier plan-approval checkpoint

The report-approval work above (`AWAITING_APPROVAL`, `await_report_approval`,
`GET /draft`, `report-decision`) deliberately left the *plan*-approval step
untouched — before this, a proposal could only be approved as-is or silently
abandoned, with no way to see gathered evidence or revise the goal before the
graph spent a synthesis call on it, and no reject-with-reason.

- **New graph checkpoint.** `await_plan_approval` (`interrupt()`, same pattern
  as `await_report_approval`) sits on a new node between `aggregate` and
  `synthesize` in `multi_wave_research.py` — reached once real evidence
  exists but before the costly synthesis call runs. Wired onto the
  `aggregate -> await_plan_approval -> synthesize` edge only: the automatic
  `REVISE_SYNTHESIS`/`RESEARCH_GAPS` repair-loop edges
  (`prepare_synthesis_revision`/`aggregate_gap_evidence -> synthesize`) still
  bypass it, so it's a human checkpoint once per run, not on every internal
  retry.
- **New lifecycle state.** `ResearchRunStatus.AWAITING_PLAN_APPROVAL`, with
  the same `{RESEARCHING, CANCELLED}` transition shape as `AWAITING_APPROVAL`.
  `execution.py`'s `_finalize_or_pause` now inspects which `interrupt()`
  payload (`{"kind": "plan_approval" | "report_approval", ...}`) a paused
  `ainvoke()` actually returned to route to the right status/event, instead
  of assuming report-approval unconditionally.
- **Inspection + decision endpoints.** `ResearchPlanInspectionService` reads
  the paused run's checkpoint directly (`channel_values["plan"]`/
  `["evidence_bundle"]` — no draft/review exist yet at this point) — same
  pattern as `ResearchDraftInspectionService`. `GET /research/runs/{id}/plan`
  exposes goal/rewritten_goal/complexity/tasks/evidence-summary/citations;
  `POST /research/runs/{id}/plan-decision` approves (optionally with an
  `edited_plan.rewritten_goal` — the *only* plan field still safe to change,
  since retrieval for `tasks` has already run and produced the evidence being
  reviewed) or rejects with a reason.
- **Rejection has no fallback answer, unlike report rejection.** A rejected
  *report* still has a synthesized draft to publish as a plain answer
  (`report_rejected_returned_as_answer`). A rejected *plan* has no draft at
  all — `synthesize` never ran — so `route_after_plan_approval` routes
  straight to `END` and the execution service marks the run `CANCELLED`
  (`terminal_reason="plan_rejected_by_user"`) rather than
  `COMPLETED_WITH_LIMITATIONS`. The gathered evidence isn't discarded (it's
  a plain, unreduced state channel that survives regardless of which node
  the graph ends at), it's just never turned into a report.
- **Expiry sweep widened.** `ResearchRunRepository.list_stale_awaiting_approval`
  now covers both `AWAITING_APPROVAL` and `AWAITING_PLAN_APPROVAL` so the new
  checkpoint doesn't introduce a second unbounded-wait blind spot alongside
  the existing (still-unwired-to-a-cron) one tracked as D5.
- **Frontend.** A new `goal_review` stage sits between `running` and
  `report_review` in `use-deep-research.ts`'s state machine, triggered by the
  same live SSE event stream (`research_awaiting_plan_approval`, no new
  connection needed). New `PlanGoalReview` component (mirrors `DraftReview`,
  but only the goal is editable — tasks/complexity are read-only since
  retrieval for them already ran).

Verified: full repo suite **1361 passed**, ruff/mypy clean across every
touched backend path, frontend `tsc --noEmit`/`eslint`/`next build` all
clean. New backend tests cover the graph's new interrupt (pause, edited-goal
resume, rejection routing, malformed-payload guard), `record_plan_decision`,
`ResearchPlanInspectionService`, and the new `/plan` and `/plan-decision`
endpoints (including the 409-when-not-awaiting-plan-approval case). Every
existing graph/execution test that previously invoked the graph straight
through to the report-approval interrupt now resumes past the new
plan-approval interrupt first — updated, not skipped.

## 2026-07-25 Web Search Tool Platform — third human-approval checkpoint

Deep Research can now search the public web via Tavily, gated by a third
`interrupt()` checkpoint that mirrors the plan-approval checkpoint exactly.
See ADR-036 and `RESEARCH_RUNTIME_IMPLEMENTATION_TRACKER.md`'s "Web Search
Tool Platform" section for the full breakdown; summary:

- **New platform**, `app/ai/tools/web_search/` — canonical models, provider
  interface/registry, `WebSearchService` (policy/budget/domain-filter/dedupe),
  a Tavily provider over raw `httpx` (no new SDK dependency). Framework- and
  LangGraph-independent, matching every other platform boundary in this repo.
- **No separate secure Web Fetch Platform** (PRD §14) in this pass — Tavily
  extracts page content server-side, so ResearchMind never fetches an
  arbitrary URL itself; there's no new SSRF surface to defend yet. Extracted
  text still passes through the existing Context Guardrails Platform
  (prompt-injection scan) before becoming evidence.
- **Reuses the existing bounded gap-research loop** instead of adding a
  parallel node family: `review`'s `RESEARCH_GAPS` decision (and a forced
  check on `REQUIRED` mode even when review passes) can now route through a
  web-search branch inside the same iteration/cost-budgeted loop
  `prepare_gap_research` already uses. A decline (or `DISABLED`, or the
  agent's own "no") falls back to that exact pre-existing node — not a
  separate compatibility path.
- **`AUTO` mode asks; `REQUIRED` never does.** The necessity decision itself
  is a small structured-output call pinned to a cheap OpenAI (`gpt-5-nano`)
  or Claude (`claude-haiku-4-5`, a new catalog entry) model — a dedicated
  registry, deliberately separate from the shared `GenerationRegistry` used
  for synthesis/review, so this one bounded decision's model choice never
  depends on the rest of the app's configuration. Falls through to the
  shared runtime via `RoutingStrategy.CLASSIFICATION` (never `AUTO`'s
  Groq default) if neither OpenAI nor Claude is configured.
- **New user-facing toggle**: `web_search_mode` (disabled/auto/required) +
  `web_search_auto_approve` (pre-authorize, skip the approval pause) on
  `ResearchProposalRequest` only — Linear Research (`/research`,
  `/research/stream`) and Chat have zero code changes and are unaffected by
  construction, not by a compatibility shim.
- **Frontend**: an Off/Auto/Required toggle + "skip approval" checkbox in
  the Deep Research composer (visible only in Deep mode), and a new
  `web_search_review` stage/approval card in `deep-research-block.tsx`
  mirroring the plan-approval card.

Verified: full repo suite **1397 passed** (31 new tests: web_search platform,
necessity decision, evidence normalization, and eight new/extended
`multi_wave_research` graph scenarios — disabled, AUTO decline, AUTO
approve-and-merge, pre-approved toggle, rejection fallback, malformed-payload
fallback, REQUIRED forcing, budget exhaustion), ruff/mypy clean on all 736
backend source files, frontend `tsc --noEmit`/`eslint`/`next build` all
clean. Both global (`WEB_SEARCH_ENABLED`) and per-request
(`web_search_mode=disabled`) default off.

### 2026-07-25, same day, later — real-run bug fix + early evidence-relevance detour

A real Deep Research run with web evidence crashed publishing its report:
`ResearchService._runtime_evidence_metadata` assumed every evidence item's
`document_id`/`chunk_id` was a real UUID, which broke on web evidence's
URL/`web:<uuid>` strings. Fixed with a deterministic `uuid5` fallback;
web citation markers also shortened from `web:<uuid>` to `W{round}-{n}`
(fixes a citation-card display bug the long form caused, matches the
app's `S1`/`S2` style).

Separately, the same run exposed a real product gap: a query entirely
outside the private corpus's topic (asking about climate change against a
knowledge base containing only a mental-health PDF) produced a synthesized
report on the wrong topic, with the mismatch only disclosed in prose in the
abstract — because the post-review gap-detection loop only fires *after* a
full synthesis pass, and a confidently off-topic corpus can still pass
citation-integrity review cleanly (review checks citation validity/coverage,
not subject-matter match). Fixed by routing through the existing
necessity-decision checkpoint *unconditionally*, right after evidence
aggregation and before plan approval, whenever `auto`/`required` is set —
so a topical mismatch is caught (and, in AUTO, asked about) before any
synthesis is spent on it. Rejected a numeric relevance-score threshold as
the detection mechanism first: `ResearchEvidenceReference.score` is a
Reciprocal Rank Fusion sum (rank-derived), not a semantic-similarity
measure, and can't reliably tell a confidently-wrong top hit from a
genuinely relevant one — see ADR-036's addendum. `REQUIRED` mode's forced
web round moved to this same early check (was a post-review-PASS check).

Verified: full repo suite **1401 passed**, ruff/mypy clean.

### 2026-07-25, same day, later still — AUTO mode model swap + Chat web search

Two more changes closed out this feature for the day:

- **AUTO's necessity-decision model swapped `gpt-5-nano` → `gpt-5-mini`.**
  Production logs showed `gpt-5-nano` unreliably following the
  structured-output contract for this one call (not truncation — genuinely
  invalid/non-repairable JSON, twice in a row) so `decide()` silently
  failed closed to "no search needed" every time, making AUTO mode appear
  broken end-to-end. `gpt-5-mini` is this app's already-proven default
  elsewhere; paired with a stricter JSON-only system prompt and higher
  `max_tokens`/`max_regeneration_attempts` (300→600, 1→2). See ADR-036's
  addendum.
- **Chat can now use web search too** (Linear Research explicitly excluded,
  per product decision). No approval checkpoint — Chat has no
  interrupt/resume mechanism, so a new `web_search_enabled` toggle on
  `ChatStreamRequest` *is* the approval, once, up front, for every turn.
  Reuses the same `WebSearchService`/`WebSearchNecessityService`/
  `normalize_web_search_result` Deep Research uses; new
  `app/ai/runtime/chat/web_search.py::run_chat_web_search()` (best-effort,
  degrades to no-op on any failure) and `ChatEventType`
  (`chat_web_search_started/completed/skipped`, `category=TOOL`) wired into
  both `stream_chat` (SSE) and `stream_chat_ws`. Frontend: a Web Search
  toggle in the chat composer, `use-chat.ts` handles the three new event
  types, and `message-bubble.tsx` renders a "Searching the web…"/"Searched
  the web" chip with clickable source-domain pills once results land. See
  ADR-036's addendum.

Verified: full repo suite **1410 passed** (8 new tests for
`run_chat_web_search`), ruff/mypy clean on all 1159 backend + test source
files, frontend `tsc --noEmit`/`eslint`/`next build` all clean. Chat's
toggle defaults off; Linear Research is untouched by construction (no
`web_search_enabled` field on its request/response schemas).

### 2026-07-25, same day, latest — citation web-source UI + composer label

Two small, frontend-only UX gaps surfaced from live user testing of the
above, once web search was actually reachable end to end:

- **A stale worker again explained an apparent AUTO-mode regression.**
  After deploying the Chat work, a Deep Research AUTO run appeared to
  repeat the original "didn't ask about web search" symptom. Diffed every
  file touched this session against the previous working state: none of
  `multi_wave_research.py`, `dependencies/research.py`, `bootstrap/
  worker.py`, or `execution.py` had changed. Worker logs (once restarted)
  confirmed the detour, necessity decision, and Tavily search all ran
  correctly (`web_search_evaluated mode=auto needs_web_search=True` →
  `web_search.service.search_completed` → evidence merged). Root cause was
  the same recurring gotcha as before: the worker process hadn't picked up
  the latest deploy. No code change.
- **Citations never showed which source a result came from.** Every
  citation surface (sidebar `CitationCard`, the plan-review "Sources found
  so far" chips, the report draft's "Sources" chips, and inline `[S1]`/
  `[W1-1]` answer markers) rendered document and web citations
  identically. Fixed client-side only, deriving from the citation-ID
  scheme the backend already sets (`S{n}` = document,
  `W{round}-{n}` = web, no backend change needed): a new
  `isWebCitation()` helper (`features/research/types.ts`), applied across
  `citation-card.tsx` (network icon + "Web" tag), `plan-goal-review.tsx`,
  `draft-review.tsx`, and `deep-research-block.tsx`'s rejected-report
  citation list (all get a blue/network-icon treatment instead of the
  default amber). Along the way, found and fixed a real bug in
  `research-block.tsx`'s inline-citation-marker regex
  (`CITATION_TOKEN`): it only matched `S\d+`, so a web citation marker
  like `[W1-1]` embedded in answer text rendered as plain unstyled text,
  not a chip, in the rejected-report fallback answer path.
- **The Deep Research composer's Off/Auto/Required toggle had no label**
  identifying it as web search — added a small "Web search" text label
  before the toggle group in `research-composer.tsx`, matching the
  existing "Model" label convention.

Verified: frontend `tsc --noEmit`/`eslint`/`next build` all clean
(backend untouched by this entry).

## 2026-07-25/26 Research Intelligence MCP Paper Search Platform — ResearchMind's first MCP client

**Not general-purpose MCP/multi-agent work.** ResearchMind became an MCP
**client** of exactly one external server, for exactly one tool
(`search_papers`), reachable from exactly two call sites. The Phase 6
Agentic AI Platform and Phase 7 MCP Ecosystem (a general MCP manager,
registry, multiple external servers, planner-driven capability routing) are
unaffected and remain deferred per ADR-033 — see ADR-037's own framing of
this distinction. See ADR-037 for the full decision record.

- **New platform**, `app/ai/tools/paper_search/` — mirrors
  `app/ai/tools/web_search/` file-for-file: canonical
  `PaperSearchRequest`/`PaperSearchResult` models, a
  `PaperSearchProviderInterface`, a `PaperSearchService`
  (policy/caching/normalization), a provider registry. No LangGraph or
  Chat-runtime imports — both runtimes depend on it, not the other way
  around.
- **`ResearchIntelligenceMCPProvider`** (`providers/mcp_client.py`) — the
  official `mcp` SDK's `streamablehttp_client` + `ClientSession`, a fresh
  connection per call (no persistent session; acceptable given both call
  sites fire at most once per Chat turn / Deep Research run). Only
  `search_papers` is wired; the other 6 tools the server exposes
  (`get_paper`, `get_paper_citations`, etc.) are explicitly out of scope.
  Auth is an optional static bearer token
  (`settings.mcp_papers_auth_token`) — no cached/refreshed JWT
  service-token provider, no retry-with-backoff, no 9-category error
  taxonomy (all part of a fuller PRD, `prds/1.researchmind_mcp_integration_prd.md`,
  explicitly deferred as a later hardening pass).
- **Caching** (`cache/`) — a Valkey-backed, fail-open, TTL cache keyed by
  `sha256(query|max_results)`, mirroring the query-embedding cache's shape
  rather than the Generation Runtime's L1/L2/L3 caching platform (wrong fit
  for a tool call's JSON result).
- **Chat**: `ChatStreamRequest.paper_search_enabled` (default off) mirrors
  `web_search_enabled` exactly — the toggle *is* the approval, once per
  turn. Deliberately **no** necessity-decision LLM call first (unlike Web
  Search's AUTO mode) — `run_chat_paper_search()`
  (`app/ai/runtime/chat/paper_search.py`) always searches when enabled,
  confirmed cheaper/simpler and avoids a second fragile-structured-output
  necessity surface after ADR-036 already hit that failure mode once.
- **Deep Research**: `ResearchProposalRequest.paper_suggestions_enabled`
  (default off, Deep-Research-only — never added to Linear Research's
  request schema). **Not a 4th approval checkpoint** — a new
  `suggest_related_papers` graph node runs sequentially between
  `persist_final_report` and `END`, wrapped in a broad `try/except` plus an
  `asyncio.wait_for` timeout on top of the provider's own timeout. The
  report is already durably persisted by the time this node runs, so a
  slow/broken MCP server can never hold report delivery hostage — any
  failure (disabled, unconfigured, empty result, exception) emits
  `RESEARCH_RELATED_PAPERS_SKIPPED` and the run reaches `END` exactly as it
  would have without the feature; success emits
  `RESEARCH_RELATED_PAPERS_COMPLETED` carrying up to 5 suggested papers
  (title/authors/year/url) directly in the event's metadata.
- **Query distillation, not raw prompt/goal.** Confirmed live (2026-07-25)
  that both a raw conversational Chat prompt and Deep Research's
  `rewritten_goal` (a full sentence/question, not a topic phrase) return
  zero results from `search_papers`. Both call sites now distill through
  `PaperQueryExtractionService` (`app/ai/runtime/chat/paper_query.py`) first,
  falling back to the raw text if extraction is unavailable or fails.
- **`LangGraphResearchEventAdapter.progress()` gained an opt-in
  `extra_metadata` param** — every other Research Runtime event carries
  only a stable `{"label": ...}` payload by design (internal node
  names/task questions/evidence excerpts never cross this boundary, per
  ADR-032/ADR-036); surfacing the actual paper list needed one narrow,
  additive exception. Default `None` leaves all ~15 existing call sites
  unaffected.
- **Frontend**: the SSE event log needed almost no new plumbing — it
  already generically logs `{type, label, timestamp}` for any event, so the
  three new event types render automatically. Only the paper list itself
  needed new code: a `DeepResearchTurn.relatedPapers` field and a small
  read-only card rendered after the report completes (no approve/reject
  controls — there's no checkpoint to decide on). Chat gained a
  `PaperSearchStatus` chip in `message-bubble.tsx` and a toggle in the
  composer, alongside the existing web-search toggle.
- **Session-state-updater fix, same session** (Memory Platform,
  `app/ai/memory/session/state_updater.py`) — a real production bug: a
  Deep Research follow-up using a pronoun ("so how is magma related to
  it?") had no durable session-level "what is this about" state to resolve
  against, since the old `state_from_user_turn`'s narrow trigger-phrase
  gate never captured ordinary topic drift. A new
  `SessionStateUpdaterService` asks a cheap model to maintain one evolving,
  ≤300-character sentence describing the session's current subject after
  every turn, upserted in place via a new
  `MemoryService.get_latest_session_state()` (tag lookup by
  `metadata["kind"]`, not appended as a growing pile of snapshots). Mirrors
  `MemoryExtractionService`'s shape (Generation Runtime call, structured
  output, fail-open), not the dedicated-cheap-model-registry pattern
  `WebSearchNecessityService`/`PaperQueryExtractionService` use — this is
  Memory-Platform-native work, so it follows that platform's own
  composition precedent instead.

Enabling paper search requires both `MCP_PAPERS_ENABLED` and
`MCP_PAPERS_SERVER_URL`; either being absent degrades
`PaperSearchService.available` to `False` and both surfaces silently no-op.

## Not Yet Built

- ❌ Web Search Tool Platform's standalone SSRF-hardened Web Fetch Platform,
  multi-provider fallback (Exa/Brave/MCP), org-wide domain policy
  management, and dedicated evaluation/benchmark harness — deferred per
  ADR-036; not needed while Tavily's own content extraction is the only
  search path.
- ⛔ Chat → Deep Research escalation ("Research this" suggestion + handoff) — **out of
  scope, will not be built.** The Research-interface equivalent (Linear → Deep) is built
  and is a distinct surface (see above); Chat is intended to stay a standalone fast
  conversational surface with no path into Deep Research.
- ✅ Horizontal worker scaling — **fixed 2026-07-24, this bullet was stale, corrected now.**
  `research_runtime_main.py` runs `settings.research_runtime_worker_concurrency` concurrent
  claim lanes in-process (each its own DB session), and the claim query
  (`SELECT ... FOR UPDATE SKIP LOCKED`) already made running more copies of the process safe
  too. Global load-shedding (`deep_research_max_queued_runs`, `503`+`Retry-After` on
  `/proposals/{id}/approve`) bounds the queue depth either way. Residual: both are static
  config, not autoscaling.
- ✅ Expiry/auto-reject for a run stuck in `awaiting_approval` — **fixed 2026-07-24
  (commit `95a6c8c`), this bullet was stale, corrected now.**
  `ResearchRunService.expire_stale_awaiting_approval()` auto-cancels (not auto-approves) any
  run left at `AWAITING_APPROVAL`, `AWAITING_PLAN_APPROVAL`, or `AWAITING_WEB_SEARCH_APPROVAL`
  past a 72h TTL (`research_runtime_awaiting_approval_ttl_hours`), genuinely scheduled via
  `ResearchRuntimeWorker`'s own poll loop (piggybacked, at most once/hour) rather than a
  separate cron process — wired in `app/bootstrap/worker.py::create_research_runtime_worker()`.
- 🟡 The Research UI's default (Linear-mode) submission path now waits on a full
  escalation-check planner call before running Linear Research — a deliberate, requested
  tradeoff, not a bug, but it means the UI's "fast path" is slower than the raw
  `POST /research` API. Parallelizing instead of gating is a documented follow-up.
- ❌ General-purpose MCP ecosystem (MCP manager/registry, multiple external servers, planner-driven capability routing) and multi-agent orchestration (Phase 6/7) — explicitly deferred per ADR-033 until the single-agent runtime proves a measurable limitation it can't address. Not affected by the narrow MCP **client** integration added 2026-07-25/26 for paper search (ADR-037, one server, one tool, two call sites) — see the section above; that work does not start Phase 6/7.

---

# Current Production Knowledge Pipeline

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

Indexing (dense + sparse)

↓

Qdrant (hybrid — dense + sparse vectors, same collection)

↓

Retrieval (dense + sparse + hybrid RRF fusion, metadata-filtered, owner-scoped, parallel dense+sparse execution)

↓

Reranking (optional, Voyage AI by default for hybrid)

↓

Context Platform (parent expansion, adjacent merge, compression, guardrails, citations, prompt formatting)

↓

Routing Platform (task-based strategy → scored model catalog → provider + fallback chain)

↓

Generation Platform (native structured output → parser fallback → input/output/hallucination validation → regeneration)
```

Now wired into the pipeline above: the Guardrails Platform (`app/ai/guardrails/`, Milestone 11.16) — input/retrieval/generation checks run automatically inside `GenerationService`/`ContextBuilderService` (see Milestone 11.16's "Integration" subsection); only `evaluate_runtime()` still has no live caller — the new `/research` API (Phase 4) is deliberately linear with no reasoning/tool loop for it to guard.

---

# Current Project Status

| Phase | Status |
|--------|--------|
| Phase 1 — Identity Platform | ✅ Complete |
| Phase 2.1 — Upload Platform | ✅ Complete |
| Phase 2.2 — Processing Platform | ✅ Complete |
| Phase 2.3 — Chunking Platform | ✅ Complete |
| Phase 2.4 — Embedding Platform | ✅ Complete |
| Runtime Metrics Foundation | ✅ Complete |
| Observability Platform | 🚧 Deferred |
| Phase 2.5 — Vector Store Platform | ✅ Complete |
| Phase 2.6 — Indexing Platform (Hybrid Retrieval) | ✅ Complete |
| Phase 2.7 — Retrieval Platform | ✅ Complete (incl. Metadata Filtering + Reranking + 3-way Parallel Retrieval [dense+sparse+metadata via `asyncio.gather`] + genuinely end-to-end Parent/Child retrieval) |
| Phase 2.8 — Context Platform | ✅ Complete (Parent Expansion, Adjacent Merge, Compression V1-V4, LangChain compression wired into `build()`'s default pipeline, Guardrails V1, Citations, Prompt Formatter — Phase 3.7, `context_platform_complexion_prd.md`) |
| Phase 2.9 — Generation Platform | ✅ Complete, per `generation_platform_complexion_prd.md` (Structured Output Integration, Validation Platform integration incl. input/output/hallucination/runtime validators + scoring + five runtime contracts, a Validation Policy Layer, every PRD output validator, Regeneration, Prompt Platform bridge, Routing Platform, Runtime Caching Platform, Streaming Platform (SSE+WS chat, wired), Runtime Metrics Integration, Artifact Platform (generation results persisted incl. metrics.json) done) |
| Milestone 2.9.12 — Generation Runtime Platform | ✅ Complete, per `generation_runtime_platform_prd.md` (thin orchestration layer, `execute_generation()` canonical entrypoint, no new generation behavior) |
| Milestone 11.16 — Guardrails Platform | ✅ Complete (MVP Foundation — input/retrieval/generation/runtime guardrails, Source Trust, policies, scoring, artifacts) + ✅ Integrated into `GenerationService`/`ContextBuilderService` (runtime stage still has no live caller) |
| Milestone 3.10 — Artifact Platform | ✅ Generation/Streaming/Conversation/Research artifacts complete and wired (`GenerationService`, `StreamingService`, `chat.py`, `ResearchService`) — 🟡 Session/Agent/Evaluation artifacts built but scaffold-only (no runtime exists yet to call them) |
| Phase 4 — Research API Platform | ✅ Complete, per `research_api_prd.md` — ResearchMind's first live, end-to-end product surface: `POST /research`, `/research/stream`, `/research/citations`, `GET /research/{id}` |
| Phase 4.1 — Research Frontend Integration | ✅ Complete — `apps/web`'s Research page wired to the live API (real SSE via `use-research.ts`/`lib/sse.ts`, `mock-engine.ts` deleted); 3 backend bugs found + fixed along the way (stream-completion event-type mismatch, retired Claude model, `temperature` rejected by the new model) |
| Benchmark Platform | ✅ Foundation Complete (incl. Retrieval, Metadata Filtering, Reranking, **Generation**, and **Regression Detection**) — see "Evaluation Platform PRD Reconciliation" above |
| Milestone 12 — Memory Platform | ✅ Core complete; M0-M2/M4-M12 implemented with operational rollout pending — including the safe scope-aware management API, explicit edits/moves, per-scope settings, and cross-tenant tests. M3 rollout, M6-M10 calibration, M13 Project UI, and Project-product activation remain pending. |
| Milestone 2.9.7 Addendum — Routing AUTO Default | ✅ Complete — `RoutingStrategy.AUTO` now hard-defaults to Groq instead of the scoring engine's own top pick; all other strategies unaffected |
| Phase 4.2 — Chat Surface Frontend Integration | ✅ Complete — separate `/chat` surface with live SSE and server-backed conversation list/replay; both stream completion event variants persist turns, replay is deterministic user → assistant, and Groq titles are derived from the first user question with full-title tooltips |

---

# Recently Completed

✅ Evaluation Worker Expired-ORM Error Handling — fixed the online scoring
job's row-failure path so it snapshots `generation_id` before transaction
work. Failed commits or scoring operations can expire SQLAlchemy ORM rows; the
old logger then triggered implicit async I/O and masked the real error with
`MissingGreenlet`. The worker now preserves and logs the original row error,
rolls back safely, and continues polling. The online-scoring job suite passes
(30 tests) and focused Ruff checks pass.

✅ Scope-aware Memory Management API (M12) + Personal/Project UI (M13 complete)
— the API now enumerates all canonical durable types with scope/project/type/
source/date/origin filters and returns a safe projection without owner IDs or
raw metadata. Scope authorization precedes storage for every mutation; edits
are explicit and audited, vector-backed edits re-index, moves require
confirmation and validate both scopes, and capture/retrieval settings are
independent from retention. Real PostgreSQL tests cover two users and two
projects. The first-class
`/memory` navigation destination backed by authenticated, owner-scoped
`GET /memory`. The API performs stable newest-first pagination, case-insensitive
content search, feedback-source filtering, and returns accurate filtered
totals. Users can review durable USER memories, edit them inline through the
existing bounded mutation path, and delete them through a product-native
confirmation dialog. The UI includes responsive summary cards, debounced
server-side filtering, pager controls, race-safe request handling, and useful
loading/error/empty states. Project Memory is visibly disabled rather than
simulated; M5 now provides its scope/authorization foundation, while the
Project/workspace runtime and UI activation remain. Focused API tests
pass (9), alongside Ruff, mypy, frontend TypeScript, and diff checks.

✅ Cost Ledger, Runtime Categorization, Cache Accounting, and Memory-Provider Resilience — added the owner-scoped PostgreSQL `generation_usage` ledger and authenticated usage summary, then wired the dashboard to display actual monthly/all-time estimated cost instead of hardcoded values. Every completed owner-owned Chat, Research, title-generation, and memory-extraction request is recorded idempotently with provider/model/tokens/cost/cache/stream metadata. New rows are explicitly categorized as `chat`, `research`, `conversation_title`, or `memory_extraction`; earlier ledger rows cannot be safely reclassified automatically and may remain `NULL`. Cache replays are covered by regression tests and persist as `cache_hit=true` with zero incremental provider cost. Research now opts into the safe exact-then-semantic cache profile: it can reuse an answer only when the complete effective prompt and context match, preserving correctness for follow-up turns. Memory extraction now uses low-cost Groq first and retries with OpenAI when Groq fails; the JSON-output instruction and OpenAI temperature retry address provider-specific 400 errors found in live testing. Qdrant-backed document statistics now power dashboard chunks/embeddings rather than hardcoded estimates. Remaining memory efficiency work is tracked above rather than silently changing retrieval or extraction behavior.

✅ Chat Conversation History + Reliability Follow-up — Chat history is now account-backed: `GET /chat/conversations` returns owner-scoped summaries and `GET /chat/conversations/{conversation_id}` replays an owner-scoped thread, so the sidebar can reopen conversations after reload or on another device. The stream route now treats both `complete` and live-provider `completed` terminal events as completion, fixing the case where sidebar rows existed but messages were never persisted. Message persistence and replay establish deterministic user → assistant ordering even when database timestamps tie. A low-cost Groq title is generated strictly from the persisted first user question through a database-backed lease: one successful title per conversation, no repeated calls on later turns, safe retry after failure, and no concurrent overwrite. The sidebar truncates visually but exposes the full title through a native tooltip and accessible label. Focused chat integration tests (6), `ruff`, `mypy`, and frontend TypeScript checks pass.

✅ Chat Pagination + Prompt-Context Compaction — Chat replay no longer silently stops at a fixed history slice. Owner-scoped conversation and message endpoints accept cursor pagination (default page size **50**, hard maximum **100**) and return `next_cursor`; the UI can explicitly load earlier conversations/messages. Canonical PostgreSQL message rows are retained. Before a Chat generation, a deterministic, persisted rolling summary represents older turns while the newest **12** messages remain verbatim; the summary is capped at **4,000 characters** and prioritizes explicit user interests, preferences, and decisions. This is intentionally zero-provider-cost: it is not an LLM summarization call and does not add generation latency or usage-ledger spend. The additive migration `d9e2f4a6b8c0` adds the summary/boundary fields. Focused pagination/compaction tests passed (**8**), alongside backend lint/type checks and frontend type checking. ADR-030 records the defaults, behavior, trade-offs, and future real-traffic tuning criteria.

✅ Memory Platform (Milestone 12, per `memory_platform_prd.md`) + wired into Chat and Research, two Generation Platform bugs fixed, Routing AUTO default changed to Groq — a new `app/ai/memory/` package (Session→Valkey, User/Semantic/Research→Postgres+Qdrant, a `MemoryService` orchestrator, `/memory` API) built to the PRD, then extended same-session against a user-supplied 5-pipeline architecture review (Reciprocal Rank Fusion search — fixed a real bug where results were sorted by importance alone, discarding Qdrant relevance ranking; LLM-driven extraction via `MemoryExtractionService`; a lifecycle sweep that was unscheduled at that milestone and is now superseded by the M3 recurring worker) and wired into `ResearchService` via Runtime Memory Injection. A further same-day follow-up wired the identical pattern into `chat.py` (both `/chat/stream` and `/chat/ws`) — which required first fixing a Generation Platform bug that turned out to be a **total, unconditional outage of every chat message on every account** (`GenerationService._validate()` hard-rejected `chat.py`'s always-empty `PromptContext.context`, since chat has never wired retrieval), originally reported as a narrower zero-document edge case. A second, independent bug (`GenerationRequest.output_model` couldn't be JSON-serialized for artifact persistence, failing open/silently) was fixed alongside it. Separately, `RoutingStrategy.AUTO` now hard-defaults to Groq instead of the scoring engine's own top pick (previously claude-sonnet-5 almost always), via a new `RoutingService._select_for_strategy()`; every other strategy is unaffected. Fixing the memory/chat wiring surfaced 3 test failures in the repo's real `tests/` suite (2 integration fakes needed for the new `MemoryService`/`MemoryExtractionService` dependencies, 1 unit test asserting the since-removed empty-context rejection) — all fixed; full suite (1160 tests), ruff, and mypy pass clean. See Milestone 12 and the Milestone 2.9.7 Addendum above for full detail, including a process note on a live-smoke-testing misstep corrected mid-session.

✅ Parent/Child Retrieval + 3-way Parallel Retrieval — closed the last two tracked Retrieval Platform gaps. **Parent/Child Retrieval**: a new `HierarchicalChunkingProvider` (`apps/api/app/ai/knowledge/chunking/providers/hierarchical.py`) uses LangChain's `RecursiveCharacterTextSplitter` in two passes (parent sections, then child chunks per parent) — children carry `structure.parent_chunk_id`; parents are tagged `is_parent` and excluded from embedding/indexing by `EmbeddingService`, but persisted in the `ChunkArtifact` for the Context Platform's `ParentExpansionService` to resolve against. This was the missing producer half — the consumer half (expansion) had existed for a while with zero real data to expand. **Parallel Retrieval**: `RetrievalService.search_hybrid()` grew from a dense+sparse 2-way `asyncio.gather()` to a genuine 3-way one — a new `QdrantRetrievalProvider.search_metadata()` (filter-only Qdrant `scroll()`, no vector similarity; short-circuits to empty with no filters, since an unfiltered scroll would ignore `owner_id` tenant scoping) is now fused in by RRF alongside dense and sparse, with `RetrievalStatistics.metadata_latency_ms` tracked alongside the existing dense/sparse latencies. New/updated tests: hierarchical chunking integration test, `EmbeddingService` parent-exclusion unit test, `RetrievalService`/`QdrantRetrievalProvider` unit tests for the metadata branch, and a new `fusion/test_rrf.py` covering 3-way RRF fusion. Full affected-suite runs, `ruff`, and `mypy` all pass clean.

✅ Generation Benchmark Cost Metrics — added `avg_cost_usd`, `cost_per_query`, and `cost_per_1k_queries` to the Generation Benchmark (`benchmarks/generation/benchmark.py`), reading directly off `GenerationResult.statistics.estimated_cost_usd` (already computed from real per-model pricing in `apps/api/app/ai/runtime/generation/catalog/models.py`, already flowing through every `GenerationService.generate()` call, but never previously surfaced by any benchmark). All three metrics registered in `benchmarks/regression/thresholds.py` at the same 25% relative-increase threshold as latency, so a cost regression (e.g. an accidental model-tier change) now fails `--check-regression` the same way a latency regression does. Verified live: Groq $0.16/1k queries, OpenAI $0.25/1k, Claude $3.76/1k for the 13-query dataset — a ~24x spread that now shows up directly in the provider comparison table. While validating this, also diagnosed and cleaned up a false "regression" from the prior session: two ad-hoc Generation Benchmark dev runs (no code change between them) had been diffed against each other, producing spurious relevance/completeness/latency violations from LLM sampling non-determinism and provider latency jitter — not a real defect. Deleted the stale `regression.json`/`regression_report.md` and replaced with a clean single-run `report.json` baseline.

✅ Evaluation Platform PRD Reconciliation + Generation Benchmark + Regression Detection — `evaluation_platform_prd.md` asked for a new `app/ai/evaluation/` platform; investigation found it would have duplicated the already-real `benchmarks/` package (Engineering Benchmarks) and the already-live AI Runtime Observability Platform (Runtime Evaluation), and forked the separately-designed, not-yet-built Experimentation Platform. Built only what was genuinely missing, directly into `benchmarks/`: a **Generation Benchmark** (`benchmarks/generation/`, deterministic no-LLM faithfulness/groundedness/relevance/completeness/citation-accuracy/hallucination-rate scoring across every configured `GenerationProvider`, a new hand-written 13-query dataset) and **Regression Detection** (`benchmarks/regression/`, threshold-based pass/fail vs. the previous `report.json`, wired into `runner.py` via `--check-regression`, non-zero exit on failure). Also wired the pre-existing-but-unused `ndcg_at_k` into the Retrieval Benchmark's reported metrics. Verified live end-to-end against real Groq/OpenAI/Claude traffic and real Qdrant/Voyage retrieval — found and fixed a real bug along the way (`citation_accuracy` was structurally always 0.0 because the benchmark told the model to cite a filename it was never given; fixed by tagging the context with `[Source: <filename>]`) and confirmed the regression detector both catches real drift and passes cleanly on an unchanged rerun. See the Engineering Benchmark Platform section above for full detail. `mypy`/`ruff` clean across `benchmarks/` (35 files)

✅ Research Frontend Integration (Phase 4.1) — `apps/web`'s Research page is wired to the live `/research`/`/research/stream` APIs for the first time, replacing the placeholder `mock-engine.ts` (deleted) with a real `use-research.ts` hook + `lib/sse.ts` SSE client, a new `citation-card.tsx` component, and matching updates across the research feature's components/types/API client. Turning this on against live infra surfaced and fixed three real backend bugs: (1) `ResearchService.stream_research()` only recognized `CoreEventType.COMPLETE` as "stream finished," missing the `StreamEventType.COMPLETED` value live provider streams actually emit — every real (non-cache-hit) research turn silently never persisted its `research_sessions` row; (2) `claude-sonnet-4`/`claude-sonnet-4-20250514` have been fully retired from the configured Anthropic account (confirmed via `GET /v1/models`) — every hardcoded reference across settings/config/catalog/prompts/token-counter updated to `claude-sonnet-5`; (3) `claude-sonnet-5` rejects the `temperature` parameter outright as an effort-based reasoning model — `ClaudeProvider` now retries once without `temperature` on that specific 400 rather than hardcoding a model-name list. See Phase 4.1 above for full detail, findings, and open to-dos (no frontend Chat surface yet; SSE error path not fully hardened; no automated model-deprecation check).

✅ Research API Platform (Phase 4, per `research_api_prd.md`) — **ResearchMind's first live, end-to-end product surface**: a user can upload documents, ask a question, and get a grounded, cited, streamable answer back. New `apps/api/app/api/v1/research.py` (`POST /research`, `/research/stream`, `/research/citations`, `GET /research/{research_id}`, all auth-required and owner-scoped) and a new `ResearchService` (`apps/api/app/ai/research/service.py`) that composes the Retrieval Platform (hybrid search + rerank), Context Platform (dedup/expand/merge/compress/cite), Generation Runtime Platform (its first real caller), Streaming Platform (for the streaming route), and best-effort Artifact persistence — adding no new retrieval/context/generation logic of its own, per the PRD's Non-Goals (no query decomposition, no research planning/multi-step loops, no agents, no LangGraph; a Research Runtime, Deep Research Runtime, and Agent Platform are named as future milestones). New `ResearchSession` Postgres table (`app/models/research.py`, `research_sessions`, migration `37117c83beb2`) is the live read path for replay; `ResearchRepository`/`research` schemas/`dependencies/research.py`+`dependencies/context.py` round out the wiring. Every request sets `runtime=RuntimeType.RESEARCH`/`artifact_runtime=ArtifactRuntime.RESEARCH` — the first live code exercising either enum value, and the first live caller of the previously scaffold-only Research Artifact writer (see Milestone 3.10). 23 new tests (`tests/unit/ai/research/`, `tests/integration/test_research_repository.py`, `tests/integration/ai/test_research_api.py`); full repo suite (1068 tests), ruff, and mypy pass clean; migration verified to round-trip

✅ Generation Runtime Platform (Generation Platform Milestone 2.9.12, per `generation_runtime_platform_prd.md`) — a thin orchestration layer, `apps/api/app/ai/runtime/generation/orchestration/`, giving every future caller one canonical entrypoint, `execute_generation()`, into the already-complete `GenerationService.generate()` flow instead of reaching into `GenerationService` directly. Re-implements nothing: `GenerationRequest`/`GenerationResult` and the full frozen execution ordering (validation → guardrails → routing → cache → provider → structured outputs → guardrails → validation → runtime validation → metrics → artifacts) were already done. Adds `GenerationExecutionContext` (trace id, timing, provider/routing/cache/validation/guardrail summaries), `GenerationExecutionState` (context + request + result/failure), a `GenerationRuntimeInterface` ABC, and the `GenerationRuntime` orchestrator that mints the context, delegates to `GenerationService`, and folds the outcome back in for tracing. New `get_generation_runtime()` FastAPI dependency. Had no real caller until the Research API Platform above. 11 new unit tests under `tests/unit/ai/runtime/generation/orchestration/`

✅ Generation Platform Completion (Phase 3.8, per `generation_platform_complexion_prd.md`) — closes out the Generation Platform at 100% (see Milestone 2.9.11 above for full detail). Six deliverables: (1) **Runtime Contract Expansion** — `PlannerRuntimeContract`, `ReviewerRuntimeContract`, `AgentRuntimeContract`, `MCPRuntimeContract` join the pre-existing `ResearchRuntimeContract`, plus a new `DependencyValidator` (cycle detection for step dependencies) and a generalized `ConsistencyValidator` (configurable field names, reused by MCP instead of a bespoke check); all five remain registered-but-dormant until a `/research` API sets `GenerationRequest.runtime`. (2) **Validation Policy Layer** — `AcceptancePolicy`/`FailFastPolicy`/`RuntimeValidationPolicy` (`generation/policies/`), wired into `GenerationService` with unchanged default regeneration behavior; a new pre-flight `_enforce_fail_fast_input_validation()` runs input validation before guardrails/routing/provider. (3) **Remaining Output Validators** — `FormattingValidator`, `ResponseSizeValidator`, and top-level `CompletenessValidator`/`ConsistencyValidator` (thin delegates to the existing runtime validators), registered in the PRD's pipeline order. (4) **Runtime Metrics Integration** — `GenerationMetricsService`/`GenerationMetricsSnapshot` (`generation/observability/`), new Prometheus-ready counters (`infrastructure/metrics/generation.py`), and `generation.started/failed`/`validation.started/completed`/`provider.started/completed` structlog events. (5) **Artifact Completion** — `GenerationArtifact` now always persists a `metrics.json` snapshot. (6) **Flow Activation** — metrics recording now runs before artifact persistence, matching the target execution flow. Caught and fixed a real bug along the way: `write_json_artifact`'s `exclude_none=True` serialization silently requires an explicit `= None` default on every optional artifact-model field, or read-back fails validation. ~40 new test files/cases; full repo suite (1034 tests), ruff, and mypy pass clean

✅ Context Platform Completion (Phase 3.7, per `context_platform_complexion_prd.md`) — closes out the Context Platform at 100%. Two deliverables: (1) **LangChain compression wiring** — `ContextBuilderService.build()` now takes an optional `query: str | None = None`, threaded into every `CompressionRequest` it builds (embedding-redundancy, the new LangChain stage, token-budget); a new `CompressionStrategy.LANGCHAIN_CONTEXTUAL` stage runs between embedding-redundancy and token-budget, gated by a new `settings.enable_langchain_compression` flag (currently defaults to `True`, but stays a flag rather than unconditional since it's an LLM call requiring an API key) and only when a `query` was actually passed. (2) **LLM Compression Provider (V4)** — `LLMCompressionProvider` is no longer a `NotImplementedError` stub: it calls `GenerationService.generate()` once per chunk (reusing the Generation Platform, no direct provider calls) asking for a concise, query-relevant summary, controlled by a new `LLMCompressionConfig` (`provider: GenerationProvider = GROQ`, `max_tokens: int = 300`, `temperature: float = 0`). Unlike the LangChain provider (which drops irrelevant chunks), V4 never drops a chunk and falls back to that individual chunk's original content — not the whole batch — on a per-chunk failure, empty summary, or blank input; every field but `content` survives via `chunk.model_copy()`. Registered in `create_compression_service()` but intentionally not wired into `build()`'s default pipeline, matching the PRD's narrower scope for V4 ("provider implemented" vs. V3's "wired into default pipeline"). `LLMCompressionProvider`'s `GenerationService` dependency is lazily constructed on first use (mirrors `LangChainCompressionProvider`'s lazily-built LLM) — eager construction at `create_compression_service()` time was tried first and surfaced a latent, pre-existing bug: `TokenCounter.__init__` unconditionally builds a `genai.Client()`, which raises without `GEMINI_API_KEY` configured; no code path had called `create_generation_service()` directly before this, so it was previously dormant. 24 new/changed unit tests (13 for `LLMCompressionProvider`, mocked `GenerationService.generate()`, no network calls; the rest covering `ContextBuilderService`'s new query/LangChain wiring); full repo suite (911 tests), ruff, and mypy pass clean

✅ Guardrails Platform Integration (per `guardrail_integration_prd.md`) — wired the already-complete Guardrails Platform (Milestone 11.16) into the two live composition roots, introducing no new registries/interfaces/services. `GenerationService` gets an optional `guardrail_service`: `evaluate_input()` gates every `generate()`/`stream_generate()` call before the provider runs, and the full `evaluate()` report lands on a new `GenerationResult.guardrails` field before `ValidationService` runs. `ContextBuilderService` gets an optional `guardrail_platform_service`: `evaluate_retrieval()` gates the raw retrieved chunks before dedup/expansion/compression. `GuardrailService.evaluate()` now persists artifacts via the pre-existing `GuardrailArtifactWriter` (best-effort) and emits `guardrails.started/completed/blocked/failed` events plus six new Prometheus-shaped counters through the same `MetricsRecorder` interface the Upload platform already used. 14 new unit tests; full repo suite (854 tests), ruff, and mypy pass clean

✅ Runtime Validation Platform (Generation Platform Milestone 2.9.4 extension, per `runtime_validation_prd.md`) — a fourth `ValidationStage.RUNTIME` stage added to the existing Validation Platform, not a separate platform: `generation/validation/runtime/` (`RuntimeType` enum + new `GenerationRequest.runtime` field, `RuntimeRegistry`/`RuntimeValidationService` keyed by `RuntimeType`, five generic reusable validators — completeness, consistency, confidence, evidence, citation — and the first concrete contract, `ResearchRuntimeContract`, composing them into one `ValidatorOutcome` tagged `"research_contract"`). `ValidationRegistry`/`ValidationService` extended (`register_runtime_validator()`/`register_runtime_contract()`, `runtime_validators`, `validate_runtime()`) rather than duplicated; `ValidationService`'s duplicate crash-handling/aggregation logic across stages was extracted into a shared `aggregation.py` in the process. `compute_overall_score()`'s pre-existing `runtime_score` weight (0.20) now actually gets fed. No caller sets `GenerationRequest.runtime` yet (needs a `/research` API), so the stage is a no-op in production today — exercised only by the 109 new unit tests. Full repo suite (840 tests), ruff, and mypy pass clean

✅ Streaming Platform (Generation Platform Milestone 2.9.10, per `streaming_platform_prd.md`/ADR-028) — Runtime Event Platform (`runtime/events/`: canonical `StreamEvent`, layered event-type model so future runtimes never touch shared code, one shared `GenericStreamChunkAdapter`) + Generation Streaming Platform (`generation/streaming/`: `GenerationService.stream_generate()`, `StreamingService` with cache-hit replay and cache-store-on-complete, SSE transport with heartbeat/timeout-ceiling, WebSocket transport), wired into a new `POST /api/v1/chat/stream` + `/api/v1/chat/ws` (previously an empty, unregistered `chat.py`). Required a new Conversation/Message persistence layer (models, repository, service, migration) since chat needed multi-turn history. Fixed a real bug found during the work: `CachingService` unconditionally bypassed the cache for every streaming request; now streaming participates in caching like any other request, with the hit-replay decision moved to `StreamingService`. Also fixed self-contradictions in the PRD/ADR-028/architecture docs (a flat event-type enum vs. the docs' own layered model, inconsistent `StreamEvent` field counts) before implementing. 24 new unit/integration tests; full repo suite (828 tests), ruff, and mypy pass clean

✅ LangChain Compression Provider (Context Platform Milestone 2.8.3, V3, per `langchain-compression-prd.md`) — query-aware compression via `ContextualCompressionRetriever` + `LLMChainExtractor` (`langchain-classic`, added as a new dependency now that these classes live outside core `langchain` 1.x). Extends the pre-existing compression scaffold (`interfaces.py`/`create.py`/`registry.py`) rather than the PRD's literal `base.py`/standalone-provider file layout, since that scaffold was already production-wired into `ContextBuilderService`. Metadata/citations preserved via `chunk.model_copy()` keyed by `chunk_id`; a new `exceptions.py` (`CompressionError`/`CompressionProviderError`/`CompressionTimeoutError`) backs a new fallback path in `CompressionService.compress()` — a provider failure now returns the original chunks instead of breaking generation. `providers/llm.py` (V4) intentionally left unimplemented. 12 new unit tests (LangChain's own `FakeListChatModel`, no network calls) plus fallback/exception-hierarchy tests

✅ Runtime Caching Platform (Generation Platform Milestone 2.9.9, per `runtime_caching_platform_prd.md`/ADR-027) — L1 Exact Cache (Valkey-backed), L2 Semantic Cache (LangChain `RedisSemanticCache` against a dedicated `redis-stack-server` instance, context-isolated via a folded discriminator), L3 Session Cache (implemented, not yet wired to a caller), a `CachePolicyResolver` (AUTO/NEVER/EXACT_ONLY/SEMANTIC/SESSION per `CacheRuntime`), in-memory `CacheStatistics`, streaming bypass, and `GenerationResult.metadata["cache"]` artifact stamping. Wired directly into `GenerationService`. Required downgrading `redis` to `<8.0` to satisfy `langchain-redis`'s `redisvl` dependency (verified safe against actual usage) and fixing resulting stub regressions in the pre-existing `ValkeyQueue`. 22 new unit tests

✅ Routing Platform (Generation Platform Milestone 2.9.7, per `routing_platform_prd.md`/ADR-026) — a new decision layer between callers and the Generation Platform's providers: a scored `ModelCatalogRegistry` (12 models, per-task 0-1 scores, cost/context/policy metadata), a `RoutingService` (capability filter → policy filter → strategy-weighted scoring → distinct-provider-preferred fallback chain), 15 task-based `RoutingStrategy` values (6 with dedicated profiles — planning, summarization, review, validation, coding, research), structlog-logged `RoutingDecision`s, and a `GenerationService.generate()` integration that routes automatically (with fallback retry) when no explicit `provider` is given. 44 new unit tests; full repo suite (746 tests), ruff, and mypy pass clean

✅ Guardrails Platform (Milestone 11.16) — new standalone platform (`app/ai/guardrails/`) spanning input/retrieval/generation/runtime stages: prompt injection/jailbreak detection, scope validation, PII detection, a new Source Trust Platform (`trust/`), citation integrity, faithfulness enforcement + schema enforcement (both reusing the Validation Platform's validators), PII leakage detection, and a runtime budget guardrail + loop detection. `GuardrailService` (crash-safe aggregation, weighted risk scoring, fail/risk/regeneration/runtime policies), `GuardrailArtifactWriter`, and 113 new unit tests. Composes rather than duplicates the pre-existing `ContextGuardrailService` (Milestone 2.8.4). Deleted two dead, zero-reference guardrails scaffolds discovered during the work. Standalone — not yet wired into `GenerationService`, matching how the Validation Platform itself shipped

✅ Generation Platform — Validation Platform integration (`generation/validation/`): input validators (`EmptyPromptValidator`, `TokenBudgetValidator`, `ProviderLimitsValidator`, `ContextValidator`), a new `JsonValidator` alongside `SchemaValidator`/`CitationValidator`, a new lightweight `HallucinationValidator` (deterministic, no LLM judge), a `ValidationRegistry`, a multi-stage `ValidationService`, weighted `overall_score` (`validation/scoring.py`), and a `ValidationReport` replacing the old single-stage `ValidationResult` on `GenerationResult.validation`; regeneration now correctly reacts only to the output stage — see Milestone 2.9.4. 17 new test files (~100 cases) added

✅ Generation Platform — Provider Structured Output Integration: native schema-constrained decoding for all five providers (OpenAI, Claude, Gemini, Groq, Ollama), parser/repair fallback, Markdown/XML parser-registry connection, `ResponseFormat.XML` added

✅ Generation Platform — LangChain `with_structured_output()` bridge (OpenAI, Claude, Gemini, Ollama — `generation/langchain/output_parsers.py`; Groq excluded, `langchain-groq` incompatible with the pinned `groq` SDK)

✅ Generation Platform — Regeneration Strategy: opt-in regenerate-on-invalid-output loop with corrective feedback (`max_regeneration_attempts`, `GenerationResult.regeneration_attempts`)

✅ Generation Platform — Provider Capability Flags: capability-mismatch guard (`generation.capability_mismatch` logging) on top of the pre-existing `ProviderCapabilities`/`supports_*` accessors

✅ Generation Platform — Prompt Platform Integration: `GenerationService.generate_from_template()` bridges the pre-existing `generation/prompts/` template platform into Generation, with schema-aware format instructions (`PydanticOutputParser.get_format_instructions()`)

✅ Context Platform foundation — ChunkArtifactReader, ParentExpansionService, AdjacentMergeService (~90% of Milestone 2.8 complete)

✅ Compression Platform — Token Budget Provider (V1) + Embedding Compression Provider (V2, drops chunks above similarity threshold)

✅ Context Guardrails V1 — provider architecture, `RuleBasedGuardrailProvider`, risk scoring, statistics

✅ Citation Platform — citation IDs, page numbers, headings/heading paths, chunk IDs

✅ Prompt Formatter — strategy-based formatting (`DEFAULT`, `NOTEBOOKLM`, `PERPLEXITY`, `RESEARCH`, `AGENT`)

✅ Parallel Retrieval — dense + sparse search executed concurrently via `asyncio.gather`

✅ Metadata Filtering (`owner_id`, `document_id`, `filename`, `language`) across dense, sparse, and hybrid retrieval

✅ Retrieval API authentication + server-enforced `owner_id` scoping (fixed a gap where requests worked without a bearer token and could spoof another user's `owner_id`)

✅ Reranking Platform (Voyage AI `rerank-2` + local CrossEncoder `BAAI/bge-reranker-base`), wired into hybrid retrieval by default

✅ Metadata Filtering Benchmark (`leakage_rate` correctness signal, MRR uplift)

✅ Reranking Benchmark (hybrid-only vs. +CrossEncoder vs. +Voyage AI; Recall@5, MRR, NDCG@5, latency, cost)

✅ NDCG@K metric added to the retrieval benchmark suite

✅ Retrieval Platform foundation (dense, sparse, hybrid RRF search + `/retrieve`, `/retrieve/sparse`, `/retrieve/hybrid`)

✅ Query embedding cache (Valkey-backed, TTL-based)

✅ Retrieval Benchmark (dense vs. sparse vs. hybrid, ADR-020 metrics)

✅ Vector Store Platform (Qdrant provider)

✅ Sparse Embeddings (FastEmbed SPLADE)

✅ Qdrant Native Hybrid Indexing (dense + sparse, same collection)

✅ Ingestion Pipeline Benchmark (real end-to-end run, dense+sparse metrics)

✅ Runtime Metrics Foundation

✅ Runtime Report Generation

✅ Shared Embedding Batching

✅ Sentence Transformers Provider

✅ Voyage AI Provider

✅ OpenAI Provider

✅ Multi-provider Embedding Platform

✅ End-to-End Embedding Pipeline

---

# Current Focus

## Phase 2.8 — Context Platform (✅ complete) + Phase 2.9 — Generation Platform (✅ complete)

Parent Expansion, Adjacent Merge, Token Budget + Embedding + LangChain + LLM Compression (V1-V4), Guardrails V1, Citations, and Prompt Formatter are all implemented (see Milestone 2.8 above), bringing the Context Platform to 100% complete (Phase 3.7, `context_platform_complexion_prd.md`) — `ContextBuilderService.build()` now takes an optional `query` and, when `settings.enable_langchain_compression` is on, runs query-aware LangChain compression as part of its default pipeline. Remaining nearby scope (not part of Phase 3.7):

- Forward `HybridRetrieveRequest.rerank` from the `/retrieve/hybrid` endpoint into `RetrievalService.search_hybrid` (it currently always uses the service's `rerank=True` default regardless of the request body)
- Retrieval result cache
- Scaling the retrieval benchmark dataset (5 → 20-50 documents, 20 → 100 queries, chunk-level relevance) — see `README.md` TODO

The **Generation Platform** (Milestone 2.9) is now 100% complete, per `generation_platform_complexion_prd.md` (see Milestones 2.9 and 2.9.11 above): provider abstraction, Structured Output Integration (native decoding + parser fallback + Markdown/XML registry + LangChain `with_structured_output()`), Validation Platform integration (input/output/hallucination/runtime validators, registry, weighted scoring, `ValidationReport`, and all five per-runtime Validation Contracts — Research/Planner/Reviewer/Agent/MCP), a Validation Policy Layer (Acceptance/Fail-Fast/Runtime Validation), Regeneration Strategy, a provider-capability guard, Prompt Platform integration, a Routing Platform (scored model catalog, task-based strategies, capability/policy filtering, fallback chains — Milestone 2.9.7), a Runtime Caching Platform (L1 exact/L2 semantic/L3 session caching, policy resolution — Milestone 2.9.9), a Streaming Platform (canonical event protocol, SSE + WebSocket transports, wired into a live `POST /api/v1/chat/stream` / `/api/v1/chat/ws` — Milestone 2.9.10), Runtime Metrics Integration, and an Artifact Platform (canonical, immutable, policy-gated persistence for generation/streaming/conversation/research executions, incl. a `metrics.json` snapshot — Milestone 3.10) are all done. Streaming rate limiting and a real multi-message chat history API remain separately as Streaming Platform (Milestone 2.9.10) gaps.

The **Guardrails Platform** (Milestone 11.16, see above) is now complete as an MVP foundation — input/retrieval/generation/runtime guardrails, a new Source Trust Platform, policies, weighted risk scoring, and artifact persistence — and is now wired into both `GenerationService` and `ContextBuilderService` (per `guardrail_integration_prd.md`, see Milestone 11.16's "Integration" subsection). Only the runtime stage (`evaluate_runtime()`) still has no live caller — the new `/research` API is deliberately linear with no reasoning/tool loop for it to guard.

The **Artifact Platform** (Milestone 3.10, see above) is now complete for three live AI Runtime execution types — a new centralized `app/ai/artifacts/` package persists every `GenerationService.generate()` call and every completed `StreamingService` stream as an immutable, versioned, policy-gated artifact, plus one immutable file per completed conversation turn from `chat.py` and one per completed research call from `ResearchService`. Session/Agent/Evaluation artifacts are fully built and unit-tested but remain unwired, since none of those runtimes exist yet — the same "build ahead of the API surface" pattern already used by the Runtime Caching Platform.

## Generation Runtime Platform (✅ complete) + Phase 4 — Research API Platform (✅ complete)

The **Generation Runtime Platform** (Milestone 2.9.12, per `generation_runtime_platform_prd.md`) closed the last gap between "every platform is done" and "a product can call them": one canonical `execute_generation()` entrypoint over the already-complete `GenerationService.generate()` flow, so Research/Planner/Reviewer/Agent/MCP runtimes never need to reach into `GenerationService` directly. It re-implements nothing — see Milestone 2.9.12 above.

The **Research API Platform** (Phase 4, per `research_api_prd.md`) is that entrypoint's first real caller, and **ResearchMind's first live, end-to-end product surface**: `POST /research` (+ `/research/stream`, `/research/citations`, `GET /research/{id}`) lets a user upload documents, ask a question, and get back a grounded, cited, streamable answer. `ResearchService` composes Retrieval + Context + Generation Runtime + Streaming + best-effort Artifact persistence in a deliberately linear flow — no query decomposition, planning, multi-step loops, agents, or LangGraph (PRD §4 Non-Goals; a Research Runtime, Deep Research Runtime, and Agent Platform are named as what comes next). This is the first live traffic to exercise `RuntimeType.RESEARCH`/`ArtifactRuntime.RESEARCH` and the first live caller of the previously scaffold-only Research Artifact writer. See Phase 4 above for full detail.

Next up: Evaluation Platform expansion (Milestone 6) and a LangGraph-based Research Runtime (Milestone 7) — query decomposition, planning, multi-step agentic loops on top of this linear foundation.

## Phase 4.1 — Research Frontend Integration (✅ complete)

`apps/web`'s Research page now talks to the real backend end-to-end for the first time — see Phase 4.1 above for the full write-up, the three bugs found and fixed while validating it (stream-completion event-type mismatch, a retired Claude model, and Claude Sonnet 5's dropped `temperature` parameter), and the open to-do list.

## Phase 4.2 — Chat Surface Frontend Integration (✅ complete)

The design question Phase 4.1 deferred — separate Chat nav entry/page vs. a unified mode-toggle input — is now settled: Chat has its own `/chat` page and server-backed conversation replay. `GET /chat/conversations` and `GET /chat/conversations/{conversation_id}` are owner-scoped; the frontend no longer treats localStorage as the history source of truth. The remaining deliberate scope boundary is citations: Chat has transcript and memory context but no retrieval/RAG stage, so document-grounded answers remain on Research.

## Phase 3.9 — AI Runtime Observability Platform (✅ complete)

Per `oberservability_platform_prd.md`, a new top-level `app/ai/observability/` package implements the metrics/statistics/report/artifact/LangSmith layers the PRD calls for, added alongside (not replacing) the pre-existing, unrelated `app/ai/observability/{models,runtime,report,timer}.py` module the Knowledge Processing pipeline already used. Canonical snapshot models + pure derivation functions for Retrieval/Streaming/Research/Agent metrics, a Statistics Platform (percentiles/averages/rates/rankings, pure aggregation over a caller-assembled list — no persistent store, matching the PRD's own deferral of Prometheus/Grafana-style infra), markdown report builders, and a new `ObservabilityArtifact` (metrics/statistics/report, S3-persisted under `observability/{execution_id}/`) are all live. `RetrievalStatistics` also gained real per-stage latency fields (`dense_latency_ms`/`sparse_latency_ms`/`rerank_latency_ms`/`reranker_provider`), populated from timings `RetrievalService.search_hybrid()` was already computing and previously discarding.

**LangSmith tracing is real, not stubbed** — `langsmith` added as a direct dependency, a `RuntimeTracer`/`LangSmithTracer` bracket the provider call, gated on **both** `LANGSMITH_API_KEY` and the new `LANGSMITH_TRACING` flag (an API key alone no longer enables tracing, so ops can leave it configured and toggle tracing off locally). `LANGSMITH_ENDPOINT`/`LANGSMITH_PROJECT` settings were also added and wired through.

**Three real bugs were found and fixed via live verification against an actual LangSmith account and S3 bucket — not caught by the unit test suite, which all passed throughout:**

1. **Streaming was completely dark.** The first pass only instrumented `GenerationService.generate()`, but the frontend's real traffic (`/research/stream`, `/chat/stream`) goes through `stream_generate()`/`StreamingService`, which calls the provider directly, bypassing all of it. Fixed by giving `GenerationService` read-only `metrics_service`/`observability_service`/`tracer` properties (mirroring its pre-existing `registry` property) so `StreamingService` reuses the identical instances instead of composing its own, and wrapping the live stream loop the same way `_execute_once()` wraps the non-streaming call. This one fix means **Chat needed zero additional wiring** — it already goes through the same `StreamingService.stream_generate()` path.
2. **A missing artifact-policy rule silently ate every research artifact write.** `ResearchService` tags requests `ArtifactRuntime.RESEARCH`, but the default policy table only had an `OBSERVABILITY` rule for `CHAT` — any unmapped `(runtime, category)` pair fails safe to `NEVER`, so every write was skipped via a `logger.debug` line, invisible unless you went looking. LangSmith traces worked fine throughout (tracing and artifact persistence are gated completely independently), which is exactly why this stayed hidden. Fixed with an explicit `(RESEARCH, OBSERVABILITY) -> PERMANENT` rule, matching Research's own canonical/always-permanent artifact policy.
3. **The tracer never sent a real prompt or a real output.** `RuntimeTracer.trace()` only ever accepted generic `tags` (provider/model/runtime), which got passed straight through as LangSmith's `inputs` — metadata masquerading as input — and nothing was ever sent as `outputs`, so every trace showed "No outputs" and Monitoring's Cost/Token/Latency charts had nothing to compute from. Fixed by adding a real `inputs` param (the actual prompt) and a `TraceHandle` (yielded by the trace context manager) with `set_output(content, prompt_tokens, completion_tokens, total_tokens)`, called once the result is known but before the trace closes.

A fourth, separate real gap was found (not a bug in this session's own work) and closed: **streamed generations never ran post-generation validation/guardrail scoring at all** — `stream_generate()` only checks input-side guardrails before generation starts; the output-side checks (`_enforce_generation_guardrails`/`ValidationService.validate()`) are `_execute_once()`-only, so every streamed response's `metrics.json` had `validation_score`/`hallucination_score`/`runtime_score`/`guardrail_risk_score` stuck at `null`. New `GenerationService.score_completed_stream()` runs the same checks informationally after a stream completes — a blocked guardrail verdict is recorded, never raised, since there's nothing left to stop once tokens reached the client. **Operational note**: verified that no guardrail/validator in this codebase actually calls an LLM today (all rule-based/regex/lexical-overlap or explicit MVP stubs), so this currently costs CPU only, zero provider spend — but it's now documented policy that any future LLM-based guardrail/validator must default to Groq, never an expensive frontier provider, since this scoring pass runs unconditionally on every streamed request.

**Separately, and unrelated to observability**: verifying Research's follow-up-question behavior surfaced a real, pre-existing product gap — **Research has zero multi-turn conversation memory**. Every `/research`/`/research/stream` call embeds the raw query string into a fresh vector search with no history, no query rewriting/condensation, and no session continuity (`research_id` is generated fresh every call and never reloaded). Chat already has persisted conversation history (just flattened to a single string at the provider boundary, a separate known limitation) — Research and Chat's conversation machinery are entirely disconnected. See `AI_ENGINEERING_AUDIT.md` for the full write-up; not fixed this cycle, flagged for a future Research Runtime milestone.

All work verified with full-suite runs throughout (ended at 1151 passing, up from 1132 at the start of this cycle), `ruff check .` and `mypy apps/api/app` clean after every change.

## Milestone 12 — Memory Platform (✅ complete) + wired into both live surfaces

Per `memory_platform_prd.md`, closes the multi-turn conversation memory gap flagged in Phase 3.9 above (*"Research has zero multi-turn conversation memory at all"*) — and, in the same session, extends the fix to Chat too. See Milestone 12 above for full detail: storage routing (Session/Valkey, User+Semantic+Research/Postgres+Qdrant), the `MemoryService` orchestrator and `/memory` API, the 5-pipeline alignment pass (RRF search fix, LLM extraction, lifecycle sweep), and Runtime Memory Injection wired into both `ResearchService` and `chat.py`. Also closed along the way: two Generation Platform bugs (an unconditional Chat outage from a blanket empty-context validation check, and a silent artifact-serialization failure) — see the Milestone 12 write-up and the Milestone 2.9.7 Addendum (Routing AUTO default changed to Groq) above.

With this, Chat now has session continuity and durable user/research memory (though still no retrieval/RAG grounding — a separate, still-open gap), and Research has the multi-turn continuity it was previously missing entirely.

---

# Immediate Roadmap

```
Retrieval (dense + sparse + hybrid + parallel) ✅

↓

Metadata Filtering ✅

↓

Reranking ✅

↓

Context Platform (100%) ✅
  Parent Expansion ✅
  Adjacent Merge ✅
  Compression (Token Budget + Embedding + LangChain + LLM, V1-V4) ✅ — LangChain wired into build()'s default pipeline (opt-in via settings.enable_langchain_compression)
  Guardrails V1 ✅
  Citation Platform ✅
  Prompt Formatter ✅

↓

Generation Platform (100%) ✅ — per `generation_platform_complexion_prd.md`
  Provider Abstraction (5 providers) ✅
  Structured Output Integration (native + fallback + registry + LangChain) ✅
  Validation Platform Integration (input/output/hallucination/runtime validators, registry, scoring, ValidationReport, 5 runtime contracts — Research/Planner/Reviewer/Agent/MCP) ✅
  Validation Policy Layer (Acceptance/Fail-Fast/Runtime Validation) ✅
  Output Validators (JSON/Schema/Formatting/Completeness/Consistency/Response Size/Citation, pipeline order) ✅
  Regeneration Strategy ✅
  Provider Capability Guard ✅
  Routing Platform (scored catalog, task-based strategies, fallback chains) ✅
  Prompt Platform Integration ✅
  Runtime Caching Platform (L1 exact, L2 semantic, L3 session, policy resolution) ✅ — Session Cache not yet wired to a caller ⏳
  Streaming Platform (runtime/events + generation/streaming, SSE + WebSocket, chat.py wired) ✅ — rate limiting, real multi-message history ⏳
  Runtime Metrics Integration (GenerationMetricsService, Prometheus-ready counters) ✅
  Artifact Platform (generation/streaming/conversation/research artifacts incl. metrics.json, S3-persisted) ✅ — session/agent/evaluation artifacts scaffold-only ⏳

↓

Generation Runtime Platform (Milestone 2.9.12) ✅ — per `generation_runtime_platform_prd.md`
  execute_generation() canonical entrypoint over GenerationService.generate() ✅
  GenerationExecutionContext / GenerationExecutionState (trace id, timing) ✅
  get_generation_runtime() FastAPI dependency ✅

↓

Guardrails Platform (Milestone 11.16) ✅ Foundation — ✅ wired into GenerationService + ContextBuilderService
  Input Guardrails (Prompt Injection, Scope, PII) ✅
  Retrieval Guardrails (Context Sanitization, Source Trust, Citation Integrity) ✅
  Generation Guardrails (Faithfulness, Schema Enforcement, PII Leakage) ✅
  Runtime Guardrails (Budget, Loop Detection) ✅ — Tool Policy, Approval Gate interfaces only ⏳; no live caller yet — /research is deliberately linear, no reasoning loop
  Wiring into GenerationService (input gate + full report on GenerationResult.guardrails) ✅
  Wiring into ContextBuilderService (retrieval-stage gate) ✅
  Wiring into a router / agent runtime ⏳ (needs a Research/Agent Runtime with an actual loop)

↓

Phase 4 — Research API Platform ✅ — per `research_api_prd.md`, ResearchMind's first live, end-to-end product surface
  POST /research, /research/stream, /research/citations, GET /research/{id} ✅ (auth-required, owner-scoped)
  ResearchService — Retrieval + Context + Generation Runtime + Streaming + best-effort Artifacts ✅
  ResearchSession Postgres table (research_sessions) for replay ✅
  RuntimeType.RESEARCH / ArtifactRuntime.RESEARCH exercised by live traffic for the first time ✅
  Query decomposition, planning, multi-step/agentic loops, LangGraph ❌ (deliberate Non-Goals — next milestone)

↓

Phase 4.1 — Research Frontend Integration ✅ — apps/web wired to the live Research API
  use-research.ts hook + lib/sse.ts SSE client (replaces mock-engine.ts) ✅
  citation-card.tsx + updated research components/types/api client ✅
  Bugs found + fixed: stream-completion event-type mismatch, retired Claude model, temperature rejected ✅
  SSE error path hardening (non-Timeout/StopAsyncIteration exceptions kill the stream silently) ⏳

↓

Phase 4.2 — Chat Surface Frontend Integration ✅ — apps/web's new /chat page wired to the live Chat API
  features/chat/ (types, use-chat.ts, ChatGPT-style bubble components) ✅
  api.chat.stream() in lib/api.ts + "Chat" nav entry ✅
  Backend fix required first: GenerationRequest.session_id now set in chat.py (was blocking multi-turn chat) ✅
  GET /chat/conversations + /chat/conversations/{id} — owner-scoped server history/replay ✅
  Both completion event variants persist completed turns; replay stays user → assistant ✅
  Groq title uses first persisted user question; full title available via sidebar tooltip ✅
  Citations/sources panel ❌ (blocked on Chat retrieval/RAG wiring, a separate gap)

↓

Generation Usage Ledger ✅ — owner-scoped estimated AI cost tracking for Chat and Research
  `generation_usage` PostgreSQL ledger, append-only and idempotent by generation request ID ✅
  Records provider/model/runtime category, token totals, estimated USD cost, cache status, streaming flag, and conversation/session linkage ✅
  Runtime categories distinguish `chat`, `research`, `memory_extraction`, and `conversation_title`; legacy rows recorded before categorization can remain `NULL` ⚠️
  GenerationService + StreamingService persist successful owner-owned requests; a verified cache replay records `cache_hit=true`, `streamed=true`, and `$0` new provider spend ✅
  `GET /usage/summary` returns authenticated user's all-time/current-month cost, request, and token totals ✅
  Dashboard displays estimated AI cost for the current month plus all-time total ✅
  Research now uses a safe exact-then-semantic cache profile: an exact replay requires the same fully rendered transcript, memory context, retrieval context, model, and generation settings; a repeated sentence in a changed conversation deliberately remains a miss to avoid stale answers ✅
  Historical usage before this migration is intentionally unavailable; streamed provider usage is an estimate when the provider does not supply exact token metadata. LangSmith's displayed `$0` is not itself cache proof; the ledger's `cache_hit` field is authoritative ⚠️

↓

Phase 3.9 — AI Runtime Observability Platform ✅ — per `oberservability_platform_prd.md`
  Metrics/Statistics/Reports subpackages (Retrieval/Streaming/Research/Agent snapshots, percentiles/aggregations/rankings, markdown reports) ✅
  ObservabilityArtifact (metrics/statistics/report, S3-persisted under observability/{execution_id}/) ✅
  LangSmith tracing — real, dual-gated on LANGSMITH_API_KEY + LANGSMITH_TRACING ✅
  Wired into GenerationService.generate() AND stream_generate() (fixed after live testing found streaming was dark) ✅ — Chat gets this for free via StreamingService
  Wired into ProcessingService (Knowledge pipeline) — metrics/report only, no LangSmith trace (no LLM call) ✅
  score_completed_stream() — informational, non-blocking validation/guardrail scoring for streamed responses (closes a real feature-parity gap vs. non-streaming) ✅
  Trace Input/Output/Token content (real prompt + real output + usage_metadata, not just tags) ✅
  Retrieval/Agent metrics artifact persistence (record_retrieval/record_agent) ❌ (canonical snapshots exist, no live artifact-write call site yet)

↓

Chat 🟡 — streaming chat (SSE + WebSocket), owner-scoped server history/replay, Memory Platform injection/extraction, deterministic message ordering, and first-question Groq titles are live. It is still not wired to query rewriting or Retrieval/Context (`PromptContext.chunks` remains empty), so cited/document-grounded answers belong on Research.

↓

Milestone 12 — Memory Platform ✅ — per `memory_platform_prd.md`
  Session (Valkey) / User + Semantic + Research (Postgres + Qdrant) storage routing ✅
  MemoryService orchestrator + /memory API (remember/recall/search/forget/update/context) ✅
  Reciprocal Rank Fusion search (fixed a real importance-only sort bug) ✅
  LLM-driven extraction (MemoryExtractionService) ✅ — Groq is primary and OpenAI is an automatic fallback; structured-output prompts/provider handling were hardened for each provider's JSON/temperature constraints
  Lifecycle sweep (MemoryLifecycleService.sweep_stale()) ✅ — not yet scheduled ⏳
  Runtime Memory Injection wired into ResearchService ✅ and chat.py ✅
  Memory consolidation, decay staging, reflection memories, agent-shared memory ❌ (deliberate future work per both docs)
  Dedicated Memory Platform automated tests ❌ (tests/integration/test_memory.py still an empty stub)
  Efficiency follow-up ⏳ — every turn currently reads session memory and performs separate semantic/research searches; query embeddings are Valkey-cached, but the two vector searches are sequential and durable-memory extraction still runs after every completed turn. Next: embed once, search both durable stores concurrently, skip durable retrieval when the user has no durable memories, gate extraction to potentially durable turns, and de-duplicate session memory against the persisted transcript.

↓

Evaluation Platform Expansion — NDCG ✅, Groundedness ✅, Faithfulness ✅, Citation Accuracy ✅, Hallucination Rate ✅ (derived metric), Regression Detection ✅, Cost Metrics ✅ (`avg_cost_usd`/`cost_per_query`/`cost_per_1k_queries`) — E2E Evaluation ⏳, Security Evaluation ⏳, LangSmith dataset sync ⏳ (all built into `benchmarks/`, not a new `app/ai/evaluation/` — see Engineering Benchmark Platform section above). **Superseded — see `PRIORITIZED_ROADMAP.md` Wave 0/Wave 1 (E1–E23) and `EVALUATION_IMPLEMENTATION_TRACKER.md` for current detail; this entry is kept only as a historical trail.** All three items marked ⏳ here are now ✅: E2E/golden-set evaluation (Ragas scoring over a 115-example golden set), an adversarial security dataset (18 cases), and LangSmith dataset sync — plus a full feedback loop, online scoring, internal dashboard, LLM-as-judge, latency-SLO alerts, cost forecasting, and promotion review that didn't exist when this entry was written.

↓

Research Runtime (Query Decomposition, Planner, Agents, Reviewer, Summarizer, LangGraph) — builds on top of the now-live, deliberately linear Research API Platform above. **Superseded — see Phase 6 above for full current detail; this entry is kept only as a historical trail.**
  Phase 1 foundation ✅ — direct LangGraph 1.2.9 ownership, compact JSON-safe state, deterministic reducers, disabled walking-skeleton graph, in-memory interrupt/resume test, canonical event adapter, and ADR-031/032 are complete.
  Phase 2 lifecycle/checkpoint spike ✅ — `research_runs` separates owner-scoped graph lifecycle from completed replay sessions; migration, status-transition policy, Postgres checkpointer dependency, and interrupt/resume test are in place.
  Multi-turn conversation memory for Research ✅ — `research_conversations` groups turns, prior turns are folded into prompts, SESSION memory is scoped to the conversation id.
  Planner, decomposition, multi-wave retrieval, evidence, synthesis, review, bounded repair, budgets, PDF reports, cancellation, and crash-resume ✅ — a real, working (if frontend-less) Deep Research product surface. See Phase 6 above.

↓

Long-Term Platform (Research Sessions, MCP, Feedback Learning) — Memory ✅ landed early as Milestone 12, no longer purely long-term
```

---

# Long-Term Vision

ResearchMind is evolving into a production-grade AI Engineering Platform.

The platform is built around independent, provider-driven AI capabilities connected through canonical artifacts.

Every platform follows the same engineering principles:

- Canonical Models
- Canonical Artifacts
- Provider Pattern
- Registry Pattern
- Factory Pattern
- Composition Roots
- Framework Independence
- Production-first Engineering

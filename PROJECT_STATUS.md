# ResearchMind AI — Project Status

**Last Updated:** 2026-07-18

**Current Maturity:** NotebookLM++ + Perplexity Foundation — Hybrid Retrieval, Reranking, Parent Expansion, and Context Guardrails are all in place, putting the platform ahead of NotebookLM and closing in on a Perplexity v1 experience. The Context Platform's Compression stage is now complete end to end (V1-V4 — Token Budget, Embedding Redundancy, LangChain Contextual, and LLM per-chunk summarization — per `context_platform_complexion_prd.md`), with LangChain compression wired into `ContextBuilderService.build()`'s default pipeline behind an opt-in `settings.enable_langchain_compression` flag. A platform-wide Guardrails Platform (input/retrieval/generation/runtime stages, Source Trust, policies, scoring, artifacts) now sits alongside the Validation Platform as a completed foundation layer, and — per `guardrail_integration_prd.md` — is wired directly into both `GenerationService` (input gate before every provider call, full evaluate() report attached to `GenerationResult.guardrails`) and `ContextBuilderService` (retrieval-stage gate before context building). The Generation Platform is now fully complete, per `generation_platform_complexion_prd.md`: Routing Platform (model/provider selection, scored catalog, strategy-weighted fallback chains), Runtime Caching Platform (L1 exact/L2 semantic/L3 session caching, policy resolution, wired into `GenerationService`), Streaming Platform (canonical event protocol, SSE + WebSocket transports, `stream_generate()`, cache-hit replay), five per-runtime Validation Contracts (Research/Planner/Reviewer/Agent/MCP), a Validation Policy Layer, every PRD output validator, and Runtime Metrics Integration are all done. Critically, the Generation Platform is now reachable over HTTP for the first time — `POST /api/v1/chat/stream` (SSE) and `/api/v1/chat/ws` (WebSocket) are live, backed by a new minimal Conversation/Message persistence layer. A new, centralized Artifact Platform (`app/ai/artifacts/`, per `artifacts_platform_prd.md`) now persists every generation call, completed stream, and conversation turn as an immutable, versioned, policy-gated artifact in S3 — the canonical execution history layer the ingestion side has always had, now extended to the runtime side. A thin Generation Runtime Platform (`app/ai/runtime/generation/orchestration/`, per `generation_runtime_platform_prd.md`) then gave every future caller one canonical entrypoint, `execute_generation()`, into that already-complete `GenerationService.generate()` flow instead of reaching into `GenerationService` directly — and that entrypoint now has its first real caller: the new Research API Platform (Phase 4, per `research_api_prd.md`) is ResearchMind's **first live, end-to-end product surface** — `POST /api/v1/research` (plus `/research/stream`, `/research/citations`, `GET /research/{research_id}`) lets a user upload documents, ask a question, and get back a grounded, cited, streamable answer, via a new `ResearchService` composing Retrieval (hybrid search + rerank) + Context (dedup/expand/merge/compress/cite) + Generation Runtime + Streaming + best-effort Artifact persistence. This is also the first live code exercising `RuntimeType.RESEARCH` and `ArtifactRuntime.RESEARCH` — previously reserved-but-unused enum values — and the first live caller of the previously scaffold-only Research Artifact writer. Session/Agent/Evaluation artifacts remain built but scaffold-only, since those runtimes still don't exist yet. Most recently, an **AI Runtime Observability Platform** (`oberservability_platform_prd.md`, Phase 3.9) shipped and was hardened through several rounds of real-world verification against a live LangSmith account and S3 bucket: canonical metrics/statistics/report-builder subpackages under a new `app/ai/observability/`, real (not stubbed) LangSmith tracing + artifact persistence wired into **both** Generation entry points — `generate()` and, after a bug found via live testing, `stream_generate()` too (meaning Research, Chat, and any future streaming caller all get it "for free") — plus the Knowledge Processing pipeline (parse/chunk/embed/index, no LLM call, so metrics/report only, no trace). Three real bugs were found and fixed by testing against the actual frontend rather than trusting the initial implementation: (1) tracing/artifacts were wired into `generate()` only, silently dark for every streamed request; (2) a missing `(RESEARCH, OBSERVABILITY)` artifact policy rule silently skipped every research artifact write even with tracing working; (3) the tracer only ever sent metadata tags as LangSmith's "input" and never sent an "output" at all. A follow-up closed a real product gap surfaced by the same verification: streamed generations never ran post-generation validation/guardrail scoring at all (only pre-generation input checks) — `GenerationService.score_completed_stream()` now runs the same checks `generate()` does, informationally, never blocking (there's nothing left to stop once tokens reached the client). Separately, verifying the Research feature surfaced an unrelated, real product gap: **Research has no multi-turn conversation memory at all** — every query is a fully standalone retrieval + generation call with no history, no query rewriting, and no session continuity, unlike Chat (which has persisted history, just flattened at the provider boundary). See `AI_ENGINEERING_AUDIT.md` for the full write-up. Most recently, `evaluation_platform_prd.md` (Phase 4.1 in its own header, a number already taken in this file by Research Frontend Integration) asked for a full new Evaluation Platform — datasets/evaluators/benchmarks/experiments/regression/reports under a new `app/ai/evaluation/`. Investigation found that would have duplicated two things that already exist under different names: the "Engineering Benchmarks" layer described in `docs/architecture/evaluation-strategy.md` is already real, working code at repo-root `benchmarks/` (not the empty `app/ai/quality/` scaffold the PRD's folder layout would have paralleled), and the "Runtime Evaluation" layer described in `docs/architecture/evaluation-platform.md` is already implemented as the AI Runtime Observability Platform above — confirmed by `STRUCTURE.md`'s own annotation on that doc's sibling. The PRD's Experiment Platform section was also deferred, since it would have forked the separately-designed, not-yet-built async Experimentation Platform before it exists. What was real and missing — Generation evaluation and Regression Detection — was built directly into `benchmarks/` instead; see the Engineering Benchmark Platform section below for detail, including a real citation-accuracy bug found and fixed via live verification against Groq/OpenAI/Claude. Maturity ladder: `NotebookLM++ → Perplexity v1 (reached) → Open Deep Research → Manus / Glean`.

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

**Status:** ✅ Complete (Foundation + Metadata Filtering + Reranking)

ResearchMind can now query the hybrid Qdrant index built in Milestone 2.6. Dense, sparse, and hybrid (RRF-fused) retrieval are implemented, benchmarked, and exposed via API. Metadata filtering and reranking are now implemented end-to-end; only the advanced retrieval strategies (parent/child, query decomposition, multi-query) and a retrieval result cache remain open.

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
- ✅ Parallel retrieval — dense + sparse search executed concurrently via `asyncio.gather`
- 🔄 Parent/Child retrieval — reclassified out of the Retrieval Platform into the Context Platform (see Milestone 2.8 below); implemented there as Parent Expansion + Adjacent Merge
- ❌ Query decomposition — moved to the future Research Runtime (Phase 7)

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

**Finding:** exactly the pattern reranking is supposed to produce — Recall@5 was already 1.0 for `hybrid_only` and didn't move for either reranker, while MRR and NDCG@5 both improved (MRR: 0.925 → 1.0 with CrossEncoder, → 0.95 with Voyage; NDCG@5: 0.9446 → 1.0 with CrossEncoder, → 0.9631 with Voyage). On this small benchmark corpus, the free local CrossEncoder outperformed the paid Voyage reranker on both quality and latency, though this shouldn't be over-generalized from 5 documents / 20 queries.

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
- 20-query hand-curated ground-truth dataset (`benchmarks/datasets/research-papers/retrieval_queries.json`), document-level relevance, 4 query categories (semantic, acronym, exact-keyword, code-entity)
- ✅ NDCG — `ndcg_at_k` implemented in `benchmarks/retrieval/metrics.py` (binary relevance, standard DCG/IDCG), used by the Reranking Benchmark below

**Finding:** on the current 5-document benchmark corpus, dense, sparse, and hybrid are statistically indistinguishable — Recall@5/10/20 = 1.0 for all three, and hybrid's MRR (0.925) was actually slightly *lower* than dense (0.95) or sparse (0.975) alone. The corpus is too small (5 documents, 20 queries, document-level relevance) to meaningfully stress any retriever or give RRF real ranking disagreement to resolve. This does not mean Hybrid Retrieval is ineffective — it means the benchmark can't yet answer that question. See the dataset-scaling and chunk-level-relevance TODO in `README.md`.

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

**Status:** ✅ Complete

Implemented

- `ChunkArtifactReader` — loads persisted `ChunkArtifact`s from storage so parent chunks can be resolved without S3 object listing
- `ParentExpansionService` — resolves `parent_chunk_id` from retrieved child chunks into full parent context
- Vector payload extended with `chunk_artifact_id`, `chunking_strategy`, `parent_chunk_id`

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

- `GenerationReplayService` / `StreamReplayService` (`artifacts/replay/`) — real and unit-tested, reconstruct a `GenerationResult` or re-emit a stored `StreamEvent` sequence in order from persisted artifacts; no new API route added for either, just the services
- `ResearchReplayService` — scaffold stub, `replay()` raises `NotImplementedError` naming the missing Research Runtime rather than silently returning empty data

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

`apps/web/src/features/research/mock-engine.ts` (the placeholder that previously faked streaming/citations/sources for UI development) is deleted. In its place: a new `use-research.ts` hook driving per-turn state (`searching` → `generating` → `done`/`error`), a new `lib/sse.ts` client for consuming the backend's `text/event-stream` responses via `fetch` + `ReadableStream` (not a bare `EventSource`, matching `chat.py`'s own documented reasoning — `EventSource` can't attach a custom bearer `Authorization` header), and a new `citation-card.tsx` component. `research-block`/`research-composer`/`research-sidebar`/`source-card`/`source-panel`/`streaming-status`/`types.ts`/`lib/api.ts` all updated to match the real API contract (citations, sources, `research_id`, replay-by-id) instead of mocked shapes. Research history persists client-side in `localStorage`, keyed by `research_id`.

## Findings (bugs discovered turning this on against live infra, all fixed)

1. **Live-streamed research turns silently never persisted.** `ResearchService.stream_research()` only treated `CoreEventType.COMPLETE` (`"complete"`) as "generation finished," but `StreamingService`'s live-provider path (`_stream_live`) actually emits `StreamEventType.COMPLETED` (`"completed"`) — `CoreEventType.COMPLETE` is only ever emitted on the cache-hit-replay path. Every real (non-cache-hit) research stream finished, showed an answer in the UI, and then `GET /research/{id}` 404'd, because `_persist_session`/`_persist_artifact` were never reached. Fixed in `apps/api/app/ai/research/service.py` by checking both event-type values.
2. **`claude-sonnet-4` (bare, and its dated `-20250514` snapshot) has been fully retired** from the configured Anthropic account — confirmed directly against `GET /v1/models`, which no longer lists either. Every hardcoded reference (`.env`, `.env.example`, `core/settings.py`, `generation/config.py`, `generation/catalog/models.py`, `generation/prompts/service.py`, `generation/observability/token_counter.py`) updated to `claude-sonnet-5`; one test assertion (`tests/unit/ai/runtime/generation/prompts/test_service.py`) updated to match the new default.
3. **`claude-sonnet-5` rejects the `temperature` sampling parameter outright** (400 `invalid_request_error`, `` `temperature` is deprecated for this model``) — it's an "effort"-based reasoning model, not a classic sampling-temperature one. Rather than hardcoding a model-name list that would rot as Anthropic ships new snapshots, `ClaudeProvider.stream()`/`_create_message()` (`generation/providers/claude.py`) now attempt the call with `temperature` first and, on that specific error, retry once without it.

## To-Do / Open Items

- **Chat has no frontend surface yet** — `apps/web`'s nav is Dashboard/Research/Documents only; Chat exists only as a backend API (`/chat/stream`, `/chat/ws`). Open design discussion (deferred at the user's request): a separate "Chat" nav entry + page mirroring the backend's already-separate persistence/retrieval-grounding split (no citations/retrieved-passages panels, multi-turn history) vs. a single unified input with a mode toggle. No decision made yet.
- **SSE error path is not fully hardened.** `_sse_byte_stream` (`runtime/generation/streaming/transports/sse.py`) only catches `TimeoutError`/`StopAsyncIteration` around `events.__anext__()` — any other exception raised deeper in a route's stream generator (e.g. a future DB/commit failure) propagates unhandled and silently kills the SSE connection with no client-visible `error` event, rather than converting cleanly like the existing `CoreEventType.ERROR` path does. Noticed while investigating Finding 1 above, though Finding 1's actual root cause was the event-type mismatch, not this gap — still worth hardening defensively.
- **No automated check for upstream model deprecations.** Finding 2 was only caught by a live 404 during manual testing, not proactively. Worth a periodic (manual or CI) cross-check of `generation/catalog/models.py` model names against `GET /v1/models` so a provider-side retirement doesn't silently break generation again.

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
| Phase 2.7 — Retrieval Platform | ✅ Complete (incl. Metadata Filtering + Reranking + Parallel Retrieval) |
| Phase 2.8 — Context Platform | ✅ Complete (Parent Expansion, Adjacent Merge, Compression V1-V4, LangChain compression wired into `build()`'s default pipeline, Guardrails V1, Citations, Prompt Formatter — Phase 3.7, `context_platform_complexion_prd.md`) |
| Phase 2.9 — Generation Platform | ✅ Complete, per `generation_platform_complexion_prd.md` (Structured Output Integration, Validation Platform integration incl. input/output/hallucination/runtime validators + scoring + five runtime contracts, a Validation Policy Layer, every PRD output validator, Regeneration, Prompt Platform bridge, Routing Platform, Runtime Caching Platform, Streaming Platform (SSE+WS chat, wired), Runtime Metrics Integration, Artifact Platform (generation results persisted incl. metrics.json) done) |
| Milestone 2.9.12 — Generation Runtime Platform | ✅ Complete, per `generation_runtime_platform_prd.md` (thin orchestration layer, `execute_generation()` canonical entrypoint, no new generation behavior) |
| Milestone 11.16 — Guardrails Platform | ✅ Complete (MVP Foundation — input/retrieval/generation/runtime guardrails, Source Trust, policies, scoring, artifacts) + ✅ Integrated into `GenerationService`/`ContextBuilderService` (runtime stage still has no live caller) |
| Milestone 3.10 — Artifact Platform | ✅ Generation/Streaming/Conversation/Research artifacts complete and wired (`GenerationService`, `StreamingService`, `chat.py`, `ResearchService`) — 🟡 Session/Agent/Evaluation artifacts built but scaffold-only (no runtime exists yet to call them) |
| Phase 4 — Research API Platform | ✅ Complete, per `research_api_prd.md` — ResearchMind's first live, end-to-end product surface: `POST /research`, `/research/stream`, `/research/citations`, `GET /research/{id}` |
| Phase 4.1 — Research Frontend Integration | ✅ Complete — `apps/web`'s Research page wired to the live API (real SSE via `use-research.ts`/`lib/sse.ts`, `mock-engine.ts` deleted); 3 backend bugs found + fixed along the way (stream-completion event-type mismatch, retired Claude model, `temperature` rejected by the new model) |
| Benchmark Platform | ✅ Foundation Complete (incl. Retrieval, Metadata Filtering, Reranking, **Generation**, and **Regression Detection**) — see "Evaluation Platform PRD Reconciliation" above |

---

# Recently Completed

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

`apps/web`'s Research page now talks to the real backend end-to-end for the first time — see Phase 4.1 above for the full write-up, the three bugs found and fixed while validating it (stream-completion event-type mismatch, a retired Claude model, and Claude Sonnet 5's dropped `temperature` parameter), and the open to-do list. The biggest open product question right now isn't a bug: **Chat has a complete backend (`/chat/stream`, `/chat/ws`) but no frontend surface at all**, and how to present Chat alongside Research in the UI (separate nav entry/page vs. a unified mode-toggle input) is an active, deliberately deferred design discussion — see the To-Do list in Phase 4.1.

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
  Frontend Chat surface ❌ (no nav entry/page yet — design discussion deferred, see below)
  SSE error path hardening (non-Timeout/StopAsyncIteration exceptions kill the stream silently) ⏳

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

Chat 🟡 — basic streaming chat (SSE + WebSocket, Conversation/Message history) is live via the Streaming Platform (Milestone 2.9.10); not yet wired to Retrieval/Context (no `PromptContext.chunks`), so the now-guardrail-aware `ContextBuilderService` still isn't reachable from this path — see `guardrail_integration_prd.md`'s "Retrieval Integration" note. No frontend surface yet either (see Phase 4.1 above) — deferred decision on separate nav/page vs. unified mode-toggle with Research

↓

Evaluation Platform Expansion — NDCG ✅, Groundedness ✅, Faithfulness ✅, Citation Accuracy ✅, Hallucination Rate ✅ (derived metric), Regression Detection ✅, Cost Metrics ✅ (`avg_cost_usd`/`cost_per_query`/`cost_per_1k_queries`) — E2E Evaluation ⏳, Security Evaluation ⏳, LangSmith dataset sync ⏳ (all built into `benchmarks/`, not a new `app/ai/evaluation/` — see Engineering Benchmark Platform section above)

↓

Research Runtime (Query Decomposition, Planner, Agents, Reviewer, Summarizer, LangGraph) — builds on top of the now-live, deliberately linear Research API Platform above
  Multi-turn conversation memory for Research ❌ — confirmed 2026-07-18: every /research call is fully standalone (no history, no query rewriting, research_id never reloaded); Chat has persisted history but Research has none at all, see AI_ENGINEERING_AUDIT.md

↓

Long-Term Platform (Research Sessions, Memory, MCP, Feedback Learning)
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

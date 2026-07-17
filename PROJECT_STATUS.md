# ResearchMind AI — Project Status

**Last Updated:** 2026-07-17

**Current Maturity:** NotebookLM++ + Perplexity Foundation — Hybrid Retrieval, Reranking, Parent Expansion, Compression, Context Guardrails, and Prompt Formatter strategies are all in place, putting the platform ahead of NotebookLM and closing in on a Perplexity v1 experience. A standalone, platform-wide Guardrails Platform (input/retrieval/generation/runtime stages, Source Trust, policies, scoring, artifacts) now sits alongside the Validation Platform as a completed foundation layer. The Generation Platform's Routing Platform (model/provider selection, scored catalog, strategy-weighted fallback chains) is now complete, bringing Generation to ~75%. Maturity ladder: `NotebookLM++ → Perplexity v1 (almost here) → Open Deep Research → Manus / Glean`.

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
- ❌ `POST /research`
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

**Status:** 🟡 In Progress

Implemented

- Provider architecture (`context/compression/interfaces.py`, `models.py`, `enums.py`, `service.py`, `registry.py`, `create.py`)
- ✅ Token Budget Provider — sorts by score, fits into token budget (V1)
- ✅ Embedding Compression Provider — drops redundant chunks by embedding similarity (V2)

Remaining

- ❌ LangChain Provider — `ContextualCompressionRetriever` (V3)
- ❌ LLM Compression Provider — chunk-level relevant-summary compression (V4)

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

~90% complete.

Remaining before Milestone 2.8 closes:

- LangChain compression provider (V3)
- LLM compression provider (V4)

---

# Milestone 2.9 — Generation Platform

**Status:** 🟡 ~75% Complete

The Generation Platform owns all LLM interactions, consuming the Context Platform's `Prompt Context` output. Provider abstraction (all five providers), Structured Output Integration, a multi-stage Validation Platform integration (input/output/hallucination validators, a `ValidationRegistry`, weighted scoring, and a `ValidationReport`), a regenerate-on-invalid-output loop, a Prompt Platform bridge, and a Routing Platform (model/provider selection with fallback chains) are all implemented this milestone. Detail: `docs/architecture/structured-output-platform.md` (Structured Output/Validation) and `docs/architecture/model-routing-platform.md` + ADR-026 (Routing).

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

**Status:** 🟡 In Progress (Input/Output/Hallucination stage validators, a `ValidationRegistry`, weighted scoring, and a multi-stage `ValidationReport` done; per-runtime Contracts/Runtime Validators and a few PRD output checks remain)

Implemented (`generation/validation/` — a narrow slice of `validation_platform_prd.md`'s full target design, still living inside the Generation Platform rather than as its own top-level platform; see that PRD's Implementation Status note and `docs/architecture/structured-output-platform.md` → "Validation Platform Integration" for full detail)

- `ValidationRegistry` — dynamic per-stage validator registration (input/output/hallucination)
- `ValidationService` — per-stage (`validate_input()`/`validate_output()`/`validate_hallucination()`) and full (`validate()`) flows; a crashing validator becomes a WARNING issue rather than failing the whole check
- `ValidationReport` — replaces the old single-stage `ValidationResult` on `GenerationResult.validation`: one `ValidationResult` per stage plus a renormalized `overall_score` (`validation/scoring.py`, weighted per the PRD's §15 formula)
- Input validators — `EmptyPromptValidator` (empty/whitespace prompts, unrendered `{placeholder}` template variables), `TokenBudgetValidator` (estimated tokens vs. context window — a cheap deterministic word-count estimate, not `TokenCounter`'s real provider API calls, to stay deterministic per the PRD's Principle 2), `ProviderLimitsValidator` (streaming/structured_output/json_mode/tool_calling requested vs. the resolved provider's capabilities), `ContextValidator` (empty/duplicate chunks, orphaned citation references)
- Output validators — `SchemaValidator` (`parsed_output` vs. `request.output_schema` via `jsonschema`, added `jsonschema` + `types-jsonschema` dependencies), `JsonValidator` (new — is `content` itself valid/repairable/unparseable JSON, independent of `SchemaValidator`'s shape check), `CitationValidator` (bracketed `[S1]`-style markers vs. `request.prompt_context.citations`/`chunks`, catching fabricated citations)
- Hallucination validator — `HallucinationValidator` (new — deterministic lexical-overlap groundedness score against retrieved context, no LLM judge, WARNING-only to keep the false-positive rate low)
- Regeneration only reacts to `output_validation.valid` — input-stage issues (token budget, missing capability) describe the request, not the response, so re-generating with the same request wouldn't fix them; hallucination issues are WARNING-only and never gate it either

Remaining

- ❌ Runtime Validators (per-runtime contracts: research/planner/reviewer/agent/mcp) and the Contracts layer
- ❌ Completeness / Consistency / Formatting / Response Size output checks (PRD §9 — no stub files for these ever existed, unlike `json_validator.py`/`hallucination_validator.py`)
- ❌ Acceptance/Fail-Fast policy objects (regeneration is still governed directly inside `GenerationService`, as below)

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

## Not Yet Built

- ❌ `POST /research` API, streaming chat API
- ❌ Caching (`generation/caching/` scaffolding exists, not wired)
- ❌ Artifact persistence
- ❌ Runtime Validators / Contracts layer, Completeness/Consistency/Formatting/Response-Size output checks (see Milestone 2.9.4)
- ❌ Adaptive/evaluation-driven routing, budget-aware routing, A/B experimentation (Routing Platform Phase 2+ — see Milestone 2.9.7)
- 🟡 Test suite — `validation/`, `providers/`, `prompts/`, `routing/`, `catalog/`, and core `service.py` all have unit test coverage now; still nothing under `caching/` or `artifacts/`

Generation-level guardrails, previously listed here as a gap, are now implemented — see Milestone 11.16 below.

---

# Milestone 11.16 — Guardrails Platform

**Status:** ✅ Complete (MVP Foundation, per `guardrails_platform_prd.md`)

The Guardrails Platform answers a different question than the Validation Platform: not "did the system produce a good output?" but "should the system even perform this operation?" It is a new, standalone, platform-wide package (`apps/api/app/ai/guardrails/`, sibling to `knowledge/`, `runtime/`, `quality/`) spanning Input → Retrieval → Generation → Runtime stages, built to the same conventions as the Validation Platform (deterministic checks, a crash-safe `GuardrailService`, a `GuardrailRegistry`, weighted risk scoring, an `@lru_cache` composition root).

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
- `create.py` — `get_guardrail_service()`, the integration seam for future callers (not yet wired into `GenerationService`/context builder/a router — same standalone-but-complete posture the Validation Platform shipped with)

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

## Testing

113 new unit tests under `tests/unit/ai/guardrails/`, mirroring the Validation Platform's test-tree conventions (shared `factories.py`, local `_Fake...` doubles, real-dependency composition tests for the reuse points). Full repo suite (744 tests), `ruff format --check`, `ruff check`, and `mypy` all pass clean across all 706 source files.

## Not Yet Built (by design — matches PRD §21/§22 MVP scope)

- ❌ LLM-based classifiers (Llama Guard, Lakera, NeMo Guardrails) — explicitly skipped for MVP
- ❌ Wiring into `GenerationService`, the context builder, or a router (PRD's "Phase 6 — Generation Integration", intentionally deferred, same as Validation Platform)
- ❌ Enterprise ACL / multi-tenant Access Control, real Tool Policy providers, a working Approval Gate implementation (LangGraph interrupts/checkpoints)
- ❌ Security dashboards, attack datasets, red-teaming (PRD's Phase 2-4 future roadmap)

---

# Engineering Benchmark Platform

**Status:** ✅ Foundation Complete

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
- Retrieval Benchmark — benchmarks dense, sparse, and hybrid (RRF) retrieval against a dedicated, reproducible Qdrant collection (`benchmark_retrieval`, dropped/recreated per run, never touches production data); reports Recall@5/10/20, Precision@5/10, MRR, avg/P95/P99 latency, and a qualitative cost model per ADR-020
- Metadata Filtering Benchmark — validates `owner_id` filtering against a dedicated `benchmark_retrieval_filtering` collection with a distinct synthetic owner per document; reports Recall@K/Precision@K/MRR plus a `leakage_rate` correctness signal (0.0 for every filtered candidate)
- Reranking Benchmark — compares `hybrid_only` vs. `hybrid_cross_encoder` vs. `hybrid_voyage` on the same hybrid candidate pool per query against a dedicated `benchmark_reranking` collection; reports Recall@5, MRR, NDCG@5, latency, and a qualitative cost model

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

Standalone (not yet wired into the pipeline above): the Guardrails Platform (`app/ai/guardrails/`, Milestone 11.16) — input/retrieval/generation/runtime checks, `GuardrailService.evaluate()` as the future integration seam. Same posture the Validation Platform shipped with before its narrow slice was integrated into `GenerationService`.

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
| Phase 2.8 — Context Platform | 🟡 ~90% Complete (Parent Expansion, Adjacent Merge, Compression V1/V2, Guardrails V1, Citations, Prompt Formatter done; LangChain + LLM compression remain) |
| Phase 2.9 — Generation Platform | 🟡 ~75% Complete (Structured Output Integration, Validation Platform integration incl. input/output/hallucination validators + scoring, Regeneration, Prompt Platform bridge, Routing Platform done; runtime validators/contracts, caching, artifacts, /research API remain) |
| Milestone 11.16 — Guardrails Platform | ✅ Complete (MVP Foundation — input/retrieval/generation/runtime guardrails, Source Trust, policies, scoring, artifacts; standalone, not yet wired into the generation pipeline) |
| Benchmark Platform | ✅ Foundation Complete (incl. Retrieval, Metadata Filtering, Reranking Benchmarks) |

---

# Recently Completed

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

## Phase 2.8 — Context Platform (wrapping up) + Phase 2.9 — Generation Platform (~75% complete, in progress)

Parent Expansion, Adjacent Merge, Token Budget + Embedding Compression, Guardrails V1, Citations, and Prompt Formatter are all implemented (see Milestone 2.8 above), bringing the Context Platform to ~90% complete. Remaining scope to close it out:

- LangChain compression provider (V3 — `ContextualCompressionRetriever`)
- LLM compression provider (V4 — chunk-level relevant-summary compression)
- Forward `HybridRetrieveRequest.rerank` from the `/retrieve/hybrid` endpoint into `RetrievalService.search_hybrid` (it currently always uses the service's `rerank=True` default regardless of the request body)
- Retrieval result cache
- Scaling the retrieval benchmark dataset (5 → 20-50 documents, 20 → 100 queries, chunk-level relevance) — see `README.md` TODO

The **Generation Platform** (Milestone 2.9) is now ~75% complete (see Milestone 2.9 above): provider abstraction, Structured Output Integration (native decoding + parser fallback + Markdown/XML registry + LangChain `with_structured_output()`), Validation Platform integration (input/output/hallucination validators, registry, weighted scoring, `ValidationReport`), Regeneration Strategy, a provider-capability guard, Prompt Platform integration, and now a Routing Platform (scored model catalog, task-based strategies, capability/policy filtering, fallback chains — Milestone 2.9.7) are all done. Remaining before it's complete: `/research` API, streaming chat API, caching, artifact persistence, per-runtime Validation Contracts/Runtime Validators, and the remaining PRD output checks (completeness/consistency/formatting/response-size). Then Evaluation Platform expansion (Milestone 6) and a LangGraph-based Research Runtime (Milestone 7) follow.

The **Guardrails Platform** (Milestone 11.16, see above) is now complete as a standalone MVP foundation — input/retrieval/generation/runtime guardrails, a new Source Trust Platform, policies, weighted risk scoring, and artifact persistence. It is not yet wired into `GenerationService`, the context builder, or a router (the PRD's own "Generation Integration" is explicitly a later phase); `get_guardrail_service()` is the integration seam once that wiring is prioritized.

---

# Immediate Roadmap

```
Retrieval (dense + sparse + hybrid + parallel) ✅

↓

Metadata Filtering ✅

↓

Reranking ✅

↓

Context Platform (~90%) 🟡
  Parent Expansion ✅
  Adjacent Merge ✅
  Compression (Token Budget + Embedding) ✅ — LangChain / LLM compression ⏳
  Guardrails V1 ✅
  Citation Platform ✅
  Prompt Formatter ✅

↓

Generation Platform (~75%) 🟡
  Provider Abstraction (5 providers) ✅
  Structured Output Integration (native + fallback + registry + LangChain) ✅
  Validation Platform Integration (input/output/hallucination validators, registry, scoring, ValidationReport) 🟡 — runtime validators/contracts, completeness/consistency/formatting/response-size ⏳
  Regeneration Strategy ✅
  Provider Capability Guard ✅
  Routing Platform (scored catalog, task-based strategies, fallback chains) ✅
  Prompt Platform Integration ✅
  /research API, streaming chat, caching, artifacts ❌

↓

Guardrails Platform (Milestone 11.16) ✅ Foundation — standalone, not yet wired in
  Input Guardrails (Prompt Injection, Scope, PII) ✅
  Retrieval Guardrails (Context Sanitization, Source Trust, Citation Integrity) ✅
  Generation Guardrails (Faithfulness, Schema Enforcement, PII Leakage) ✅
  Runtime Guardrails (Budget, Loop Detection) ✅ — Tool Policy, Approval Gate interfaces only ⏳
  Wiring into GenerationService / context builder / a router ⏳

↓

Chat

↓

Evaluation Platform Expansion (NDCG, Groundedness, Faithfulness, Hallucinations, Citation Accuracy, E2E, Security)

↓

Research Runtime (Query Decomposition, Planner, Agents, Reviewer, Summarizer, LangGraph)

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

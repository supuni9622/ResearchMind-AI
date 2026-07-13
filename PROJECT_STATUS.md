# ResearchMind AI — Project Status

**Last Updated:** 2026-07-13

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

**Status:** 🟡 In Progress (Foundation Complete)

ResearchMind can now query the hybrid Qdrant index built in Milestone 2.6. Dense, sparse, and hybrid (RRF-fused) retrieval are implemented, benchmarked, and exposed via API. Metadata filtering, reranking, and the advanced retrieval strategies remain open.

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
- ❌ Parallel retrieval
- ❌ Parent/Child retrieval
- ❌ Query decomposition

## Result Processing

- ✅ Reciprocal Rank Fusion (RRF)
- ✅ Top-K selection
- ❌ Metadata filtering — `_build_filter` exists on the Qdrant provider but is currently a stub that always returns `None`; **recommended next milestone** (document_id, filename, owner_id, tags)
- ❌ Voyage AI reranking
- ❌ CrossEncoder reranking

## Performance

- ✅ Query embedding cache — Valkey-backed, TTL-based expiry, toggleable via `QUERY_EMBEDDING_CACHE_ENABLED`
- ❌ Retrieval result cache

## APIs

- ✅ `POST /api/v1/retrieve` — dense
- ✅ `POST /api/v1/retrieve/sparse` — sparse
- ✅ `POST /api/v1/retrieve/hybrid` — hybrid (RRF)
- ❌ `POST /research`
- ❌ Streaming chat
- ❌ Citations

## Retrieval Evaluation

Implemented

- `RetrievalBenchmark` — evaluates dense, sparse, and hybrid against a dedicated, reproducible Qdrant collection (`benchmark_retrieval`, dropped/recreated every run, never touches production data)
- Metrics: Recall@5/10/20, Precision@5/10, MRR, avg/P95/P99 latency, qualitative cost model — matches the ADR-020 required metric set
- 20-query hand-curated ground-truth dataset (`benchmarks/datasets/research-papers/retrieval_queries.json`), document-level relevance, 4 query categories (semantic, acronym, exact-keyword, code-entity)
- ❌ NDCG — explicitly deferred per ADR-020

**Finding:** on the current 5-document benchmark corpus, dense, sparse, and hybrid are statistically indistinguishable — Recall@5/10/20 = 1.0 for all three, and hybrid's MRR (0.925) was actually slightly *lower* than dense (0.95) or sparse (0.975) alone. The corpus is too small (5 documents, 20 queries, document-level relevance) to meaningfully stress any retriever or give RRF real ranking disagreement to resolve. This does not mean Hybrid Retrieval is ineffective — it means the benchmark can't yet answer that question. See the dataset-scaling and chunk-level-relevance TODO in `README.md`.

Documentation

- ADR-020 — Retrieval Evaluation First Development
- `docs/architecture/retrieval-benchmarking-strategy.md` — benchmark methodology, query categories, decision gate

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

Retrieval (dense + sparse + hybrid RRF fusion)
```

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
| Phase 2.7 — Retrieval Platform | 🟡 In Progress (Foundation Complete) |
| Benchmark Platform | ✅ Foundation Complete (incl. Retrieval Benchmark) |

---

# Recently Completed

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

## Phase 2.7 — Retrieval Platform (continued)

Semantic, sparse, and hybrid retrieval are implemented, benchmarked, and exposed via API (see Milestone 2.7 above). The remaining scope from ADR-019 splits into two candidate directions:

### Option A — Metadata Filtering (recommended next)

Support filtering retrieval by:

- `document_id`
- `filename`
- `owner_id`
- `tags`

`QdrantRetrievalProvider._build_filter` already exists as the integration point but is currently a stub that always returns `None`. This is what makes retrieval production-ready for multi-tenant/multi-document use (e.g. "search only within this workspace" or "search only this document").

### Also remaining

- Voyage AI Reranker / CrossEncoder reranking
- Parent/Child Retrieval
- Query Decomposition
- Retrieval result cache
- Scaling the retrieval benchmark dataset (5 → 20-50 documents, 20 → 100 queries, chunk-level relevance) — see `README.md` TODO

---

# Immediate Roadmap

```
Retrieval (dense + sparse + hybrid) ✅

↓

Metadata Filtering

↓

Reranking

↓

Research API

↓

Chat

↓

Citations
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

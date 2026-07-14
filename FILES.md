# File Map

Every file and folder in the ResearchMind-AI monorepo.
`(empty)` = file exists but has no content yet.

---

## Root

| File | Description |
|------|-------------|
| `.editorconfig` | (empty) |
| `.env` | Local development environment variables (gitignored) |
| `.env.example` | Template for `.env` — copy and fill in values |
| `.env.test` | Environment variables for the test suite (uses `researchmind_test` DB, `127.0.0.1` to avoid IPv6 issues) |
| `.gitignore` | Git ignore rules |
| `.pre-commit-config.yaml` | Pre-commit hooks: ruff check, ruff format, mypy |
| `.python-version` | Pinned Python version for uv/pyenv |
| `alembic.ini` | Alembic configuration (points to `alembic/env.py`) |
| `CHANGELOG.md` | Version changelog |
| `docker-compose.yml` | Local dev stack — PostgreSQL (5432), Valkey (6379), Qdrant (6333/6334) |
| `FILES.md` | This file — complete file and folder map |
| `LICENSE` | Project license |
| `phase-3-ai-runtime-roadmap.md` | Frozen v1.0 Retrieval & AI Runtime roadmap (Phase 3.1–3.10 — Retrieval Foundation through Evaluation Platform); architecture frozen, progress status tracked inline per phase |
| `PROJECT_STATUS.md` | Current milestone and progress tracker |
| `pyproject.toml` | Python project config: dependencies, ruff, mypy, pytest settings |
| `README.md` | Project overview, quickstart, auth guide, Alembic troubleshooting |
| `ROADMAP.md` | Feature and milestone roadmap |
| `SECURITY.md` | (empty) |
| `setup_commands.md` | Makefile-style shortcut commands (`docker compose up/down`) |
| `STRUCTURE.md` | High-level folder/file structure with layer descriptions |
| `DEV_GUIDE.md` | Step-by-step local development guide — setup, Alembic issues, Docker rules, auth testing |
| `test.txt` | Stray scratch file — can be deleted |

---

## `.claude/`

| File | Description |
|------|-------------|
| `settings.local.json` | Local Claude Code permission/tooling settings (gitignored-style local overrides) |

---

## `.github/`

| File | Description |
|------|-------------|
| `ISSUE_TEMPLATE/` | GitHub issue templates (directory, no files yet) |
| `workflows/ci.yml` | GitHub Actions CI pipeline |

---

## `.vscode/`

| File | Description |
|------|-------------|
| `extensions.json` | Recommended VS Code extensions |
| `settings.json` | Workspace settings (Python interpreter, formatter, etc.) |

---

## `agents/`

All subdirectories are empty — planned AI agent implementations.

| Directory | Purpose |
|-----------|---------|
| `evaluator/` | Evaluates research quality |
| `planner/` | Plans research strategy |
| `research/` | Core research agent |
| `reviewer/` | Reviews and critiques output |
| `shared/` | Shared agent utilities |
| `summarizer/` | Summarizes research findings |

---

## `alembic/`

| File | Description |
|------|-------------|
| `README` | Alembic usage notes |
| `env.py` | Alembic runtime config — async engine setup, model imports for autogenerate |
| `script.py.mako` | Template for new migration files |
| `versions/43dc35ceb875_debug.py` | Migration 1: creates `users` table + `updated_at` trigger |
| `versions/a97b3b8eee9f_create_documents_table.py` | Migration 2: creates `documents` table with FK to `users` |
| `versions/1b6e40f3a754_split_document_status_into_upload_.py` | Migration 3: splits the single `status` column into `upload_status` + `processing_status` (+ `processed_at`, `processing_error`) |

---

## `apps/`

### `apps/api/app/`

#### `ai/`

AI subsystem. Document processing, metadata/statistics enrichment, and upload (including duplicate detection) are implemented; most other subdirectories are still scaffolded and empty.

##### `ai/config/`

| File | Description |
|------|-------------|
| `__init__.py` | (empty) |
| `settings.py` | AI-specific configuration settings |

##### `ai/guardrails/`

| File | Description |
|------|-------------|
| `__init__.py` | (empty) |
| `policies.py` | (empty) |
| `scanners.py` | (empty) |

##### `ai/knowledge/`

| Directory | Status |
|-----------|--------|
| `cache/` | **Implemented** — Valkey-backed embedding cache + query-embedding cache, see below |
| `chunking/` | **Implemented** — see below |
| `embeddings/` | **Implemented** — see below |
| `indexing/` | **Implemented** — see below |
| `processing/` | **Implemented** — see below |
| `reranking/` | **Implemented** — Voyage AI + CrossEncoder providers; see below |
| `retrieval/` | **Implemented** — dense, sparse, hybrid (RRF), metadata filtering; see below |
| `upload/` | **Implemented** — see below |
| `vectorstores/` | **Implemented** — see below |

##### `ai/knowledge/cache/` — **Implemented**

Two independent caches, structurally parallel to each other. `embeddings/` sits in front of dense *document chunk* embedding generation so identical chunk text is never re-embedded with the same provider/model/configuration; `query_embeddings/` sits in front of dense *retrieval query* embedding generation for the same reason. Both follow the same pattern: an ABC, a `create.py` composition root that returns a Valkey-backed implementation or a `Null*` no-op based on a settings flag, and a TTL applied on every write so the cache can never grow unbounded.

| File | Description |
|------|-------------|
| `__init__.py` | Package marker |
| `embeddings/create.py` | `create_embedding_cache()` — composition root; returns `ValkeyEmbeddingCache` or `NullEmbeddingCache` based on `settings.embedding_cache_enabled` |
| `embeddings/interfaces.py` | `EmbeddingCache` ABC — `get_many()` / `set_many()` |
| `embeddings/key.py` | `build_embedding_cache_key()` — derives a stable cache key from provider, model, configuration fingerprint, and chunk text |
| `embeddings/null.py` | `NullEmbeddingCache` — no-op fallback when caching is disabled |
| `embeddings/valkey.py` | `ValkeyEmbeddingCache` — Redis-backed cache, honors `settings.embedding_cache_ttl_seconds`, fails open on Redis errors (treated as a full cache miss, never propagated) |
| `query_embeddings/create.py` | `create_query_embedding_cache()` — composition root; returns `ValkeyQueryEmbeddingCache` or `NullQueryEmbeddingCache` based on `settings.query_embedding_cache_enabled` |
| `query_embeddings/interfaces.py` | `QueryEmbeddingCache` ABC — `get()` / `set()` |
| `query_embeddings/key.py` | `build_query_embedding_cache_key()` — derives a stable cache key from provider, model, configuration fingerprint, and query text |
| `query_embeddings/null.py` | `NullQueryEmbeddingCache` — no-op fallback when caching is disabled |
| `query_embeddings/valkey.py` | `ValkeyQueryEmbeddingCache` — Redis-backed cache, honors `settings.query_embedding_cache_ttl_seconds` (default 24h — shorter than the 30-day document cache, since it only bounds Redis memory rather than tracking document freshness), fails open on Redis errors |

##### `ai/knowledge/chunking/` — **Implemented**

Chunking pipeline. Transforms a canonical `ProcessedDocument` into retrieval-ready `Chunk` objects and persists a full chunking run as a canonical `ChunkArtifact` (`chunks.json`). Structurally parallel to `processing/`: a provider registry behind a single service, plus a dedicated `artifacts/` sub-package for the persisted output. Fixed, Recursive (LangChain), and Markdown strategies are implemented; the enum already lists Hierarchical/Semantic/LLM/Adaptive for future providers.

| File | Description |
|------|-------------|
| `__init__.py` | (empty) |
| `base.py` | `BaseChunkingProvider[ConfigT]` — generic base class shared by every provider (config, version, configuration fingerprint); the legacy `_build_chunk` helper is superseded by `ChunkFactory` |
| `chunk_factory.py` | `ChunkFactory` — canonical `Chunk` mapper (`from_text()`); every provider builds chunks through this factory instead of constructing `Chunk` directly |
| `config.py` | `BaseChunkingConfig` (`chunk_size`/`chunk_overlap` + overlap-smaller-than-size validator), `FixedChunkingConfig`, `RecursiveChunkingConfig` (separators, `keep_separator`), `MarkdownChunkingConfig` (heading levels, `strip_headers`, `return_each_line`) |
| `enums.py` | `ChunkingStrategy` (fixed/recursive/markdown/hierarchical/semantic/llm/adaptive), `ChunkContentType` |
| `exceptions.py` | `ChunkingError` hierarchy — `ChunkingProviderNotFoundError`, `ChunkingValidationError` |
| `factory.py` | `create_chunking_registry()` — single place providers are constructed/registered; `create_chunking_service()` — composition root wrapping it in a `ChunkingService`. Both the Processing Platform and the Benchmark Platform depend on `create_chunking_registry()` rather than duplicating provider construction |
| `interfaces.py` | `ChunkingProvider` ABC |
| `models.py` | `Chunk` and its sub-models — `ChunkContent`, `ChunkStructure`, `ChunkStatistics`, `ChunkProvenance`, `ChunkExperiment` |
| `registry.py` | `ChunkingRegistry` — strategy → provider resolution |
| `service.py` | `ChunkingService` — validates the document (rejects empty/whitespace-only text via `ChunkingValidationError`), resolves the provider, delegates chunk generation |
| `providers/fixed.py` | `FixedChunkingProvider` — fixed-size overlapping character windows; stops once a window reaches the end of the text so the final chunk's overlap with its predecessor is never short |
| `providers/recursive.py` | `RecursiveChunkingProvider` — delegates to LangChain's `RecursiveCharacterTextSplitter`, encapsulating LangChain behind the provider so the rest of the app stays framework-independent |
| `providers/markdown.py` | `MarkdownChunkingProvider` — splits on Markdown headings (`MarkdownHeaderTextSplitter`) first, then recursively splits oversized sections, preserving heading hierarchy (`heading`, `heading_path`) on each chunk |
| `statistics/service.py` | `ChunkStatisticsService` — character/word/sentence counts, estimated token count (4-chars-per-token heuristic), average token length; shared by every provider |
| `artifacts/models.py` | `ChunkArtifact` — canonical persistence model for a full chunking run (`document`, `strategy`, `statistics`, `evaluation`, `chunks`), serialized to `chunks.json` |
| `artifacts/builder.py` | `ChunkArtifactBuilder` — builds a `ChunkArtifact` from a list of `Chunk`s |
| `artifacts/writer.py` | `ChunkArtifactWriter` — persists a `ChunkArtifact` to storage under `documents/{owner_id}/{document_id}/chunking/{strategy}/{artifact_id}/chunks.json` |
| `evaluators/` | (empty) — planned chunk quality evaluators |

##### `ai/knowledge/embeddings/` — **Implemented**

Embedding pipeline. Transforms a canonical `ChunkArtifact` into vector `Embedding` objects and persists a full embedding run as a canonical `EmbeddingArtifact` (`embeddings.json`). Structurally parallel to `chunking/`: a provider registry behind a single service, plus a dedicated `artifacts/` sub-package for the persisted output. Sentence Transformers, Voyage AI, and OpenAI providers are all implemented and registered.

| File | Description |
|------|-------------|
| `__init__.py` | (empty) |
| `base.py` | `BaseEmbeddingProvider[ConfigT]` — generic base class shared by every provider (config, version, configuration fingerprint) |
| `batching.py` | `EmbeddingBatcher` — lazily splits an iterable of chunks into fixed-size batches; shared by every provider that calls a batch-limited SDK (Sentence Transformers, Voyage AI, OpenAI) |
| `config.py` | `BaseEmbeddingConfig` (`batch_size`, `normalize_embeddings`), `SentenceTransformerEmbeddingConfig`, `VoyageAIEmbeddingConfig`, `OpenAIEmbeddingConfig` |
| `create.py` | `create_voyage_client()` / `create_openai_client()` — construct the real Voyage/OpenAI SDK clients from settings; `create_embedding_registry()` — single place providers are constructed/registered (Sentence Transformers, Voyage AI, OpenAI); `create_embedding_service()` — composition root wrapping it in an `EmbeddingService`. Both the Processing Platform and the Benchmark Platform depend on `create_embedding_registry()` rather than duplicating provider construction |
| `enums.py` | `EmbeddingProvider` (sentence_transformers/voyage_ai/openai/bge/instructor/nomic) |
| `exceptions.py` | `EmbeddingError` hierarchy — `EmbeddingProviderNotFoundError`, `EmbeddingValidationError`, `EmbeddingGenerationError` |
| `factory.py` | `EmbeddingFactory` — canonical `Embedding` mapper (`from_vector()`); every provider builds embeddings through this factory instead of constructing `Embedding` directly |
| `interfaces.py` | `EmbeddingProvider` ABC |
| `models.py` | `Embedding` and its sub-models — `EmbeddingVector`, `EmbeddingProvenance`, `EmbeddingProviderMetadata`, `EmbeddingStatistics`, `EmbeddingExperiment` |
| `registry.py` | `EmbeddingRegistry` — provider → implementation resolution |
| `service.py` | `EmbeddingService` — validates the chunk artifact (rejects empty/blank-text chunks via `EmbeddingValidationError`), resolves the provider, delegates embedding generation |
| `providers/sentence_transformers.py` | `SentenceTransformerEmbeddingProvider` — wraps the real `sentence-transformers` library, batches chunks via `EmbeddingBatcher`, encapsulating the library behind the provider so the rest of the app stays framework-independent |
| `providers/voyage.py` | `VoyageAIEmbeddingProvider` — wraps the Voyage AI SDK's `Client`, batches chunks via `EmbeddingBatcher`, coerces quantized int vectors to floats before building canonical embeddings |
| `providers/openai.py` | `OpenAIEmbeddingProvider` — wraps the OpenAI SDK's `OpenAI` client, batches chunks via `EmbeddingBatcher` |
| `artifacts/models.py` | `EmbeddingArtifact` — canonical persistence model for a full embedding run (`document`, `chunking`, `execution`, `statistics`, `evaluation`, `embeddings`), serialized to `embeddings.json` |
| `artifacts/builder.py` | `EmbeddingArtifactBuilder` — builds an `EmbeddingArtifact` from a `ChunkArtifact` and its generated embeddings |
| `artifacts/writer.py` | `EmbeddingArtifactWriter` — persists an `EmbeddingArtifact` to storage under `documents/{owner_id}/{document_id}/embeddings/{provider}/{artifact_id}/embeddings.json` |

##### `ai/knowledge/indexing/` — **Implemented**

Indexing Platform (ADR-018, ADR-019). Transforms an `EmbeddingArtifact` (dense vectors) plus its source `ChunkArtifact` (chunk text) into `VectorStoreRecord`s carrying both a dense vector and a sparse SPLADE vector, and upserts them into Qdrant via the Vector Store Platform. Persists a full indexing run as a canonical `IndexingArtifact` (`indexing.json`). ResearchMind does not run a separate BM25 platform — sparse vectors generated here are what Qdrant uses for native hybrid/lexical retrieval.

| File | Description |
|------|-------------|
| `__init__.py` | (empty) |
| `models.py` | `IndexingRequest` (`owner_id`, `operation`, `embedding_artifact`, `chunk_artifact`), `IndexingExecution`, `IndexingResult` |
| `enums.py` | `IndexType` (vector/bm25/knowledge_graph), `IndexStatus`, `IndexOperation` |
| `interfaces.py` | `IndexingServiceInterface` ABC — `index()`, `reindex()`, `delete()` |
| `exceptions.py` | `IndexingError` hierarchy — `InvalidIndexingRequestError`, `IndexingExecutionError`, `IndexProviderError`, `IndexArtifactError`, `SparseEmbeddingError` |
| `service.py` | `IndexingService` — validates the request, matches each dense embedding back to its source chunk by `chunk_id`, generates sparse vectors for the batch via `FastEmbedSparseEmbeddingProvider`, builds `VectorStoreRecord`s (dense + sparse + payload incl. real `chunk_index`), creates the Qdrant collection if missing, upserts, builds statistics, persists the artifact |
| `create.py` | `create_sparse_embedding_provider()` / `create_indexing_artifact_writer()` / `create_indexing_service()` — composition root |
| `providers/__init__.py` | (empty) |
| `providers/fastembed.py` | `FastEmbedSparseEmbeddingProvider` — wraps FastEmbed's `SparseTextEmbedding` (SPLADE, default model `prithivida/Splade_PP_en_v1`); inference is synchronous/CPU-bound so it runs via `asyncio.to_thread`; wraps failures in `SparseEmbeddingError` |
| `artifacts/models.py` | `IndexingArtifact` — canonical persistence model (`execution`, `vector_index` incl. `CollectionDefinition` + `IndexStatistics`), serialized to `indexing.json` |
| `artifacts/builder.py` | `IndexingArtifactBuilder` — builds an `IndexingArtifact` from an `IndexingExecution` + `IndexingResult` |
| `artifacts/writer.py` | `IndexingArtifactWriter` — persists an `IndexingArtifact` to storage under `documents/{owner_id}/{document_id}/indexing/{execution_id}/indexing.json` |

##### `ai/knowledge/processing/` — **Implemented**

| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `adapters/docling.py` | Docling adapter — alternative entry point into the Docling library |
| `parsers/base.py` | `BaseDocumentParser` abstract class |
| `parsers/docling.py` | Docling-backed parser implementation |
| `artifact_builder.py` | Builds `ProcessingArtifacts` from a `ProcessedDocument` |
| `artifact_writer.py` | Persists artifacts to storage (S3) |
| `artifacts.py` | `ProcessingArtifact` / `ProcessingArtifacts` models |
| `enums.py` | `DocumentFormat`, `ParserType`, `ProcessingStatus`, `ProcessingStage` |
| `exceptions.py` | `ProcessingError` hierarchy |
| `interfaces.py` | `DocumentParser` ABC, `ParseRequest` |
| `models.py` | `ProcessedDocument`, block types, `ProcessingResult` |
| `registry.py` | `ParserRegistry` — format → parser resolution |
| `service.py` | `ProcessingService` — orchestrates the full pipeline (parse → enrich → build/write artifacts → chunk → persist chunk artifacts → embed → persist embedding artifacts → index dense+sparse vectors into Qdrant → persist indexing artifacts) |
| `temporary_file_manager.py` | `TemporaryFileManager` — creates temp files from downloaded document bytes, preserves extension, cleans up after processing |

###### `ai/knowledge/processing/metadata/` — **Implemented**

Metadata enrichment pipeline. Providers enrich the canonical `ProcessedDocument` with additional metadata; each provider contributes without overwriting metadata owned by another provider.

| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `base.py` | `BaseMetadataProvider` — base implementation concrete providers should inherit from |
| `interfaces.py` | `MetadataProvider` ABC |
| `models.py` | `MetadataUpdate` model |
| `registry.py` | Metadata provider registry — registration and pipeline resolution |
| `service.py` | `MetadataEnrichmentService` — coordinates providers, enriches the document |
| `providers/__init__.py` | Package exports |
| `providers/language.py` | Detects primary document language via `langdetect`, run against extracted text (not the raw file) |
| `providers/pdf.py` | Extracts embedded PDF metadata via `pypdf`; reads metadata only, does not inspect content |

###### `ai/knowledge/processing/statistics/` — **Implemented**

Statistics enrichment pipeline, structurally parallel to `metadata/`. Providers enrich the canonical `DocumentStatistics` model.

| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `base.py` | `BaseStatisticsProvider` — base implementation for concrete providers |
| `interfaces.py` | `StatisticsProvider` ABC |
| `models.py` | `DocumentStatistics` model |
| `registry.py` | Statistics provider registry |
| `service.py` | `StatisticsEnrichmentService` — coordinates providers, enriches statistics |
| `providers/pdf.py` | PDF-specific statistics (currently: page count); structural stats (headings, tables, etc.) are deferred to a future Docling statistics provider |

##### `ai/knowledge/reranking/` — **Implemented**

Reranking Platform (ADR-022). Reorders a candidate pool of `RetrievedChunk`s using deeper (query, chunk) relevance scoring than embedding similarity alone provides. Structurally parallel to `retrieval/`: provider abstraction, registry, service, composition root — no separate `artifacts/` sub-package (reranking doesn't persist a canonical artifact). Wired into `RetrievalService.search_hybrid(rerank=True)` by default and benchmarked in `benchmarks/reranking/`.

| File | Description |
|------|-------------|
| `__init__.py` | (empty) |
| `base.py` | `BaseRerankingProvider` — shared `VERSION = "1.0.0"` / `version` property for every provider |
| `config.py` | `CrossEncoderConfig` (`model`, default `BAAI/bge-reranker-base`), `VoyageRerankerConfig` (`model`, default `rerank-2`) |
| `create.py` | `create_reranking_registry()` — constructs `CrossEncoderReranker` always, `VoyageReranker` only if `settings.voyage_api_key` is set (Voyage is optional); `create_reranking_service()` — composition root wrapping it in a `RerankingService` |
| `enums.py` | `RerankingProvider` (cross_encoder/voyage_ai) |
| `exceptions.py` | `RerankingError` hierarchy — `RerankingProviderNotFoundError`, `RerankingValidationError` |
| `interfaces.py` | `RerankingProviderInterface` ABC — `provider`, `version`, `rerank()` |
| `models.py` | `RerankingRequest` (`query`, `chunks: list[RetrievedChunk]`, `top_k`), `RerankedChunk` (`chunk`, `rerank_score`), `RerankingResult` (`chunks`, `duration_ms`) |
| `registry.py` | `RerankingRegistry` — provider → implementation resolution; `has()` lets callers check whether an optional provider (Voyage) was actually registered before using it |
| `service.py` | `RerankingService` — validates the request (empty query, empty chunks), resolves the provider, delegates to `rerank()` |
| `providers/__init__.py` | (empty) |
| `providers/cross_encoder.py` | `CrossEncoderReranker` — wraps `sentence_transformers.CrossEncoder` (local CPU inference, no marginal cost), scores `(query, chunk.content)` pairs, sorts descending, truncates to `top_k` |
| `providers/voyage.py` | `VoyageReranker` — wraps the Voyage AI SDK's `Client.rerank()` (imports `Client` from `voyageai.client` directly, mirroring the embedding provider's import, since `voyageai.Client` isn't a declared public re-export) |

##### `ai/knowledge/retrieval/` — **Implemented**

Retrieval Platform (ADR-018, ADR-019, ADR-020, ADR-021). Queries the hybrid Qdrant index built by the Indexing Platform. Dense (Voyage AI), sparse (FastEmbed SPLADE), hybrid (Reciprocal Rank Fusion of dense + sparse), and metadata filtering are all implemented, benchmarked (`benchmarks/retrieval/`), and exposed via API (`/retrieve`, `/retrieve/sparse`, `/retrieve/hybrid`) — all three endpoints now require authentication and force `owner_id` from the authenticated user rather than the request body. Parent/Child retrieval and Query Decomposition are not yet implemented — see `PROJECT_STATUS.md` Milestone 2.7.

| File | Description |
|------|-------------|
| `__init__.py` | (empty) |
| `base.py` | `BaseRetrievalProvider[ConfigT]` — generic base class shared by every provider (config, version, configuration fingerprint); mirrors `BaseEmbeddingProvider[ConfigT]` |
| `config.py` | `BaseRetrievalConfig` (`default_top_k`, `max_top_k`, `strategy`, `enable_runtime_metrics`) + `QdrantRetrievalConfig` (`collection_name`, `score_threshold`, `with_payload`, `with_vectors`, `search_batch_size`) |
| `create.py` | `create_retrieval_registry()` / `create_query_embedding_service()` / `create_sparse_query_embedding_service()` / `create_fusion_service()` / `create_retrieval_service()` — composition root; `create_retrieval_service()` now also wires in `create_reranking_service()` so `RetrievalService` can rerank hybrid results |
| `enums.py` | `RetrievalProvider` (qdrant), `RetrievalStrategy` (dense/sparse/hybrid/parent_child/query_decomposition), `RetrievalOperation` |
| `exceptions.py` | `RetrievalError` hierarchy — `RetrievalProviderNotFoundError`, `RetrievalValidationError`, `RetrievalExecutionError` |
| `interfaces.py` | `RetrievalProviderInterface` ABC — `provider`, `version`, `config`, `configuration_fingerprint`, `search()`, `search_sparse()` |
| `models.py` | `RetrievalQuery`, `RetrievedChunk`, `RetrievalStatistics`, `RetrievalExecution`, `RetrievalResult` (`statistics` is `None` until the service populates it after the provider returns) |
| `registry.py` | `RetrievalRegistry` — provider → implementation resolution; constructor takes the provider list directly (no separate `register()` method, unlike `EmbeddingRegistry`) |
| `service.py` | `RetrievalService` — validates (empty/whitespace query, max length, `top_k` bounds) and normalizes (whitespace collapsing) the query, then `search()` (dense), `search_sparse()`, and `search_hybrid(rerank=True)` (retrieves up to `min(top_k*5, 50)` candidates from both dense and sparse, fuses via RRF down to `top_k`, then reranks via Voyage AI by default when a `reranking_service` is configured); populates `RetrievalStatistics`/`RetrievalExecution` on the result |
| `providers/qdrant.py` | `QdrantRetrievalProvider` — `search()` queries the named `dense` Qdrant vector, `search_sparse()` queries the named `sparse` vector (both via `qdrant_client.query_points`, `using=`); `_build_filter()` translates canonical `RetrievalQuery.filters` (`owner_id`, `document_id`, `filename`, `language`) into a Qdrant `Filter`/`FieldCondition`/`MatchValue`, applied to both search methods; shared `_map_points()` static method maps Qdrant points → `RetrievedChunk` (missing optional payload fields default to `""`/`0`/`{}`) |
| `query/dense_service.py` | `QueryEmbeddingService` — generates dense query embeddings; checks the query embedding cache first, then dispatches to the Voyage AI or OpenAI provider SDK directly (reaching past the provider's own `.embed(ChunkArtifact)` interface, since that's shaped for document chunks, not raw query strings), coercing int vector values to float |
| `query/models.py` | `DenseQueryEmbedding`, `SparseQueryEmbedding` (`indices`, `values`) |
| `query/sparse_service.py` | `SparseQueryEmbeddingService` — wraps `FastEmbedSparseEmbeddingProvider.embed([query])` to produce a single `SparseQueryEmbedding` |
| `fusion/interfaces.py` | `FusionStrategy` ABC — `fuse(*, dense, sparse, top_k) -> RetrievalResult` |
| `fusion/models.py` | `FusionResult` (`chunk_id`, `score`, `dense_rank`, `sparse_rank`) — currently unused scaffold; `ReciprocalRankFusion` returns a `RetrievalResult` directly rather than a list of `FusionResult` |
| `fusion/rrf.py` | `ReciprocalRankFusion` — Reciprocal Rank Fusion, `score += 1 / (k + rank)` per result set, default `k=60` (matches the original paper and Elasticsearch/Azure AI Search defaults); keeps the first-seen copy of a chunk when it appears in both result sets |
| `fusion/service.py` | `RetrievalFusionService` — thin wrapper selecting the configured `FusionStrategy` (currently always RRF) |

##### `ai/knowledge/upload/` — **Implemented**

| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `constants.py` | Upload limits: max file size, allowed MIME types |
| `enums.py` | `UploadStatus` (pending/validated/stored/failed), `UploadSource` (api/web/cli/system) |
| `exceptions.py` | Upload-specific exceptions |
| `interfaces.py` | Abstract interfaces for the upload pipeline |
| `models.py` | Upload-related data models |
| `processing_job_builder.py` | `ProcessingJobBuilder` — builds the canonical `ProcessingJob` (document_id, owner_id, storage_key) from a persisted `Document` |
| `schemas.py` | Pydantic schemas for upload requests and responses |
| `service.py` | `UploadService` — orchestrates validate → duplicate check → hash → S3 upload → DB write → enqueue processing job (async); logs `document.uploaded` with duration, `document.processing_enqueued`, `document.upload_failed` with traceback |
| `storage.py` | Upload-specific storage helpers |
| `types.py` | Type aliases used across the upload module |
| `validators.py` | `UploadValidator` — validates filename, content type, file size; logs `upload.validation_failed` with `reason` field for each rule |

###### `ai/knowledge/upload/duplicate/` — **Implemented**

Duplicate document detection, checked during upload before storage/DB writes.

| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `exceptions.py` | `DuplicateDetectionError` base exception |
| `interfaces.py` | `DuplicateDetector` ABC — the upload workflow depends only on this abstraction |
| `models.py` | Request/response models exchanged between the upload workflow and the duplicate detection service |
| `service.py` | `DuplicateDetectionService` — determines whether a document already exists for a user based on its SHA-256 checksum (hash computation itself is delegated to `FileHasher`) |

##### `ai/knowledge/vectorstores/` — **Implemented**

Vector Store Platform (ADR-017, ADR-019). Provider-independent vector database abstraction — canonical `VectorStoreRecord`s in, provider SDK types never leak out. Qdrant is the only implemented provider; it stores a named `dense` vector and a named `sparse` vector per point in the same collection so Qdrant can serve native hybrid retrieval without a separate BM25 system.

| File | Description |
|------|-------------|
| `__init__.py` | (empty) |
| `models.py` | `VectorPayload`, `VectorStoreRecord` (`vector` + optional `sparse_vector`), `SparseVector` (`indices`, `values`), `CollectionDefinition`, `CollectionMetadata`, `IndexStatistics` (incl. `indexed_sparse_vectors`) |
| `enums.py` | `VectorStoreProvider` (qdrant/chromadb/pgvector/pinecone/weaviate — only qdrant implemented), `VectorDistanceMetric`, `VectorOperation` |
| `interfaces.py` | `VectorStoreProviderInterface` ABC — `create_collection`, `collection_exists`, `upsert`, `delete_document`, `count`, `collection_info` |
| `exceptions.py` | `VectorStoreError` hierarchy — `CollectionAlreadyExistsError`, `CollectionNotFoundError`, `VectorStoreValidationError`, `VectorIndexingError`, `VectorDeletionError`, `CollectionOperationError` |
| `base.py` | `BaseVectorStoreProvider[ConfigT]` — generic base shared by every provider (config, version, configuration fingerprint) |
| `config.py` | `BaseVectorStoreConfig` (`batch_size`, `create_collection_if_missing`) + `QdrantVectorStoreConfig` (collection name, distance metric, HNSW params, `on_disk_payload`), plus placeholder configs for Chroma/pgvector/Pinecone/Weaviate |
| `registry.py` | `VectorStoreRegistry` — provider → implementation resolution |
| `service.py` | `VectorStoreService` — validates records (rejects empty vectors), resolves the provider, delegates every operation |
| `create.py` | `create_qdrant_client()` / `create_vectorstore_registry()` / `create_vectorstore_service()` — composition root |
| `providers/qdrant.py` | `QdrantVectorStoreProvider` — creates collections with named `dense` + `sparse` vector configs (`DENSE_VECTOR_NAME`/`SPARSE_VECTOR_NAME` constants), converts records into `PointStruct`s carrying both named vectors, batches upserts, filters deletes by `document_id` payload field |
| `artifacts/` | `builder.py` / `models.py` / `writer.py` — all empty; unused scaffold, superseded by `indexing/artifacts/` |

##### `ai/quality/`

All subdirectories empty — planned evaluation and quality framework.

| Directory | Purpose |
|-----------|---------|
| `benchmarks/` | Performance benchmarks |
| `evaluation/` | LLM evaluation framework |
| `experiments/` | Experiment tracking |
| `regression/` | Regression test suite |
| `telemetry/` | Metrics and telemetry |
| `tracing/` | LangSmith / OTEL tracing |

##### `ai/registry/`

All files empty — planned model and provider registries.

| File | Purpose |
|------|---------|
| `embeddings.py` | (empty) |
| `evaluators.py` | (empty) |
| `mcp.py` | (empty) |
| `models.py` | (empty) |
| `prompts.py` | (empty) |
| `providers.py` | (empty) |
| `rerankers.py` | (empty) |

##### `ai/runtime/`

All subdirectories empty — planned inference runtime.

| Directory | Purpose |
|-----------|---------|
| `prompts/` | Runtime prompt management |
| `providers/` | Provider adapters |
| `registry/` | Runtime model registry |
| `routing/` | Request routing logic |
| `streaming/` | Streaming response handling |
| `structured_output/` | Structured output parsing |

##### `ai/shared/`

All files empty — planned shared AI types and interfaces.

| File | Purpose |
|------|---------|
| `exceptions.py` | (empty) |
| `interfaces.py` | (empty) |
| `models.py` | (empty) |
| `types.py` | (empty) |

---

#### `api/`

| File | Description |
|------|-------------|
| `deps.py` | (empty) — shared route dependencies placeholder |
| `v1/api.py` | Central router — includes all v1 sub-routers |
| `v1/admin.py` | (empty) |
| `v1/auth.py` | `POST /auth/callback` (Cognito code exchange) and `GET /auth/me` |
| `v1/chat.py` | (empty) |
| `v1/documents.py` | `GET /documents` — lists the current user's documents; `POST /documents/upload` — validates filename, measures file size, delegates to `UploadService` (upload now enqueues async processing instead of processing synchronously — the old inline `ProcessingService` call is commented out) |
| `v1/evaluation.py` | (empty) |
| `v1/feedback.py` | (empty) |
| `v1/health.py` | `GET /health` — checks PostgreSQL, Valkey, Qdrant connectivity |
| `v1/reports.py` | (empty) |
| `v1/retrieval.py` | `POST /retrieve` (dense), `POST /retrieve/sparse`, `POST /retrieve/hybrid` (RRF, reranks via Voyage AI by default) — all three require `Depends(get_current_user)` and build their `RetrievalQuery.filters` via `_scoped_filters()`, which always overwrites `owner_id` with the authenticated user's id (never trusts the request body); each asserts `result.statistics is not None` (guaranteed non-`None` by the time `RetrievalService` returns, but the field is `Optional` until then) before building the response |

---

#### `auth/`

| File | Description |
|------|-------------|
| `dependencies.py` | `get_current_user` FastAPI dependency — extracts Bearer token, verifies JWT, syncs user, binds `user_id` to structlog context |
| `jwt.py` | `JWTVerifier` — fetches JWKS from Cognito, validates signature/expiry/audience/issuer, asserts `token_use == "id"` |
| `providers/base.py` | `AuthenticationProvider` abstract base — defines contract for all identity providers |
| `providers/cognito.py` | AWS Cognito implementation — issuer URL, audience, JWKS URL, claims normalization |

---

#### `core/`

| File | Description |
|------|-------------|
| `constants.py` | Static application constants |
| `health.py` | Health check functions for PostgreSQL, Valkey, Qdrant; logs `health.degraded` and per-service warnings |
| `lifespan.py` | FastAPI lifespan — configures logging, runs migrations (`AUTO_MIGRATE`), initializes infrastructure, logs `app.starting` / `app.ready` / `app.shutdown_complete` |
| `logging.py` | Structlog configuration — stdlib bridge via `ProcessorFormatter`, environment-aware renderer (ConsoleRenderer in dev, JSON in production), silences noisy loggers |
| `settings.py` | Pydantic `Settings` — all env vars; includes `auto_migrate` flag, `queue_provider` (`QueueProvider.VALKEY` default), `sqs_queue_url`, `queue_max_attempts`, `qdrant_url`/`qdrant_collection_name`, `embedding_cache_enabled`/`embedding_cache_ttl_seconds`, `query_embedding_cache_enabled`/`query_embedding_cache_ttl_seconds` (default 24h), `sparse_embedding_model` (default `prithivida/Splade_PP_en_v1`), `cross_encoder_model` (default `BAAI/bge-reranker-base`), `voyage_reranker_model` (default `rerank-2`) |
| `setup.py` | App factory and setup helpers |

---

#### `bootstrap/` — **Implemented**

| File | Description |
|------|-------------|
| `worker.py` | Application composition root for the worker process — `create_processing_worker(session)` wires up storage, parser/metadata/statistics registries, the Chunking Platform (`create_chunking_service()`, `ChunkArtifactBuilder`, `ChunkArtifactWriter`), the Embedding Platform (`create_embedding_service()`, `EmbeddingArtifactBuilder`, `EmbeddingArtifactWriter`), the Indexing Platform (`create_indexing_service()`, `IndexingArtifactBuilder`, `IndexingArtifactWriter`), `ProcessingService`, `DocumentProcessingService`, `QueuedDocumentProcessingService`, and the configured queue into a `ProcessingWorker` |

---

#### `db/`

| File | Description |
|------|-------------|
| `base.py` | SQLAlchemy `DeclarativeBase` |
| `mixins.py` | `TimestampMixin` — adds `created_at` and `updated_at` to models |
| `postgres.py` | Async PostgreSQL engine factory |
| `qdrant.py` | Qdrant vector store async client factory |
| `session.py` | Async session factory and `get_db` dependency |
| `valkey.py` | Valkey (Redis) async client factory |

---

#### `dependencies/`

| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `cache.py` | (empty) |
| `database.py` | (empty) |
| `settings.py` | (empty) |
| `upload.py` | FastAPI dependency providers for the upload/processing workflow: `get_document_storage`, `get_file_hasher`, `get_document_repository`, `get_processing_queue`, `get_processing_service` (now also wires the Chunking Platform — `_get_chunking_service`, `_get_chunk_artifact_builder`, `ChunkArtifactWriter` — the Embedding Platform — `_get_embedding_service`, `_get_embedding_artifact_builder`, `EmbeddingArtifactWriter` — and the Indexing Platform — `_get_indexing_service`, `_get_indexing_artifact_builder`, `IndexingArtifactWriter`), `get_document_processing_service`, `get_queued_document_processing_service`, `get_upload_service`, `get_processing_worker` |
| `reranking.py` | `get_reranking_service()` — `@lru_cache`d singleton, wraps `create_reranking_service()` |
| `retrieval.py` | `get_retrieval_service()` — `@lru_cache`d singleton, wraps `create_retrieval_service()` |
| `vector_store.py` | (empty) |

---

#### `exceptions/`

| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `auth.py` | (empty) |
| `base.py` | `AppException` base class + `NotFoundException`, `ValidationException`, `ConflictException`, `UnauthorizedException` |
| `document.py` | (empty) |
| `handlers.py` | Global FastAPI exception handlers — `AppException` → `app.exception` warning, `RequestValidationError` → `app.validation_error` warning with field errors, unhandled → `app.unhandled_exception` with traceback |
| `health.py` | (empty) |
| `research.py` | (empty) |

---

#### `infrastructure/`

##### `infrastructure/aws/`

| File | Description |
|------|-------------|
| `__init__.py` | (empty) |
| `session.py` | AWS session / boto3 client factory |

##### `infrastructure/hashing/`

| File | Description |
|------|-------------|
| `__init__.py` | Package exports (`SHA256Hasher`, `FileHasher`) |
| `exceptions.py` | Hashing-specific exceptions |
| `interfaces.py` | `FileHasher` abstract interface |
| `sha256.py` | `SHA256Hasher` — async SHA-256 file hashing via `asyncio.to_thread`; logs `hasher.sha256_complete` with `bytes_read` and `duration_ms` |

##### `infrastructure/metrics/`

| File | Description |
|------|-------------|
| `__init__.py` | (empty) |
| `interfaces.py` | `MetricsEmitter` abstract interface |
| `models.py` | (empty) |
| `noop.py` | No-op metrics emitter (used when no metrics backend is configured) |
| `upload.py` | Upload-specific metrics definitions |

##### `infrastructure/queue/` — **Implemented** (ADR-011, ADR-012)

Async queue abstraction backing asynchronous document processing. `UploadService` enqueues jobs; `apps/worker` consumes them.

| File | Description |
|------|-------------|
| `__init__.py` | Package marker |
| `enums.py` | `QueueProvider` StrEnum — `VALKEY`, `SQS` |
| `exceptions.py` | `QueueError` hierarchy — `QueueConnectionError`, `QueueEnqueueError`, `QueueDequeueError`, `QueueAcknowledgeError`, `QueueRejectError` |
| `factory.py` | `create_processing_queue(settings)` — selects `ValkeyQueue` or `SQSQueue` based on `settings.queue_provider` |
| `interfaces.py` | `ProcessingQueue` ABC — `enqueue`, `dequeue`, `acknowledge`, `reject`, `retry` |
| `models.py` | `ProcessingJob` (document_id, owner_id, storage_key, attempt, created_at), `QueueMessage` (job + provider metadata) |
| `providers/__init__.py` | Package marker |
| `providers/sqs.py` | `SQSQueue` — Amazon SQS implementation via boto3 run in `asyncio.to_thread`; `reject`/`retry` rely on SQS redrive policy for dead-lettering |
| `providers/valkey.py` | `ValkeyQueue` — Redis List-backed implementation; `reject` pushes to a `<queue>-dlq` dead-letter list and logs `queue.dead_letter`; `ping()` for health checks |

##### `infrastructure/storage/`

| File | Description |
|------|-------------|
| `__init__.py` | Package exports (`DocumentStorage`, `create_storage`) |
| `exceptions.py` | `StorageUploadError`, `StorageDownloadError`, `StorageDeleteError`, `StorageNotFoundError` |
| `factory.py` | `create_storage(settings)` factory — selects backend based on config |
| `interfaces.py` | `DocumentStorage` abstract interface — upload, download, delete, exists, generate_presigned_url |
| `key_generator.py` | `StorageKeyGenerator` — generates deterministic S3 object keys |
| `models.py` | Storage-related data models |
| `s3.py` | `S3StorageService` — AWS S3 implementation via `asyncio.to_thread`; logs each operation with key and `duration_ms`; logs failures with reason |

---

#### `main.py`

FastAPI application entry point — creates the app, registers middleware and exception handlers.

---

#### `middleware/`

| File | Description |
|------|-------------|
| `__init__.py` | Package docstring |
| `cors.py` | CORS middleware configuration — allows `frontend_url` origin |
| `request_id.py` | Generates `X-Request-ID` UUID per request and sets it on `request.state` |
| `request_logging.py` | Generates `request_id` (fixing middleware ordering bug), binds `request_id`/`method`/`path`/`client` to contextvars; logs `http.request` with `user_agent`/`query` and `http.response` with `status`/`duration_ms` |
| `request_timing.py` | Sets `X-Process-Time` response header |

---

#### `models/`

| File | Description |
|------|-------------|
| `__init__.py` | Exports all models (required so Alembic autogenerate can detect them) |
| `document.py` | `Document` SQLAlchemy model — id, owner_id (FK→users), filename, storage_key, content_type, size_bytes, checksum, `upload_status`, `processing_status`, `processed_at`, `processing_error` |
| `enums.py` | `DocumentUploadStatus` StrEnum (pending, uploading, completed, failed) and `DocumentProcessingStatus` StrEnum (pending, processing, completed, failed) — split from the original single `DocumentStatus` |
| `user.py` | `User` SQLAlchemy model — id, auth_provider, provider_user_id, email, username, full_name, avatar_url, is_active, is_verified, is_superuser, last_login_at |

---

#### `repositories/`

| File | Description |
|------|-------------|
| `__init__.py` | Exports `UserRepository` |
| `document.py` | `DocumentRepository` — CRUD operations for documents |
| `user.py` | `UserRepository` — get by id/email/provider_user_id, create, update, delete, exists |

---

#### `routers/`

Empty directory — placeholder.

---

#### `schemas/`

| File | Description |
|------|-------------|
| `__init__.py` | (empty) |
| `auth.py` | `CallbackRequest` (code, redirect_uri, code_verifier), `TokenResponse` (id_token, access_token, refresh_token, expires_in) |
| `chat.py` | Chat request/response schemas |
| `common.py` | Shared schemas: `SuccessResponse`, `ErrorDetail`, `ErrorResponse` |
| `document.py` | Document request/response schemas |
| `error.py` | Error response schemas |
| `health.py` | Health check response schemas |
| `report.py` | (empty) |
| `retrieval.py` | `BaseRetrieveRequest` (`query`, `top_k`, `filters`) subclassed by `DenseRetrieveRequest`, `SparseRetrieveRequest`, and `HybridRetrieveRequest` (adds `rerank: bool = True`, not yet forwarded by the `/retrieve/hybrid` endpoint); `RetrievedChunkResponse` (`chunk_id`, `document_id`, `filename`, `chunk_index`, `content`, `score` — does not expose `owner_id`), `RetrieveResponse` (`query`, `total_chunks`, `duration_ms`, `chunks`) |

---

#### `services/`

| File | Description |
|------|-------------|
| `__init__.py` | Package marker |
| `auth.py` | `AuthService.exchange_code()` — POSTs to Cognito `/oauth2/token`, supports PKCE and confidential clients; logs exchange start/success/failure |
| `document_processing_service.py` | `DocumentProcessingService` — orchestrates the processing lifecycle and persists status transitions (PROCESSING → COMPLETED/FAILED) |
| `queued_document_processing_service.py` | `QueuedDocumentProcessingService` — bridges the queue to the processing pipeline: resolves the `Document` for a `ProcessingJob`, builds the `ParseRequest`, and invokes `DocumentProcessingService` |
| `user.py` | `UserService` — `sync_user`, `create_user`, `get_user_by_id/email`, `update_last_login`, `deactivate_user`; logs all lifecycle events including `user.not_found` and `user.deactivated` |

---

## `apps/web/`

Next.js 15 frontend — **implemented** (Cognito auth, dashboard, documents, research chat scaffolding).

| File | Description |
|------|-------------|
| `.env.local` | Cognito client ID, domain, redirect URI, API URL |
| `.env.local.example` | Template for `.env.local` |
| `.gitignore` | Frontend-specific git ignore rules |
| `eslint.config.mjs` | ESLint configuration |
| `next-env.d.ts` | Next.js TypeScript environment declarations (generated) |
| `next.config.ts` | Next.js configuration |
| `package.json` | Next.js 15, React 19, Tailwind 3, TypeScript dependencies |
| `postcss.config.mjs` | PostCSS configuration (Tailwind) |
| `README.md` | Setup instructions and auth flow diagram |
| `tailwind.config.ts` | Custom palette: ink, stone, sage, amber scales |
| `tsconfig.json` | TypeScript configuration |
| `tsconfig.tsbuildinfo` | TypeScript incremental build cache (generated) |
| `src/app/(app)/dashboard/page.tsx` | Dashboard page |
| `src/app/(app)/documents/page.tsx` | Document upload page (drag-and-drop) |
| `src/app/(app)/research/page.tsx` | Research chat interface |
| `src/app/(app)/layout.tsx` | `AppShell` — auth guard, redirects unauthenticated users |
| `src/app/auth/callback/page.tsx` | Cognito OAuth callback — exchanges code for token |
| `src/app/globals.css` | Global styles |
| `src/app/layout.tsx` | Root layout — fonts, `AuthProvider` |
| `src/app/page.tsx` | Landing / sign-in page |
| `src/components/auth/login-button.tsx` | Cognito hosted UI redirect button |
| `src/components/layout/sidebar.tsx` | App sidebar navigation |
| `src/hooks/use-auth.tsx` | `AuthContext` — token storage, profile fetch, `isUnauthorized` state |
| `src/lib/api.ts` | Typed API client (`UserProfile`, `Document`) |
| `src/lib/auth.ts` | Cognito URL builders, token storage (sessionStorage) |
| `src/lib/errors.ts` | `extractErrorMessage` — maps an `ErrorResponse`/`ErrorDetail` body (from `app/schemas/common.py`) to a display string |

## `apps/worker/` — **Implemented** (ADR-012)

Standalone background worker process that consumes document processing jobs from the queue asynchronously, decoupling upload from processing.

| File | Description |
|------|-------------|
| `__init__.py` | Package marker |
| `main.py` | Entry point (`python -m apps.worker.main`) — builds the worker via `create_processing_worker`, registers `SIGINT`/`SIGTERM` handlers for graceful shutdown, runs until stopped |
| `metrics.py` | `WorkerMetrics` dataclass — in-memory counters (processed/successful/failed/retried/dead-lettered jobs, average processing time), reset on restart |
| `processing_worker.py` | `ProcessingWorker` — polls the queue, delegates to `QueuedDocumentProcessingService`, retries failed jobs up to `settings.queue_max_attempts` before dead-lettering, logs periodic `processing_worker.metrics`, supports graceful `stop()` |

---

## `benchmarks/` — **Implemented**

Engineering Benchmark Platform — an offline framework for comparing competing AI implementations (chunking strategies, embedding providers, dense/sparse/hybrid retrieval, metadata filtering, reranking) against version-controlled datasets. Deliberately separate from automated tests (which verify correctness) and from the planned Runtime Evaluation / Experimentation platforms (which observe or replay the *production* pipeline). Executed manually via `uv run python -m benchmarks.runner <name> --dataset <path>`.

| File | Description |
|------|-------------|
| `README.md` | Platform overview — goals, testing-vs-benchmarking philosophy, relationship to Runtime Evaluation and the Experimentation Platform, repository layout, report format, usage. "Current" category list now includes Embeddings; `Usage` documents the actual `python -m benchmarks.runner <name> --dataset <path>` invocation |
| `runner.py` | CLI entry point (`python -m benchmarks.runner <benchmark> --dataset <path> [--output <path>]`) — resolves the benchmark from `create_benchmark_registry()`, runs it, writes `report.md` + `report.json` |
| `factory.py` | `create_benchmark_registry()` — composition root; constructs each benchmark (currently: `ChunkingBenchmark`, `EmbeddingBenchmark`, `RetrievalBenchmark`, `MetadataFilteringBenchmark`, `RerankingBenchmark`) and registers it with a `BenchmarkRegistry`; the latter three each get their own dedicated Qdrant collection (`benchmark_retrieval`/`benchmark_retrieval_filtering`/`benchmark_reranking`) so runs never interfere with each other |
| `registry.py` | `BenchmarkRegistry` — name → benchmark resolution (keyed by `Benchmark.name.lower()`) |
| `interfaces/benchmark.py` | `Benchmark` ABC — `name` property, `run(dataset_path) -> BenchmarkReport` |
| `models/report.py` | Canonical report models — `BenchmarkCandidate` (one implementation's metrics), `BenchmarkDataset`, `BenchmarkReport` |
| `common/dataset_loader.py` | `DatasetLoader` — loads every `ProcessedDocument` from a dataset directory (`<paper>/processed_document.json`) |
| `common/report_generator.py` | `BenchmarkReportGenerator` — renders a `BenchmarkReport` as Markdown (comparison table + per-candidate sections) or JSON |
| `common/metrics.py` | `average()` / `percentile()` — shared statistical helpers (mean, nearest-rank percentile), extracted out of `retrieval/benchmark.py` once `reranking/benchmark.py` needed the same logic |
| `common/report.py` | (empty) — superseded by `models/report.py` |
| `common/timer.py` | `Timer` — dependency-free, high-resolution timer (`start()`/`stop()`/`elapsed_seconds`/`elapsed_milliseconds`); also usable as a context manager (`with Timer() as timer:`) |
| `chunking/benchmark.py` | `ChunkingBenchmark` — runs every registered chunking provider over the same document set and aggregates chunk-count/size/word/token metrics per strategy |
| `chunking/report_generator.py` | `ChunkingBenchmarkReportGenerator` — currently a thin subclass of the generic `BenchmarkReportGenerator`; placeholder for chunking-specific visualizations |
| `chunking/reports/chunking/report.{md,json}` | Checked-in example output from a real `chunking` benchmark run (Fixed vs. Recursive vs. Markdown over the research-papers dataset) |
| `embeddings/benchmark.py` | `EmbeddingBenchmark` — chunks every document once (fixed `RECURSIVE` strategy, so every provider embeds identical input), then runs each registered embedding provider (Sentence Transformers, Voyage AI, OpenAI) against those chunks, timing latency/throughput/dimensions via `Timer`. Wraps each provider's run in its own try/except so one provider failing (e.g. a Voyage AI rate limit) is recorded as a `notes.error` on that candidate rather than aborting the whole report |
| `embeddings/report_generator.py` | `EmbeddingBenchmarkReportGenerator` — thin subclass of the generic `BenchmarkReportGenerator`; placeholder for embedding-specific visualizations |
| `embeddings/reports/embeddings/report.{md,json}` | Checked-in example output from a real `embeddings` benchmark run — Sentence Transformers completed all 5 documents (1481 chunks, 384-dim); Voyage AI completed 1 of 5 documents before hitting the configured account's free-tier rate limit (3 RPM), captured as a candidate-level error note |
| `retrieval/benchmark.py` | `RetrievalBenchmark` — builds a dedicated, reproducible Qdrant collection (`benchmark_retrieval`, dropped/recreated every run via `BenchmarkRetrievalIndexer`, never touches production data), then evaluates 3 candidates (dense, sparse, hybrid) against the 20-query ground-truth dataset, reporting Recall@5/10/20, Precision@5/10, MRR, avg/P95/P99 latency, a qualitative cost model, and a per-category Recall@10 breakdown — matches the ADR-020 required metric set |
| `retrieval/dataset.py` | `RetrievalBenchmarkQuery`, `RetrievalQueryDataset`, `load_retrieval_queries()` — loads/validates `retrieval_queries.json` |
| `retrieval/indexer.py` | `BenchmarkRetrievalIndexer` — chunks the benchmark corpus, embeds dense (Voyage AI) + sparse (FastEmbed SPLADE), builds `VectorStoreRecord`s, and upserts into the dedicated benchmark collection; deliberately doesn't reuse `IndexingService` since that's hardwired to `settings.qdrant_collection_name` |
| `retrieval/metrics.py` | `recall_at_k()` / `precision_at_k()` / `reciprocal_rank()` / `ndcg_at_k()` — pure, document-level relevance functions; a ranked (possibly duplicate-containing) list of retrieved chunk filenames is first collapsed to a ranked list of unique documents by first occurrence before computing each metric. `ndcg_at_k` uses binary relevance (standard DCG/IDCG, `log2(rank+1)` discount) |
| `retrieval/metadata_filtering_benchmark.py` | `MetadataFilteringBenchmark` — assigns each benchmark document its own synthetic `owner_id` (via `BenchmarkRetrievalIndexer`'s optional `owner_ids_by_document_id` param), then compares unfiltered vs. owner-filtered dense/sparse/hybrid search per query against a dedicated `benchmark_retrieval_filtering` Qdrant collection. Reports Recall@5/10/20, Precision@5/10, MRR, latency, and `leakage_rate` (fraction of returned chunks belonging to the wrong owner — the benchmark's correctness signal, expected to be exactly 0.0 for filtered candidates); queries whose relevant documents span more than one owner are skipped (a single equality filter can't select multiple owners) |
| `reranking/benchmark.py` | `RerankingBenchmark` — computes one shared hybrid (dense+sparse, RRF-fused) candidate pool per query against a dedicated `benchmark_reranking` collection, then scores three candidates against that same pool: `hybrid_only` (no reranking), `hybrid_cross_encoder`, `hybrid_voyage`. Reports Recall@5, MRR, NDCG@5, latency, and a qualitative `cost_model` note; `hybrid_voyage` degrades to a `skipped` note (rather than failing the run) if `VOYAGE_API_KEY` isn't configured |
| `pipeline/benchmark.py` | `PipelineBenchmark` — end-to-end ingestion pipeline benchmark. Pushes every dataset document through the real Chunking → Embedding (Voyage AI) → Indexing (dense+sparse, Qdrant) services, aborting immediately on any failure rather than skipping. Has its own CLI entry point (`python -m benchmarks.pipeline.benchmark`) rather than going through `runner.py`, because its report shape (rich per-document/aggregate/throughput/storage/memory metrics) doesn't fit the candidate-comparison `BenchmarkReport` model |
| `pipeline/dataset.py` | `load_pipeline_dataset()` — loads each dataset entry's `ProcessedDocument` plus its source JSON size |
| `pipeline/models.py` | `PipelineBenchmarkReport` and sub-models: `DocumentPipelineResult`, `ChunkingMetrics`, `EmbeddingMetrics`, `IndexingMetrics` (`vector_count`, `sparse_vector_count`, `sparse_embedding_model`, `collection_name`), `ArtifactSizes`, `StatSummary`, `ThroughputSummary`, `StorageSummary`, `MemorySummary`, `SuccessReport`, `Observations` (incl. `average_sparse_vectors_generated`), `ProductionReadiness` |
| `pipeline/pipeline_runner.py` | `run_document_pipeline()` — runs one document through the real pipeline and collects `RuntimeMetricsCollector` timings; records both dense (`indexed_vectors`) and sparse (`indexed_sparse_vectors`) vector counts from the `IndexingResult` |
| `pipeline/report_generator.py` | `PipelineReportGenerator` — renders `PipelineBenchmarkReport` as Markdown (environment, dataset, per-document table incl. dense/sparse vector columns, aggregate stats, pipeline timing, storage, throughput, memory, success, observations, production readiness) |
| `pipeline/services.py` | `PipelineServices` / `create_pipeline_services()` — constructs the real Chunking/Embedding/Indexing services via their production composition roots (mirrors `app.bootstrap.worker`), so the benchmark exercises the real object graph |
| `pipeline/stats.py` | `summarize()` — average/minimum/maximum/median/p95 for a list of metric values |
| `datasets/README.md` | Benchmark dataset philosophy — deterministic, version-controlled, immutable once published; documents the `processed_document.json`-per-paper layout |
| `datasets/research-papers/paper-00{1-5}/processed_document.json` | Canonical `ProcessedDocument` fixtures — the current benchmark corpus (5 research papers) |
| `datasets/research-papers/retrieval_queries.json` | 20-query hand-curated ground truth for the Retrieval Benchmark — document-level relevance, 4 categories (5 each: semantic, acronym, exact_keyword, code_entity), grounded in the actual content of the 5 benchmark papers |
| `reports/.gitkeep` | Placeholder keeping the default `--output` directory tracked in git |
| `reports/ingestion-benchmark-report.md` | Checked-in example output from a real `pipeline` benchmark run (5 research papers) — includes dense + sparse vector counts and the SPLADE model used; indexing is now the dominant per-document latency cost (SPLADE CPU inference), not embedding |
| `reports/ingestion-benchmark.json` | Same run, machine-readable |
| `reports/retrieval/report.{md,json}` | Checked-in example output from a real `retrieval` benchmark run — dense/sparse/hybrid all hit Recall@5/10/20 = 1.0 on the current 5-document corpus (too small/easy to distinguish candidates); hybrid's MRR (0.925) was slightly lower than dense (0.95) or sparse (0.975) alone |
| `reports/metadatafiltering/report.{md,json}` | Checked-in example output from a real `metadatafiltering` benchmark run — `leakage_rate: 0.0` for every filtered candidate (vs. 0.16–0.21 unfiltered), MRR raised to 1.0 for dense/sparse/hybrid |
| `reports/reranking/report.{md,json}` | Checked-in example output from a real `reranking` benchmark run — Recall@5 unchanged by reranking (already 1.0), MRR/NDCG@5 both improved substantially (MRR 0.925 → 1.0 CrossEncoder / → 0.95 Voyage) |

---

## `datasets/`

| Directory | Purpose |
|-----------|---------|
| `golden/` | Ground-truth / golden datasets for evaluation |
| `processed/` | Cleaned and processed data |
| `raw/` | Raw ingested data |

All empty.

---

## `docs/`

### `docs/adrs/` — Architecture Decision Records

| File | Description |
|------|-------------|
| `README.md` | ADR index |
| `ADR-001-monorepo.md` | Decision: monorepo structure |
| `ADR-002-fastapi.md` | Decision: FastAPI as the web framework |
| `ADR-003-fastapi-lifespan.md` | Decision: lifespan for startup/shutdown |
| `ADR-004-application-state.md` | Decision: app state for shared resources |
| `ADR-005-api-contracts.md` | Decision: typed Pydantic schemas for all API contracts |
| `ADR-006-settings-vs-constants.md` | Decision: separating env-driven settings from static constants |
| `ADR-007-middleware-registration.md` | Decision: middleware registration pattern |
| `ADR-008-typed-api-schemas.md` | Decision: explicit response models on all endpoints |
| `ADR-009-identity-architecture` | Decision: external identity provider (Cognito), ResearchMind owns users not auth |
| `ADR-010-document-processing-strategy.md` | Decision: document processing pipeline strategy (Docling-based parsing) |
| `ADR-011-queue-abstraction.md` | Decision: queue abstraction for asynchronous document processing (SQS/Valkey-backed) |
| `ADR-012-asynchronous-document-processing.md` | Decision: move document processing off the upload request path into a standalone worker consuming the queue |
| `ADR-013-canonical-chunk-model.md` | Decision: canonical `Chunk` model — the framework-independent knowledge unit consumed by embeddings/retrieval/reranking/citation/evaluation |
| `ADR-014-chunking-provider-architecture.md` | Decision: chunking provider architecture — registry-based strategy pattern supporting multiple simultaneous chunking strategies |
| `ADR-015-canonical-ai-platform-pipeline.md` | Decision: every AI platform consumes the canonical artifact produced by the previous platform — the pipeline communicates only through artifacts, never provider SDK types |
| `ADR-016-observability-platform.md` | Decision: Observability is a first-class platform within the AI Engineering Platform, not an afterthought bolted onto individual services |
| `ADR-017-vector-store-platform.md` | Decision: Vector Store Platform architecture — provider-independent abstraction over vector databases; Qdrant as the first implemented provider |
| `ADR-018-knowledge-indexing-and-retrieval-architecture.md` | Decision: split Indexing and Retrieval into two independent platforms; Hybrid Retrieval, multiple retrieval strategies, reranking, metadata filtering, caching, and evaluation are all MVP scope, not future work |
| `ADR-019-qdrant-native-hybrid-retrieval.md` | Decision: no separate BM25 platform — generate FastEmbed SPLADE sparse vectors alongside Voyage AI dense vectors and index both into the same Qdrant collection for native hybrid retrieval |
| `ADR-020-retrieval-evaluation-first-development.md` | Decision: every retrieval enhancement must demonstrate measurable improvement (Recall@K, Precision@K, MRR, latency, cost) against a benchmark before becoming part of the canonical architecture; frozen |
| `ADR-021-hybrid-retrieval-architecture.md` | Decision: Hybrid Retrieval fuses dense + sparse via Reciprocal Rank Fusion implemented at the application layer (not Qdrant-native fusion) — trades a small latency cost for observability, benchmarking flexibility, and easier experimentation (e.g. future weighted RRF) |
| `ADR-022-reranking-platform.md` | Decision: Reranking Platform architecture — provider abstraction (Voyage AI + local CrossEncoder) reordering a hybrid candidate pool via deeper (query, chunk) relevance scoring than embedding similarity alone |
| `ADR-023-framework-integration-strategy.md` | Decision: what ResearchMind builds itself vs. delegates to mature ecosystem frameworks (LangChain, LangGraph, LangSmith) — "Platform-Owned Architecture + Framework-Powered Runtime" |

---

### `docs/ai/` — AI Feature Documentation

| File | Description |
|------|-------------|
| `1.knowledge_platform/1.1.doc_upload.md` | Document upload feature spec |
| `1.knowledge_platform/1.2.doc_storage.md` | Document storage design |
| `1.knowledge_platform/1.3.doc_validation` | Document validation rules |
| `1.knowledge_platform/1.4.doc_upload_flow.md` | End-to-end upload flow diagram and explanation |
| `1.knowledge_platform/1.5.doc_upload_observability.md` | Upload observability: logging, metrics, tracing |
| `1.knowledge_platform/1.6.doc_upload_final.md` | Upload feature final summary |
| `1.knowledge_platform/1.7.doc_upload_archotecture.md` | Upload architecture deep-dive |
| `1.knowledge_platform/1.8.doc_upload_implementation.md` | Upload implementation reference |
| `1.knowledge_platform/2.2.doc_processing.md` | Processing decision notes — Docling version choice for the processing pipeline |

---

### `docs/api/`

| File | Description |
|------|-------------|
| `README.md` | API docs index |
| `authentication.md` | (empty) |
| `backend-api.md` | Backend API reference |
| `chat.md` | (empty) |
| `documents.md` | (empty) |
| `feedback.md` | (empty) |
| `openapi.md` | (empty) |
| `reports.md` | (empty) |

---

### `docs/architecture/`

| File | Description |
|------|-------------|
| `README.md` | Architecture docs index |
| `ai-framework-integration.md` | AI framework integration strategy — how ResearchMind integrates with external AI frameworks/providers (LangChain, LangGraph, Docling, Voyage AI, OpenAI SDK, Anthropic SDK, etc.) without leaking them into core contracts |
| `backend-architecture.md` | FastAPI backend architecture overview |
| `chunking-platform.md` | Chunking Platform architecture overview (Phase 2.3 foundation) — responsibility, why chunking is an independent platform, how it fits the wider Knowledge Platform |
| `chunking-platform-architecture.md` | Chunking Platform Architecture v1.0 (**Frozen**) — the pre-implementation architecture freeze document; future work extends rather than redesigns it |
| `chunk-lifecycle-and-dataflow.md` | Chunk Lifecycle & Data Flow v1.0 (**Frozen**) — how a single canonical `Chunk` object flows and is progressively enriched across the entire AI pipeline (companion to the architecture doc, focused on dataflow rather than components) |
| `db-sessions.md` | SQLAlchemy session management patterns |
| `decision-history.md` | History of architectural decisions |
| `embedding-platform.md` | Embedding Platform architecture (Phase 2.4, **Completed V1**) — provider pattern, registry, factory, artifact lifecycle, ProcessingService integration |
| `evaluation-platform.md` | Runtime Evaluation Platform (planned) — continuously observes/measures the *configured production* pipeline (latency, quality, health) without altering its behavior |
| `evaluation-strategy.md` | Evaluation strategy — why ResearchMind separates Engineering Benchmarks, Runtime Evaluation, and the Experimentation Platform into three complementary layers with different audiences and lifecycles |
| `experimentation-platform.md` | Experimentation Platform (planned) — asynchronous background evaluation of alternative AI strategies against production documents, without affecting production |
| `framework-integration-strategy.md` | Framework Integration Strategy (companion to ADR-023) — how ResearchMind integrates LangChain/LangGraph/LangSmith without letting them leak into core contracts |
| `hybrid-retrieval-indexing.md` | Hybrid Retrieval Indexing (Phase 2.5, **Completed V1 — indexing side**) — sparse embeddings (FastEmbed SPLADE) + Qdrant native hybrid indexing (ADR-018, ADR-019); complete ingestion pipeline flow diagram, Qdrant schema before/after, real end-to-end verification results |
| `identity-architecture.md` | **Full auth architecture** — Cognito flow, per-request auth, implementation table, manual testing guide, AWS Console setup, common errors, issues encountered |
| `knowledge-platform-roadmap.md` | Knowledge Platform roadmap — the full subsystem breakdown (chunking → embeddings → vector store → retrieval → reranking → memory → knowledge service) and how each communicates via canonical models |
| `metadata-filtering.md` | Metadata Filtering architecture (Milestone 2.7.1, **Complete**) — supported filters (`owner_id`, `document_id`, `filename`), Qdrant filter translation, benchmark validation exit criterion |
| `observability-platform.md` | Observability Platform architecture |
| `observability-strategy.md` | Observability strategy — logging is the only implemented pillar (structlog, request correlation); metrics/tracing are placeholders under `docs/monitoring/` |
| `project-constitution.md` | Project principles, goals, and constraints |
| `repository-structure.md` | Repository layer patterns |
| `reranking-platform.md` | Reranking Platform architecture (Milestone 2.7.2, companion to ADR-022) — CrossEncoder/Voyage AI providers, canonical models, integration strategy, evaluation metrics |
| `retrieval-benchmarking-strategy.md` | Retrieval Benchmarking Strategy (**Accepted**) — freezes the initial evaluation methodology: dense/sparse/hybrid scope, dataset size/format, 6 query categories with expected winners, ADR-020 metric requirements, the Hybrid decision gate (`Dense Results != Sparse Results`) |
| `system-overview.md` | High-level system overview |

---

### `docs/deployment/`

| File | Description |
|------|-------------|
| `README.md` | Deployment docs index |
| `local.md` | Local development setup guide |
| `production.md` | Production deployment guide |

---

### `docs/diagrams/`

| File | Description |
|------|-------------|
| `ResearchMind.drawio.png` | System architecture diagram (image) |
| `ResearchMind.drawio.xml` | System architecture diagram (editable draw.io source) |

---

### `docs/engineering-journal/`

| File | Description |
|------|-------------|
| `README.md` | Journal index |
| `template.md` | Template for new journal entries |
| `concepts/001-fastapi-lifespan.md` | Deep-dive: FastAPI lifespan context manager |
| `concepts/002-sqlalchemy-engine.md` | Deep-dive: SQLAlchemy async engine |
| `concepts/003-session-vs-engine.md` | Deep-dive: session vs engine responsibilities |
| `concepts/004-dependency-injection.md` | Deep-dive: FastAPI dependency injection |
| `concepts/005-connection-pooling.md` | Deep-dive: connection pooling |
| `concepts/006-fastapi-middleware.md` | Deep-dive: middleware execution order |
| `concepts/007-fastapi-application-state.md` | Deep-dive: app state for shared resources |
| `concepts/008-api-versioning.md` | Deep-dive: API versioning strategy |
| `concepts/009-api-contracts.md` | Deep-dive: API contracts with Pydantic |
| `concepts/010-global-exception-handling.md` | Deep-dive: global exception handlers |
| `concepts/011-pydantic-response-models.md` | Deep-dive: Pydantic response models |
| `concepts/012-connect-progresql-terminal` | How to connect to PostgreSQL via terminal |
| `concepts/README.md` | Concepts index |
| `milestones/030-backend-foundation.md` | Milestone 0.30 retrospective |
| `milestones/0.31-engineering-quality.md` | Milestone 0.31 retrospective |
| `milestones/2026-07-02-processing-platform-summary.md` | Milestone retrospective: first end-to-end Document Processing Platform implementation |
| `milestones/2026-07-04-asynchronous-document-processing.md` | Milestone retrospective: asynchronous document processing — queue abstraction, background worker, retry/dead-letter handling, worker metrics, graceful shutdown |
| `milestones/2026-07-05-fixed-chunking.md` | Milestone retrospective (Phase 2.3.3): first production-ready Fixed Chunking Platform implementation |
| `milestones/2026-07-06-runtime-metrics-foundation.md` | Milestone retrospective: Runtime Metrics Foundation |
| `milestones/README.md` | Milestones index |

---

### `docs/evaluation/`

All empty — planned evaluation documentation.

| File | Purpose |
|------|---------|
| `benchmarks.md` | (empty) |
| `hallucination-testing.md` | (empty) |
| `metrics.md` | (empty) |
| `report-quality.md` | (empty) |
| `retrieval-testing.md` | (empty) |
| `strategy.md` | (empty) |

---

### `docs/guides/`

| File | Description |
|------|-------------|
| `coding-standards.md` | (empty) |
| `contributing.md` | (empty) |
| `debugging.md` | (empty) |
| `style-guide.md` | (empty) |
| `testing.md` | Testing guide — recently updated with content (previously empty) |

---

### `docs/handoff/`

| File | Description |
|------|-------------|
| `chat-handoff1.md` | Context handoff document from session 1 |
| `chat-handoff2.md` | Context handoff document from session 2 |
| `CHATGPT_HANDOFF_PHASE_2_2.md` | Master project context/handoff doc for Phase 2.2 (document processing), written for a ChatGPT collaborator |

---

### `docs/monitoring/`

All empty — planned observability docs.

| File | Purpose |
|------|---------|
| `dashboards.md` | (empty) |
| `grafana.md` | (empty) |
| `langsmith.md` | (empty) |
| `otel.md` | (empty) |
| `prometheus.md` | (empty) |

---

### `docs/platforms/`

Platform-level design docs written before/alongside implementation — a level below the ADRs (which record a single decision) and above the code itself.

| File | Description |
|------|-------------|
| `indexing-platform.md` | Indexing Platform design doc. Predates ADR-019: its BM25 platform section (separate `bm25/` provider folder) was superseded by Qdrant native sparse vectors (FastEmbed SPLADE) generated inside `indexing/providers/fastembed.py`; the rest of the document (Vector Store section, artifact-driven design principles) matches the current implementation |
| `retrieval-platform.md` | Retrieval Platform design doc — predates implementation; `ai/knowledge/retrieval/` now implements dense/sparse/hybrid search (see `docs/adrs/ADR-020-*.md`, `ADR-021-*.md`, and `docs/architecture/retrieval-benchmarking-strategy.md` for the as-built architecture and evaluation methodology) |

---

### `docs/product/`

All empty — planned product docs.

| File | Purpose |
|------|---------|
| `faq.md` | (empty) |
| `features.md` | (empty) |
| `getting-started.md` | (empty) |
| `release-notes.md` | (empty) |

---

### `docs/project/`

Numbered project reference set — appears to be a parallel/newer take on project context alongside the root `docs/project-constitution.md` and `docs/project-handbook.md`.

| File | Description |
|------|-------------|
| `00-project-constitution.md` | Project constitution v1.0 |
| `01-current-state.md` | Current project state snapshot |
| `02-roadmap.md` | Project roadmap v1.0 |
| `03-frozen-decisions.md` | Frozen engineering decisions v1.0 |
| `04-folder-structure.md` | Folder structure reference v1.0 |
| `05-tech-stack.md` | Technology stack reference v1.0 |
| `06-chatgpt-collaboration.md` | Guide for collaborating with ChatGPT on this project |
| `07-engineering-journal.md` | Engineering journal v1.0 |

---

### `docs/reference/`

All empty — planned external references.

### `docs/research/`

All empty — planned research notes.

### `docs/runbooks/`

| File | Description |
|------|-------------|
| `README.md` | Runbooks index |
| `backup.md` | (empty) |
| `incident-response.md` | (empty) |
| `local-development.md` | Local development runbook |
| `restore.md` | (empty) |
| `troubleshooting.md` | Troubleshooting runbook |

---

### `docs/standards/`

| File | Description |
|------|-------------|
| `README.md` | Standards index |
| `branching.md` | (empty) |
| `commit-messages.md` | (empty) |
| `documentation.md` | Documentation standards |
| `git.md` | (empty) |
| `python.md` | (empty) |

---

### `docs/workflows/`

All empty — planned workflow documentation.

---

### `docs/` root

| File | Description |
|------|-------------|
| `index.md` | Docs home and navigation index |
| `phase2_roadmap.md` | Frozen Phase 2 roadmap — Upload Platform (complete) → Document Processing |
| `project-constitution.md` | Project principles and goals |
| `project-handbook.md` | Working agreements and team practices |
| `s3_configuration_guide.md` | Guide for configuring AWS S3 for document storage |

---

## `examples/`

Empty — planned usage examples and notebooks.

## `experiments/`

Empty — planned experimental code and prototypes.

---

## `infrastructure/`

All empty — planned infrastructure-as-code. (The former `s3_configuration_guide.md` here has moved to `docs/s3_configuration_guide.md`.)

| Path | Description |
|------|-------------|
| `database/` | Empty — planned DB provisioning scripts |
| `deployment/` | Empty — planned deployment manifests (k8s, etc.) |
| `docker/` | Empty — planned Dockerfiles |
| `monitoring/` | Empty — planned monitoring stack config |
| `scripts/` | Empty — planned infrastructure automation |

---

## `scripts/`

| File | Description |
|------|-------------|
| `dev.sh` | Dev startup script — runs `alembic upgrade head` then `uvicorn --reload`; prevents hot-reload from interrupting migrations |
| `benchmark_chunking.py` | Stray placeholder — a bare comment diagram (`Document → Fixed → Recursive → Markdown → Comparison Report`), no actual code; superseded by `benchmarks/chunking/benchmark.py` |
| `verify_voyage_sdk.py` | Manual smoke-test script — resolves the Voyage AI provider from `create_embedding_registry()` and prints its provider/model, verifying registry registration, dependency injection, `VOYAGE_API_KEY` loading, and Voyage client construction end-to-end (`uv run python scripts/verify_voyage_sdk.py`) |

---

## `services/`

All empty — planned internal service modules.

| Directory | Purpose |
|-----------|---------|
| `cache/` | Caching service |
| `evaluation/` | Evaluation pipeline |
| `ingestion/` | Document ingestion |
| `mcp/` | MCP server integrations |
| `memory/` | Agent memory service |
| `observability/` | Tracing and metrics |
| `providers/` | LLM provider abstractions |
| `reporting/` | Report generation |
| `retrieval/` | Vector retrieval |

---

## `shared/`

All empty — planned cross-cutting code.

| Directory | Purpose |
|-----------|---------|
| `config/` | Shared configuration |
| `constants/` | Shared constants |
| `exceptions/` | Shared exception types |
| `interfaces/` | Shared abstract interfaces |
| `prompts/` | Shared prompt templates |
| `schemas/` | Shared Pydantic schemas |
| `utils/` | Shared utility functions |

---

## `tests/`

| File | Description |
|------|-------------|
| `__init__.py` | Package marker |
| `conftest.py` | Shared pytest fixtures: `client` (TestClient), `test_engine` (async engine against `researchmind_test`), `db_session` |
| `api/__init__.py` | Package marker |
| `api/test_health.py` | Tests `GET /api/v1/health` returns `healthy` when all services are up |
| `api/test_retrieval_filters.py` | Integration tests for `/retrieve`, `/retrieve/sparse`, `/retrieve/hybrid` against a `_FakeRetrievalService` (dependency-overridden): 401 without a bearer token (real `get_current_user`, not mocked), retrieval scoped to the authenticated user, a client-supplied `owner_id` in `filters` is ignored/overridden rather than trusted |
| `integration/__init__.py` | Package marker |
| `integration/ai/knowledge/chunking/test_fixed_chunking_pipeline.py` | End-to-end Fixed Chunking pipeline test — `ProcessedDocument` → `ChunkingService` → `FixedChunkingProvider` → `list[Chunk]`, verifying ordering, provenance, experiment metadata, statistics |
| `integration/ai/knowledge/chunking/test_fixed_chunking_edge_cases.py` | Fixed Chunking edge cases — overlap is preserved between every consecutive chunk pair (incl. the truncated final chunk); empty/whitespace-only documents raise `ChunkingValidationError` |
| `integration/ai/knowledge/chunking/test_recursive_chunking_pipeline.py` | End-to-end Recursive Chunking pipeline test (`ChunkingService` → `RecursiveChunkingProvider` → `ChunkArtifactBuilder`) — canonical Chunk fields, artifact statistics, and JSON serialization |
| `integration/ai/knowledge/embeddings/test_sentence_transformers_pipeline.py` | End-to-end embedding pipeline test (`EmbeddingService` → real `SentenceTransformerEmbeddingProvider` → `EmbeddingArtifactBuilder`) — canonical Embedding fields, artifact statistics, and JSON serialization |
| `integration/ai/knowledge/processing/test_processing_service.py` | Full DoclingParser → ProcessingService pipeline integration test (parse → enrich → artifacts → chunk → chunk artifacts → embed → embedding artifacts), using the real Chunking Platform; the embedding stage uses a mocked `EmbeddingService` (via `EmbeddingFactory`) since `ProcessingService` hardcodes the Voyage AI provider and this test doesn't assert on embedding content |
| `integration/ai/knowledge/upload/test_duplicate_detection.py` | Integration test: real `UploadService`, `DuplicateDetectionService`, `DocumentRepository`, `SHA256Hasher` against the Postgres test DB (only S3 is faked) |
| `integration/test_document_repository.py` | (empty) |
| `integration/test_document_service.py` | (empty) |
| `integration/test_memory.py` | (empty) |
| `integration/test_retriever.py` | (empty) |
| `integration/test_user_repository.py` | Integration tests: create, get by email, exists, delete user via `UserRepository` |
| `integration/test_user_service.py` | Integration tests: create user, duplicate email conflict, not found, sync existing, deactivate |
| `integration/test_vector_store.py` | (empty) |
| `unit/__init__.py` | Package marker |
| `unit/test_settings.py` | Unit tests for Pydantic settings loading |
| `unit/test_prompt_builder.py` | (empty) |
| `unit/test_utils.py` | (empty) |
| `unit/ai/__init__.py` | Package marker |
| `unit/ai/knowledge/__init__.py` | Package marker |
| `unit/ai/knowledge/cache/__init__.py` | Package marker |
| `unit/ai/knowledge/cache/embeddings/__init__.py` | Package marker |
| `unit/ai/knowledge/cache/embeddings/test_key.py` | `build_embedding_cache_key()` — stable key derivation |
| `unit/ai/knowledge/cache/embeddings/test_null.py` | `NullEmbeddingCache` — `get_many` always reports a full miss, `set_many` is a no-op |
| `unit/ai/knowledge/cache/embeddings/test_valkey.py` | `ValkeyEmbeddingCache` — hit/miss decoding, empty-input short-circuit, fail-open on Redis errors, corrupt-entry handling, `set_many` writes each entry through a pipeline with the configured TTL |
| `unit/ai/knowledge/cache/query_embeddings/__init__.py` | Package marker |
| `unit/ai/knowledge/cache/query_embeddings/test_null.py` | `NullQueryEmbeddingCache` — `get` always reports a miss, `set` is a no-op |
| `unit/ai/knowledge/cache/query_embeddings/test_valkey.py` | `ValkeyQueryEmbeddingCache` — hit/miss decoding, fail-open on Redis errors, corrupt-entry handling, `set` writes with the configured TTL |
| `unit/ai/knowledge/embeddings/__init__.py` | Package marker |
| `unit/ai/knowledge/embeddings/test_registry.py` | `EmbeddingRegistry` registration, lookup, duplicate rejection, unregister/clear, defensive `providers` copy |
| `unit/ai/knowledge/embeddings/test_service.py` | `EmbeddingService` — delegates to the resolved provider; raises on unknown provider, empty chunk artifact, and blank-text chunks |
| `unit/ai/knowledge/embeddings/test_factory.py` | `EmbeddingFactory.from_vector` — provenance/statistics/provider mapping from a `Chunk`, vector dimension derivation |
| `unit/ai/knowledge/embeddings/providers/__init__.py` | Package marker |
| `unit/ai/knowledge/embeddings/providers/test_sentence_transformers.py` | `SentenceTransformerEmbeddingProvider` (mocked `SentenceTransformer`) — provider/model identifiers, lazy/cached model construction, conversion of encoded vectors into canonical `Embedding` models |
| `unit/ai/knowledge/embeddings/providers/test_voyage.py` | `VoyageAIEmbeddingProvider` (mocked Voyage client) — client invoked with configured model/input_type, canonical `Embedding` conversion, quantized int vectors coerced to floats |
| `unit/ai/knowledge/embeddings/providers/test_batching.py` | `EmbeddingBatcher` unit tests (equal-size splits, remainder handling, oversized batch_size, empty input, invalid batch_size) plus provider-level batching integration for both `SentenceTransformerEmbeddingProvider` and `VoyageAIEmbeddingProvider` |
| `unit/ai/knowledge/embeddings/artifacts/__init__.py` | Package marker |
| `unit/ai/knowledge/embeddings/artifacts/test_builder.py` | `EmbeddingArtifactBuilder` — statistics aggregation, document/chunking/execution metadata derivation, empty-embeddings `ValueError` |
| `unit/ai/knowledge/embeddings/artifacts/test_writer.py` | `EmbeddingArtifactWriter` — S3 key layout, serialized payload/content-type, storage error propagation |
| `unit/ai/knowledge/processing/__init__.py` | Package marker |
| `unit/ai/knowledge/processing/test_docling_parser.py` | `DoclingParser.parse()` with real PDF fixture |
| `unit/ai/knowledge/processing/test_models.py` | `ProcessedDocument`, block types, discriminated union |
| `unit/ai/knowledge/processing/test_registry.py` | `ParserRegistry` registration, lookup, deduplication |
| `unit/ai/knowledge/processing/test_service.py` | `ProcessingService` orchestration with `FakeParser` |
| `unit/ai/knowledge/processing/test_service_resilience.py` | Resilience tests: storage/parser failures are logged with pipeline-stage context and propagate untouched |
| `unit/ai/knowledge/processing/test_temporary_file_manager.py` | `TemporaryFileManager` — temp file lifecycle, content integrity, cleanup |
| `unit/ai/knowledge/processing/metadata/__init__.py` | Package marker |
| `unit/ai/knowledge/processing/metadata/test_service.py` | `MetadataEnrichmentService` — regression coverage for a bug where `PDFMetadataProvider` ran against every format (crashed on DOCX) |
| `unit/ai/knowledge/reranking/__init__.py` | Package marker |
| `unit/ai/knowledge/reranking/test_registry.py` | `RerankingRegistry` — get resolves a registered provider / raises `RerankingProviderNotFoundError`, `has` reflects registration state without mutating it |
| `unit/ai/knowledge/retrieval/__init__.py` | Package marker |
| `unit/ai/knowledge/retrieval/test_registry.py` | `RetrievalRegistry` — get resolves a registered provider / raises `RetrievalProviderNotFoundError`, `has`/`providers` reflect state |
| `unit/ai/knowledge/retrieval/test_service.py` | `RetrievalService` — `search()` happy path (normalized query + embedding forwarded, statistics/execution populated), whitespace normalization, validation edge cases (empty/whitespace query, over-length query, non-positive `top_k`), provider-not-found propagation |
| `unit/ai/knowledge/retrieval/providers/__init__.py` | Package marker |
| `unit/ai/knowledge/retrieval/providers/test_qdrant.py` | `QdrantRetrievalProvider` — queries the named `dense` vector with configured collection/limit/payload options, maps points to `RetrievedChunk`; missing optional payload fields default correctly, no points returns an empty list, a payload missing a required field fails fast with `KeyError` |
| `unit/ai/knowledge/retrieval/providers/test_qdrant_filters.py` | `QdrantRetrievalProvider._build_filter` — empty filters return `None`, single/multiple recognized filter keys produce the matching `FieldCondition`s, `document_id` UUID values are coerced to `str`, unsupported keys and falsy values are ignored |
| `unit/ai/knowledge/retrieval/query/__init__.py` | Package marker |
| `unit/ai/knowledge/retrieval/query/test_dense_service.py` | `QueryEmbeddingService` — cache hit skips the provider entirely; cache miss calls Voyage (default) or OpenAI and populates the cache, including int→float vector coercion; unsupported provider raises `NotImplementedError` |
| `unit/ai/knowledge/upload/__init__.py` | Package marker |
| `unit/ai/knowledge/upload/test_service.py` | `UploadService` — invalid files rejected before storage/hasher/DB touched, size boundary enforcement |
| `unit/ai/knowledge/upload/test_validators.py` | `UploadValidator` — invalid filename/extension/content-type/size rejection rules |
| `unit/benchmarks/__init__.py` | Package marker |
| `unit/benchmarks/common/__init__.py` | Package marker |
| `unit/benchmarks/common/test_metrics.py` | `average()` / `percentile()` — arithmetic mean and nearest-rank percentile, both return `0.0` for empty input rather than raising |
| `unit/benchmarks/reranking/__init__.py` | Package marker |
| `unit/benchmarks/reranking/test_benchmark.py` | `RerankingBenchmark`'s pure helpers — `_build_candidate` aggregates recall/MRR/NDCG/latency and only attaches an `error` note when one occurred; `_build_summary` reports each reranker's delta over the `hybrid_only` baseline and skips candidates with zero evaluated queries (e.g. Voyage AI not configured) |
| `unit/benchmarks/retrieval/__init__.py` | Package marker |
| `unit/benchmarks/retrieval/test_dataset.py` | `load_retrieval_queries()` — well-formed dataset parses correctly, missing file raises `FileNotFoundError` |
| `unit/benchmarks/retrieval/test_metrics.py` | `recall_at_k` / `precision_at_k` / `reciprocal_rank` / `ndcg_at_k` — counts a document once despite duplicate chunks, only credits documents within the top-k window, precision uses `k` (not unique-hit count) as the denominator, reciprocal rank finds the first relevant document and returns 0.0 when nothing relevant was retrieved, NDCG is 1.0 for the ideal ordering and more rank-sensitive than recall, empty inputs don't raise |
| `unit/infrastructure/__init__.py` | Package marker |
| `unit/infrastructure/storage/__init__.py` | Package marker |
| `unit/infrastructure/storage/test_s3_storage.py` | `S3StorageService` — wraps raw boto3 `ClientError` into typed `StorageError` subclasses for every operation |
| `unit/services/__init__.py` | Package marker |
| `unit/services/test_document_processing_service.py` | `DocumentProcessingService` — happy path persists PROCESSING then COMPLETED (flushed and committed) |
| `evaluation/__init__.py` | Package marker |
| `evaluation/test_faithfulness.py` | (empty) |
| `evaluation/test_groundedness.py` | (empty) |
| `evaluation/test_reranking.py` | (empty) |
| `evaluation/test_retrieval_precision.py` | (empty) |
| `performance/__init__.py` | Package marker |
| `performance/test_embedding_speed.py` | (empty) |
| `performance/test_latency.py` | (empty) |
| `performance/test_qdrant_speed.py` | (empty) |
| `security/__init__.py` | Package marker |
| `security/test_jailbreaks.py` | (empty) |
| `security/test_prompt_injection.py` | (empty) |
| `fixtures/sample.pdf` | PDF fixture for parser integration tests |

---

## `tools/`

Empty — planned developer tooling.

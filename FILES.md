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
| `AI_ENGINEERING_AUDIT.md` | Evidence-based audit of the AI subsystem (Knowledge + Generation Platforms) against current AI-engineering practice — enumerates gaps as additions, not corrections; several items from this audit (Provider Structured Output Integration, Output Validation, Regeneration Strategy, Provider Capability Flags, Prompt Platform Integration) have since been implemented — see `docs/architecture/structured-output-platform.md` |
| `alembic.ini` | Alembic configuration (points to `alembic/env.py`) |
| `CHANGELOG.md` | Version changelog |
| `docker-compose.yml` | Local dev stack — PostgreSQL (5432), Valkey (6379), Qdrant (6333/6334), `semantic-cache` — dedicated `redis-stack-server` (6380) backing the Runtime Caching Platform's L2 Semantic Cache (plain Valkey has no vector-search module) |
| `FILES.md` | This file — complete file and folder map |
| `LICENSE` | Project license |
| `phase-3-ai-runtime-roadmap.md` | Frozen v2.0 Retrieval, Context, Generation & Research Runtime roadmap (Phase 3.4–3.12); architecture frozen, progress status tracked inline per phase — Phase 3.8 (Generation Platform) now ~75% complete |
| `prompt_guardrails.md` | Short prompt-injection defense snippet — a "Security Notice" block to prepend inside prompt templates warning the model that retrieved context may contain untrusted instructions |
| `PROJECT_STATUS.md` | Current milestone and progress tracker |
| `pyproject.toml` | Python project config: dependencies, ruff, mypy, pytest settings |
| `README.md` | Project overview, quickstart, auth guide, Alembic troubleshooting |
| `RESEARCHMIND_PROJECT_CONTEXT_AND_HANDOFF.md` | Project context and engineering handoff document (v1.0) |
| `ResearchMind-Roadmap-v2.md` | AI Engineering Roadmap v2 — vision, objectives, frozen technology decisions, and the full 10-phase platform roadmap (Phase 0 Engineering Foundation through Phase 9 Enterprise Platform); Phase 3 (AI Runtime Platform) now ~80% complete |
| `ROADMAP.md` | Feature and milestone roadmap |
| `routing_platform_prd.md` | Routing Platform PRD — model/provider selection implemented under `generation/routing/` + `generation/catalog/` (companion to ADR-026) |
| `runtime_caching_platform_prd.md` | Runtime Caching Platform PRD — L1 exact/L2 semantic/L3 session caching implemented under `generation/caching/` (companion to ADR-027) |
| `runtime_validation_prd.md` | PRD for the Runtime Validation Platform — a 4th `ValidationStage.RUNTIME` extending the Validation Platform below (not a separate platform). Implemented under `generation/validation/runtime/`: `RuntimeType`/`GenerationRequest.runtime`, `RuntimeRegistry`/`RuntimeValidationService`, five generic validators, and the first concrete contract, `ResearchRuntimeContract`. Planner/Reviewer/Agent/MCP contracts (§16-19) remain future work; nothing in the request path sets `GenerationRequest.runtime` yet, so the stage is a no-op until a caller (e.g. a future `/research` API) does |
| `SECURITY.md` | (empty) |
| `setup_commands.md` | Makefile-style shortcut commands (`docker compose up/down`) |
| `streaming_platform_prd.md` | Streaming Platform PRD — canonical event protocol + SSE/WebSocket streaming implemented under `runtime/events/` + `generation/streaming/` (companion to ADR-028); its "Event Types" section was corrected during implementation to point at the layered model rather than list agent/research values in one flat enum |
| `STRUCTURE.md` | High-level folder/file structure with layer descriptions |
| `DEV_GUIDE.md` | Step-by-step local development guide — setup, Alembic issues, Docker rules, auth testing |
| `test.txt` | Stray scratch file — can be deleted |
| `validation_platform_prd.md` | PRD for a standalone Validation Platform (input validation, hallucination detection, per-runtime contracts, scoring, regeneration policy) — Input/Output/Hallucination/Runtime Validation, a registry, weighted scoring, and a multi-stage `ValidationReport` are implemented today inside `apps/api/app/ai/runtime/generation/validation/`; only a few output checks, the Acceptance/Fail-Fast policy layer, and the standalone-platform promotion remain — see the file's Implementation Status note |

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
| `versions/bca5e4edca5c_create_conversations_and_messages_tables.py` | Migration 4: creates `conversations` (FK to `users`) and `messages` (FK to `conversations`, `message_role` enum) tables — Streaming Platform, Milestone 2.9.10. Downgrade explicitly drops the `message_role` Postgres enum type (not done automatically by `drop_table`) so downgrade→upgrade round-trips cleanly |

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

##### `ai/guardrails/` — **Implemented (MVP Foundation)**

Guardrails Platform (PRD Milestone 11.16, `guardrails_platform_prd.md`). Standalone, platform-wide package answering "should the system do this?" (distinct from the Validation Platform's "did it work?"), spanning input/retrieval/generation/runtime stages. Not yet wired into `GenerationService`, the context builder, or a router — `create.get_guardrail_service()` is the future integration seam. See `PROJECT_STATUS.md` Milestone 11.16 for full detail. The two previous empty scaffold files here (`policies.py`, `scanners.py`) and the entire empty `ai/runtime/generation/guardrails/` scaffold (see below) were deleted as part of this build.

| Directory / File | Status |
|-----------|--------|
| (root files) | **Implemented** — `models.py`, `enums.py`, `interfaces.py`, `exceptions.py`, `registry.py`, `service.py`, `create.py`, `constants.py` |
| `input/` | **Implemented** — prompt injection/jailbreak (P0), scope validation, PII detection; rate limit/toxicity are foundation interfaces (always-allow) |
| `retrieval/` | **Implemented** — context sanitization (composes `ai/knowledge/context/guardrails/`), Source Trust, citation integrity; access control is a foundation interface |
| `generation/` | **Implemented** — faithfulness + schema enforcement (both wrap Validation Platform validators), PII leakage; moderation is a foundation interface |
| `runtime/` | **Implemented** — budget guardrail, loop detection; tool policy is a foundation interface, approval gate is interfaces-only (unregistered) |
| `trust/` | **Implemented** — new Source Trust Platform: `SourceType`, `TrustRegistry`, trust policies/scoring |
| `policies/` | **Implemented** — `FailPolicy`, `RiskPolicy`, `RegenerationPolicy`, `RuntimePolicy` |
| `scoring/` | **Implemented** — weighted `overall_risk` formula |
| `artifacts/` | **Implemented** — `GuardrailArtifact`/builder/writer, persists `guardrails/{run_id}/*.json` |
| `reports/` | **Implemented** — report/issue summarization helpers |
| `utils/` | **Implemented** — shared PII regex table |

`tests/unit/ai/guardrails/` mirrors this tree 1:1 (113 tests).

##### `ai/knowledge/`

| Directory | Status |
|-----------|--------|
| `cache/` | **Implemented** — Valkey-backed embedding cache + query-embedding cache, see below |
| `chunking/` | **Implemented** — see below |
| `context/` | **~95% Implemented** — Context Platform: parent expansion, adjacent merge, compression, guardrails, citations, prompt formatter; see below |
| `embeddings/` | **Implemented** — see below |
| `indexing/` | **Implemented** — see below |
| `processing/` | **Implemented** — see below |
| `reranking/` | **Implemented** — Voyage AI + CrossEncoder providers; see below |
| `retrieval/` | **Implemented** — dense, sparse, hybrid (RRF), metadata filtering, parallel retrieval; see below |
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

##### `ai/knowledge/context/` — **~95% Implemented**

Context Platform. Sits between Retrieval/Reranking and Generation: takes a `RetrievalResult` and produces a `PromptContext` ready to send to an LLM. Parent/child expansion was deliberately reclassified here from the Retrieval Platform, since ResearchMind's persisted `ChunkArtifact`s — not the vector index — are the source of truth for parent resolution. `ContextBuilderService.build()` runs the full pipeline: dedupe → parent expansion → adjacent merge → ordering → embedding-redundancy compression → token-budget compression → guardrails → citations → prompt formatting (the now-implemented LangChain compression provider is registered but not yet part of this default pipeline — it's query-aware and `build()` doesn't currently thread a query through). Not yet wired into a dependency provider or API route — `create_context_builder()` exists but nothing outside the package calls it yet. Test coverage: `builders/`, `artifacts/`, `citations/`, and `compression/` all have unit tests (see `tests/unit/ai/knowledge/context/`); `guardrails/` and `formatter/` do not yet.

| File | Description |
|------|-------------|
| `__init__.py` | (empty) |
| `interfaces.py` | `ContextBuilderInterface` ABC — `build(retrieval: RetrievalResult) -> ContextResult` |
| `models.py` | `ContextChunk` (canonical context unit — retrieval fields + parent-expansion fields + citation fields + `risk_level`/`risk_reasons` + `merged_chunk_ids`), `PromptContext` (`context`, `chunks`, `citations`), `ContextStatistics` (input/output/compressed chunk counts, `total_tokens`, `duration_ms`, `suspicious_chunks`, `malicious_chunks`, `security_warnings`), `ContextResult` |
| `enums.py` | (empty) — no context-level enums yet; strategy enums live in each sub-package (`compression/enums.py`, `guardrails/enums.py`, `formatter/enums.py`) |
| `service.py` | `ContextBuilderService` — orchestrates the full pipeline described above; always applies `EMBEDDING_REDUNDANCY` then `TOKEN_BUDGET` compression (max 6000 tokens), `RULE_BASED` guardrails, and `DEFAULT` prompt formatting (strategy selection isn't yet exposed to callers) |
| `create.py` | `create_parent_expansion_service()` / `create_context_builder()` — composition root wiring every sub-package's own `create_*` function into one `ContextBuilderService` |
| `artifacts/reader.py` | `ChunkArtifactReader` — loads a persisted `ChunkArtifact` from storage by `owner_id`/`document_id`/`strategy`/`artifact_id`; deliberately knows nothing about retrieval or context building |
| `artifacts/create.py` | `create_chunk_artifact_reader()` — composition root |
| `builders/deduplication.py` | `DeduplicationService` — drops repeat `chunk_id`s, keeping first occurrence |
| `builders/parent_expansion.py` | `ParentExpansionService` — groups chunks by `(owner_id, document_id, chunking_strategy, chunk_artifact_id)` metadata, loads each artifact once via `ChunkArtifactReader`, and enriches chunks with `parent_content`/`page_numbers`/`heading`/`heading_path` from the resolved parent |
| `builders/adjacent_merge.py` | `AdjacentMergeService` — sorts by `(document_id, chunk_index)` and merges runs of consecutive same-document chunks into one block, tracking `merged_chunk_ids` and taking the max score |
| `builders/ordering.py` | `ContextOrderingService` — sorts final chunks by score descending, chunk index ascending as tiebreaker |
| `builders/compression.py` | `CompressionService` — legacy no-op stub (`compress()` returns its input unchanged); superseded by `compression/service.py`, not called by `ContextBuilderService` |
| `citations/models.py` | `Citation` (`citation_id`, `filename`, `document_id`, `page_numbers`, `heading`, `heading_path`, `chunk_ids`), `CitationResult` |
| `citations/interfaces.py` | `CitationServiceInterface` ABC — `build(chunks) -> CitationResult` |
| `citations/service.py` | `CitationService` — numbers chunks `S1`, `S2`, ... in order, writes `citation_id` back onto each chunk, and builds one `Citation` per chunk (`chunk_ids` uses `merged_chunk_ids` when the chunk came from Adjacent Merge, else its own id) |
| `citations/create.py` | `create_citation_service()` — composition root |
| `compression/enums.py` | `CompressionStrategy` — `TOKEN_BUDGET`, `EMBEDDING_REDUNDANCY`, `LANGCHAIN_CONTEXTUAL`, `LLM` |
| `compression/interfaces.py` | `CompressionProvider` ABC — `compress(request) -> CompressionResult` |
| `compression/exceptions.py` | `CompressionError` hierarchy — `CompressionProviderError`, `CompressionTimeoutError` (new) |
| `compression/models.py` | `CompressionRequest` (`chunks`, `query`, `top_k`, `max_tokens`, `similarity_threshold`), `CompressionStatistics` (chunk counts + `estimated_saved_tokens`, plus `original_tokens`/`compressed_tokens`/`duration_ms` — populated by `LangChainCompressionProvider`, left at 0 by providers that don't measure them), `CompressionResult` |
| `compression/registry.py` | `CompressionRegistry` — strategy → provider resolution |
| `compression/service.py` | `CompressionService` — resolves the strategy from the registry, delegates; a provider raising `CompressionError` mid-compression now falls back to returning the original, uncompressed chunks (logged as `context.compression.fallback`) rather than propagating — an unregistered strategy still raises `ValueError` as before, since that's a caller/wiring bug, not a runtime failure |
| `compression/create.py` | `create_compression_service()` — registers all four providers (Token Budget, Embedding, LangChain, LLM) |
| `compression/providers/token_budget.py` | `TokenBudgetCompressionProvider` (V1) — sorts by score descending, greedily packs chunks into a token budget (default 6000, `len(content)//4` heuristic), skipping any chunk that would overflow it |
| `compression/providers/embedding.py` | `EmbeddingCompressionProvider` (V2) — encodes chunk text with the local `sentence-transformers/all-MiniLM-L6-v2` model (`get_local_embedding_model()`), computes a cosine-similarity matrix, and drops later chunks whose similarity to an earlier kept chunk is ≥ 0.95 (configurable) |
| `compression/providers/langchain.py` | `LangChainCompressionProvider` (V3) — **Implemented**. Query-aware extraction via LangChain's `ContextualCompressionRetriever` + `LLMChainExtractor` (from the new `langchain-classic` dependency — these classes moved out of core `langchain` in the 1.x split); a `_StaticDocumentRetriever` adapts the already-retrieved chunk list into the retriever interface `ContextualCompressionRetriever` expects, since there's no real retrieval step left to perform. Chunks the LLM extracts nothing relevant from are dropped; every field but `content` (citations, scores, parent links, risk metadata) survives via `chunk.model_copy()` keyed by `chunk_id`. The LLM is DI'd via constructor, lazily defaulting to `ChatOpenAI(gpt-5-nano)` off `settings.openai_api_key` only when actually needed. Emits `context.compression.langchain.started/completed/failed` via structlog. `providers/llm.py` (V4) remains unimplemented by design — this scaffold's LLM is only used to power `LLMChainExtractor`, not as the future standalone LLM compression strategy |
| `compression/providers/llm.py` | `LLMCompressionProvider` (V4) — scaffolded, `compress()` `raise NotImplementedError` |
| `guardrails/enums.py` | `ChunkRiskLevel` (safe/suspicious/malicious), `GuardrailStrategy` (`RULE_BASED` implemented; `LLAMA_GUARD`/`NEMO`/`LAKERA` reserved for future providers) |
| `guardrails/interfaces.py` | `GuardrailProvider` ABC — `validate(chunks) -> GuardrailResult` |
| `guardrails/models.py` | `GuardrailStatistics` (safe/suspicious/malicious counts), `GuardrailResult` (`chunks`, `removed_chunks`, `warnings`, `statistics`) |
| `guardrails/registry.py` | `GuardrailRegistry` — strategy → provider resolution |
| `guardrails/service.py` | `ContextGuardrailService` — resolves the strategy from the registry, delegates |
| `guardrails/create.py` | `create_context_guardrail_service()` — registers `RuleBasedGuardrailProvider` under `RULE_BASED` |
| `guardrails/providers/rule_based.py` | `RuleBasedGuardrailProvider` — regex-based prompt-injection/jailbreak detection over chunk content (11 patterns: ignore-instructions, system/developer/assistant-instructions, reveal-hidden-prompt, tool/function call, execute-code, browse, send-email, jailbreak); 0 matches → `SAFE`, 1 match → `SUSPICIOUS`, 2+ matches → `MALICIOUS` (adds a warning) |
| `formatter/enums.py` | `PromptFormatStrategy` — `DEFAULT`, `NOTEBOOKLM`, `PERPLEXITY`, `RESEARCH`, `AGENT` |
| `formatter/interfaces.py` | `PromptFormatterProvider` ABC — `format(context: PromptContext) -> PromptFormattingResult` |
| `formatter/models.py` | `PromptFormattingResult` (`formatted_context`) |
| `formatter/registry.py` | `PromptFormatterRegistry` — strategy → provider resolution |
| `formatter/service.py` | `PromptFormatterService` — resolves the strategy from the registry, delegates |
| `formatter/create.py` | `create_prompt_formatter_service()` — registers all five providers |
| `formatter/providers/default.py` | `DefaultPromptFormatterProvider` — one `====`-delimited section per chunk: source id, document, heading, pages, parent context, content |
| `formatter/providers/notebooklm.py` | `NotebookLMFormatterProvider` — near-identical to Default but wraps each section top-and-bottom with `====` dividers and an uppercase `SOURCE [Sx]` label |
| `formatter/providers/perplexity.py` | `PerplexityFormatterProvider` — compact "Evidence [Sx]" blocks, newline-flattened content truncated to 1000 characters |
| `formatter/providers/research.py` | `ResearchFormatterProvider` — groups chunks by `heading` (falling back to `filename`) into `TOPIC:` sections, each listing its sources |
| `formatter/providers/agent.py` | `AgentFormatterProvider` — machine-oriented `FACTS` / `EVIDENCE` two-block output, each fact truncated to 500 characters and tagged with its citation id |

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

Retrieval Platform (ADR-018, ADR-019, ADR-020, ADR-021). Queries the hybrid Qdrant index built by the Indexing Platform. Dense (Voyage AI), sparse (FastEmbed SPLADE), hybrid (Reciprocal Rank Fusion of dense + sparse), parallel dense+sparse execution, and metadata filtering are all implemented, benchmarked (`benchmarks/retrieval/`), and exposed via API (`/retrieve`, `/retrieve/sparse`, `/retrieve/hybrid`) — all three endpoints now require authentication and force `owner_id` from the authenticated user rather than the request body. Parent/Child retrieval was reclassified into the Context Platform (`ai/knowledge/context/builders/parent_expansion.py`) rather than implemented here — see `PROJECT_STATUS.md` Milestone 2.8. Query Decomposition is not yet implemented (deferred to the future Research Runtime).

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

| File / Directory | Status |
|-----------|--------|
| `__init__.py` | (empty) |
| `generation/` | **~85% Implemented** — Generation Platform; see below |
| `routing/__init__.py` | (empty) — vestigial top-level scaffold, superseded by `generation/routing/` |
| `streaming/__init__.py` | (empty) — vestigial top-level scaffold, unrelated to and untouched by the now-implemented `generation/streaming/` and `events/` (see below) — the name overlap is coincidental, not a naming migration |
| `events/` | **Implemented** — Runtime Event Platform (Streaming Platform Milestone 2.9.10, `streaming_platform_prd.md`/ADR-028); see below |

##### `ai/runtime/events/` — **Implemented** (Runtime Event Platform — `streaming_platform_prd.md`, ADR-028, `docs/architecture/streaming-platform.md`)

Provider-independent canonical event protocol, the "Layer 2" of the Streaming Platform's two-layer design. Layered so future runtimes (Research/Agent/Tool) each own their own event-type vocabulary rather than extending one shared enum — the flaw an earlier draft of ADR-028 had, since fixed (see `generation/streaming/` below and the ADR itself).

| File | Description |
|------|-------------|
| `enums.py` | `EventCategory` (generation/research/agent/tool), `CoreEventType` (start/token/thinking/complete/error) — the only enum `StreamEvent` itself depends on |
| `models.py` | `StreamEvent` — `event_id`, `session_id`, `request_id`, `parent_event_id`, `category: EventCategory`, `type: str` (plain string, not bound to `CoreEventType` — each domain populates it with its own values), `timestamp`, `content`, `metadata` |
| `interfaces.py` | `ProviderEventAdapterInterface` — `to_stream_event(chunk: StreamChunk, *, session_id, request_id) -> StreamEvent` |
| `create.py` | `get_event_adapter()` — `@lru_cache`d factory returning the one shared adapter |
| `adapters/base.py` | `GenericStreamChunkAdapter` — the single adapter every provider goes through, since every provider's `stream()` already normalizes SDK-specific chunks into the identical `StreamChunk` shape before anything leaves the provider; a separate `openai.py`/`claude.py`/... adapter file per provider (as an earlier ADR-028 draft's file-tree listed) would itself be the provider-duplication the ADR rejects |
| `provider/models.py` | `ProviderEventMetadataKeys` — constants for well-known `StreamEvent.metadata` keys (`finish_reason`, `token_count_delta`); no behavior |
| `research/models.py` | `ResearchEventType` — reserved for the future Research Runtime; not emitted by anything today |
| `agent/models.py` | `AgentEventType` — reserved for the future Agent Runtime; not emitted by anything today |
| `tool/models.py` | `ToolEventType` — reserved for the future Tool Runtime; not emitted by anything today |

##### `ai/runtime/generation/` — **~85% Implemented**

Generation Platform. Owns all LLM interactions, consuming the Context Platform's `PromptContext` output. Provider-independent runtime over five LLM providers, with native structured-output decoding, a parser/repair fallback, input/output/hallucination/runtime validation, a regenerate-on-invalid-output loop, an optional bridge into the pre-existing Prompt Platform, a Routing Platform that resolves a model/provider (with automatic fallback) from a task-based strategy when no provider is given explicitly, a Runtime Caching Platform that short-circuits the provider call on a cache hit, and a Streaming Platform providing SSE/WebSocket delivery. **Now wired into an API route** — `POST /api/v1/chat/stream` and `/api/v1/chat/ws` (see `api/v1/chat.py` below) call `GenerationService` via `StreamingService`; `/research` still does not exist. Detail: `docs/architecture/structured-output-platform.md` (Structured Output/Validation, continuously updated), `docs/architecture/model-routing-platform.md` + ADR-026 (Routing), `docs/architecture/runtime-caching-platform.md` + ADR-027 (Caching), and `docs/architecture/streaming-platform.md` + ADR-028 (Streaming). Generation-level guardrails no longer live here — the empty `guardrails/` scaffold that previously sat in this directory was deleted; generation-stage guardrails are implemented at the new top-level `ai/guardrails/generation/` platform instead (see above).

| Directory | Status |
|-----------|--------|
| (root files) | **Implemented** — core service, models, interfaces, registry, composition root |
| `providers/` | **Implemented** — Groq, OpenAI, Claude, Gemini, Ollama |
| `structured_output/` | **Implemented** — parser registry, repair, schemas |
| `validation/` | **~80% Implemented** — input, output, hallucination, and runtime stage validators, registry, scoring, and `ValidationReport` done (including a `ResearchRuntimeContract`); a few output checks and the Acceptance/Fail-Fast policy layer remain |
| `langchain/` | **~25% Implemented** — `with_structured_output()` bridge done; prompt factory/runnables/semantic cache empty |
| `prompts/` | **Implemented** (pre-existing) — template loading, rendering, few-shot, versioning; now bridged into Generation |
| `catalog/` | **Implemented** — scored per-model capability/cost/policy catalog + `ModelCatalogRegistry` |
| `routing/` | **Implemented** — Routing Platform: capability/policy filtering, task-based strategy scoring, fallback chains |
| `caching/` | **Implemented** — Runtime Caching Platform: L1 exact (Valkey), L2 semantic (LangChain `RedisSemanticCache` against a dedicated `redis-stack-server`), L3 session (Valkey, not yet called by anything), policy resolution; streaming requests now participate identically to non-streaming ones (the old blanket `request.stream` bypass was removed — see `streaming/` below) |
| `streaming/` | **Implemented** — Generation Streaming Platform: `StreamingService`, SSE + WebSocket transports; see below |
| `artifacts/` | ❌ Empty stubs |
| `observability/` | **Partial** — `token_counter.py` implemented; `cost_tracker.py`/`latency_tracker.py`/`metrics_collector.py`/`token_tracker.py`/`models.py`/`service.py` empty |

###### `ai/runtime/generation/` (root)

| File | Description |
|------|-------------|
| `models.py` | `GenerationRequest` (`prompt_context`, `user_prompt`, `system_prompt`, `response_format`, `output_schema`, `output_model` — auto-derives `output_schema` via a `model_validator`, `max_regeneration_attempts`, `tools`, `routing_strategy: RoutingStrategy \| None`, `required_capabilities: list[RequiredCapability]` — the latter two only consulted when `generate()` is called without an explicit `provider`, `cache_runtime`/`cache_policy`, `runtime: RuntimeType \| None` — resolves which runtime contract applies in `validate_runtime()`, unset by every caller today, ...), `GenerationResult` (`content`, `parsed_output`, `validation`, `regeneration_attempts`, `statistics`, `raw_response`, ...), `ProviderCapabilities`, `GenerationStatistics`, `GenerationExecution`, `StreamChunk`, `ToolDefinition` |
| `interfaces.py` | `GenerationProviderInterface` ABC — `generate()`, `generate_structured()` (defaults to `generate()`; providers override when they add native structured-output handling), `stream()`, `supports_*` capability accessors (`supports_structured_output`, `supports_json_mode`, `supports_tools`, `supports_streaming`, `supports_reasoning`, `supports_vision`, ...) reading from `ProviderCapabilities` |
| `enums.py` | `GenerationProvider` (groq/openai/claude/gemini/ollama), `GenerationOperation`, `ResponseFormat` (text/json/markdown/xml/structured), `PromptStrategy`. `RoutingStrategy` used to live here (manual/cheapest/fastest/quality/privacy/auto, enum only) — replaced by the task-based `RoutingStrategy` now in `routing/enums.py` |
| `exceptions.py` | `GenerationError` hierarchy — `GenerationProviderNotFoundError`, `GenerationValidationError`, `GenerationExecutionError`, `PromptValidationError`, `OutputValidationError`, `GuardrailViolationError` |
| `config.py` | `BaseGenerationConfig` + per-provider configs (`OpenAIGenerationConfig`, `ClaudeGenerationConfig`, `GeminiGenerationConfig`, `GroqGenerationConfig`, `OllamaGenerationConfig`) — model name, temperature, max_tokens, context window, `ProviderCapabilities`, cost per 1M tokens |
| `registry.py` | `GenerationRegistry` — provider enum → `GenerationProviderInterface` resolution |
| `service.py` | `GenerationService` — the orchestrator. `generate(request, provider=None)`: validates the request, then either calls `_generate_with_provider()` directly (explicit `provider`) or `_generate_with_routing()` — resolves a `RoutingDecision` via the wired `RoutingService` (strategy defaults to `AUTO`), tries the selected model then each `fallback_models` entry in order via `_generate_with_provider()`, catching `GenerationExecutionError`/`GenerationProviderNotFoundError` per candidate and raising only once every candidate has failed; stamps a compact routing summary onto `GenerationResult.metadata["routing"]`. `_generate_with_provider()` (the old `generate()` body): checks provider capability support (`_check_capability_support` — logs `generation.capability_mismatch`, never blocks), runs one attempt (`_execute_once`: routes to `generate_structured()` when a schema/JSON/STRUCTURED response is requested, else `generate()`; runs Markdown/XML parser-registry fallback, `output_model` re-validation, and the full `ValidationService.validate()` flow — input + output + hallucination stages), then regenerates with corrective feedback up to `request.max_regeneration_attempts` while `_needs_regeneration()` is true. `generate_from_template()` — bridges `PromptService`: renders a template, flattens the resulting messages into `system_prompt`/`user_prompt`, appends `PydanticOutputParser.get_format_instructions()` when `output_model` is set, then calls `generate()` |
| `create.py` | `create_generation_registry()` / `create_generation_service()` — composition root; registers whichever of the five providers have credentials configured, wires `structured_output_registry` (`get_structured_output_registry()`), `validation_service` (`get_validation_service()`), `prompt_service` (`get_prompt_service()`), and `routing_service` (`create_routing_service()`) into `GenerationService` |

###### `ai/runtime/generation/providers/` — **Implemented**

| File | Description |
|------|-------------|
| `base.py` | `BaseGenerationProvider[ConfigT]` — generic base shared by every provider: config/version/fingerprint, `_execute_with_retry()` (exponential backoff on request-level exceptions), `build_result()`, `build_statistics()`, `estimate_cost()`, `build_messages()`, default `generate_structured()` (delegates to `generate()`), default `stream()` (raises `NotImplementedError`), and `parse_structured_output()` — the shared parser fallback: strict `json.loads()`, then `StructuredOutputRepair.try_parse_json()`, returns `None` (logged) if both fail |
| `claude.py` | `ClaudeProvider` — `AsyncAnthropic`. Native structured output via `output_config={"format": {"type": "json_schema", "schema": ...}}` (the modern Structured Outputs API) when a schema is available, falling back to a prompt-enforced JSON instruction otherwise; tool calling; streaming |
| `openai.py` | `OpenAIProvider` — `AsyncOpenAI` Responses API. Native structured output via `text.format` (`json_schema` when a schema is available, else `json_object`); streaming |
| `gemini.py` | `GeminiProvider` — `google.genai.Client`. Native structured output via `response_mime_type` + `response_json_schema` (not `response_schema`, which expects Gemini's restricted OpenAPI-subset `Schema` type — `response_json_schema` accepts standard JSON Schema); streaming |
| `groq.py` | `GroqProvider` — `AsyncGroq`. Native structured output via `response_format` (`json_schema` with `strict: True` when a schema is available, else `json_object`); streaming |
| `ollama.py` | `OllamaProvider` — `ollama.AsyncClient`. Native structured output via `format` (the JSON Schema dict itself when available, else the `"json"` literal); streaming; `get_model_metadata()` also lists locally installed models |
| `helpers/structured.py` | Per-provider structured-output config builders — `build_openai_text_config`, `build_claude_output_config` / `build_claude_json_instruction`, `build_gemini_generation_config`, `build_groq_response_format`, `build_ollama_format` — each returns `None`/a text-mode fallback when no schema is available |
| `helpers/prompt_builder.py` | `build_prompt_text()` (flat string, OpenAI/Gemini), `build_chat_messages()` (OpenAI/Groq/Ollama message list), `build_claude_messages()` (Claude's separate system+messages shape) |
| `helpers/usage.py` | `Usage` — canonical token-usage shape every provider maps its SDK response into |
| `helpers/cost.py` | Shared cost-estimation helper |

###### `ai/runtime/generation/structured_output/` — **Implemented**

Parser registry + text-repair pipeline. Connected into `GenerationService` two ways: `providers/base.py`'s `parse_structured_output()` reuses `StructuredOutputRepair` directly for JSON/Pydantic; `GenerationService._parse_via_registry()` routes Markdown/XML responses through the full registry.

| File | Description |
|------|-------------|
| `interfaces.py` | `OutputParserInterface` ABC — `parse(text, schema=None)` |
| `models.py` | `OutputFormat` (json/pydantic/markdown/xml), `StructuredOutputRequest`, `StructuredOutputResult` |
| `registry.py` | `StructuredOutputRegistry` — format → parser resolution (`register`/`get`/`exists`/`list_formats`) |
| `repair.py` | `StructuredOutputRepair` — fixes common LLM JSON mistakes: strips markdown code fences, extracts embedded JSON from surrounding prose, fixes trailing commas, conservatively fixes single-quoted keys/values, balances missing braces/brackets; `try_parse_json()` combines clean+parse and requires a dict result |
| `service.py` | `StructuredOutputService` — standalone text→objects pipeline (`parse()`, `parse_json()`, `parse_pydantic()`, `parse_markdown()`, `parse_xml()`) for callers with raw text in hand, independent of `GenerationService` |
| `create.py` | `get_structured_output_registry()` / `get_structured_output_service()` — `@lru_cache`d composition root; registers `JsonParser`, `PydanticParser`, `MarkdownParser`, `XMLParser` |
| `parsers/json.py` | `JsonParser` — wraps LangChain's `JsonOutputParser` |
| `parsers/pydantic.py` | `PydanticParser` — wraps LangChain's `PydanticOutputParser`; requires a schema |
| `parsers/markdown.py` | `MarkdownParser` — splits on `##` headings into a `{title: content}` dict |
| `parsers/xml.py` | `XMLParser` — wraps `xmltodict.parse()` |
| `schemas/research_report.py` | `ResearchReport` — executive summary, findings, limitations, references |
| `schemas/planner.py` | `PlannerOutput` — objective, plan steps |
| `schemas/citations.py` | `Citation` (`source`, `quote`), `CitationCollection` — a simpler, LLM-output-facing shape, distinct from the canonical `Citation` in `ai/knowledge/context/citations/models.py` |
| `schemas/agent.py` | `AgentExecutionResult` — plans, tool calls, reviews, final responses |

###### `ai/runtime/generation/validation/` — **~80% Implemented**

Input, Output, Hallucination, and Runtime Validation. A narrow slice of the broader `validation_platform_prd.md` vision (see that file's Implementation Status note) is implemented here, inside the Generation Platform rather than as its own top-level platform; a few PRD *output*-stage checks (completeness/consistency/formatting/response-size — distinct from the same-named runtime-stage validators in `runtime/` below) and the Acceptance/Fail-Fast policy layer remain.

| File | Description |
|------|-------------|
| `interfaces.py` | `InputValidatorInterface` ABC — `validate(request: GenerationRequest, context: InputValidationContext) -> ValidatorOutcome`; `OutputValidatorInterface` ABC — `validate(result: GenerationResult) -> ValidatorOutcome` (used for output-stage, hallucination-stage, and — reused rather than duplicated — the generic runtime-stage validators in `runtime/validators/`). Either returns an empty outcome rather than erroring when there's nothing to check |
| `models.py` | `ValidationSeverity` (error/warning), `ValidationStage` (input/output/hallucination/runtime), `ValidationIssue` (`validator`, `stage`, `severity`, `message`, `details`), `ValidatorOutcome` (`issues`, optional `score`), `InputValidationContext` (`context_window`, `supports_streaming`/`supports_structured_output`/`supports_json_mode`/`supports_tool_calling` — plain primitives, not `ProviderCapabilities` directly, to avoid an import cycle with `generation/models.py`), `ValidationResult` (`valid`, `issues`, optional `score`), `ValidationReport` (`input_validation`/`output_validation`/`hallucination_validation`/`runtime_validation` — populated whenever `GenerationRequest.runtime` is set and a matching contract is registered, `None` otherwise —, `overall_score`, `valid`, and an `issues` property flattening every stage) |
| `registry.py` | `ValidationRegistry` — dynamic per-stage registration (`register_input_validator`/`register_output_validator`/`register_hallucination_validator`), each with a read-only accessor property; plus `register_runtime_validator()`/`register_runtime_contract()` and a `runtime_validators` property, both delegating to a composed `RuntimeRegistry` (`runtime/registry.py`) |
| `scoring.py` | `compute_overall_score()` — weighted average of whichever stage scores are present (PRD §15 weights: input 0.15 / output 0.35 / hallucination 0.30 / runtime 0.20), renormalized over only the stages that actually produced a score; `None` when none did |
| `aggregation.py` | `crash_outcome()` / `aggregate_outcomes()` — the per-stage crash-handling (a raising validator becomes a WARNING issue) and issue/score aggregation logic, extracted out of `ValidationService` so `RuntimeValidationService` (`runtime/service.py`) could reuse it instead of duplicating it |
| `service.py` | `ValidationService` — `validate_input()`/`validate_output()`/`validate_hallucination()`/`validate_runtime()` (per-stage; the last delegates to a composed `RuntimeValidationService`) and `validate()` (full four-stage report); a crashing validator becomes a WARNING issue rather than failing the whole check; each stage's `valid = no ERROR-severity issues` |
| `create.py` | `create_validation_registry()` / `get_validation_service()` — `@lru_cache`d composition root; registers all four input validators, all three output validators, the hallucination validator, and the `ResearchRuntimeContract` |
| `output/schema_validator.py` | `SchemaValidator` — validates `parsed_output` against `request.output_schema` via `jsonschema.validate()`; independent of the `output_model` re-validation already done in `GenerationService` (this checks any raw schema dict, including one with no corresponding Pydantic model) |
| `output/json_validator.py` | `JsonValidator` — checks whether `result.content` itself is well-formed JSON when JSON was expected (`response_format` JSON/STRUCTURED or `output_schema` set), independent of `SchemaValidator`'s shape check; valid as-is scores 1.0, repairable via `StructuredOutputRepair` is a WARNING at 0.5, unparseable even after repair is an ERROR at 0.0 |
| `output/citation_validator.py` | `CitationValidator` — scans `result.content` for bracketed citation markers (`[S1]`, `[S1, S2]` — the convention `CitationService.build()` and the Context Platform's prompt formatters already use) and flags any not present in `request.prompt_context.citations`/`chunks`, catching fabricated citations; skips entirely when there are no known citations |
| `output/hallucination_validator.py` | `HallucinationValidator` — registered under the `hallucination` stage (not `output`); deterministic, no-LLM groundedness proxy: the fraction of the response's "significant" words (≥4 chars) that also appear in the retrieved context; WARNING-only below a 0.3 threshold (biased toward the PRD's <5% false-positive target), always contributes a groundedness score when there's enough content/context to measure |
| `input/empty_prompt.py` | `EmptyPromptValidator` — empty/whitespace-only `user_prompt` (ERROR — unreachable via `GenerationService`, which already hard-rejects this before any validator runs) or `system_prompt` (WARNING), plus unrendered `{placeholder}` template variables left in either (matches `PromptBuilder.extract_variables()`'s syntax) |
| `input/token_budget.py` | `TokenBudgetValidator` — estimated prompt tokens (cheap words×1.3 approximation, deliberately not `TokenCounter`'s real provider API calls — stays deterministic per the PRD's Principle 2) vs. the resolved provider's context window; WARNING near the limit, ERROR over it, contributes a budget-health score |
| `input/provider_limits.py` | `ProviderLimitsValidator` — streaming/structured_output/json_mode/tool_calling requested but unsupported by the resolved provider; mirrors (doesn't replace) `GenerationService._check_capability_support`'s log-only guard, making the same signal available as a `ValidationIssue` |
| `input/context_validation.py` | `ContextValidator` — data-quality checks on `request.prompt_context`: empty chunk content, duplicate `chunk_id`s, chunks whose `citation_id` has no matching `Citation`; all WARNING |

###### `ai/runtime/generation/validation/runtime/` — **Implemented** (Research contract only; per `runtime_validation_prd.md`)

The 4th `ValidationStage.RUNTIME` stage — semantic/workflow/domain-level correctness a schema/citation check can't express (PRD §1's example: `{"summary": "AI is important."}` passes schema validation but has no citations/evidence/sections/confidence for the Research Runtime). Extends the Validation Platform above rather than being a separate platform (PRD Principle 5); resolved from a new `GenerationRequest.runtime: RuntimeType | None` field — unset by every caller today, so this stage is a no-op in production (see `runtime_validation_prd.md`'s Not Implemented note).

| File | Description |
|------|-------------|
| `enums.py` | `RuntimeType` — `chat`/`research`/`planner`/`reviewer`/`agent`/`mcp`. Distinct from `caching.enums.CacheRuntime`, which drives cache policy rather than output-correctness requirements |
| `interfaces.py` | `RuntimeValidatorInterface` ABC (`name`/`runtime`/`validate(result) -> ValidatorOutcome`) — a single reusable runtime-stage check; `RuntimeContractInterface` ABC (`runtime`/`validate(result) -> ValidatorOutcome`) — what constitutes a valid output for one `RuntimeType`, aggregating its own checks into one outcome |
| `fields.py` | `get_field()` / `get_list_field()` / `item_id()` — duck-typed field extraction off `GenerationResult.parsed_output` (typed `Any`; no runtime output schema is guaranteed to be a specific Pydantic model), handling `BaseModel`, `dict`, and bare-string list items (e.g. `citations: ["S1", "S2"]`) uniformly |
| `registry.py` | `RuntimeRegistry` — per-`RuntimeType` contract/validator lookup: `register_contract()`/`register_validator()`, `contract_for()`/`validators_for()`, and `all_validators` (flattens everything — backs `ValidationRegistry.runtime_validators`) |
| `service.py` | `RuntimeValidationService` — resolves `result.request.runtime`, runs that runtime's registered contract plus any standalone validators (crash-safe, reuses `aggregation.py`), logs `runtime.validation.{started,completed,failed}` via structlog with `duration_ms`/`score`/`issue_count`; a request with no `runtime` set skips the stage entirely (trivially valid, no score) |
| `validators/completeness.py` | `CompletenessValidator` — configurable `required_fields` (scalar presence, e.g. `summary`/`confidence`) / `list_minimums` (e.g. `sections: 2`) / `min_summary_length` (only checked when `"summary"` is itself a required field) |
| `validators/consistency.py` | `ConsistencyValidator` — an `evidence` item's `section_id` must reference a real `sections` entry; flags orphan references. No-ops unless both fields are present as lists |
| `validators/confidence.py` | `ConfidenceValidator` — `confidence` (if present) must be numeric and in `[0, 1]`; contributes it as this check's score when valid |
| `validators/evidence.py` | `EvidenceValidator` — each `evidence` item needs non-empty `content` plus a source pointer (`citation_id`/`section_id`); `minimum` item count defaults to 0 so a contract using `CompletenessValidator`'s `list_minimums` for the count doesn't double-flag it |
| `validators/citation.py` | `RuntimeCitationValidator` — structured `citations`/`evidence[].citation_id` fields vs. `request.prompt_context`'s known citations; the structured-output counterpart to `output/citation_validator.py`, which only scans bracketed markers in free-text `content` |
| `contracts/base.py` | `BaseRuntimeContract` — implements both runtime interfaces (so a contract instance satisfies `RuntimeValidatorInterface.name` too); runs a subclass's `checks` list and merges their outcomes into one `ValidatorOutcome` tagged with `contract_name` (matching the PRD §21 report example), preserving the originating check's name in `ValidationIssue.details["check"]` |
| `contracts/research.py` | `ResearchRuntimeContract` (`contract_name = "research_contract"`) — the first, and so far only, concrete contract (PRD §15): summary present, ≥2 sections, ≥1 citation, ≥1 evidence item, confidence in `[0, 1]`; entirely composed from `validators/`, no bespoke per-field logic |

###### `ai/runtime/generation/langchain/` — **~25% Implemented**

| File | Description |
|------|-------------|
| `__init__.py` | Package marker |
| `output_parsers.py` | `generate_structured()` / `generate_structured_from_request()` — standalone alternative to `GenerationService` using LangChain's `with_structured_output()` (provider formatting + parsing + Pydantic validation in one call) for callers who don't need routing/retries/cost-tracking. Supports OpenAI (`ChatOpenAI`), Claude (`ChatAnthropic`), Gemini (`ChatGoogleGenerativeAI`), Ollama (`ChatOllama`); **not** Groq — no released `langchain-groq` version is compatible with the pinned `groq>=1.5.0` SDK floor the native `GroqProvider` requires |
| `prompt_factory.py` | (empty) |
| `runnables.py` | (empty) |
| `semantic_cache.py` | (empty) |

###### `ai/runtime/generation/prompts/` — **Implemented** (pre-existing; now bridged into Generation)

Prompt Platform. Pre-dates the Structured Output / Validation / Regeneration work and was, until `GenerationService.generate_from_template()`, fully disconnected from Generation.

| File | Description |
|------|-------------|
| `builder.py` | `PromptBuilder.build_from_directory()` — loads a template from `prompt.md` + `metadata.yaml` + `examples.json` on disk; `extract_variables()` parses `{variable}` placeholders |
| `create.py` | `get_prompt_registry()` (loads every template under `PROMPTS_TEMPLATES_DIRECTORY`), `get_token_counter()`, `get_prompt_service()` — `@lru_cache`d composition root |
| `interfaces.py` | `PromptRegistryInterface`, `PromptServiceInterface` ABCs |
| `models.py` | `PromptTemplate` (`name`, `version`, `template`, `variables`, `examples`, `metadata`), `PromptMetadata` (few-shot/routing/evaluation/generation/context/memory/artifacts/runtime/future sub-configs), `PromptRenderRequest`, `PromptRenderResult` |
| `registry.py` | `PromptRegistry` — name+version → `PromptTemplate` resolution |
| `service.py` | `PromptService` — `render()` / `render_text()` / `render_messages()` (builds a `ChatPromptTemplate` via `PromptFactory`, invokes it with the caller's variables, returns LangChain `BaseMessage`s); validates that every declared template variable was supplied |
| `langchain/prompt_factory.py` | `PromptFactory.build()` — constructs a LangChain `ChatPromptTemplate` (system message + optional `FewShotChatMessagePromptTemplate` + human message) from a `PromptTemplate` |

###### `ai/runtime/generation/catalog/` — **Implemented**

Model Catalog. Answers "what models exist, and what are they good at" — metadata, capabilities, cost, and per-task 0-1 scores, consumed by the Routing Platform below to stay model-agnostic (a strategy asks for "highest planning score", not "give me Claude").

| File | Description |
|------|-------------|
| `models.py` | `ModelMetadata` (provider, model name, display name, context window, `ProviderCapabilities`, cost per 1M input/output tokens, `average_latency_ms`, ten per-task 0-1 scores — `quality`/`reasoning`/`coding`/`summarization`/`classification`/`extraction`/`planning`/`review`/`speed`/`reliability`, and policy flags `priority`/`enabled`/`experimental`/`local`) + one instance per known model (`GPT_5`, `GPT_5_MINI`, `GPT_5_NANO`, `CLAUDE_SONNET_4`, `CLAUDE_OPUS_4`, `GEMINI_2_5_PRO`, `GEMINI_2_5_FLASH`, `LLAMA_3_3_70B`, `DEEPSEEK_R1_DISTILL_70B`, `QWEN3`, `DEEPSEEK_R1`, `PHI4` — the three Ollama models are `local=True, experimental=True`) + `ALL_MODELS` / `MODELS_BY_PROVIDER`. Used to seed default model names/costs in `create.py` and as the candidate pool for `RoutingService` |
| `registry.py` | `ModelCatalogRegistry` — `all()`/`enabled()` (excludes only hard-`enabled=False` models; `experimental`/`local` are gated later at routing time)/`by_provider()`/`local_models()`/`get(provider, model_name)`/`has()`/`total_models()`; `get_model_catalog_registry()` — `@lru_cache`d factory |

###### `ai/runtime/generation/routing/` — **Implemented** (Routing Platform — `routing_platform_prd.md`, ADR-026, `docs/architecture/model-routing-platform.md`)

The decision layer between callers (agents, planners, runtime services) and the Generation Platform's providers: which model, which provider, why, and what the fallback chain is. Does not execute prompts or perform generation itself.

| File | Description |
|------|-------------|
| `enums.py` | `RoutingStrategy` — 15 task-based values (`AUTO`, `FAST`, `CHEAP`, `QUALITY`, `REASONING`, `CODING`, `LONG_CONTEXT`, `STRUCTURED_OUTPUT`, `SUMMARIZATION`, `CLASSIFICATION`, `EXTRACTION`, `VALIDATION`, `PLANNING`, `REVIEW`, `LOCAL`); `RequiredCapability` — capability gate mapped onto a `ProviderCapabilities` boolean field |
| `models.py` | `RoutingRequest` (`strategy`, `required_capabilities`, `min_context_window`, `allow_experimental`, `allow_local`, `excluded_models`, `max_fallbacks`, `request_id`), `RoutingDecision` (`selected_model`, `fallback_models`, `score`, `reasons`, `evaluated_count`, `routing_latency_ms`), `RoutingStrategyProfile` (weights + required capabilities/min context window/`require_local` a strategy resolves to) |
| `interfaces.py` | `RoutingServiceInterface` ABC — synchronous `route(request) -> RoutingDecision` (routing is pure in-memory computation, not I/O) |
| `exceptions.py` | `RoutingError`, `NoEligibleModelsError` (raised when capability/policy filtering leaves no candidates) |
| `service.py` | `RoutingService` — `route()`: resolves the strategy's `RoutingStrategyProfile` (falls back to `AUTO` for an unrecognized strategy) → filters `catalog.enabled()` by capability requirements, `min_context_window`, and policy (disabled models always excluded; `experimental`/`local` excluded unless the request or the `LOCAL` strategy's `require_local` opts in) → scores survivors via `ScoringService` → builds a fallback chain preferring a distinct provider per slot before repeating one → returns a `RoutingDecision`, logged via `structlog` (`routing.decision`) |
| `create.py` | `build_strategy_profiles()` — merges the six dedicated task profiles with `DEFAULT_STRATEGY_WEIGHTS`-derived profiles for the rest; `create_routing_service()` — `@lru_cache`d composition root |
| `scoring/weights.py` | `ScoringWeights` (per-dimension weights: `quality`/`reasoning`/`planning`/`review`/`coding`/`summarization`/`classification`/`extraction`/`speed`/`reliability`/`cost`/`context`/`structured_output`); `DEFAULT_STRATEGY_WEIGHTS` — weight profiles for the 9 strategies without a dedicated `strategies/` module |
| `scoring/interfaces.py` | `ScoredModel` (`model`, `score` on a 0-10 scale, `reasons`), `ScoringEngineInterface` ABC — `score_candidates(models, weights) -> list[ScoredModel]`, sorted best-first |
| `scoring/service.py` | `ScoringService` — blends each weighted dimension (direct 0-1 catalog fields; `cost`/`context` min-max normalized across the candidate set, cheapest/largest scoring 1.0; `structured_output` scored 0/1); reasons surface the top-3 weighted contributing dimensions (e.g. "highest planning score") plus a bonus "supports long context" rule for the widest window above a 500k-token threshold |
| `strategies/planning.py`, `summarization.py`, `review.py`, `validation.py`, `coding.py`, `research.py` | One `RoutingStrategyProfile` constant each (`PLANNING_PROFILE`, ... `RESEARCH_PROFILE`, the last mapping to `RoutingStrategy.REASONING`) — weights transcribed from the PRD's per-task tables, plus any dedicated `required_capabilities`/`min_context_window` (e.g. `VALIDATION_PROFILE` requires `STRUCTURED_OUTPUT`, `RESEARCH_PROFILE` requires a 100k-token minimum context window) |

###### `ai/runtime/generation/caching/` — **Implemented** (Runtime Caching Platform — `runtime_caching_platform_prd.md`, ADR-027, `docs/architecture/runtime-caching-platform.md`)

Caches `GenerationResult`s to cut provider cost, latency, and duplicate execution. Wired directly into `GenerationService._generate_with_provider`: a lookup runs once a candidate model is resolved (before the provider call), a store runs after generation (incl. any regeneration attempts) completes. L3 Session Cache is a deliberately separate API surface — keyed by a caller-tracked session id rather than request content — implemented and exposed but still not called by anything; a minimal `Conversation`/`Message` persistence layer now exists (Streaming Platform, Milestone 2.9.10 — see `models/conversation.py` below) but nothing has wired it to L3 yet.

| File | Description |
|------|-------------|
| `models.py` | `CacheKey` (frozen, `redis_key()` — provider/model/routing_strategy/prompt_hash/context_hash/schema_hash/temperature/top_p), `CacheResult` (`hit`, `level`, `generation_result`, optional `similarity`, `lookup_latency_ms`), `CacheStatistics` (exact/semantic/session hits, misses, `total_lookups`/`hit_ratio` properties, `tokens_saved`, `cost_saved`) |
| `enums.py` | `CacheLevel` (exact/semantic/session), `CachePolicy` (auto/never/exact_only/semantic/session), `CacheRuntime` (chat/research/benchmark/planner/tool_agent/summarizer/reviewer/critic) |
| `interfaces.py` | `ExactCacheProviderInterface`/`SemanticCacheProviderInterface`/`SessionCacheProviderInterface` ABCs — all fail-open by contract (a backend error is a miss/no-op, never raised) |
| `exceptions.py` | `CachingError`, `CacheBackendUnavailableError` |
| `service.py` | `CachingService` — `lookup()`/`store()` (L1 Exact → L2 Semantic per resolved `CachePolicy`; streaming and non-streaming requests are treated identically — see `generation/streaming/` below for why the old blanket streaming bypass was removed), `get_session()`/`set_session()`/`invalidate_session()`/`clear_session()` (L3), `statistics` property, structlog `caching.lookup` per call |
| `create.py` | `create_caching_service()` — `@lru_cache`d composition root; `create_exact_cache_provider()`/`create_semantic_cache_provider()`/`create_session_cache_provider()` each return a `Null*` no-op when their `settings.*_cache_enabled` flag is off; wires a shared Valkey client (L1/L3) and a `RedisSemanticCache` against `settings.semantic_cache_redis_url` (L2) |
| `exact/key_builder.py` | `hash_prompt()`/`hash_context()`/`hash_schema()` (sha256, unit-separator-joined to avoid system/user-split collisions), `build_exact_cache_key()` |
| `exact/provider.py` | `ValkeyExactCacheProvider` — stores/retrieves full `GenerationResult` JSON under `CacheKey.redis_key()` |
| `exact/null.py` | `NullExactCacheProvider` |
| `semantic/embeddings_adapter.py` | `OpenAISemanticCacheEmbeddings` — thin `langchain_core.embeddings.Embeddings` adapter over the OpenAI client (only sync `embed_query`/`embed_documents` implemented; LangChain's default async delegation via executor is sufficient) |
| `semantic/provider.py` | `RedisSemanticCacheProvider` — wraps `langchain_redis.RedisSemanticCache`; stores the full `GenerationResult` JSON as the `Generation.text` payload; folds `context_hash` + every other non-prompt `CacheKey` field into the library's `llm_string` post-retrieval filter (ADR-027's cross-document isolation constraint); `CacheResult.similarity` always `None` — the library's `BaseCache` interface doesn't surface the matched distance |
| `semantic/null.py` | `NullSemanticCacheProvider` |
| `session/provider.py` | `ValkeySessionCacheProvider` — namespaced `cache:session:{session_id}:{key}` store; `clear()` uses `scan_iter(match=...)` |
| `session/null.py` | `NullSessionCacheProvider` |
| `policies/models.py` | `RuntimeCacheProfile` (`runtime`, `policy`, `exact_ttl_seconds`) |
| `policies/service.py` | `CachePolicyResolver` — explicit `GenerationRequest.cache_policy` override wins, else the `CacheRuntime` profile, else a default profile (mirrors `RoutingService._resolve_profile`'s fallback-to-AUTO shape) |

Infra: L2 requires a RediSearch-capable server, which plain Valkey doesn't provide — see the dedicated `semantic-cache` (`redis-stack-server`) docker-compose service and the `redis` client downgrade (`<8.0`, to satisfy `langchain-redis`'s `redisvl` dependency) noted in `PROJECT_STATUS.md` Milestone 2.9.9.

`tests/unit/ai/runtime/generation/caching/` — 22 tests (+1 updated for the streaming-participates-in-cache fix below): key builder determinism/sensitivity, policy resolution precedence/fallback, `CachingService` policy branching (AUTO/EXACT_ONLY/SEMANTIC/NEVER), statistics, session cache independence.

###### `ai/runtime/generation/streaming/` — **Implemented** (Generation Streaming Platform — `streaming_platform_prd.md`, ADR-028, `docs/architecture/streaming-platform.md`)

Real-time execution support for generation workloads — the "Layer 2 orchestration" half of the Streaming Platform, sitting on top of `runtime/events/`'s canonical protocol (see above). Every provider's `stream()` method (`generation/providers/*.py`) already existed before this milestone; what was missing was `GenerationService.stream_generate()`, cache-aware orchestration, and a transport layer, all filled in here.

| File | Description |
|------|-------------|
| `enums.py` | `StreamTransport` (sse/websocket), `ValidationEventType` (validation_started/validation_completed — generation-scoped, not a Layer-3 `runtime/events/` domain, since validation is a Generation Platform concern; not yet emitted) |
| `models.py` | `StreamCacheOutcome` (`hit`, `level`, `replayed`) — carried in the START event's `metadata["cache"]` |
| `interfaces.py` | `StreamSerializerInterface` — `serialize(event: StreamEvent) -> str \| dict` |
| `service.py` | `StreamingService` — `stream_generate(request, provider=None)`: resolves the provider/model (via `GenerationService.resolve_streaming_provider()` when not explicit), checks the Runtime Cache; on a **hit**, replays the cached content as character-chunked synthetic `TOKEN` events (`_REPLAY_CHUNK_CHARS = 12`) rather than skipping the stream contract; on a **miss**, streams live via `GenerationService.stream_generate()`, converts each `StreamChunk` to a `StreamEvent` via the shared adapter, and stores the assembled result once `COMPLETE` is reached (best-effort `count_tokens()`-estimated statistics, since provider `stream()` implementations don't surface real usage mid-stream) |
| `create.py` | `create_streaming_service()` — composition root; reuses `create_generation_service()`'s own registry (via the new `GenerationService.registry` property) rather than building a second, duplicate one |
| `transports/sse.py` | `sse_stream_response()` — wraps a `StreamEvent` async generator as a `StreamingResponse` (`text/event-stream`, `X-Accel-Buffering: no`); emits a `: ping` heartbeat comment on a 15s idle interval (guards against load-balancer/proxy idle-connection timeouts) and enforces a 300s hard duration ceiling |
| `transports/websocket.py` | `run_websocket_stream()` — sends each `StreamEvent` as a JSON frame over an accepted `WebSocket`; a client disconnect closes the underlying event generator, cancelling the in-flight generation |
| `serializers/sse.py` | `serialize_sse()` — `event: <type>\ndata: <json>\n\n` wire format |
| `serializers/json.py` | `serialize_json()` — `StreamEvent.model_dump(mode="json")`, used by the WebSocket transport |

`GenerationService.stream_generate()` (R2) and the public `resolve_streaming_provider()`/`registry` property live in `generation/service.py` itself, alongside `generate()`.

`tests/unit/ai/runtime/generation/streaming/test_service.py` — cache-hit replay, live-stream store-on-complete, error-mid-stream, no-caching-service paths. `tests/unit/ai/runtime/events/adapters/test_base.py` — `StreamChunk` → `StreamEvent` mapping. `tests/unit/ai/runtime/generation/test_service.py` gained `stream_generate()` coverage (provider resolution, capability check, routing). `tests/integration/ai/test_chat_stream.py` — end-to-end `POST /api/v1/chat/stream` (SSE frame order, persisted turn).

###### Not Yet Implemented (all files empty)

| Directory | Purpose (planned) |
|-----------|--------|
| `artifacts/` | Generation result persistence |
| `observability/` (most files) | Cost/latency/token tracking, metrics collection — `token_counter.py` is the one implemented exception |

##### `ai/shared/`

Mostly empty — planned shared AI types and interfaces. `local_embeddings.py` is a real, implemented exception: a shared local embedding model used outside the Embedding Platform proper.

| File | Purpose |
|------|---------|
| `exceptions.py` | (empty) |
| `interfaces.py` | (empty) |
| `local_embeddings.py` | `get_local_embedding_model()` — `@lru_cache`d singleton loading `sentence-transformers/all-MiniLM-L6-v2`; used by `EmbeddingCompressionProvider` (`ai/knowledge/context/compression/providers/embedding.py`) to score chunk-similarity for compression, independent of the Embedding Platform's own provider registry |
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
| `v1/chat.py` | **Implemented** (Streaming Platform, Milestone 2.9.10) — `POST /chat/stream` (SSE; `get_current_user` auth, since this is a `POST` consumed via `fetch`/`ReadableStream` on the frontend rather than a bare `EventSource`, which can't attach a custom `Authorization` header) and `WebSocket /chat/ws` (`?token=` query-param auth, since a browser's WS handshake has the same header limitation). Both load/create a `Conversation` via `ConversationService`, fold prior turns into a transcript-prefixed `user_prompt`, call `StreamingService.stream_generate()`, and persist the completed turn once the stream reaches `COMPLETE` (`_persist_on_complete` — accumulation/persistence lives at the route level, not inside the generic Streaming Platform, keeping that platform conversation-agnostic) |
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
| `dependencies.py` | `authenticate_token(token, session)` — verifies a JWT and syncs the user (shared by both HTTP and WebSocket auth); `get_current_user` FastAPI dependency wraps it for the `Authorization` header. Also used directly by the chat WebSocket route (`?token=` query param), since a browser's WS handshake can't set a custom header either |
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
| `generation.py` | **Implemented** (Streaming Platform, Milestone 2.9.10) — `get_generation_service()` / `get_streaming_service()` (`@lru_cache`d singletons, wrap `create_generation_service()`/`create_streaming_service()`), `get_conversation_service(session)` — request-scoped (not cached — carries the per-request DB session), builds a `ConversationService` |
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
| `conversation.py` | **Implemented** (Streaming Platform, Milestone 2.9.10) — `Conversation` (id, owner_id FK→users, title) and `Message` (id, conversation_id FK→conversations, `role: MessageRole`, content, provider, model) SQLAlchemy models, modeled directly on `document.py`'s conventions |
| `document.py` | `Document` SQLAlchemy model — id, owner_id (FK→users), filename, storage_key, content_type, size_bytes, checksum, `upload_status`, `processing_status`, `processed_at`, `processing_error` |
| `enums.py` | `DocumentUploadStatus` StrEnum (pending, uploading, completed, failed), `DocumentProcessingStatus` StrEnum (pending, processing, completed, failed) — split from the original single `DocumentStatus` — and `MessageRole` StrEnum (user, assistant) |
| `user.py` | `User` SQLAlchemy model — id, auth_provider, provider_user_id, email, username, full_name, avatar_url, is_active, is_verified, is_superuser, last_login_at |

---

#### `repositories/`

| File | Description |
|------|-------------|
| `__init__.py` | Exports `UserRepository`, `DocumentRepository`, `ConversationRepository` |
| `conversation.py` | **Implemented** (Streaming Platform, Milestone 2.9.10) — `ConversationRepository`: `create`, `get_by_id_for_owner` (owner-scoped, so a caller can never load another user's conversation by id), `add_message`, `list_messages` (oldest-first, for transcript building) |
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
| `chat.py` | **Implemented** — `ChatStreamRequest` (`user_prompt`, `conversation_id`, `provider`, `routing_strategy`), used by both `/chat/stream` and `/chat/ws` |
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
| `conversation.py` | **Implemented** (Streaming Platform, Milestone 2.9.10) — `ConversationService`: `get_or_create()` (owner-scoped), `load_history()` (returns langchain `HumanMessage`/`AIMessage`), `append_turn()` (persists both halves of a completed exchange, commits explicitly like `UserService`) |
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
| `ADR-024-generation-model-strategy.md` | Decision: Generation Platform adopts a multi-provider model strategy optimizing for quality/cost/latency/privacy/capability diversity rather than benchmark rankings alone |
| `ADR-025-platform-roadmap.md` | Decision: freezes the long-term platform roadmap — ResearchMind is an AI Research Platform (Knowledge → Context → Generation → Evaluation → Research Runtime → Agent Runtime → MCP Integrations), not a single RAG application; Generation Platform maturity tracked inline (~75%) |
| `ADR-026-model-routing-platform.md` | Decision: introduces a dedicated Model Routing Platform inside the Generation Platform — a centralized decision layer (model/provider/fallback selection, cost optimization, task-based routing) rather than embedding model choice inside agents or duplicating provider-selection logic across callers |
| `ADR-027-runtime-caching-platform.md` | Decision: introduces a Runtime Caching Platform (L1 exact/L2 semantic/L3 session) wired into `GenerationService`; streaming requests participate in caching identically to non-streaming ones (corrected as part of the Streaming Platform work — see ADR-028) rather than bypassing the cache entirely |
| `ADR-028-streaming-platform.md` | Decision: introduces the Streaming Platform as two independent layers — a Runtime Event Platform (`runtime/events/`, canonical `StreamEvent` protocol reusable by any future runtime) and a Generation Streaming Platform (`generation/streaming/`, SSE/WebSocket transport + cache-aware orchestration) — rather than a chat-only streaming feature or a duplicated `streaming/providers/` hierarchy. Reconciled during implementation: the event-type model is layered (each future runtime owns its own enum) rather than one flat shared enum, and `StreamEvent` is the richer 8-field shape consistently across the doc |

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
| `model-routing-platform.md` | Model Routing Platform architecture (companion to ADR-026, **Implemented**) — model catalog, task-based `RoutingStrategy`, capability/policy filtering, the scoring engine, fallback chain construction, observability |
| `observability-platform.md` | Observability Platform architecture |
| `observability-strategy.md` | Observability strategy — logging is the only implemented pillar (structlog, request correlation); metrics/tracing are placeholders under `docs/monitoring/` |
| `project-constitution.md` | Project principles, goals, and constraints |
| `repository-structure.md` | Repository layer patterns |
| `reranking-platform.md` | Reranking Platform architecture (Milestone 2.7.2, companion to ADR-022) — CrossEncoder/Voyage AI providers, canonical models, integration strategy, evaluation metrics |
| `retrieval-benchmarking-strategy.md` | Retrieval Benchmarking Strategy (**Accepted**) — freezes the initial evaluation methodology: dense/sparse/hybrid scope, dataset size/format, 6 query categories with expected winners, ADR-020 metric requirements, the Hybrid decision gate (`Dense Results != Sparse Results`) |
| `runtime-caching-platform.md` | Runtime Caching Platform architecture (companion to ADR-027, **Implemented**) — L1 exact/L2 semantic/L3 session caching, policy resolution; its "Streaming" section was corrected during the Streaming Platform work to remove the blanket `request.stream` cache bypass |
| `streaming-platform.md` | Streaming Platform architecture (companion to ADR-028, **Implemented**) — Runtime Event Platform + Generation Streaming Platform two-layer design, layered event-type model, SSE/WebSocket transports, cache-hit replay, "Production Considerations" (SSE heartbeats, proxy buffering, stream timeout ceiling, browser `EventSource`/WebSocket auth limitations) |
| `structured-output-platform.md` | Structured Output Platform (**~99% complete in its own scope**) — the continuously-updated, detailed architecture doc for `generation/structured_output/`, `generation/validation/`, `generation/langchain/`, and the Prompt Platform bridge: native provider structured output, parser/repair fallback, input/output/hallucination validation (registry, scoring, `ValidationReport`), regeneration strategy, provider capability flags, prompt-template integration |
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
| `unit/ai/knowledge/context/__init__.py` | Package marker |
| `unit/ai/knowledge/context/factories.py` | Not a test module — shared `make_context_chunk()` factory imported by the tests below |
| `unit/ai/knowledge/context/test_service.py` | `ContextBuilderService.build()` — dedup runs before anything downstream, final `PromptContext` is populated from the formatted result, adjacent same-document chunks are merged, output is ordered by score descending, one numbered citation is produced per final chunk, `retrieval_strategy` is set from (or left `None` without) `RetrievalResult.statistics`, `parent_chunk_id` is parsed out of chunk metadata before parent expansion runs |
| `unit/ai/knowledge/context/artifacts/__init__.py` | Package marker |
| `unit/ai/knowledge/context/artifacts/test_reader.py` | `ChunkArtifactReader.load()` — builds the expected `documents/{owner_id}/{document_id}/chunking/{strategy}/{artifact_id}/chunks.json` storage key, parses the downloaded payload into a canonical `ChunkArtifact`, propagates storage errors untouched |
| `unit/ai/knowledge/context/builders/__init__.py` | Package marker |
| `unit/ai/knowledge/context/builders/test_deduplication.py` | `DeduplicationService` — collapses repeated `chunk_id`s, preserves first-occurrence order, no-op when there are no duplicates or the input is empty |
| `unit/ai/knowledge/context/builders/test_ordering.py` | `ContextOrderingService` — sorts by score descending, breaks ties by ascending `chunk_index`, empty input returns empty |
| `unit/ai/knowledge/context/builders/test_adjacent_merge.py` | `AdjacentMergeService` — empty input is a no-op, a single chunk still gains `merged_chunk_ids`, two/three consecutive same-document chunks are combined into one block, a gap in `chunk_index` is not bridged, chunks from different documents are never merged |
| `unit/ai/knowledge/context/builders/test_parent_expansion.py` | `ParentExpansionService.expand()` — empty input never calls the reader; chunks missing artifact metadata are skipped; the artifact is loaded even when no chunk has a `parent_chunk_id`; a resolvable parent enriches the chunk; an unresolvable `parent_chunk_id` leaves the chunk unenriched; the artifact is loaded once per shared `(owner_id, document_id, strategy, artifact_id)` group and separately per distinct group |
| `unit/ai/knowledge/context/citations/__init__.py` | Package marker |
| `unit/ai/knowledge/context/citations/test_service.py` | `CitationService.build()` — citations are numbered starting at `S1`, the `citation_id` is written back onto the source chunk, citation fields are mapped from the chunk, `chunk_ids` uses the chunk's own id when it wasn't merged and `merged_chunk_ids` when it was, empty input returns an empty result |
| `unit/ai/knowledge/context/compression/__init__.py` | Package marker |
| `unit/ai/knowledge/context/compression/test_registry.py` | `CompressionRegistry` — `get` resolves a registered provider / raises for an unregistered strategy, `register` overwrites the previous provider for a strategy |
| `unit/ai/knowledge/context/compression/test_service.py` | `CompressionService` — delegates to the resolved provider, raises `ValueError` when the strategy isn't registered, falls back to the original chunks (unchanged) when the resolved provider raises `CompressionError` |
| `unit/ai/knowledge/context/compression/test_create.py` | `create_compression_service()` — registers all four strategies (Token Budget, Embedding Redundancy, LangChain, LLM) |
| `unit/ai/knowledge/context/compression/test_exceptions.py` | Compression exception hierarchy — `CompressionProviderError`/`CompressionTimeoutError` are both catchable as `CompressionError` (new) |
| `unit/ai/knowledge/context/compression/providers/__init__.py` | Package marker |
| `unit/ai/knowledge/context/compression/providers/test_token_budget.py` | `TokenBudgetCompressionProvider` — prefers highest score first, keeps every chunk that fits the budget, skips an oversized chunk while continuing to pack smaller ones, falls back to the default budget when `max_tokens` is `None`, reports accurate statistics, empty input returns an empty result |
| `unit/ai/knowledge/context/compression/providers/test_embedding.py` | `EmbeddingCompressionProvider` — zero or one chunk never calls the model, a later near-duplicate chunk is dropped, dissimilar chunks are kept, a custom `similarity_threshold` is honored, statistics are accurate, every chunk's content text is encoded |
| `unit/ai/knowledge/context/compression/providers/test_langchain.py` | `LangChainCompressionProvider` (new) — 0 chunks never builds an LLM, a missing/blank query raises `CompressionProviderError`, chunks the (`FakeListChatModel`-faked) LLM extracts nothing relevant from are dropped, every non-content field survives on kept chunks, statistics are accurate, a provider failure/timeout is wrapped in `CompressionProviderError`/`CompressionTimeoutError`, no injected LLM + no configured API key raises |
| `unit/ai/knowledge/context/compression/providers/test_stub_providers.py` | `LLMCompressionProvider` — confirmed to still `raise NotImplementedError` (V4 not built yet; the former `LangChainCompressionProvider` case here was replaced by `test_langchain.py` now that V3 is implemented) |
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
| `unit/ai/runtime/generation/` | Generation Platform test tree — `test_service.py` (`GenerationService` delegation, empty-prompt/context validation errors, provider-not-found/error propagation, the ValidationService integration: `result.validation` populated from the report, input-only ERRORs don't trigger regeneration, output-stage ERRORs do; plus routing integration — routes to the selected model when no `provider` is given, falls back through `fallback_models` on `GenerationExecutionError`, skips unregistered-provider candidates, raises once every candidate fails, wraps `NoEligibleModelsError` as `GenerationValidationError`), `test_registry.py`, `providers/test_*.py` (one per provider), `prompts/test_*.py` (builder/registry/service/templates/examples/token estimation) |
| `unit/ai/runtime/generation/catalog/` | `test_registry.py` — `ModelCatalogRegistry` `all()`/`enabled()` (excludes only `enabled=False`, keeps `experimental`/`local`)/`get()`/`has()`/`by_provider()`/`local_models()`/`total_models()`, and that `get_model_catalog_registry()` is a cached singleton |
| `unit/ai/runtime/generation/routing/` | Routing Platform test tree — `test_service.py` (`RoutingService` capability/policy filtering — disabled always excluded, experimental/local opt-in, `LOCAL` strategy narrows to local models, required capabilities combine request + profile, `min_context_window`, `excluded_models`; unknown-strategy fallback to `AUTO`; fallback chain prefers distinct providers then repeats; `max_fallbacks` bounds including 0; `NoEligibleModelsError` when nothing survives), `scoring/test_service.py` (`ScoringService` weighted blending, cost/context normalization relative to the candidate set, boolean capability scoring, sorting, reasons) |
| `unit/ai/runtime/generation/validation/` | Validation Platform test tree — `factories.py` (shared `make_request`/`make_result`/`make_chunk`/`make_citation` builders — `make_request()` now also takes `runtime: RuntimeType \| None`), `test_models.py` (`ValidationReport.issues` flattening, `ValidatorOutcome` defaults), `test_scoring.py` (`compute_overall_score` renormalization), `test_registry.py` (`ValidationRegistry` per-stage isolation, defensive copies, `register_runtime_validator`/`register_runtime_contract` delegation), `test_service.py` (per-stage aggregation, stage-stamping, crash → WARNING, `validate_runtime()` contract resolution, full four-stage report assembly); `input/test_empty_prompt.py`, `input/test_context_validation.py`, `input/test_provider_limits.py`, `input/test_token_budget.py`; `output/test_schema_validator.py`, `output/test_citation_validator.py`, `output/test_json_validator.py`, `output/test_hallucination_validator.py` — one file per validator, covering its main and edge cases |
| `unit/ai/runtime/generation/validation/runtime/` | Runtime Validation Platform test tree (new, 109 cases) — `test_registry.py` (`RuntimeRegistry` per-`RuntimeType` isolation, `contract_for`/`validators_for`, `all_validators` flattening), `test_service.py` (`RuntimeValidationService` — no-runtime-set no-op, matching contract runs + stage-stamping, non-matching runtime ignored, standalone validators run alongside the contract, crash → WARNING); `validators/test_completeness.py`, `validators/test_consistency.py`, `validators/test_confidence.py`, `validators/test_evidence.py`, `validators/test_citation.py` (one file per generic validator); `contracts/test_research.py` (`ResearchRuntimeContract` — compliant output is valid, the PRD §3 trivial-output example fails every requirement, every issue tagged with `contract_name`) |
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

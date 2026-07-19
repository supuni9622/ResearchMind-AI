# Project Structure

Complete folder and file structure of the ResearchMind-AI monorepo.

```
ResearchMind-AI/
│
├── .claude/
│   └── settings.local.json      # Local Claude Code permission/tooling settings
│
├── .github/
│   ├── ISSUE_TEMPLATE/          # GitHub issue templates
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI pipeline
│
├── agents/                      # AI agent definitions (planned)
│   ├── evaluator/               # Evaluates research quality
│   ├── planner/                 # Plans research strategy
│   ├── research/                # Core research agent
│   ├── reviewer/                # Reviews and critiques output
│   ├── shared/                  # Shared agent utilities
│   └── summarizer/              # Summarizes research findings
│
├── alembic/                     # Database migration framework
│   ├── versions/
│   │   ├── 43dc35ceb875_debug.py                          # Initial migration: creates users table + updated_at trigger
│   │   ├── a97b3b8eee9f_create_documents_table.py          # Creates documents table with processing lifecycle columns
│   │   ├── 1b6e40f3a754_split_document_status_into_upload_.py  # Splits status into upload_status + processing_status
│   │   ├── bca5e4edca5c_create_conversations_and_messages_tables.py  # Creates conversations + messages tables (Streaming Platform, Milestone 2.9.10); downgrade explicitly drops the message_role enum type
│   │   └── d9e2f4a6b8c0_add_conversation_history_compaction.py # Adds persisted Chat prompt-summary and compaction-boundary fields
│   ├── env.py                   # Alembic runtime config (async engine, model imports)
│   ├── script.py.mako           # Migration file template
│   └── README                   # Alembic usage notes
│
├── apps/                        # Deployable applications
│   ├── api/                     # FastAPI backend
│   │   └── app/
│   │       ├── ai/              # AI subsystem
│   │       │   ├── artifacts/                # Artifact Platform (Milestone 3.10) — centralized, cross-cutting canonical persistence for AI Runtime executions; see artifacts_platform_prd.md
│   │       │   │   ├── models.py            # ArtifactMetadata, JsonDictFile (generic dict[str, Any] wrapper for the scaffold-only domains)
│   │       │   │   ├── enums.py             # ArtifactPolicy (never/session/short_term/long_term/permanent), ArtifactCategory (incl. OBSERVABILITY), ArtifactRuntime (incl. PROCESSING — new, for the Knowledge Processing pipeline's observability artifacts)
│   │       │   │   ├── interfaces.py        # ArtifactBuilder/Writer/ReaderInterface (generic Protocols)
│   │       │   │   ├── exceptions.py        # ArtifactError hierarchy
│   │       │   │   ├── create.py            # composition root — storage + per-category writer factories + get_artifact_policy_service() + create_observability_artifact_writer()
│   │       │   │   ├── policies/            # ArtifactPolicyService.should_persist(runtime, category), DEFAULT_ARTIFACT_POLICY_RULES — incl. (CHAT|RESEARCH|PROCESSING, OBSERVABILITY) rules
│   │       │   │   ├── writers/base.py      # write_json_artifact()/write_text_artifact() / BaseArtifactWriter — shared upload boilerplate (write_text_artifact added for report.md)
│   │       │   │   ├── readers/base.py      # BaseArtifactReader — _read_json()/_read_json_optional()/_read_text()
│   │       │   │   ├── generation/          # Implemented, live — GenerationArtifact, wired into GenerationService.generate()
│   │       │   │   ├── streaming/           # Implemented, live — StreamArtifact, wired into StreamingService._stream_live()
│   │       │   │   ├── conversation/        # Implemented, live — ConversationTurnArtifact (one immutable file per turn) + ConversationIdentity, wired into chat.py
│   │       │   │   ├── session/             # Scaffold-only — SessionArtifact, unwired (no session concept distinct from Conversation yet)
│   │       │   │   ├── research/            # Implemented, live — ResearchArtifact, wired into ResearchService (Phase 4, research_api_prd.md)
│   │       │   │   ├── agent/               # Scaffold-only — AgentArtifact, unwired (no Agent Runtime yet)
│   │       │   │   ├── evaluation/          # Scaffold-only, deliberately unwired — EvaluationArtifact is S3-backed, but benchmarks/ (the real evaluation harness, see below) is explicitly independent of production infra; reserved for a future online/API-triggered evaluation surface (api/v1/evaluation.py is still empty)
│   │       │   │   ├── observability/       # Implemented, live (new, Phase 3.9, oberservability_platform_prd.md) — ObservabilityArtifact (metrics/statistics as dict[str, Any], report as markdown string), ObservabilityArtifactBuilder/Writer/Reader; storage layout observability/{execution_id}/{metadata.json,metrics.json,statistics.json?,report.md}; wired from GenerationService.generate()/stream_generate() and ProcessingService.process()
│   │       │   │   └── replay/              # GenerationReplayService/StreamReplayService (real), ResearchReplayService (stub)
│   │       │   ├── config/
│   │       │   │   └── settings.py          # AI-specific configuration
│   │       │   ├── guardrails/               # Guardrails Platform (Milestone 11.16) — standalone, spans input/retrieval/generation/runtime; wired into GenerationService + ContextBuilderService (guardrail_integration_prd.md)
│   │       │   │   ├── models.py            # GuardrailIssue, GuardrailResult, GuardrailReport
│   │       │   │   ├── enums.py             # GuardrailSeverity, GuardrailStage, GuardrailCategory, GuardrailAction
│   │       │   │   ├── interfaces.py        # Input/Retrieval/Generation/RuntimeGuardrailInterface ABCs
│   │       │   │   ├── exceptions.py        # GuardrailError hierarchy
│   │       │   │   ├── registry.py          # GuardrailRegistry — per-stage ordered registration
│   │       │   │   ├── service.py           # GuardrailService — evaluate_input/retrieval/generation/runtime/evaluate(), crash-safe aggregation
│   │       │   │   ├── create.py            # create_guardrail_registry(), get_guardrail_service() (@lru_cache)
│   │       │   │   ├── constants.py         # shared thresholds/limits
│   │       │   │   ├── input/
│   │       │   │   │   ├── prompt_injection.py     # PromptInjectionGuardrail — regex, P0, jailbreak escalation
│   │       │   │   │   ├── scope_validation.py     # ScopeValidationGuardrail — off-topic heuristic
│   │       │   │   │   ├── pii_detection.py        # PiiDetectionGuardrail — email/CC/API-key/token regex
│   │       │   │   │   ├── rate_limit.py           # RateLimitGuardrail — foundation, always-allow
│   │       │   │   │   └── toxicity.py             # ToxicityGuardrail — foundation, always-allow
│   │       │   │   ├── retrieval/
│   │       │   │   │   ├── context_sanitization.py # ContextSanitizationGuardrail — composes ai/knowledge/context/guardrails/
│   │       │   │   │   ├── access_control.py       # AccessControlGuardrail — foundation, permissive default
│   │       │   │   │   ├── source_trust.py         # SourceTrustGuardrail — uses trust/
│   │       │   │   │   └── citation_integrity.py   # CitationIntegrityGuardrail — chunk/citation existence check
│   │       │   │   ├── generation/
│   │       │   │   │   ├── faithfulness.py         # FaithfulnessGuardrail — wraps HallucinationValidator (Validation Platform)
│   │       │   │   │   ├── schema_enforcement.py   # SchemaEnforcementGuardrail — wraps SchemaValidator/JsonValidator
│   │       │   │   │   ├── pii_leakage.py          # PiiLeakageGuardrail — regex on generated content
│   │       │   │   │   └── moderation.py           # ModerationGuardrail — foundation, always-allow
│   │       │   │   ├── runtime/
│   │       │   │   │   ├── execution_limits.py     # BudgetPolicy, ExecutionState
│   │       │   │   │   ├── budget_guardrail.py     # BudgetGuardrail — max_tokens/cost/tool_calls/iterations/runtime_seconds
│   │       │   │   │   ├── loop_detection.py       # LoopDetectionGuardrail — max_iterations + repeated-state-hash detection
│   │       │   │   │   ├── tool_policy.py          # ToolPolicyGuardrail — foundation, allow-all default
│   │       │   │   │   └── approval_gate.py        # ApprovalRequest/Response + ApprovalGateInterface — interfaces only, unregistered
│   │       │   │   ├── trust/                       # new Source Trust Platform (PRD §9)
│   │       │   │   │   ├── models.py               # SourceTrust, SourceType
│   │       │   │   │   ├── trust_registry.py       # TrustRegistry — static trust-score-by-source-type table
│   │       │   │   │   ├── trust_policies.py       # action_for_trust_score() — RiskPolicy -> GuardrailAction
│   │       │   │   │   └── scoring.py              # compute_trust_score() — base + peer-reviewed bonus
│   │       │   │   ├── policies/
│   │       │   │   │   ├── fail_policy.py          # FailPolicy (FAIL_OPEN/FAIL_CLOSED)
│   │       │   │   │   ├── risk_policy.py          # RiskPolicy (LOW/MEDIUM/HIGH/CRITICAL) + thresholds
│   │       │   │   │   ├── regeneration_policy.py  # RegenerationPolicy
│   │       │   │   │   └── runtime_policy.py       # RuntimePolicy
│   │       │   │   ├── scoring/
│   │       │   │   │   ├── weights.py              # STAGE_WEIGHTS (input .30/retrieval .30/generation .20/runtime .20)
│   │       │   │   │   └── overall_risk.py         # compute_overall_risk() — renormalizing weighted average
│   │       │   │   ├── artifacts/
│   │       │   │   │   ├── models.py               # GuardrailArtifact — versioned wrapper over GuardrailReport
│   │       │   │   │   ├── builders.py             # GuardrailArtifactBuilder — pure build()
│   │       │   │   │   └── writers.py              # GuardrailArtifactWriter — persists guardrails/{run_id}/*.json
│   │       │   │   ├── reports/
│   │       │   │   │   ├── guardrail_report.py     # summarize_report(), stage_summaries()
│   │       │   │   │   └── issue_report.py         # group_by_severity/category, count_by_severity
│   │       │   │   └── utils/
│   │       │   │       └── patterns.py             # match_any() + shared PII_PATTERNS
│   │       │   ├── knowledge/               # RAG knowledge pipeline
│   │       │   │   ├── cache/               # Embedding + query-embedding caches
│   │       │   │   │   ├── embeddings/
│   │       │   │   │   │   ├── create.py           # create_embedding_cache() — composition root (Valkey or Null based on settings)
│   │       │   │   │   │   ├── interfaces.py       # EmbeddingCache ABC
│   │       │   │   │   │   ├── key.py              # build_embedding_cache_key() — provider+model+config-fingerprint+text hash
│   │       │   │   │   │   ├── null.py             # NullEmbeddingCache — no-op fallback
│   │       │   │   │   │   └── valkey.py           # ValkeyEmbeddingCache — Redis-backed vector cache
│   │       │   │   │   └── query_embeddings/
│   │       │   │   │       ├── create.py           # create_query_embedding_cache() — composition root (Valkey or Null based on settings)
│   │       │   │   │       ├── interfaces.py       # QueryEmbeddingCache ABC — get()/set()
│   │       │   │   │       ├── key.py              # build_query_embedding_cache_key() — provider+model+config-fingerprint+query hash
│   │       │   │   │       ├── null.py             # NullQueryEmbeddingCache — no-op fallback
│   │       │   │   │       └── valkey.py           # ValkeyQueryEmbeddingCache — Redis-backed, TTL-based query embedding cache (fails open on Redis errors)
│   │       │   │   ├── chunking/            # Document chunking pipeline
│   │       │   │   │   ├── artifacts/
│   │       │   │   │   │   ├── builder.py          # ChunkArtifactBuilder — builds ChunkArtifact from generated chunks
│   │       │   │   │   │   ├── models.py           # ChunkArtifact + sub-models (document, strategy, statistics, evaluation)
│   │       │   │   │   │   └── writer.py           # ChunkArtifactWriter — persists ChunkArtifact to storage (S3)
│   │       │   │   │   ├── evaluators/             # Chunk quality evaluators (planned)
│   │       │   │   │   ├── providers/
│   │       │   │   │   │   ├── fixed.py            # FixedChunkingProvider — fixed-size overlapping character windows
│   │       │   │   │   │   ├── recursive.py        # RecursiveChunkingProvider — LangChain RecursiveCharacterTextSplitter
│   │       │   │   │   │   └── markdown.py         # MarkdownChunkingProvider — heading-aware split, then recursive on oversized sections
│   │       │   │   │   ├── statistics/
│   │       │   │   │   │   └── service.py          # ChunkStatisticsService — character/word/sentence/token statistics
│   │       │   │   │   ├── base.py                 # BaseChunkingProvider — generic base (config, version, fingerprint)
│   │       │   │   │   ├── chunk_factory.py         # ChunkFactory — canonical Chunk mapper used by every provider
│   │       │   │   │   ├── config.py               # BaseChunkingConfig + Fixed/Recursive/Markdown configs
│   │       │   │   │   ├── enums.py                # ChunkingStrategy, ChunkContentType
│   │       │   │   │   ├── exceptions.py           # ChunkingError hierarchy
│   │       │   │   │   ├── factory.py              # create_chunking_registry() / create_chunking_service() — composition root (Fixed, Recursive, Markdown)
│   │       │   │   │   ├── interfaces.py           # ChunkingProvider ABC
│   │       │   │   │   ├── models.py               # Chunk + sub-models (content, structure, statistics, provenance, experiment)
│   │       │   │   │   ├── registry.py             # ChunkingRegistry — strategy → provider resolution
│   │       │   │   │   └── service.py              # ChunkingService — validates document, delegates to provider
│   │       │   │   ├── context/             # Context Platform — Retrieval/Reranking → Generation (complete)
│   │       │   │   │   ├── artifacts/
│   │       │   │   │   │   ├── create.py           # create_chunk_artifact_reader() — composition root
│   │       │   │   │   │   └── reader.py           # ChunkArtifactReader — loads a persisted ChunkArtifact from storage by owner/document/strategy/artifact id
│   │       │   │   │   ├── builders/
│   │       │   │   │   │   ├── adjacent_merge.py   # AdjacentMergeService — merges consecutive same-document chunks into one block
│   │       │   │   │   │   ├── compression.py      # CompressionService — legacy no-op stub, superseded by compression/service.py
│   │       │   │   │   │   ├── deduplication.py    # DeduplicationService — drops repeat chunk_ids, keeps first occurrence
│   │       │   │   │   │   ├── ordering.py         # ContextOrderingService — sorts by score desc, chunk_index asc tiebreak
│   │       │   │   │   │   └── parent_expansion.py # ParentExpansionService — resolves parent_chunk_id via ChunkArtifactReader, enriches with parent_content/page_numbers/heading
│   │       │   │   │   ├── citations/
│   │       │   │   │   │   ├── create.py           # create_citation_service() — composition root
│   │       │   │   │   │   ├── interfaces.py       # CitationServiceInterface ABC
│   │       │   │   │   │   ├── models.py           # Citation, CitationResult
│   │       │   │   │   │   └── service.py          # CitationService — numbers chunks S1/S2/..., builds one Citation per chunk
│   │       │   │   │   ├── compression/            # Compression Platform (V1–V4 implemented; V3 wired into build()'s default pipeline, flag-gated)
│   │       │   │   │   │   ├── providers/
│   │       │   │   │   │   │   ├── embedding.py        # EmbeddingCompressionProvider (V2) — drops near-duplicate chunks via cosine similarity ≥ 0.95
│   │       │   │   │   │   │   ├── langchain.py        # LangChainCompressionProvider (V3) — Implemented, wired into build()'s default pipeline (flag-gated): ContextualCompressionRetriever + LLMChainExtractor (langchain-classic), query-aware extraction, metadata/citations preserved via chunk.model_copy()
│   │       │   │   │   │   │   ├── llm.py              # LLMCompressionProvider (V4) — Implemented: per-chunk GenerationService.generate() summarization, never drops a chunk, per-chunk fallback to original content on failure; registered but not part of build()'s default pipeline
│   │       │   │   │   │   │   └── token_budget.py     # TokenBudgetCompressionProvider (V1) — greedy score-sorted packing into a token budget
│   │       │   │   │   │   ├── create.py           # create_compression_service() — registers all four strategies
│   │       │   │   │   │   ├── enums.py            # CompressionStrategy (token_budget/embedding_redundancy/langchain_contextual/llm)
│   │       │   │   │   │   ├── exceptions.py       # CompressionError hierarchy — CompressionProviderError, CompressionTimeoutError
│   │       │   │   │   │   ├── interfaces.py       # CompressionProvider ABC
│   │       │   │   │   │   ├── models.py           # LLMCompressionConfig, CompressionRequest, CompressionStatistics (+ original_tokens/compressed_tokens/duration_ms), CompressionResult
│   │       │   │   │   │   ├── registry.py         # CompressionRegistry — strategy → provider resolution
│   │       │   │   │   │   └── service.py          # CompressionService — resolves strategy, delegates; falls back to original chunks if the provider raises CompressionError
│   │       │   │   │   ├── formatter/               # Prompt Formatter — strategy-based knowledge representation
│   │       │   │   │   │   ├── providers/
│   │       │   │   │   │   │   ├── agent.py            # AgentFormatterProvider — FACTS/EVIDENCE machine-oriented output
│   │       │   │   │   │   │   ├── default.py          # DefaultPromptFormatterProvider — NotebookLM-style sectioned output
│   │       │   │   │   │   │   ├── notebooklm.py       # NotebookLMFormatterProvider — divider-wrapped sectioned output
│   │       │   │   │   │   │   ├── perplexity.py       # PerplexityFormatterProvider — compact truncated evidence blocks
│   │       │   │   │   │   │   └── research.py         # ResearchFormatterProvider — groups chunks by heading into TOPIC sections
│   │       │   │   │   │   ├── create.py           # create_prompt_formatter_service() — registers all five strategies
│   │       │   │   │   │   ├── enums.py            # PromptFormatStrategy (default/notebooklm/perplexity/research/agent)
│   │       │   │   │   │   ├── interfaces.py       # PromptFormatterProvider ABC
│   │       │   │   │   │   ├── models.py           # PromptFormattingResult
│   │       │   │   │   │   ├── registry.py         # PromptFormatterRegistry — strategy → provider resolution
│   │       │   │   │   │   └── service.py          # PromptFormatterService — resolves strategy, delegates
│   │       │   │   │   ├── guardrails/              # Context Guardrails V1
│   │       │   │   │   │   ├── providers/
│   │       │   │   │   │   │   └── rule_based.py       # RuleBasedGuardrailProvider — regex prompt-injection/jailbreak detection, risk scoring
│   │       │   │   │   │   ├── create.py           # create_context_guardrail_service() — registers RuleBasedGuardrailProvider
│   │       │   │   │   │   ├── enums.py            # ChunkRiskLevel, GuardrailStrategy (rule_based implemented; llama_guard/nemo/lakera reserved)
│   │       │   │   │   │   ├── interfaces.py       # GuardrailProvider ABC
│   │       │   │   │   │   ├── models.py           # GuardrailStatistics, GuardrailResult
│   │       │   │   │   │   ├── registry.py         # GuardrailRegistry — strategy → provider resolution
│   │       │   │   │   │   └── service.py          # ContextGuardrailService — resolves strategy, delegates
│   │       │   │   │   ├── create.py               # create_parent_expansion_service() / create_context_builder() — composition root
│   │       │   │   │   ├── enums.py                # (empty) — strategy enums live in each sub-package
│   │       │   │   │   ├── interfaces.py           # ContextBuilderInterface ABC
│   │       │   │   │   ├── models.py               # ContextChunk, PromptContext, ContextStatistics, ContextResult
│   │       │   │   │   └── service.py              # ContextBuilderService — build(retrieval, query=None): dedupe → parent expansion → adjacent merge → ordering → compression (embedding → LangChain [flag-gated] → token budget) → guardrails → citations → prompt formatting
│   │       │   │   ├── embeddings/          # Embedding generation pipeline
│   │       │   │   │   ├── artifacts/
│   │       │   │   │   │   ├── builder.py          # EmbeddingArtifactBuilder — builds EmbeddingArtifact from a ChunkArtifact + generated embeddings
│   │       │   │   │   │   ├── models.py           # EmbeddingArtifact + sub-models (document, chunking, execution, statistics, evaluation)
│   │       │   │   │   │   └── writer.py           # EmbeddingArtifactWriter — persists EmbeddingArtifact to storage (S3)
│   │       │   │   │   ├── providers/
│   │       │   │   │   │   ├── sentence_transformers.py  # SentenceTransformerEmbeddingProvider — real SentenceTransformers model, batches via EmbeddingBatcher
│   │       │   │   │   │   ├── voyage.py                 # VoyageAIEmbeddingProvider — real Voyage AI Client, batches via EmbeddingBatcher, coerces int vectors to float
│   │       │   │   │   │   └── openai.py                 # OpenAIEmbeddingProvider — real OpenAI client, batches via EmbeddingBatcher
│   │       │   │   │   ├── base.py                 # BaseEmbeddingProvider — generic base (config, version, fingerprint)
│   │       │   │   │   ├── batching.py             # EmbeddingBatcher — lazily splits chunks into fixed-size batches, shared by every provider
│   │       │   │   │   ├── config.py               # BaseEmbeddingConfig + SentenceTransformer/VoyageAI/OpenAI configs
│   │       │   │   │   ├── create.py               # create_voyage_client() / create_openai_client() / create_embedding_registry() / create_embedding_service() — composition root
│   │       │   │   │   ├── enums.py                # EmbeddingProvider
│   │       │   │   │   ├── exceptions.py           # EmbeddingError hierarchy
│   │       │   │   │   ├── factory.py              # EmbeddingFactory — canonical Embedding mapper used by every provider
│   │       │   │   │   ├── interfaces.py           # EmbeddingProvider ABC
│   │       │   │   │   ├── models.py               # Embedding + sub-models (vector, provenance, provider, statistics, experiment)
│   │       │   │   │   ├── registry.py             # EmbeddingRegistry — provider → implementation resolution
│   │       │   │   │   └── service.py              # EmbeddingService — validates chunk artifact, delegates to provider
│   │       │   │   ├── indexing/            # Indexing Platform — dense + sparse vectors → Qdrant hybrid (ADR-018, ADR-019)
│   │       │   │   │   ├── artifacts/
│   │       │   │   │   │   ├── builder.py          # IndexingArtifactBuilder — builds IndexingArtifact from an IndexingResult
│   │       │   │   │   │   ├── models.py           # IndexingArtifact + sub-models (execution, VectorIndexArtifact)
│   │       │   │   │   │   └── writer.py           # IndexingArtifactWriter — persists IndexingArtifact to storage (S3)
│   │       │   │   │   ├── providers/
│   │       │   │   │   │   └── fastembed.py        # FastEmbedSparseEmbeddingProvider — SPLADE sparse vectors, off-loop via asyncio.to_thread
│   │       │   │   │   ├── create.py               # create_sparse_embedding_provider() / create_indexing_service() — composition root
│   │       │   │   │   ├── enums.py                # IndexType, IndexStatus, IndexOperation
│   │       │   │   │   ├── exceptions.py           # IndexingError hierarchy (incl. SparseEmbeddingError)
│   │       │   │   │   ├── interfaces.py           # IndexingServiceInterface ABC
│   │       │   │   │   ├── models.py               # IndexingRequest (embedding_artifact + chunk_artifact), IndexingExecution, IndexingResult
│   │       │   │   │   └── service.py              # IndexingService — builds dense+sparse VectorStoreRecords, creates/upserts into Qdrant, persists artifact
│   │       │   │   ├── processing/          # Document processing pipeline
│   │       │   │   │   ├── adapters/
│   │       │   │   │   │   └── docling.py          # Docling adapter (alternative entry point)
│   │       │   │   │   ├── parsers/
│   │       │   │   │   │   ├── base.py             # BaseDocumentParser abstract class
│   │       │   │   │   │   └── docling.py          # Docling-backed parser implementation
│   │       │   │   │   ├── metadata/               # Metadata enrichment pipeline
│   │       │   │   │   │   ├── providers/
│   │       │   │   │   │   │   ├── language.py     # Language detection provider (langdetect)
│   │       │   │   │   │   │   └── pdf.py          # PDF embedded-metadata provider (pypdf)
│   │       │   │   │   │   ├── base.py             # BaseMetadataProvider abstract class
│   │       │   │   │   │   ├── interfaces.py       # MetadataProvider ABC
│   │       │   │   │   │   ├── models.py           # MetadataUpdate model
│   │       │   │   │   │   ├── registry.py         # Metadata provider registry
│   │       │   │   │   │   └── service.py          # MetadataEnrichmentService — coordinates providers
│   │       │   │   │   ├── statistics/             # Statistics enrichment pipeline
│   │       │   │   │   │   ├── providers/
│   │       │   │   │   │   │   └── pdf.py          # PDF statistics provider (page count)
│   │       │   │   │   │   ├── base.py             # BaseStatisticsProvider abstract class
│   │       │   │   │   │   ├── interfaces.py       # StatisticsProvider ABC
│   │       │   │   │   │   ├── models.py           # DocumentStatistics model
│   │       │   │   │   │   ├── registry.py         # Statistics provider registry
│   │       │   │   │   │   └── service.py          # StatisticsEnrichmentService — coordinates providers
│   │       │   │   │   ├── artifact_builder.py     # Builds ProcessingArtifacts from ProcessedDocument
│   │       │   │   │   ├── artifact_writer.py      # Persists artifacts to storage (S3)
│   │       │   │   │   ├── artifacts.py            # ProcessingArtifact / ProcessingArtifacts models
│   │       │   │   │   ├── enums.py                # DocumentFormat, ParserType, ProcessingStatus, ProcessingStage
│   │       │   │   │   ├── exceptions.py           # ProcessingError hierarchy
│   │       │   │   │   ├── interfaces.py           # DocumentParser ABC, ParseRequest
│   │       │   │   │   ├── models.py               # ProcessedDocument, block types, ProcessingResult
│   │       │   │   │   ├── registry.py             # ParserRegistry — format → parser resolution
│   │       │   │   │   ├── service.py              # ProcessingService — orchestrates the full pipeline (parse → enrich → artifacts → chunk → chunk artifacts → embed → embedding artifacts → index (dense+sparse) → indexing artifacts); PipelineRuntimeMetrics (via the pre-existing RuntimeMetricsCollector, previously log-only) now also persisted as an ObservabilityArtifact via an optional observability_service param (ArtifactRuntime.PROCESSING) — see the new top-level ai/observability/ below
│   │       │   │   │   └── temporary_file_manager.py  # Temp file lifecycle for downloaded documents
│   │       │   │   ├── reranking/           # Reranking Platform — Voyage AI + CrossEncoder (ADR-022)
│   │       │   │   │   ├── providers/
│   │       │   │   │   │   ├── cross_encoder.py    # CrossEncoderReranker — local BAAI/bge-reranker-base (sentence-transformers), no marginal cost
│   │       │   │   │   │   └── voyage.py           # VoyageReranker — Voyage AI Client.rerank() (rerank-2)
│   │       │   │   │   ├── base.py                 # BaseRerankingProvider — shared VERSION/version property
│   │       │   │   │   ├── config.py               # CrossEncoderConfig, VoyageRerankerConfig
│   │       │   │   │   ├── create.py               # create_reranking_registry() / create_reranking_service() — composition root; Voyage only registered if settings.voyage_api_key is set
│   │       │   │   │   ├── enums.py                # RerankingProvider (cross_encoder/voyage_ai)
│   │       │   │   │   ├── exceptions.py           # RerankingError hierarchy
│   │       │   │   │   ├── interfaces.py           # RerankingProviderInterface ABC — provider, version, rerank()
│   │       │   │   │   ├── models.py               # RerankingRequest, RerankedChunk, RerankingResult
│   │       │   │   │   ├── registry.py             # RerankingRegistry — provider → implementation resolution, has()
│   │       │   │   │   └── service.py              # RerankingService — validates request, delegates to provider
│   │       │   │   ├── retrieval/           # Retrieval Platform — dense, sparse, hybrid, parallel, metadata filtering (ADR-018, ADR-019, ADR-020, ADR-021, ADR-022)
│   │       │   │   │   ├── fusion/
│   │       │   │   │   │   ├── interfaces.py       # FusionStrategy ABC
│   │       │   │   │   │   ├── models.py           # FusionResult (unused scaffold — RRF returns RetrievalResult directly)
│   │       │   │   │   │   ├── rrf.py              # ReciprocalRankFusion — RRF (k=60, matches Elasticsearch/Azure AI Search defaults)
│   │       │   │   │   │   └── service.py          # RetrievalFusionService — wraps the configured fusion strategy
│   │       │   │   │   ├── providers/
│   │       │   │   │   │   └── qdrant.py           # QdrantRetrievalProvider — search() (named "dense" vector) + search_sparse() (named "sparse" vector); _build_filter() translates RetrievalQuery.filters (owner_id/document_id/filename/language) into a Qdrant Filter; shared _map_points() chunk mapper
│   │       │   │   │   ├── query/
│   │       │   │   │   │   ├── dense_service.py    # QueryEmbeddingService — Voyage AI/OpenAI query embeddings, Valkey-backed cache
│   │       │   │   │   │   ├── models.py           # DenseQueryEmbedding, SparseQueryEmbedding
│   │       │   │   │   │   └── sparse_service.py   # SparseQueryEmbeddingService — FastEmbed SPLADE query embeddings
│   │       │   │   │   ├── base.py                 # BaseRetrievalProvider[ConfigT] — generic base (config, version, fingerprint)
│   │       │   │   │   ├── config.py               # BaseRetrievalConfig + QdrantRetrievalConfig
│   │       │   │   │   ├── create.py               # create_retrieval_registry() / create_query_embedding_service() / create_sparse_query_embedding_service() / create_fusion_service() / create_retrieval_service() — composition root; wires create_reranking_service() into RetrievalService
│   │       │   │   │   ├── enums.py                # RetrievalProvider, RetrievalStrategy (dense/sparse/hybrid/parent_child/query_decomposition), RetrievalOperation
│   │       │   │   │   ├── exceptions.py           # RetrievalError hierarchy
│   │       │   │   │   ├── interfaces.py           # RetrievalProviderInterface ABC — search(), search_sparse()
│   │       │   │   │   ├── models.py               # RetrievalQuery, RetrievedChunk, RetrievalStatistics (incl. optional dense_latency_ms/sparse_latency_ms/rerank_latency_ms/reranker_provider, now populated by search_hybrid() from timings that were already computed), RetrievalExecution, RetrievalResult
│   │       │   │   │   ├── registry.py             # RetrievalRegistry — provider → implementation resolution
│   │       │   │   │   └── service.py              # RetrievalService — validation, normalization, search() / search_sparse() / search_hybrid(rerank=True) (dense+sparse candidate pool → RRF fusion → reranks via Voyage AI by default)
│   │       │   │   ├── upload/              # Document upload handling
│   │       │   │   │   ├── duplicate/
│   │       │   │   │   │   ├── exceptions.py       # DuplicateDetectionError hierarchy
│   │       │   │   │   │   ├── interfaces.py       # DuplicateDetector ABC
│   │       │   │   │   │   ├── models.py           # Duplicate check request/response models
│   │       │   │   │   │   └── service.py          # DuplicateDetectionService — checksum-based lookup
│   │       │   │   │   ├── constants.py     # Upload limits and allowed MIME types
│   │       │   │   │   ├── enums.py         # Upload-specific enums
│   │       │   │   │   ├── exceptions.py    # Upload exceptions
│   │       │   │   │   ├── interfaces.py    # Upload abstract interfaces
│   │       │   │   │   ├── models.py        # Upload domain models
│   │       │   │   │   ├── processing_job_builder.py  # Builds ProcessingJob from a persisted Document
│   │       │   │   │   ├── schemas.py       # Upload Pydantic schemas
│   │       │   │   │   ├── service.py       # UploadService orchestration — now enqueues async processing
│   │       │   │   │   ├── storage.py       # Storage operations for uploads
│   │       │   │   │   ├── types.py         # Upload type aliases
│   │       │   │   │   └── validators.py    # File validation logic
│   │       │   │   └── vectorstores/        # Vector Store Platform — Qdrant native hybrid retrieval (ADR-017, ADR-019)
│   │       │   │       ├── artifacts/              # (empty) — unused scaffold, superseded by indexing/artifacts/
│   │       │   │       ├── providers/
│   │       │   │       │   └── qdrant.py           # QdrantVectorStoreProvider — named dense+sparse vectors per point, collection CRUD, upsert, delete
│   │       │   │       ├── base.py                 # BaseVectorStoreProvider[ConfigT] — generic base (config, version, fingerprint)
│   │       │   │       ├── config.py               # BaseVectorStoreConfig + Qdrant/Chroma/PgVector/Pinecone/Weaviate configs
│   │       │   │       ├── create.py               # create_qdrant_client() / create_vectorstore_registry() / create_vectorstore_service() — composition root
│   │       │   │       ├── enums.py                # VectorStoreProvider, VectorDistanceMetric, VectorOperation
│   │       │   │       ├── exceptions.py           # VectorStoreError hierarchy
│   │       │   │       ├── interfaces.py           # VectorStoreProviderInterface ABC
│   │       │   │       ├── models.py               # VectorStoreRecord, SparseVector, VectorPayload, CollectionDefinition, CollectionMetadata, IndexStatistics
│   │       │   │       ├── registry.py             # VectorStoreRegistry — provider → implementation resolution
│   │       │   │       └── service.py              # VectorStoreService — validates records, delegates to provider
│   │       │   ├── memory/                   # Conversation Memory Platform — canonical PostgreSQL durable memory, Valkey compact session state, and Qdrant-backed semantic/research retrieval
│   │       │   │   ├── extraction/            # MemoryExtractionService + orchestrator — policy-gated, canonical-turn-idempotent durable extraction; Groq primary with OpenAI fallback
│   │       │   │   ├── policy/                # Eligibility policy and bounded interest promotion — explicit durable interests immediately eligible; generic topics require two distinct sessions and one 90-day promotion claim
│   │       │   │   ├── retrieval/             # Durable-memory availability cache + shared query embedding; semantic and research searches run concurrently and fail open independently
│   │       │   │   ├── session/               # Compact, non-transcript session state in Valkey
│   │       │   │   ├── semantic/              # PostgreSQL canonical semantic-memory service, indexed in Qdrant for search
│   │       │   │   ├── research/              # PostgreSQL canonical research-memory service, indexed in Qdrant for search
│   │       │   │   ├── profile/               # USER-memory persistence and duplicate/supersession handling
│   │       │   │   ├── storage/               # Postgres/Valkey/vector-store adapters; PostgreSQL remains the source of truth
│   │       │   │   ├── observability/         # Structured decision, failure, and latency metrics; generation ledger distinguishes answer and memory-extraction cost
│   │       │   │   └── services/              # Memory context assembly/formatting and duplicate suppression against canonical history
│   │       │   ├── observability/            # AI Runtime Observability Platform (Phase 3.9, oberservability_platform_prd.md) — implemented 2026-07-18
│   │       │   │   ├── models.py            # PRE-EXISTING, unrelated to the PRD below despite the name collision — PipelineRuntimeMetrics/RuntimeStageMetric/ArtifactMetric, used by ProcessingService's RuntimeMetricsCollector
│   │       │   │   ├── runtime.py           # PRE-EXISTING — RuntimeMetricsCollector (stage timing/artifact-size collector for the Knowledge Processing pipeline)
│   │       │   │   ├── report.py            # PRE-EXISTING — RuntimeReportBuilder.build(PipelineRuntimeMetrics) -> markdown string; now also reused by ObservabilityService.record_processing()
│   │       │   │   ├── timer.py             # PRE-EXISTING — Timer, reused by validation/runtime/service.py
│   │       │   │   ├── service.py           # NEW — ObservabilityService.record_generation()/record_processing(): best-effort, policy-gated report+artifact persistence via ObservabilityArtifactBuilder; record_processing() has no LangSmith trace (no LLM call to trace)
│   │       │   │   ├── create.py            # NEW — get_observability_service() (lru_cache) wiring the real artifact writer + policy service
│   │       │   │   ├── metrics/             # NEW — canonical snapshot models + pure build_*_metrics_snapshot() functions: retrieval.py, streaming.py, research.py, agent.py (Generation's own snapshot in runtime/generation/observability/models.py is reused as-is, not duplicated)
│   │       │   │   ├── statistics/          # NEW — enums.py (TimeWindow), models.py (PercentileStats/RankingEntry/StatisticsSnapshot), aggregator.py (percentile/compute_percentiles/average/rate/rank_by_count/rank_by_average — pure functions), service.py (Generation/RetrievalStatisticsBuilder); no persistent metrics store, pure aggregation over a caller-assembled list
│   │       │   │   ├── reports/             # NEW — markdown report builders: generation.py, retrieval.py, system.py (no research.py — PRD labels Research Report "Future")
│   │       │   │   └── providers/langsmith/ # NEW, real (not stubbed) — client.py (get_langsmith_client(), lazy/cached, gated on settings.langsmith_api_key, passes api_url=settings.langsmith_endpoint), tracing.py (RuntimeTracer ABC + TraceHandle ABC, NoOpTracer/_NoOpTraceHandle, LangSmithTracer/_LangSmithTraceHandle — trace(inputs=real prompt, tags=metadata incl. streamed) yields a handle whose set_output(content, prompt_tokens, completion_tokens, total_tokens) populates update_run(outputs=...) before the trace closes), recorder.py (LangSmithMetricsRecorder, reads tracing.py's current_run_id ContextVar to attach create_feedback() to the active trace), create.py (create_runtime_tracer()/create_langsmith_metrics_recorder() — require BOTH settings.langsmith_api_key AND settings.langsmith_tracing=true, an API key alone does not enable tracing)
│   │       │   ├── quality/                 # Dead scaffold — 0-byte __init__.py files present since the very first commit, predates every evaluation doc; docs/evaluation/strategy.md's own "Current Status: Not Implemented" confirms it. Real Generation/Regression evaluation was built into repo-root benchmarks/ instead — see PROJECT_STATUS.md's "Evaluation Platform PRD Reconciliation"
│   │       │   │   ├── benchmarks/
│   │       │   │   ├── evaluation/
│   │       │   │   ├── experiments/
│   │       │   │   ├── regression/
│   │       │   │   ├── telemetry/
│   │       │   │   └── tracing/
│   │       │   ├── registry/                # Model and provider registries
│   │       │   │   ├── embeddings.py        # Embedding model registry
│   │       │   │   ├── evaluators.py        # Evaluator registry
│   │       │   │   ├── mcp.py               # MCP server registry
│   │       │   │   ├── models.py            # LLM model registry
│   │       │   │   ├── prompts.py           # Prompt template registry
│   │       │   │   ├── providers.py         # LLM provider registry
│   │       │   │   └── rerankers.py         # Reranker registry
│   │       │   ├── runtime/                 # Implemented — Generation Platform (complete, per generation_platform_complexion_prd.md) + Streaming Platform
│   │       │   │   ├── routing/__init__.py        # (empty) — vestigial, superseded by generation/routing/
│   │       │   │   ├── streaming/__init__.py      # (empty) — vestigial top-level scaffold, unrelated to (and untouched by) the now-implemented generation/streaming/ and events/ below — coincidental name overlap
│   │       │   │   ├── events/                     # Runtime Event Platform (Streaming Platform Milestone 2.9.10, streaming_platform_prd.md/ADR-028)
│   │       │   │   │   ├── enums.py                # EventCategory, CoreEventType — the only enum StreamEvent depends on
│   │       │   │   │   ├── models.py               # StreamEvent (event_id/session_id/request_id/parent_event_id/category/type: str/timestamp/content/metadata)
│   │       │   │   │   ├── interfaces.py           # ProviderEventAdapterInterface — to_stream_event(chunk, *, session_id, request_id)
│   │       │   │   │   ├── create.py               # get_event_adapter() — @lru_cache'd factory
│   │       │   │   │   ├── adapters/base.py        # GenericStreamChunkAdapter — one shared adapter for every provider (StreamChunk already normalized per-provider)
│   │       │   │   │   ├── provider/models.py      # ProviderEventMetadataKeys — well-known metadata keys, no behavior
│   │       │   │   │   ├── research/models.py      # ResearchEventType — reserved for the future Research Runtime, unused today
│   │       │   │   │   ├── agent/models.py         # AgentEventType — reserved for the future Agent Runtime, unused today
│   │       │   │   │   └── tool/models.py          # ToolEventType — reserved for the future Tool Runtime, unused today
│   │       │   │   └── generation/                # Generation Platform — see docs/architecture/structured-output-platform.md
│   │       │   │       ├── models.py               # GenerationRequest (output_schema/output_model/max_regeneration_attempts/runtime: RuntimeType | None/...), GenerationResult (parsed_output/validation/regeneration_attempts), ProviderCapabilities
│   │       │   │       ├── interfaces.py           # GenerationProviderInterface ABC — generate()/generate_structured()/stream(), supports_* capability accessors
│   │       │   │       ├── enums.py                # GenerationProvider, ResponseFormat (incl. xml)
│   │       │   │       ├── exceptions.py           # GenerationError hierarchy
│   │       │   │       ├── config.py               # BaseGenerationConfig + per-provider configs
│   │       │   │       ├── registry.py             # GenerationRegistry — provider → implementation resolution
│   │       │   │       ├── service.py              # GenerationService — generate() (explicit provider, or routes via RoutingService from request.routing_strategy with automatic fallback across the decision's fallback_models) → capability guard → native structured output → parser fallback → input/output/hallucination validation → regeneration loop; generate_from_template() (PromptService bridge + format instructions); _execute_once() wraps the provider call in self._tracer.trace() (RuntimeTracer, PRD §11.1) and, after generate() records metrics, calls ObservabilityService.record_generation() best-effort; read-only registry/metrics_service/observability_service/tracer properties expose the same instances to StreamingService; score_completed_stream(request, result) — informational, non-blocking guardrail+validation scoring for an already-completed stream (see streaming/service.py below)
│   │       │   │       ├── create.py               # create_generation_service() — composition root wiring providers + structured_output_registry + validation_service + prompt_service + routing_service + observability_service (get_observability_service()) + tracer (create_runtime_tracer())
│   │       │   │       ├── providers/
│   │       │   │       │   ├── base.py             # BaseGenerationProvider[ConfigT] — retry, parse_structured_output() (json.loads → StructuredOutputRepair fallback)
│   │       │   │       │   ├── claude.py           # ClaudeProvider — native output_config.format (Structured Outputs API) + prompt-JSON fallback
│   │       │   │       │   ├── openai.py           # OpenAIProvider — native text.format (json_schema/json_object)
│   │       │   │       │   ├── gemini.py           # GeminiProvider — native response_json_schema (not response_schema)
│   │       │   │       │   ├── groq.py             # GroqProvider — native response_format (json_schema/json_object)
│   │       │   │       │   ├── ollama.py           # OllamaProvider — native format (schema dict or "json")
│   │       │   │       │   └── helpers/            # structured.py, prompt_builder.py, usage.py, cost.py
│   │       │   │       ├── structured_output/      # Implemented — parser registry, repair, schemas
│   │       │   │       │   ├── registry.py         # StructuredOutputRegistry — format → parser resolution
│   │       │   │       │   ├── repair.py           # StructuredOutputRepair — fixes markdown fences, trailing commas, single quotes, missing braces
│   │       │   │       │   ├── service.py          # StructuredOutputService — standalone text→objects pipeline
│   │       │   │       │   ├── create.py           # get_structured_output_registry()/get_structured_output_service()
│   │       │   │       │   ├── parsers/            # json.py, pydantic.py (LangChain), markdown.py, xml.py
│   │       │   │       │   └── schemas/            # research_report.py, planner.py, citations.py, agent.py
│   │       │   │       ├── validation/             # Implemented — input/output/hallucination/runtime validators, registry, scoring, ValidationReport
│   │       │   │       │   ├── service.py          # ValidationService — validate_input()/validate_output()/validate_hallucination()/validate_runtime()/validate() (now logs validation.started/completed); crashing validator → WARNING not a hard failure
│   │       │   │       │   ├── registry.py         # ValidationRegistry — dynamic per-stage registration (input/output/hallucination), plus register_runtime_validator()/register_runtime_contract() delegating to a composed RuntimeRegistry
│   │       │   │       │   ├── scoring.py          # compute_overall_score() — weighted, renormalized over whichever stages produced a score
│   │       │   │       │   ├── aggregation.py      # crash_outcome()/aggregate_outcomes() — shared per-stage crash-handling + issue/score aggregation, used by both ValidationService and RuntimeValidationService
│   │       │   │       │   ├── create.py           # create_validation_registry() / get_validation_service() — registers all input+output(7, pipeline order)+hallucination validators and all 5 runtime contracts
│   │       │   │       │   ├── output/
│   │       │   │       │   │   ├── json_validator.py       # JsonValidator — content is valid/repairable/unparseable JSON (independent of SchemaValidator's shape check)
│   │       │   │       │   │   ├── schema_validator.py     # SchemaValidator — jsonschema.validate() against output_schema
│   │       │   │       │   │   ├── formatting_validator.py # FormattingValidator — balanced Markdown fences / parseable XML (JSON left to JsonValidator)
│   │       │   │       │   │   ├── completeness_validator.py  # CompletenessValidator (top-level) — self-configures from request.output_schema's required/properties, delegates to runtime/validators/completeness.py
│   │       │   │       │   │   ├── consistency_validator.py   # ConsistencyValidator (top-level) — delegates to runtime/validators/consistency.py with its default field names
│   │       │   │       │   │   ├── response_size_validator.py # ResponseSizeValidator — configurable min/max chars + truncation-risk flag via finish_reason
│   │       │   │       │   │   ├── citation_validator.py   # CitationValidator — flags [S1]-style markers not in prompt_context.citations
│   │       │   │       │   │   └── hallucination_validator.py  # HallucinationValidator — deterministic lexical-overlap groundedness score, no LLM, registered under the hallucination stage
│   │       │   │       │   ├── input/
│   │       │   │       │   │   ├── empty_prompt.py        # EmptyPromptValidator — empty/whitespace prompts, unrendered {placeholder} variables
│   │       │   │       │   │   ├── token_budget.py        # TokenBudgetValidator — estimated tokens vs. context window (cheap deterministic estimate)
│   │       │   │       │   │   ├── provider_limits.py     # ProviderLimitsValidator — streaming/structured_output/json_mode/tool_calling vs. resolved provider capabilities
│   │       │   │       │   │   └── context_validation.py  # ContextValidator — empty/duplicate chunks, orphaned citation references
│   │       │   │       │   └── runtime/            # Runtime Validation Platform (per runtime_validation_prd.md, generation_platform_complexion_prd.md) — 4th ValidationStage.RUNTIME stage; all 5 contracts implemented, dormant until GenerationRequest.runtime is set
│   │       │   │       │       ├── enums.py            # RuntimeType (chat/research/planner/reviewer/agent/mcp) — backs the new GenerationRequest.runtime field
│   │       │   │       │       ├── interfaces.py       # RuntimeValidatorInterface (name/runtime/validate), RuntimeContractInterface (runtime/validate)
│   │       │   │       │       ├── fields.py           # get_field()/get_list_field()/item_id() — duck-typed field extraction off GenerationResult.parsed_output (typed Any)
│   │       │   │       │       ├── registry.py         # RuntimeRegistry — per-RuntimeType contract/validator lookup (register_contract/register_validator, contract_for/validators_for/all_validators)
│   │       │   │       │       ├── service.py          # RuntimeValidationService — resolves request.runtime, runs the matching contract + standalone validators, crash-safe, structlog runtime.validation.{started,completed,failed} events
│   │       │   │       │       ├── validators/         # Generic, reusable checks — each implements the existing OutputValidatorInterface, not a new one
│   │       │   │       │       │   ├── completeness.py     # CompletenessValidator — configurable required_fields/list_minimums/min_summary_length
│   │       │   │       │       │   ├── consistency.py      # ConsistencyValidator — configurable list_field/id_keys/ref_list_field/ref_key (defaults: sections/evidence/section_id); orphan-reference check
│   │       │   │       │       │   ├── confidence.py       # ConfidenceValidator — confidence in [0, 1], contributed as the outcome's score
│   │       │   │       │       │   ├── evidence.py         # EvidenceValidator — evidence items have content + a citation_id/section_id source pointer
│   │       │   │       │       │   ├── citation.py         # RuntimeCitationValidator — structured citations/evidence fields vs. prompt_context, the structured-output counterpart to output/citation_validator.py
│   │       │   │       │       │   └── dependency.py       # DependencyValidator — configurable list_field/id_keys/dependency_key (defaults: steps/depends_on); unknown-dependency + cycle detection (DFS)
│   │       │   │       │       └── contracts/
│   │       │   │       │           ├── base.py         # BaseRuntimeContract — implements both runtime interfaces; composes `checks`, re-tags every issue with contract_name (details["check"] keeps the original check name)
│   │       │   │       │           ├── research.py     # ResearchRuntimeContract — summary/≥2 sections/≥1 citation/≥1 evidence/confidence in [0,1]
│   │       │   │       │           ├── planner.py      # PlannerRuntimeContract — plan/≥1 steps/acyclic step dependencies
│   │       │   │       │           ├── reviewer.py     # ReviewerRuntimeContract — critique/confidence in [0,1]/≥1 recommendations
│   │       │   │       │           ├── agent.py        # AgentRuntimeContract — reasoning/completion_state/≥1 tool_trace entries
│   │       │   │       │           └── mcp.py          # MCPRuntimeContract — ≥1 tool_outputs/execution_metadata/tool_references referential integrity
│   │       │   │       ├── policies/                # Implemented — Validation Policy Layer (generation_platform_complexion_prd.md)
│   │       │   │       │   ├── acceptance.py       # AcceptancePolicy — Accept/Reject/Regenerate decision from a ValidationReport + parse-failure flag
│   │       │   │       │   ├── fail_fast.py        # FailFastPolicy — should an input-stage failure stop generation before the provider call
│   │       │   │       │   └── runtime.py          # RuntimeValidationPolicy — should a failed runtime contract also gate regeneration (opt-in, default off)
│   │       │   │       ├── langchain/              # ~25% Implemented
│   │       │   │       │   ├── output_parsers.py   # with_structured_output() bridge — OpenAI/Claude/Gemini/Ollama (not Groq — langchain-groq incompatible with pinned groq SDK)
│   │       │   │       │   ├── prompt_factory.py   # (empty)
│   │       │   │       │   ├── runnables.py        # (empty)
│   │       │   │       │   └── semantic_cache.py   # (empty)
│   │       │   │       ├── prompts/                # Implemented (pre-existing) — now bridged into Generation
│   │       │   │       │   ├── builder.py          # PromptBuilder — loads prompt.md + metadata.yaml + examples.json from disk
│   │       │   │       │   ├── registry.py         # PromptRegistry — name+version → PromptTemplate
│   │       │   │       │   ├── service.py          # PromptService — render()/render_messages() via LangChain ChatPromptTemplate
│   │       │   │       │   ├── create.py           # get_prompt_service() — composition root
│   │       │   │       │   ├── models.py           # PromptTemplate, PromptMetadata, PromptRenderRequest/Result
│   │       │   │       │   └── langchain/prompt_factory.py  # PromptFactory.build() — ChatPromptTemplate + few-shot
│   │       │   │       ├── catalog/                # Implemented — Model Catalog
│   │       │   │       │   ├── models.py           # ModelMetadata (capabilities, cost, per-task 0-1 scores, priority/enabled/experimental/local), ALL_MODELS/MODELS_BY_PROVIDER
│   │       │   │       │   └── registry.py         # ModelCatalogRegistry — all()/enabled()/by_provider()/get(); get_model_catalog_registry() cached factory
│   │       │   │       ├── routing/                # Implemented — Routing Platform (Model Routing Platform; see docs/architecture/model-routing-platform.md, ADR-026)
│   │       │   │       │   ├── enums.py            # RoutingStrategy (15 task-based values), RequiredCapability
│   │       │   │       │   ├── models.py           # RoutingRequest, RoutingDecision, RoutingStrategyProfile
│   │       │   │       │   ├── interfaces.py       # RoutingServiceInterface — sync route()
│   │       │   │       │   ├── exceptions.py       # RoutingError, NoEligibleModelsError
│   │       │   │       │   ├── service.py          # RoutingService — capability filter → policy filter (disabled/experimental/local) → strategy resolution → scoring → fallback chain (distinct-provider preferred) → RoutingDecision, logged via structlog
│   │       │   │       │   ├── create.py           # create_routing_service() — composition root; build_strategy_profiles() merges task + default profiles
│   │       │   │       │   ├── scoring/
│   │       │   │       │   │   ├── weights.py      # ScoringWeights, DEFAULT_STRATEGY_WEIGHTS (9 generic strategies)
│   │       │   │       │   │   ├── interfaces.py   # ScoringEngineInterface, ScoredModel
│   │       │   │       │   │   └── service.py      # ScoringService — normalizes cost/context across candidates, blends weighted score (0-10 scale) + top-dimension reasons
│   │       │   │       │   └── strategies/         # PLANNING/SUMMARIZATION/REVIEW/VALIDATION/CODING/RESEARCH profiles (weights + capability/context requirements)
│   │       │   │       ├── caching/                # Runtime Caching Platform (L1 exact/L2 semantic/L3 session) — see docs/architecture/runtime-caching-platform.md, ADR-027
│   │       │   │       │   ├── models.py           # CacheKey, CacheResult, CacheStatistics
│   │       │   │       │   ├── enums.py            # CacheLevel, CachePolicy, CacheRuntime
│   │       │   │       │   ├── interfaces.py       # Exact/Semantic/SessionCacheProviderInterface ABCs
│   │       │   │       │   ├── exceptions.py       # CachingError hierarchy
│   │       │   │       │   ├── service.py          # CachingService — lookup()/store() (L1→L2 per policy; streaming requests participate identically to non-streaming ones), get_session()/set_session()/invalidate_session()/clear_session() (L3)
│   │       │   │       │   ├── create.py           # create_caching_service() — composition root; wires Valkey (L1/L3) + dedicated redis-stack-server (L2)
│   │       │   │       │   ├── exact/              # key_builder.py (hashing + CacheKey), provider.py (ValkeyExactCacheProvider), null.py
│   │       │   │       │   ├── semantic/           # embeddings_adapter.py (OpenAI → langchain_core.Embeddings), provider.py (RedisSemanticCacheProvider), null.py
│   │       │   │       │   ├── session/            # provider.py (ValkeySessionCacheProvider), null.py
│   │       │   │       │   └── policies/           # models.py (RuntimeCacheProfile), service.py (CachePolicyResolver)
│   │       │   │       ├── streaming/               # Generation Streaming Platform (Milestone 2.9.10) — see docs/architecture/streaming-platform.md, ADR-028
│   │       │   │       │   ├── enums.py            # StreamTransport (sse/websocket), ValidationEventType (generation-scoped, not yet emitted)
│   │       │   │       │   ├── models.py           # StreamCacheOutcome (hit/level/replayed) — carried in the START event's metadata
│   │       │   │       │   ├── interfaces.py       # StreamSerializerInterface
│   │       │   │       │   ├── service.py          # StreamingService — stream_generate(): cache lookup → replay hit as synthetic TOKEN events, or stream live via GenerationService.stream_generate() and store the assembled result on COMPLETE; _stream_live() wraps the live provider stream in the shared RuntimeTracer (inputs=real prompt, tags incl. streamed=True), builds a GenerationResult unconditionally on completion (_build_stream_result), runs GenerationService.score_completed_stream() (informational guardrail/validation scoring, never blocking), then records metrics + persists an ObservabilityArtifact the same way generate() does
│   │       │   │       │   ├── create.py           # create_streaming_service() — reuses create_generation_service()'s own registry AND its metrics_service/observability_service/tracer instances (via those read-only properties), so streamed and non-streamed generations trace/record through identical collaborators
│   │       │   │       │   ├── transports/         # sse.py (StreamingResponse, heartbeat, max-duration ceiling), websocket.py (JSON frames, disconnect cancels the generator)
│   │       │   │       │   └── serializers/        # sse.py (event:/data: wire format), json.py (StreamEvent.model_dump)
│   │       │   │       └── observability/           # Implemented — Runtime Metrics Integration (generation_platform_complexion_prd.md): models.py (GenerationMetricsSnapshot), service.py (GenerationMetricsService), token_counter.py; cost_tracker.py/latency_tracker.py/metrics_collector.py/token_tracker.py deliberately left as empty scaffolds (token/cost accounting lives on GenerationResult.statistics)
│   │       │   └── shared/                  # Shared AI types and interfaces
│   │       │       ├── exceptions.py        # (empty)
│   │       │       ├── interfaces.py        # (empty)
│   │       │       ├── local_embeddings.py  # get_local_embedding_model() — cached sentence-transformers/all-MiniLM-L6-v2, used by EmbeddingCompressionProvider
│   │       │       ├── models.py            # (empty)
│   │       │       └── types.py             # (empty)
│   │       │
│   │       ├── api/             # Route layer
│   │       │   ├── deps.py              # Shared route dependencies
│   │       │   └── v1/                  # API version 1
│   │       │       ├── api.py           # Router aggregator
│   │       │       ├── admin.py         # Admin endpoints
│   │       │       ├── auth.py          # Auth endpoints (callback, me)
│   │       │       ├── chat.py          # POST /chat/stream (SSE), WebSocket /chat/ws, cursor-paginated GET /chat/conversations and /chat/conversations/{id}; bounded transcript + Memory injection, durable turn persistence, and first-question Groq titles
│   │       │       ├── documents.py     # Document management + owner-scoped Qdrant knowledge-base statistics
│   │       │       ├── evaluation.py    # Evaluation endpoints
│   │       │       ├── feedback.py      # Feedback endpoints
│   │       │       ├── health.py        # Health check endpoints
│   │       │       ├── usage.py         # Owner-scoped generation cost summary endpoint
│   │       │       └── reports.py       # Report endpoints
│   │       │
│   │       ├── auth/            # Authentication layer
│   │       │   ├── dependencies.py      # authenticate_token() (shared JWT verify+sync) + get_current_user (header) — also used by chat.py's WebSocket ?token= auth
│   │       │   ├── jwt.py               # JWT verification via JWKS
│   │       │   └── providers/           # Identity provider adapters
│   │       │       ├── base.py          # AuthenticationProvider abstract base
│   │       │       └── cognito.py       # AWS Cognito implementation
│   │       │
│   │       ├── core/            # App-level configuration and startup
│   │       │   ├── constants.py         # Static application constants
│   │       │   ├── health.py            # Health check logic
│   │       │   ├── lifespan.py          # FastAPI lifespan (startup/shutdown, auto-migrate)
│   │       │   ├── logging.py           # Structured logging (structlog + stdlib bridge)
│   │       │   ├── settings.py          # Pydantic settings (env-driven; incl. queue_provider, sqs_queue_url, queue_max_attempts, qdrant_collection_name, sparse_embedding_model)
│   │       │   └── setup.py             # App factory / setup helpers
│   │       │
│   │       ├── bootstrap/       # Composition roots shared across entry points
│   │       │   └── worker.py            # create_processing_worker() — wires the worker's object graph (incl. Chunking, Embedding, and Indexing Platforms)
│   │       │
│   │       ├── db/              # Database layer
│   │       │   ├── base.py              # SQLAlchemy DeclarativeBase
│   │       │   ├── mixins.py            # TimestampMixin (created_at, updated_at)
│   │       │   ├── postgres.py          # Async PostgreSQL engine factory
│   │       │   ├── qdrant.py            # Qdrant vector store client
│   │       │   ├── session.py           # Async session factory
│   │       │   └── valkey.py            # Valkey/Redis client
│   │       │
│   │       ├── dependencies/    # FastAPI dependency providers
│   │       │   ├── cache.py             # Cache dependency
│   │       │   ├── database.py          # DB session dependency
│   │       │   ├── generation.py        # get_generation_service()/get_streaming_service() (cached singletons), get_conversation_service(session) (request-scoped) — Streaming Platform, Milestone 2.9.10; get_conversation_artifact_writer()/get_artifact_policy_service_dependency() (cached singletons) — Artifact Platform, Milestone 3.10
│   │       │   ├── generation_usage.py  # Generation usage summary repository dependency
│   │       │   ├── settings.py          # Settings dependency
│   │       │   ├── upload.py            # Upload/processing service dependencies (incl. processing queue, worker, chunking/embedding/indexing service/artifact builder/writer)
│   │       │   └── vector_store.py      # Cached vector-store service dependency
│   │       │
│   │       ├── exceptions/      # Exception hierarchy and handlers
│   │       │   ├── auth.py              # Auth-specific exceptions
│   │       │   ├── base.py              # Base AppException class
│   │       │   ├── document.py          # Document exceptions
│   │       │   ├── handlers.py          # Global exception handlers (FastAPI)
│   │       │   ├── health.py            # Health check exceptions
│   │       │   └── research.py          # Research exceptions
│   │       │
│   │       ├── infrastructure/  # Infrastructure adapters
│   │       │   ├── aws/
│   │       │   │   └── session.py       # Boto3 session factory
│   │       │   ├── hashing/
│   │       │   │   ├── exceptions.py    # Hashing exceptions
│   │       │   │   ├── interfaces.py    # FileHasher abstract interface
│   │       │   │   └── sha256.py        # SHA-256 file hasher implementation
│   │       │   ├── metrics/
│   │       │   │   ├── interfaces.py    # MetricsCollector abstract interface
│   │       │   │   ├── models.py        # Metrics data models
│   │       │   │   ├── noop.py          # No-op metrics collector
│   │       │   │   └── upload.py        # Upload-specific metrics
│   │       │   ├── queue/               # Async queue abstraction (ADR-011, ADR-012)
│   │       │   │   ├── providers/
│   │       │   │   │   ├── sqs.py       # SQSQueue — boto3 via asyncio.to_thread; redrive-policy dead-lettering
│   │       │   │   │   └── valkey.py    # ValkeyQueue — Redis List-backed; pushes rejects to a <queue>-dlq list
│   │       │   │   ├── enums.py         # QueueProvider (VALKEY, SQS)
│   │       │   │   ├── exceptions.py    # QueueError hierarchy
│   │       │   │   ├── factory.py       # create_processing_queue(settings) — selects provider
│   │       │   │   ├── interfaces.py    # ProcessingQueue ABC (enqueue, dequeue, acknowledge, reject, retry)
│   │       │   │   └── models.py        # ProcessingJob, QueueMessage
│   │       │   └── storage/
│   │       │       ├── exceptions.py    # Storage exceptions
│   │       │       ├── factory.py       # Storage provider factory
│   │       │       ├── interfaces.py    # DocumentStorage abstract interface (incl. list_keys(*, prefix) — added for the Artifact Platform's ConversationArtifactReader)
│   │       │       ├── key_generator.py # S3 key generation logic
│   │       │       ├── models.py        # Storage data models
│   │       │       └── s3.py            # S3 storage implementation
│   │       │
│   │       ├── middleware/      # HTTP middleware
│   │       │   ├── cors.py              # CORS configuration
│   │       │   ├── register.py          # Middleware registration helper
│   │       │   ├── request_id.py        # Injects X-Request-ID header
│   │       │   ├── request_logging.py   # Structured request/response logging with correlation
│   │       │   └── request_timing.py    # Request duration (X-Process-Time header)
│   │       │
│   │       ├── models/          # SQLAlchemy ORM models
│   │       │   ├── __init__.py          # Exports all models (required for Alembic)
│   │       │   ├── conversation.py      # Conversation + Message models — includes persisted prompt-history summary/boundary; canonical messages remain replayable
│   │       │   ├── document.py          # Document model — upload_status + processing_status lifecycle columns
│   │       │   ├── enums.py             # DocumentUploadStatus, DocumentProcessingStatus (split lifecycle), MessageRole
│   │       │   └── user.py              # User model
│   │       │
│   │       ├── repositories/    # Data access layer
│   │       │   ├── conversation.py      # ConversationRepository — owner-scoped cursor-paginated replay, prompt-history reads/updates, first-user lookup, title update, deterministic ordering
│   │       │   ├── document.py          # DocumentRepository (CRUD operations)
│   │       │   └── user.py              # UserRepository (CRUD operations)
│   │       │
│   │       ├── schemas/         # Pydantic request/response schemas
│   │       │   ├── auth.py              # Auth schemas (CallbackRequest, TokenResponse)
│   │       │   ├── chat.py              # Stream request plus conversation summary/detail response schemas
│   │       │   ├── common.py            # Shared/generic schemas
│   │       │   ├── document.py          # Document schemas
│   │       │   ├── error.py             # Error response schemas
│   │       │   ├── health.py            # Health response schemas
│   │       │   └── report.py            # Report schemas
│   │       │
│   │       ├── services/        # Business logic layer
│   │       │   ├── auth.py                        # OAuth code exchange with Cognito
│   │       │   ├── conversation.py                 # ConversationService — cursor replay, rolling compaction orchestration, first prompt/title helpers, ordered append_turn()
│   │       │   ├── conversation_compaction.py      # Deterministic, zero-provider-cost bounded summary for old Chat prompt history
│   │       │   ├── document_processing_service.py # Orchestrates processing lifecycle + status updates
│   │       │   ├── queued_document_processing_service.py  # Bridges queue jobs to DocumentProcessingService
│   │       │   └── user.py                        # User sync, creation, and lifecycle
│   │       │
│   │       └── main.py          # FastAPI app entry point
│   │
│   ├── web/                     # Next.js 15 frontend (App Router)
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── (app)/                   # Auth-gated route group
│   │   │   │   │   ├── dashboard/
│   │   │   │   │   │   └── page.tsx         # Dashboard page
│   │   │   │   │   ├── documents/
│   │   │   │   │   │   └── page.tsx         # Document upload page (drag-and-drop)
│   │   │   │   │   ├── chat/
│   │   │   │   │   │   └── page.tsx         # Server-backed Chat conversation interface
│   │   │   │   │   ├── research/
│   │   │   │   │   │   └── page.tsx         # Research chat interface
│   │   │   │   │   └── layout.tsx           # AppShell — auth guard, redirects unauthenticated users
│   │   │   │   ├── auth/
│   │   │   │   │   └── callback/
│   │   │   │   │       └── page.tsx         # Cognito OAuth callback — exchanges code for token
│   │   │   │   ├── globals.css              # Global styles
│   │   │   │   ├── layout.tsx               # Root layout — fonts, AuthProvider
│   │   │   │   └── page.tsx                 # Landing / sign-in page
│   │   │   ├── components/
│   │   │   │   ├── auth/
│   │   │   │   │   └── login-button.tsx     # Cognito hosted UI redirect button
│   │   │   │   └── layout/
│   │   │   │       └── sidebar.tsx          # App sidebar navigation
│   │   │   ├── hooks/
│   │   │   │   └── use-auth.tsx             # AuthContext — token storage, profile fetch, isUnauthorized state
│   │   │   └── lib/
│   │   │       ├── api.ts                   # Typed API client (UserProfile, Document)
│   │   │       ├── auth.ts                  # Cognito URL builders, token storage (sessionStorage)
│   │   │       └── errors.ts                # extractErrorMessage — maps ErrorResponse body to a display string
│   │   ├── .env.local                       # Cognito client ID, domain, redirect URI, API URL
│   │   ├── .env.local.example               # Template for .env.local
│   │   ├── eslint.config.mjs                # ESLint configuration
│   │   ├── next.config.ts                   # Next.js configuration
│   │   ├── package.json                     # Next.js 15, React 19, Tailwind 3, TypeScript
│   │   ├── postcss.config.mjs               # PostCSS configuration (Tailwind)
│   │   ├── tailwind.config.ts               # Custom palette: ink, stone, sage, amber scales
│   │   ├── tsconfig.json                    # TypeScript configuration
│   │   └── README.md                        # Setup instructions and auth flow diagram
│   │
│   └── worker/                  # Background document processing worker (ADR-012)
│       ├── main.py              # Entry point — signal handling (SIGINT/SIGTERM) for graceful shutdown
│       ├── metrics.py           # WorkerMetrics — in-memory job counters, logged periodically
│       └── processing_worker.py # ProcessingWorker — poll/process/retry/dead-letter loop
│
├── benchmarks/                  # Engineering Benchmark Platform
│   ├── chunking/
│   │   ├── benchmark.py                     # ChunkingBenchmark — runs every registered provider over the same dataset
│   │   ├── report_generator.py              # ChunkingBenchmarkReportGenerator (subclass; chunking-specific viz placeholder)
│   │   └── reports/chunking/report.{md,json}  # Checked-in example output from a real benchmark run
│   ├── common/
│   │   ├── dataset_loader.py                # DatasetLoader — loads ProcessedDocument fixtures from a dataset directory
│   │   ├── report_generator.py              # BenchmarkReportGenerator — renders BenchmarkReport as Markdown/JSON
│   │   ├── metrics.py                       # average() / percentile() — shared statistical helpers, extracted out of retrieval/benchmark.py once reranking/benchmark.py needed the same logic
│   │   ├── report.py                        # (empty) — superseded by models/report.py
│   │   └── timer.py                         # Timer — dependency-free high-resolution timer; usable via start()/stop() or as a context manager
│   ├── datasets/
│   │   ├── README.md                        # Dataset philosophy — deterministic, version-controlled, immutable
│   │   └── research-papers/
│   │       ├── paper-001/processed_document.json
│   │       ├── paper-002/processed_document.json
│   │       ├── paper-003/processed_document.json
│   │       ├── paper-004/processed_document.json
│   │       ├── paper-005/processed_document.json
│   │       ├── retrieval_queries.json       # 20-query hand-curated ground truth (document-level relevance, 4 categories) for the Retrieval Benchmark
│   │       └── generation_queries.json      # 13-query query/context/expected_answer/citations dataset for the Generation Benchmark; context is a verbatim excerpt so scoring doesn't depend on live retrieval
│   ├── embeddings/
│   │   ├── benchmark.py                     # EmbeddingBenchmark — chunks each document once (fixed RECURSIVE strategy), then runs every registered embedding provider against identical chunks, timing latency/throughput/dimensions; isolates per-provider failures so one candidate erroring doesn't abort the report
│   │   ├── report_generator.py              # EmbeddingBenchmarkReportGenerator (subclass; embedding-specific viz placeholder)
│   │   └── reports/embeddings/report.{md,json}  # Checked-in example output (Sentence Transformers full run; Voyage AI partial — hit free-tier rate limit)
│   ├── generation/                          # Generation Benchmark — scores every configured GenerationProvider (Groq/OpenAI/Claude/Gemini/Ollama) against a shared dataset; see PROJECT_STATUS.md's "Evaluation Platform PRD Reconciliation"
│   │   ├── dataset.py                       # GenerationBenchmarkQuery, GenerationQueryDataset, load_generation_queries() — mirrors retrieval/dataset.py
│   │   ├── metrics.py                       # Deterministic no-LLM lexical-overlap scorers — faithfulness (sentence-level), groundedness (token-level), relevance, completeness, citation_accuracy; mirrors hallucination_validator.py's _significant_words() convention
│   │   └── benchmark.py                     # GenerationBenchmark — one candidate per configured provider (self._registry.providers); context tagged `[Source: <filename>]` + a citation system_prompt, both required for citation_accuracy to be non-zero
│   ├── interfaces/
│   │   └── benchmark.py                     # Benchmark ABC — name, run(dataset_path) -> BenchmarkReport
│   ├── models/
│   │   └── report.py                        # BenchmarkCandidate, BenchmarkDataset, BenchmarkReport
│   ├── pipeline/                            # End-to-end ingestion pipeline benchmark (own CLI: `python -m benchmarks.pipeline.benchmark`, not via runner.py)
│   │   ├── benchmark.py                     # PipelineBenchmark — runs every document through the real Chunking→Embedding→Indexing services, aggregates timing/storage/throughput/memory
│   │   ├── dataset.py                       # load_pipeline_dataset() — loads ProcessedDocument entries + source size from the dataset directory
│   │   ├── models.py                        # PipelineBenchmarkReport and sub-models (DocumentPipelineResult, IndexingMetrics incl. sparse_vector_count, StatSummary, ThroughputSummary, StorageSummary, Observations, ProductionReadiness)
│   │   ├── pipeline_runner.py               # run_document_pipeline() — real Chunking → Embedding (Voyage AI) → Indexing (dense+sparse, Qdrant) → artifact persistence for one document
│   │   ├── report_generator.py              # PipelineReportGenerator — renders PipelineBenchmarkReport as Markdown
│   │   ├── services.py                      # create_pipeline_services() — reuses the real composition roots (mirrors app.bootstrap.worker)
│   │   └── stats.py                         # summarize() — average/min/max/median/p95 over a metric list
│   ├── regression/                          # Regression Detection — threshold-based pass/fail comparing a fresh BenchmarkReport against the previously stored one
│   │   ├── models.py                        # RegressionIssue, RegressionResult (PRD §11.5) — compares two BenchmarkReports, no parallel canonical model invented
│   │   ├── thresholds.py                    # ThresholdDirection (MIN_DROP/MAX_INCREASE/MAX_RELATIVE_INCREASE), DEFAULT_METRIC_THRESHOLDS — metric-name-keyed, absent metrics simply aren't checked
│   │   ├── detector.py                      # RegressionDetector.compare(previous, current) -> RegressionResult — per-candidate, per-metric; a candidate present in only one report is skipped, not flagged
│   │   └── report_generator.py              # RegressionReportGenerator — renders a RegressionResult as Markdown/JSON, mirrors common/report_generator.py
│   ├── reports/
│   │   ├── .gitkeep                         # Keeps the default --output directory tracked
│   │   ├── ingestion-benchmark-report.md    # Checked-in example output from a real pipeline benchmark run (incl. dense + sparse vector counts)
│   │   ├── ingestion-benchmark.json         # Same run, machine-readable
│   │   ├── retrieval/report.{md,json}       # Checked-in example output from a real retrieval benchmark run (dense vs. sparse vs. hybrid), now including ndcg_at_5/ndcg_at_10
│   │   ├── retrieval/regression.json, regression_report.md  # Checked-in example --check-regression output — passed cleanly on an unchanged rerun
│   │   ├── metadatafiltering/report.{md,json}  # Checked-in example output — leakage_rate: 0.0 for every filtered candidate, MRR raised to 1.0
│   │   ├── reranking/report.{md,json}       # Checked-in example output — Recall@5 unchanged, MRR/NDCG@5 improved substantially with reranking
│   │   ├── generation/report.{md,json}      # Checked-in example output — Groq/OpenAI/Claude completed 13/13 queries with distinct scores; Gemini/Ollama recorded as zero-scored candidates with notes.error
│   │   └── generation/regression.json, regression_report.md  # Checked-in example --check-regression output that actually caught real regressions (a prompt change shifted relevance/completeness/latency past threshold)
│   ├── reranking/
│   │   └── benchmark.py                     # RerankingBenchmark — one shared hybrid candidate pool per query, scores hybrid_only / hybrid_cross_encoder / hybrid_voyage against it (dedicated `benchmark_reranking` collection); Recall@5, MRR, NDCG@5, latency, qualitative cost model; hybrid_voyage degrades to a "skipped" note if VOYAGE_API_KEY isn't configured
│   ├── retrieval/                           # Retrieval Benchmark — dense vs. sparse vs. hybrid (ADR-020)
│   │   ├── benchmark.py                     # RetrievalBenchmark — builds a dedicated Qdrant collection, evaluates 3 candidates against the query dataset
│   │   ├── dataset.py                       # load_retrieval_queries() — loads/validates retrieval_queries.json
│   │   ├── indexer.py                       # BenchmarkRetrievalIndexer — chunks + embeds (dense+sparse) + upserts the benchmark corpus into a dedicated collection, drop/recreate per run; accepts an optional owner_ids_by_document_id map for per-document synthetic owners
│   │   ├── metadata_filtering_benchmark.py  # MetadataFilteringBenchmark — dedicated `benchmark_retrieval_filtering` collection, per-document synthetic owners, unfiltered vs. owner-filtered dense/sparse/hybrid; reports leakage_rate (correctness signal, expect 0.0)
│   │   └── metrics.py                       # recall_at_k() / precision_at_k() / reciprocal_rank() / ndcg_at_k() — pure, document-level relevance functions; ndcg_at_k now actually wired into benchmark.py's reported metrics (previously implemented but unused)
│   ├── README.md                             # Platform overview, philosophy, workflow, usage — now documents the Generation benchmark and --check-regression
│   ├── factory.py                            # create_benchmark_registry() — composition root (Chunking, Embedding, Retrieval, MetadataFiltering, Reranking, Generation benchmarks, each retrieval-family one with its own dedicated Qdrant collection; GenerationBenchmark wired from create_generation_registry())
│   ├── registry.py                           # BenchmarkRegistry — name → benchmark resolution
│   └── runner.py                             # CLI entry point (python -m benchmarks.runner <name> --dataset <path> [--check-regression]) — the flag loads the pre-existing report.json as a baseline before overwriting it, runs RegressionDetector after, writes regression.json/regression_report.md, exits non-zero on failure
│
├── datasets/                    # Data for evaluation and testing
│   ├── golden/                  # Ground-truth / golden datasets
│   ├── processed/               # Cleaned and processed data
│   └── raw/                     # Raw ingested data
│
├── docs/                        # All project documentation
│   ├── adrs/                    # Architecture Decision Records
│   │   ├── ADR-001-monorepo.md
│   │   ├── ADR-002-fastapi.md
│   │   ├── ADR-003-fastapi-lifespan.md
│   │   ├── ADR-004-application-state.md
│   │   ├── ADR-005-api-contracts.md
│   │   ├── ADR-006-settings-vs-constants.md
│   │   ├── ADR-007-middleware-registration.md
│   │   ├── ADR-008-typed-api-schemas.md
│   │   ├── ADR-009-identity-architecture
│   │   ├── ADR-010-document-processing-strategy.md
│   │   ├── ADR-011-queue-abstraction.md
│   │   ├── ADR-012-asynchronous-document-processing.md
│   │   ├── ADR-013-canonical-chunk-model.md
│   │   ├── ADR-014-chunking-provider-architecture.md
│   │   ├── ADR-015-canonical-ai-platform-pipeline.md
│   │   ├── ADR-016-observability-platform.md
│   │   ├── ADR-017-vector-store-platform.md
│   │   ├── ADR-018-knowledge-indexing-and-retrieval-architecture.md
│   │   ├── ADR-019-qdrant-native-hybrid-retrieval.md
│   │   ├── ADR-020-retrieval-evaluation-first-development.md
│   │   ├── ADR-021-hybrid-retrieval-architecture.md
│   │   ├── ADR-022-reranking-platform.md
│   │   └── ADR-023-framework-integration-strategy.md
│   │
│   ├── ai/                      # AI feature specs (knowledge platform)
│   │   └── 1.knowledge_platform/
│   │       ├── 1.1.doc_upload.md
│   │       ├── 1.2.doc_storage.md
│   │       ├── 1.3.doc_validation
│   │       ├── 1.4.doc_upload_flow.md
│   │       ├── 1.5.doc_upload_observability.md
│   │       ├── 1.6.doc_upload_final.md
│   │       ├── 1.7.doc_upload_archotecture.md
│   │       ├── 1.8.doc_upload_implementation.md
│   │       └── 2.2.doc_processing.md
│   │
│   ├── api/                     # API reference docs
│   │   ├── authentication.md
│   │   ├── backend-api.md
│   │   ├── chat.md
│   │   ├── documents.md
│   │   ├── feedback.md
│   │   ├── openapi.md
│   │   └── reports.md
│   │
│   ├── architecture/            # System design and architecture docs
│   │   ├── ai-framework-integration.md
│   │   ├── backend-architecture.md
│   │   ├── chunk-lifecycle-and-dataflow.md   # Frozen v1.0 — Chunk lifecycle/dataflow across the whole pipeline
│   │   ├── chunking-platform-architecture.md # Frozen v1.0 — pre-implementation architecture freeze
│   │   ├── chunking-platform.md              # Chunking Platform overview (Phase 2.3 foundation)
│   │   ├── db-sessions.md
│   │   ├── decision-history.md
│   │   ├── embedding-platform.md             # Embedding Platform architecture (Phase 2.4, completed V1)
│   │   ├── evaluation-platform.md            # Runtime Evaluation Platform (status header still says "Planned", but the concept it describes is already implemented — as the AI Runtime Observability Platform, `app/ai/observability/`, confirmed by this file's own note on the sibling `observability-platform.md`; see PROJECT_STATUS.md's "Evaluation Platform PRD Reconciliation")
│   │   ├── evaluation-strategy.md            # Why three evaluation layers (Benchmarks / Runtime Eval / Experimentation) — Benchmarks now includes Generation + Regression (repo-root `benchmarks/`), Runtime Eval is the Observability Platform, Experimentation remains not started
│   │   ├── experimentation-platform.md       # Experimentation Platform (planned)
│   │   ├── framework-integration-strategy.md # Companion to ADR-023 — LangChain/LangGraph/LangSmith integration boundaries
│   │   ├── hybrid-retrieval-indexing.md      # Sparse embeddings (FastEmbed SPLADE) + Qdrant native hybrid indexing (ADR-018, ADR-019); complete ingestion pipeline flow diagram
│   │   ├── identity-architecture.md
│   │   ├── knowledge-platform-roadmap.md     # Full Knowledge Platform subsystem breakdown
│   │   ├── metadata-filtering.md             # Metadata Filtering architecture (Milestone 2.7.1, Complete) — owner_id/document_id/filename filters, benchmark validation
│   │   ├── observability-platform.md         # Original (2026-07-06) Runtime Evaluation design for the Knowledge Processing pipeline; updated 2026-07-18 — Phase 1 now implemented, but via the newer ai/observability/ platform (oberservability_platform_prd.md) rather than this doc's own proposed folder structure
│   │   ├── observability-strategy.md         # Logging-only scope doc; updated 2026-07-18 — no longer claims LangSmith "has no implementation yet" (it does now, see monitoring/langsmith.md)
│   │   ├── project-constitution.md
│   │   ├── repository-structure.md
│   │   ├── reranking-platform.md             # Reranking Platform architecture (Milestone 2.7.2, companion to ADR-022)
│   │   ├── retrieval-benchmarking-strategy.md  # Accepted — retrieval benchmark methodology: query categories, dataset format v1/v2, ADR-020 metrics, Hybrid decision gate (ADR-021 context)
│   │   └── system-overview.md
│   │
│   ├── deployment/              # Deployment guides
│   │   ├── local.md
│   │   └── production.md
│   │
│   ├── diagrams/                # Visual architecture diagrams
│   │   ├── ResearchMind.drawio.png
│   │   └── ResearchMind.drawio.xml
│   │
│   ├── engineering-journal/     # Developer learning notes and milestone write-ups
│   │   ├── concepts/
│   │   │   ├── 001-fastapi-lifespan.md
│   │   │   ├── 002-sqlalchemy-engine.md
│   │   │   ├── 003-session-vs-engine.md
│   │   │   ├── 004-dependency-injection.md
│   │   │   ├── 005-connection-pooling.md
│   │   │   ├── 006-fastapi-middleware.md
│   │   │   ├── 007-fastapi-application-state.md
│   │   │   ├── 008-api-versioning.md
│   │   │   ├── 009-api-contracts.md
│   │   │   ├── 010-global-exception-handling.md
│   │   │   ├── 011-pydantic-response-models.md
│   │   │   └── 012-connect-progresql-terminal
│   │   └── milestones/
│   │       ├── 030-backend-foundation.md
│   │       ├── 0.31-engineering-quality.md
│   │       ├── 2026-07-02-processing-platform-summary.md  # Document Processing Platform milestone retrospective
│   │       ├── 2026-07-04-asynchronous-document-processing.md  # Queue abstraction + background worker milestone retrospective
│   │       ├── 2026-07-05-fixed-chunking.md  # Fixed Chunking Platform milestone retrospective (Phase 2.3.3)
│   │       └── 2026-07-06-runtime-metrics-foundation.md  # Runtime Metrics Foundation milestone retrospective
│   │
│   ├── evaluation/              # Evaluation strategy and metrics
│   │   ├── benchmarks.md
│   │   ├── hallucination-testing.md
│   │   ├── metrics.md
│   │   ├── report-quality.md
│   │   ├── retrieval-testing.md
│   │   └── strategy.md
│   │
│   ├── guides/                  # Developer how-to guides
│   │   ├── coding-standards.md
│   │   ├── contributing.md
│   │   ├── debugging.md
│   │   ├── style-guide.md
│   │   └── testing.md
│   │
│   ├── handoff/                 # Context handoff documents between sessions
│   │   ├── chat-handoff1.md
│   │   ├── chat-handoff2.md
│   │   └── CHATGPT_HANDOFF_PHASE_2_2.md     # Master context/handoff doc for Phase 2.2 (document processing)
│   │
│   ├── monitoring/              # Observability setup docs
│   │   ├── dashboards.md
│   │   ├── grafana.md
│   │   ├── langsmith.md         # Implemented (2026-07-18, was an empty placeholder) — LangSmith config table, RuntimeTracer wiring, Input/Output/Token content fix, verification steps
│   │   ├── otel.md
│   │   └── prometheus.md
│   │
│   ├── platforms/               # Platform-level design docs (pre-implementation planning)
│   │   ├── indexing-platform.md      # Indexing Platform plan — predates ADR-019; BM25 section since superseded by Qdrant native sparse vectors
│   │   └── retrieval-platform.md     # Retrieval Platform plan — predates implementation; see ADR-020/ADR-021 and retrieval-benchmarking-strategy.md for the as-built architecture
│   │
│   ├── product/                 # Product-facing documentation
│   │   ├── faq.md
│   │   ├── features.md
│   │   ├── getting-started.md
│   │   └── release-notes.md
│   │
│   ├── project/                 # Numbered project reference set (constitution, state, roadmap, decisions)
│   │   ├── 00-project-constitution.md
│   │   ├── 01-current-state.md
│   │   ├── 02-roadmap.md
│   │   ├── 03-frozen-decisions.md
│   │   ├── 04-folder-structure.md
│   │   ├── 05-tech-stack.md
│   │   ├── 06-chatgpt-collaboration.md
│   │   └── 07-engineering-journal.md
│   │
│   ├── reference/               # External references and resources
│   │   ├── awesome-resources.md
│   │   ├── courses.md
│   │   ├── official-docs.md
│   │   └── papers.md
│   │
│   ├── research/                # Research and exploration notes
│   │   ├── embeddings.md
│   │   ├── future-ideas.md
│   │   ├── mcp-research.md
│   │   ├── papers.md
│   │   └── reranking.md
│   │
│   ├── runbooks/                # Operational runbooks
│   │   ├── backup.md
│   │   ├── incident-response.md
│   │   ├── local-development.md
│   │   ├── restore.md
│   │   └── troubleshooting.md
│   │
│   ├── standards/               # Team standards and conventions
│   │   ├── branching.md
│   │   ├── commit-messages.md
│   │   ├── documentation.md
│   │   ├── git.md
│   │   └── python.md
│   │
│   ├── workflows/               # End-to-end workflow documentation
│   │   ├── document-ingestion.md
│   │   ├── evaluation-pipeline.md
│   │   ├── feedback-loop.md
│   │   ├── report-generation.md
│   │   └── research-workflow.md
│   │
│   ├── index.md                 # Docs home / navigation index
│   ├── phase2_roadmap.md        # Frozen Phase 2 roadmap (Upload Platform → Document Processing)
│   ├── project-constitution.md  # Project principles and goals
│   ├── project-handbook.md      # Working agreements and practices
│   └── s3_configuration_guide.md  # Guide for configuring AWS S3 for document storage
│
├── examples/                    # Usage examples and notebooks (planned)
├── experiments/                 # Experimental code and prototypes (planned)
│
├── infrastructure/              # Infrastructure-as-code (planned, currently empty)
│   ├── database/                # DB provisioning scripts
│   ├── deployment/               # Deployment manifests (k8s, etc.)
│   ├── docker/                  # Dockerfile definitions
│   ├── monitoring/               # Monitoring stack config
│   └── scripts/                 # Infrastructure automation scripts
│
├── scripts/                     # Developer utility scripts
│   ├── dev.sh                   # Runs migrations then starts uvicorn dev server
│   ├── benchmark_chunking.py    # Stray placeholder (comment-only diagram); superseded by benchmarks/chunking/benchmark.py
│   └── verify_voyage_sdk.py     # Manual smoke test — resolves Voyage AI from create_embedding_registry() and prints provider/model
│
├── services/                    # Internal service modules (planned)
│   ├── cache/
│   ├── evaluation/
│   ├── ingestion/
│   ├── mcp/
│   ├── memory/
│   ├── observability/
│   ├── providers/
│   ├── reporting/
│   └── retrieval/
│
├── shared/                      # Code shared across apps and services (planned)
│   ├── config/
│   ├── constants/
│   ├── exceptions/
│   ├── interfaces/
│   ├── prompts/
│   ├── schemas/
│   └── utils/
│
├── tests/                       # Test suite
│   ├── api/
│   │   ├── test_health.py                   # Health endpoint smoke tests
│   │   └── test_retrieval_filters.py        # /retrieve, /retrieve/sparse, /retrieve/hybrid — 401 without a token (real get_current_user), retrieval scoped to the authenticated user, spoofed owner_id in filters is ignored
│   ├── e2e/                                 # End-to-end tests (planned)
│   ├── evaluation/                          # LLM evaluation tests (planned)
│   │   ├── test_faithfulness.py
│   │   ├── test_groundedness.py
│   │   ├── test_reranking.py
│   │   └── test_retrieval_precision.py
│   ├── integration/                         # Integration tests
│   │   ├── ai/knowledge/chunking/
│   │   │   ├── test_fixed_chunking_pipeline.py    # End-to-end Fixed Chunking pipeline (ordering, provenance, experiment metadata, statistics)
│   │   │   ├── test_fixed_chunking_edge_cases.py  # Overlap preservation; empty/whitespace documents raise ChunkingValidationError
│   │   │   └── test_recursive_chunking_pipeline.py  # End-to-end Recursive Chunking pipeline (ChunkArtifactBuilder + JSON serialization)
│   │   ├── ai/knowledge/embeddings/
│   │   │   └── test_sentence_transformers_pipeline.py  # End-to-end embedding pipeline (real SentenceTransformerEmbeddingProvider + EmbeddingArtifactBuilder)
│   │   ├── ai/knowledge/processing/
│   │   │   └── test_processing_service.py   # Full DoclingParser → ProcessingService pipeline (incl. chunking + a mocked embedding stage — ProcessingService hardcodes Voyage AI, which this test avoids calling for real)
│   │   ├── ai/knowledge/upload/
│   │   │   └── test_duplicate_detection.py  # Real UploadService + DuplicateDetectionService against Postgres
│   │   ├── ai/test_chat_stream.py           # Chat SSE/history integration: auth, event ordering, both completion event variants, turn persistence, and Groq title from the first user question
│   │   ├── test_document_repository.py
│   │   ├── test_document_service.py
│   │   ├── test_memory.py
│   │   ├── test_retriever.py
│   │   ├── test_user_repository.py
│   │   ├── test_user_service.py
│   │   └── test_vector_store.py
│   ├── performance/                         # Performance tests (planned)
│   │   ├── test_embedding_speed.py
│   │   ├── test_latency.py
│   │   └── test_qdrant_speed.py
│   ├── security/                            # Security tests (planned)
│   │   ├── test_jailbreaks.py
│   │   └── test_prompt_injection.py
│   ├── unit/
│   │   ├── ai/knowledge/cache/embeddings/
│   │   │   ├── test_key.py                  # build_embedding_cache_key() — stable key derivation
│   │   │   ├── test_null.py                 # NullEmbeddingCache — always-miss get_many, no-op set_many
│   │   │   └── test_valkey.py               # ValkeyEmbeddingCache — hit/miss decoding, fail-open on Redis errors, corrupt-entry handling, TTL on write
│   │   ├── ai/knowledge/cache/query_embeddings/
│   │   │   ├── test_null.py                 # NullQueryEmbeddingCache — always-miss get, no-op set
│   │   │   └── test_valkey.py               # ValkeyQueryEmbeddingCache — hit/miss decoding, fail-open on Redis errors, corrupt-entry handling, TTL on write
│   │   ├── ai/knowledge/context/             # Context Platform tests — guardrails/ and formatter/ not yet covered
│   │   │   ├── artifacts/
│   │   │   │   └── test_reader.py           # ChunkArtifactReader — storage key layout, payload parsing, error propagation
│   │   │   ├── builders/
│   │   │   │   ├── test_adjacent_merge.py   # AdjacentMergeService — chaining, document/index-gap boundaries
│   │   │   │   ├── test_deduplication.py    # DeduplicationService — collapse repeats, preserve order
│   │   │   │   ├── test_ordering.py         # ContextOrderingService — score desc, chunk_index tiebreak
│   │   │   │   └── test_parent_expansion.py # ParentExpansionService — grouped artifact loads, enrichment, unresolvable parents
│   │   │   ├── citations/
│   │   │   │   └── test_service.py          # CitationService — numbering, citation_id write-back, merged_chunk_ids handling
│   │   │   ├── compression/
│   │   │   │   ├── providers/
│   │   │   │   │   ├── test_embedding.py        # EmbeddingCompressionProvider — near-duplicate dropping, threshold, statistics
│   │   │   │   │   ├── test_langchain.py        # LangChainCompressionProvider — FakeListChatModel-faked extraction, metadata/citation preservation, statistics, timeout/failure wrapping, no-API-key error
│   │   │   │   │   ├── test_llm.py              # LLMCompressionProvider (V4) — mocked GenerationService, per-chunk fallback on failure/empty summary, never drops a chunk, statistics, configured provider/temperature/max_tokens honored
│   │   │   │   │   └── test_token_budget.py     # TokenBudgetCompressionProvider — packing, budget overflow, defaults
│   │   │   │   ├── test_create.py           # create_compression_service() registers all four strategies
│   │   │   │   ├── test_exceptions.py       # CompressionError hierarchy
│   │   │   │   ├── test_registry.py         # CompressionRegistry — get/register/overwrite
│   │   │   │   └── test_service.py          # CompressionService — delegates to resolved provider, falls back to original chunks on CompressionError
│   │   │   ├── factories.py                 # make_context_chunk() — shared test factory (not a test module)
│   │   │   └── test_service.py              # ContextBuilderService.build() — full pipeline ordering and output shape
│   │   ├── ai/knowledge/embeddings/
│   │   │   ├── artifacts/
│   │   │   │   ├── test_builder.py          # EmbeddingArtifactBuilder — statistics aggregation, metadata derivation, empty-collection guard
│   │   │   │   └── test_writer.py           # EmbeddingArtifactWriter — storage key layout, serialized payload, error propagation
│   │   │   ├── providers/
│   │   │   │   ├── test_sentence_transformers.py  # SentenceTransformerEmbeddingProvider (mocked SentenceTransformer) — identifiers, lazy/cached model construction, vector→canonical Embedding conversion
│   │   │   │   ├── test_voyage.py           # VoyageAIEmbeddingProvider (mocked client) — client invocation, canonical Embedding conversion, int→float vector coercion
│   │   │   │   └── test_batching.py         # EmbeddingBatcher unit tests + provider-level batching integration (Sentence Transformers, Voyage AI)
│   │   │   ├── test_factory.py              # EmbeddingFactory — provenance/statistics/vector mapping from a Chunk
│   │   │   ├── test_registry.py             # EmbeddingRegistry registration, lookup, deduplication
│   │   │   └── test_service.py              # EmbeddingService orchestration — delegation and validation failures
│   │   ├── ai/knowledge/reranking/
│   │   │   └── test_registry.py             # RerankingRegistry — get resolves/raises not-found, has() reflects registration state
│   │   ├── ai/knowledge/retrieval/
│   │   │   ├── providers/
│   │   │   │   ├── test_qdrant.py           # QdrantRetrievalProvider — named dense-vector query, missing-optional-field defaults, empty results, malformed-payload KeyError
│   │   │   │   └── test_qdrant_filters.py   # QdrantRetrievalProvider._build_filter — empty/single/multiple filters, document_id UUID coercion, unsupported keys and falsy values ignored
│   │   │   ├── query/
│   │   │   │   └── test_dense_service.py    # QueryEmbeddingService — cache hit/miss, Voyage/OpenAI branches, unsupported-provider NotImplementedError
│   │   │   ├── test_registry.py             # RetrievalRegistry — get/has/providers, not-found error
│   │   │   └── test_service.py              # RetrievalService — search() happy path + validation edge cases, provider-not-found propagation
│   │   ├── ai/knowledge/processing/
│   │   │   ├── metadata/
│   │   │   │   └── test_service.py          # MetadataEnrichmentService — regression coverage (PDF provider vs. non-PDF formats)
│   │   │   ├── test_docling_parser.py       # DoclingParser parse() with real PDF fixture
│   │   │   ├── test_models.py               # ProcessedDocument, block types, discriminated union
│   │   │   ├── test_registry.py             # ParserRegistry registration, lookup, deduplication
│   │   │   ├── test_service.py              # ProcessingService orchestration with FakeParser
│   │   │   ├── test_service_resilience.py   # Storage/parser failure propagation with pipeline-stage logging
│   │   │   └── test_temporary_file_manager.py  # TemporaryFileManager lifecycle
│   │   ├── ai/knowledge/upload/
│   │   │   ├── test_service.py              # UploadService — validation-before-I/O, size boundaries
│   │   │   └── test_validators.py           # UploadValidator — invalid file rejection rules
│   │   ├── ai/runtime/events/                # Runtime Event Platform tests (new, Milestone 2.9.10)
│   │   │   └── adapters/test_base.py        # GenericStreamChunkAdapter.to_stream_event() — content/type/metadata mapping, category always GENERATION, session_id/request_id pass-through and defaults
│   │   ├── ai/runtime/generation/            # Generation Platform tests (complete, per generation_platform_complexion_prd.md)
│   │   │   ├── test_service.py              # GenerationService — delegation, empty-prompt/context errors, provider-not-found/error propagation, ValidationService integration (report on result.validation, input-only errors don't regenerate, output-stage errors do), fail-fast pre-check, policy-driven regeneration (Acceptance/Runtime Validation policies), metrics recording, stream_generate() (explicit/routed provider resolution, capability check, validation, provider-not-found)
│   │   │   ├── test_registry.py             # GenerationRegistry — provider resolution
│   │   │   ├── providers/                   # test_claude.py, test_gemini.py, test_groq.py, test_ollama.py, test_openai.py, test_streaming.py, test_structured_outputs.py
│   │   │   ├── prompts/                     # test_builder.py, test_examples.py, test_prompt_factory.py, test_registry.py, test_service.py, test_templates.py, test_token_estimation.py
│   │   │   ├── policies/                    # Validation Policy Layer tests (new) — test_acceptance.py, test_fail_fast.py, test_runtime.py
│   │   │   ├── observability/                # Runtime Metrics Integration tests (new) — test_models.py (build_generation_metrics_snapshot), test_service.py (GenerationMetricsService counters/duration/snapshot)
│   │   │   ├── caching/                     # Runtime Caching Platform tests (new, 22 cases)
│   │   │   │   ├── fakes.py                     # In-memory Exact/Semantic/SessionCacheProvider doubles (not a test module)
│   │   │   │   ├── test_service.py              # CachingService — AUTO/EXACT_ONLY/SEMANTIC/NEVER policy branching, statistics, session cache independence (streaming requests now participate in cache like any other, no bypass)
│   │   │   │   ├── exact/test_key_builder.py    # hash_prompt/hash_context/hash_schema determinism + sensitivity, build_exact_cache_key stability
│   │   │   │   └── policies/test_service.py     # CachePolicyResolver — override precedence, per-runtime defaults, unknown-runtime fallback
│   │   │   ├── streaming/                   # Generation Streaming Platform tests (new, Milestone 2.9.10)
│   │   │   │   └── test_service.py              # StreamingService — cache-hit replay as synthetic TOKEN events, live-stream store-on-COMPLETE, error-mid-stream yields ERROR + skips store, no-caching-service path
│   │   │   └── validation/                  # Validation Platform tests
│   │   │       ├── factories.py             # Shared make_request()/make_result()/make_chunk()/make_citation() builders (not a test module) — make_request() now also takes runtime: RuntimeType | None
│   │   │       ├── test_models.py           # ValidationReport.issues flattening (stage order, optional runtime stage), ValidatorOutcome defaults
│   │   │       ├── test_scoring.py          # compute_overall_score() — weighted average, renormalization over only the stages that scored
│   │   │       ├── test_registry.py         # ValidationRegistry — per-stage isolation, registration order, defensive copies, register_runtime_validator()/register_runtime_contract() delegation
│   │   │       ├── test_service.py          # ValidationService — per-stage aggregation + stage-stamping, crash → WARNING (other validators still run), validate_runtime() contract resolution, full validate() report assembly across all four stages
│   │   │       ├── input/                   # test_empty_prompt.py, test_context_validation.py, test_provider_limits.py, test_token_budget.py
│   │   │       ├── output/                  # test_schema_validator.py, test_citation_validator.py, test_json_validator.py, test_hallucination_validator.py, test_formatting_validator.py, test_completeness_validator.py, test_consistency_validator.py, test_response_size_validator.py
│   │   │       └── runtime/                 # Runtime Validation Platform tests (109 cases + new contract/validator coverage)
│   │   │           ├── test_registry.py         # RuntimeRegistry — per-RuntimeType isolation, contract_for/validators_for, all_validators flattening
│   │   │           ├── test_service.py          # RuntimeValidationService — no-runtime-set no-op, matching contract runs + stage-stamping, non-matching runtime ignored, standalone validators alongside the contract, crash → WARNING
│   │   │           ├── validators/              # test_completeness.py, test_consistency.py (incl. custom field names), test_confidence.py, test_evidence.py, test_citation.py, test_dependency.py (new — cycle detection, unknown deps) — one file per generic validator
│   │   │           └── contracts/               # test_research.py, test_planner.py, test_reviewer.py, test_agent.py, test_mcp.py (all new except research) — each contract's compliant/trivial-output/contract-name-tagging cases
│   │   ├── ai/guardrails/                    # Guardrails Platform tests (new, 113 cases)
│   │   │   ├── factories.py                 # Shared make_request()/make_result()/make_chunk()/make_citation()/make_execution_state()/make_budget_policy()/make_guardrail_issue() builders (not a test module)
│   │   │   ├── test_models.py               # GuardrailReport.issues flattening, extra="forbid"
│   │   │   ├── test_registry.py             # GuardrailRegistry — per-stage isolation, registration order, defensive copies
│   │   │   ├── test_service.py              # GuardrailService — per-stage aggregation, crash → WARNING (FailPolicy open/closed), REGENERATE/BLOCK policy derivation, full evaluate() report
│   │   │   ├── test_create.py               # create_guardrail_registry()/get_guardrail_service() wiring smoke tests, end-to-end evaluate() on real dependencies
│   │   │   ├── input/                       # test_prompt_injection.py, test_scope_validation.py, test_pii_detection.py, test_rate_limit.py, test_toxicity.py
│   │   │   ├── retrieval/                   # test_context_sanitization.py, test_access_control.py, test_source_trust.py, test_citation_integrity.py
│   │   │   ├── generation/                  # test_faithfulness.py, test_schema_enforcement.py, test_pii_leakage.py, test_moderation.py
│   │   │   ├── runtime/                     # test_execution_limits.py, test_budget_guardrail.py, test_loop_detection.py, test_tool_policy.py, test_approval_gate.py
│   │   │   ├── trust/                       # test_models.py, test_trust_registry.py, test_trust_policies.py, test_scoring.py
│   │   │   ├── policies/                    # test_fail_policy.py, test_risk_policy.py, test_regeneration_policy.py, test_runtime_policy.py
│   │   │   ├── scoring/                     # test_weights.py, test_overall_risk.py
│   │   │   ├── artifacts/                   # test_models.py, test_builders.py, test_writers.py (_FakeDocumentStorage double)
│   │   │   ├── reports/                     # test_guardrail_report.py, test_issue_report.py
│   │   │   └── utils/                       # test_patterns.py
│   │   ├── ai/memory/                        # Memory Optimization test suite — eligibility, availability short-circuit, compact session state, extraction idempotency/orchestration, and two-session interest promotion
│   │   │   ├── test_availability.py
│   │   │   ├── test_extraction_policy.py
│   │   │   ├── test_interest_promotion.py
│   │   │   ├── test_memory_context.py
│   │   │   ├── test_memory_extraction_orchestrator.py
│   │   │   └── test_session_state.py
│   │   ├── infrastructure/storage/
│   │   │   └── test_s3_storage.py           # S3StorageService — boto3 ClientError → typed StorageError mapping
│   │   ├── benchmarks/common/
│   │   │   └── test_metrics.py              # average() / percentile() — mean and nearest-rank percentile, 0.0 on empty input
│   │   ├── benchmarks/reranking/
│   │   │   └── test_benchmark.py            # RerankingBenchmark — _build_candidate metric aggregation + error notes, _build_summary deltas over hybrid_only baseline
│   │   ├── benchmarks/retrieval/
│   │   │   ├── test_dataset.py              # load_retrieval_queries() — well-formed dataset, missing-file error
│   │   │   └── test_metrics.py              # recall_at_k / precision_at_k / reciprocal_rank / ndcg_at_k — dedup-by-document semantics, window boundaries, rank sensitivity, empty inputs
│   │   ├── services/
│   │   │   └── test_document_processing_service.py  # DocumentProcessingService lifecycle persistence
│   │   ├── test_prompt_builder.py
│   │   ├── test_settings.py
│   │   └── test_utils.py
│   ├── conftest.py                          # Shared pytest fixtures
│   └── fixtures/
│       └── sample.pdf                       # PDF fixture for parser integration tests
│
├── tools/                       # Developer tooling (planned)
│
├── .editorconfig                # Editor formatting rules
├── .env                         # Local environment variables (gitignored)
├── .env.example                 # Environment variable template
├── .gitignore
├── .pre-commit-config.yaml      # Pre-commit hooks (ruff, mypy, pytest)
├── .python-version              # Pinned Python version (for pyenv/uv)
├── .vscode/
│   ├── extensions.json          # Recommended VS Code extensions
│   └── settings.json            # Workspace settings
├── AI_ENGINEERING_AUDIT.md      # Evidence-based AI subsystem audit — several gaps since closed (Structured Output, Validation, Regeneration, Capability Flags, Prompt Integration)
├── alembic.ini                  # Alembic configuration file
├── CHANGELOG.md                 # Version changelog
├── DEV_GUIDE.md                 # Step-by-step local development guide
├── docker-compose.yml           # Local dev stack (PostgreSQL, Valkey, Qdrant, semantic-cache — dedicated redis-stack-server for the L2 Semantic Cache)
├── FILES.md                     # Complete file and folder map
├── LICENSE
├── phase-3-ai-runtime-roadmap.md  # Frozen v2.0 — Retrieval, Context, Generation & Research Runtime roadmap (Phase 3.4–3.12), progress tracked inline — Generation Platform (3.8) now complete, per generation_platform_complexion_prd.md
├── prompt_guardrails.md         # Prompt-injection defense snippet for prompt templates
├── PROJECT_STATUS.md            # Current project status and progress
├── pyproject.toml               # Python project config, deps, and tool settings
├── README.md                    # Project overview and quickstart
├── RESEARCHMIND_PROJECT_CONTEXT_AND_HANDOFF.md  # Project context and engineering handoff (v1.0)
├── ResearchMind-Roadmap-v2.md   # AI Engineering Roadmap v2 — 10-phase vision, frozen tech decisions — AI Runtime Platform (Phase 3) now complete for its Generation slice, per generation_platform_complexion_prd.md
├── ROADMAP.md                   # Feature and milestone roadmap
├── routing_platform_prd.md      # Routing Platform PRD — model/provider selection implemented under generation/routing/ + generation/catalog/
├── runtime_validation_prd.md    # Runtime Validation Platform PRD — the 4th ValidationStage.RUNTIME stage extending the Validation Platform below; RuntimeRegistry/RuntimeValidationService/generic validators/ResearchRuntimeContract implemented under generation/validation/runtime/; planner/reviewer/agent/mcp contracts (§16-19) remain future work
├── SECURITY.md                  # Security policy
├── setup_commands.md            # Makefile-style shortcut commands (docker compose up/down)
├── STRUCTURE.md                 # This file
├── test.txt                     # Stray scratch file — can be deleted
├── uv.lock                      # Locked dependency versions (uv)
└── validation_platform_prd.md   # Standalone Validation Platform PRD — input/output/hallucination/runtime validation, registry, scoring, and ValidationReport implemented under generation/validation/; only the standalone top-level platform promotion (Section 6) and Acceptance/Fail-Fast policy objects (Section 16) remain aspirational
```

## Key Boundaries

| Layer | Location | Purpose |
|---|---|---|
| API app | `apps/api/` | FastAPI server — routes, middleware, models, schemas |
| Frontend | `apps/web/` | Next.js 15 App Router — Cognito auth, dashboard, documents, research |
| Processing pipeline | `apps/api/app/ai/knowledge/processing/` | Docling parser, metadata/statistics enrichment, artifact builder/writer, registry, service |
| Chunking pipeline | `apps/api/app/ai/knowledge/chunking/` | Transforms a `ProcessedDocument` into retrieval-ready `Chunk`s via a registry-based provider strategy (Fixed implemented), builds/persists the canonical `ChunkArtifact` (`chunks.json`) |
| Embedding pipeline | `apps/api/app/ai/knowledge/embeddings/` | Transforms a `ChunkArtifact` into vector `Embedding`s via a registry-based provider strategy (Sentence Transformers, Voyage AI, and OpenAI implemented), builds/persists the canonical `EmbeddingArtifact` (`embeddings.json`) |
| Indexing Platform | `apps/api/app/ai/knowledge/indexing/` | Transforms an `EmbeddingArtifact` + `ChunkArtifact` into dense+sparse `VectorStoreRecord`s (sparse via FastEmbed SPLADE), upserts into Qdrant, builds/persists the canonical `IndexingArtifact` (`indexing.json`) — ADR-018, ADR-019 |
| Vector Store Platform | `apps/api/app/ai/knowledge/vectorstores/` | Provider-independent vector database abstraction; Qdrant is the only implemented provider, using named dense+sparse vectors per point for native hybrid retrieval |
| Retrieval Platform | `apps/api/app/ai/knowledge/retrieval/` | Queries the hybrid Qdrant index: dense search, sparse (SPLADE) search, hybrid search via Reciprocal Rank Fusion (`fusion/`), parallel dense+sparse execution (`asyncio.gather`), and metadata filtering (`owner_id`/`document_id`/`filename`/`language`); query validation/normalization, Voyage/FastEmbed query embedding (cached), `/retrieve`, `/retrieve/sparse`, `/retrieve/hybrid` (all three auth-protected, server-scoped to `owner_id`) — ADR-018, ADR-019, ADR-020, ADR-021. Parent/Child retrieval was reclassified into the Context Platform; query decomposition is deferred to the future Research Runtime |
| Reranking Platform | `apps/api/app/ai/knowledge/reranking/` | Reorders a hybrid candidate pool using deeper (query, chunk) relevance scoring: `VoyageReranker` (Voyage AI `rerank-2`) and `CrossEncoderReranker` (local `BAAI/bge-reranker-base`), behind a shared provider abstraction/registry/service. Wired into `RetrievalService.search_hybrid(rerank=True)` by default — ADR-022 |
| Context Platform | `apps/api/app/ai/knowledge/context/` | Turns a `RetrievalResult` (+ optional `query`) into a `PromptContext`: dedup → Parent Expansion (`ChunkArtifactReader`) → Adjacent Merge → ordering → Compression (Token Budget + Embedding Redundancy + LangChain `ContextualCompressionRetriever`/`LLMChainExtractor` [V3, wired into `build()`'s default pipeline behind `settings.enable_langchain_compression`, flag-gated and query-gated] + per-chunk LLM summarization via the Generation Platform [V4, implemented and registered but not part of the default pipeline]) → Guardrails V1 (`RuleBasedGuardrailProvider`, regex-based prompt-injection detection) → Citation Platform → strategy-based Prompt Formatter (`DEFAULT`/`NOTEBOOKLM`/`PERPLEXITY`/`RESEARCH`/`AGENT`). Complete (Phase 3.7, `context_platform_complexion_prd.md`); not yet wired into a dependency provider or API route |
| Generation Platform | `apps/api/app/ai/runtime/generation/` | Owns all LLM interactions over 5 providers (Groq, OpenAI, Claude, Gemini, Ollama): native structured-output decoding, a parser/repair fallback, input/output/hallucination/runtime Validation Platform integration (registry, weighted scoring, `ValidationReport`, five runtime contracts — Research/Planner/Reviewer/Agent/MCP), a Validation Policy Layer (`AcceptancePolicy`/`FailFastPolicy`/`RuntimeValidationPolicy`), a regenerate-on-invalid-output loop, a Prompt Platform bridge (`generate_from_template()`), a Routing Platform bridge — `generate()`/`stream_generate()` resolve a model via `routing_strategy` when no `provider` is given explicitly — a Runtime Caching Platform bridge, a Streaming Platform bridge, Runtime Metrics Integration (`GenerationMetricsService`), and an Artifact Platform bridge (`generate()` persists a `GenerationArtifact` incl. `metrics.json`). Complete, per `generation_platform_complexion_prd.md` — see `docs/architecture/structured-output-platform.md`; now reachable over HTTP via `POST /api/v1/chat/stream` / `/api/v1/chat/ws` (`/research` still does not exist, blocked on a Research Runtime) |
| Routing Platform | `apps/api/app/ai/runtime/generation/routing/`, `catalog/` | Model/provider selection layer between callers and the Generation Platform: a scored `ModelCatalogRegistry` (12 models, per-task 0-1 scores, cost/context/policy metadata), a `RoutingService` (capability + policy filtering → strategy-weighted scoring → distinct-provider-preferred fallback chain), 15 `RoutingStrategy` values (6 with dedicated task profiles), and structlog-logged `RoutingDecision`s. Implemented — see `docs/architecture/model-routing-platform.md`, ADR-026 |
| Runtime Caching Platform | `apps/api/app/ai/runtime/generation/caching/` | Caches `GenerationResult`s to cut provider cost/latency/duplicate execution: L1 Exact Cache (Valkey, content-hash keyed), L2 Semantic Cache (LangChain `RedisSemanticCache` against a dedicated `redis-stack-server` instance, context-isolated), L3 Session Cache (Valkey, implemented but not yet called by anything), and a `CachePolicyResolver` (AUTO/NEVER/EXACT_ONLY/SEMANTIC/SESSION per `CacheRuntime`). Wired into `GenerationService`. Streaming requests are no longer bypassed (see Streaming Platform row) — Implemented — see `docs/architecture/runtime-caching-platform.md`, ADR-027 |
| Memory Platform | `apps/api/app/ai/memory/` | Provides compact SESSION state, canonical PostgreSQL USER/SEMANTIC/RESEARCH memory, Qdrant search indexing, and bounded context injection for Chat and Research. The original four-memory architecture remains intact; its optimized runtime now short-circuits users with no durable memory, computes one query embedding, searches semantic/research memory concurrently, and fails open per branch. A versioned deterministic extraction policy invokes the LLM only for eligible final user-facing turns. The Generation Usage ledger labels memory-extraction cost separately from answer cost. See `docs/architecture/memory-platform.md` §26 and ADR-029. |
| Chat History Growth Controls | `apps/api/app/services/conversation.py`, `conversation_compaction.py` | Cursor-pagination provides safe canonical conversation/message replay; a persisted deterministic summary plus the newest 12 messages bounds generation history without an extra LLM call. Defaults are page size 50, page maximum 100, and a 4,000-character summary cap. Canonical rows are retained. See ADR-030. |
| Streaming Platform | `apps/api/app/ai/runtime/events/`, `apps/api/app/ai/runtime/generation/streaming/` | Real-time execution infrastructure, two independent layers: a Runtime Event Platform (`events/` — canonical `StreamEvent`, layered so future Research/Agent/Tool runtimes each own their event vocabulary rather than a shared enum) and a Generation Streaming Platform (`generation/streaming/` — `StreamingService`, SSE transport with heartbeat/timeout-ceiling, WebSocket transport). On a Runtime Cache hit, replays the content as a synthetic token stream instead of skipping the streaming contract; on a miss, streams live and stores the assembled result on completion. Wired into `POST /api/v1/chat/stream` / `/api/v1/chat/ws` (`apps/api/app/api/v1/chat.py`), backed by a new minimal `Conversation`/`Message` persistence layer. Implemented (Milestone 2.9.10) — see `docs/architecture/streaming-platform.md`, ADR-028 |
| Guardrails Platform | `apps/api/app/ai/guardrails/` | Standalone, platform-wide policy/safety layer answering "should the system do this?" (Milestone 11.16, `guardrails_platform_prd.md`) — Input (prompt injection/jailbreak, scope, PII), Retrieval (Context Sanitization composing the pre-existing `context/guardrails/`, a new Source Trust Platform, Citation Integrity), Generation (Faithfulness + Schema Enforcement, both reusing Validation Platform validators, PII Leakage), and Runtime (Budget, Loop Detection) guardrails, plus policies/scoring/artifacts. MVP foundation complete and wired directly into `GenerationService` (input gate + full `evaluate()` report on `GenerationResult.guardrails`) and `ContextBuilderService` (retrieval-stage gate) — `guardrail_integration_prd.md` |
| Artifact Platform | `apps/api/app/ai/artifacts/` | Centralized, cross-cutting canonical persistence/replay layer for AI Runtime executions (Milestone 3.10, `artifacts_platform_prd.md`) — immutable, versioned, policy-gated (`ArtifactPolicyService`). Generation artifacts (wired into `GenerationService.generate()`), Streaming artifacts (wired into `StreamingService._stream_live()`), and Conversation artifacts (wired into `chat.py`, one immutable file per turn) are live; Session/Research/Agent/Evaluation artifacts are built and unit-tested but scaffold-only, since no session/research/agent/evaluation runtime exists yet. `replay/` reconstructs a `GenerationResult` or re-emits a stored `StreamEvent` sequence from persisted artifacts |
| Upload pipeline | `apps/api/app/ai/knowledge/upload/` | File validation, duplicate detection, S3 upload, checksum hashing, enqueues async processing job |
| Async worker | `apps/worker/` | Standalone process consuming the queue, running `DocumentProcessingService` per job, retry/dead-letter handling |
| Engineering benchmarks | `benchmarks/` | Offline, manually-run comparison of competing AI implementations (chunking strategies, embedding providers, dense/sparse/hybrid retrieval, reranking, generation providers) against version-controlled datasets — independent from tests and from production infrastructure. Now includes a Generation Benchmark (`generation/`, deterministic no-LLM faithfulness/groundedness/relevance/completeness/citation-accuracy scoring) and threshold-based Regression Detection (`regression/`, wired into `runner.py` via `--check-regression`) — see `evaluation_platform_prd.md` / PROJECT_STATUS.md's "Evaluation Platform PRD Reconciliation" for why this, not a new `app/ai/evaluation/`, is where Evaluation Platform work landed |
| Infrastructure | `apps/api/app/infrastructure/` | S3 storage, SHA-256 hashing, metrics adapters, queue abstraction (Valkey/SQS-backed) |
| Composition roots | `apps/api/app/bootstrap/` | Builds shared object graphs (e.g. the worker) used by multiple entry points |
| Application services | `apps/api/app/services/` | Auth, user lifecycle, document processing orchestration, queued-job processing |
| Agents | `agents/` | Autonomous AI agents (planned) |
| Services | `services/` | Internal service modules — retrieval, ingestion, etc. (planned) |
| Shared | `shared/` | Cross-cutting code shared by apps and services (planned) |
| Infrastructure IaC | `infrastructure/` | Docker, deployment configs (planned) |
| Migrations | `alembic/` | PostgreSQL schema migrations via Alembic |
| Tests | `tests/` | Unit, integration, e2e, evaluation, performance |
| Docs | `docs/` | All project documentation |

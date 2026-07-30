# Graph Report - apps  (2026-07-30)

## Corpus Check
- Large corpus: 854 files · ~174,667 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 5994 nodes · 14031 edges · 338 communities (314 shown, 24 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 397 edges (avg confidence: 0.53)
- Token cost: 55,886 input · 0 output

## Community Hubs (Navigation)
- Knowledge Artifact Builders & Writers
- Duplicate Detection
- Chunk Artifact Models
- Chunking Strategies & Config
- Document Processing Core
- Chat Web Search & Research Evidence
- Context Compression
- Generation Interfaces & Errors
- Research Orchestration
- Reranking Providers
- Research Events & Checkpointing
- Paper Search Caching
- Processing Queue Infra
- Research Artifacts & Evidence
- Indexing Artifacts
- Metadata Providers
- Vector Store Registry
- Web Search Tool Platform
- Conversation & Memory Composition
- Research Runtime Contracts
- Context Artifacts & Parent Expansion
- Chat Paper Query Extraction
- Context Builders
- Input Guardrails
- Research Runtime (Core)
- Runtime Validation Contracts
- Embedding Models
- Generation Caching
- Auth Providers
- Web UI Components
- Service Dependency Wiring
- Retrieval Providers
- Embedding Configs
- Memory & Query Embedding Composition
- Research Planner Scheduling
- LangSmith Observability Provider
- Retrieval Statistics & Reports
- Runtime Caching Platform
- Validation Policies
- Research API Endpoints
- Generation Errors
- Processing Statistics Providers
- Metrics Recorder
- Web App Package Config
- Deep Research UI Components
- Generation Enums
- Conversation Artifact Writers
- Research Outcomes & Routing
- Output Validation Rules
- Repositories Core
- Conversation Artifact Readers
- Conversation & Message Services
- Memory Artifact Builders
- Artifact Retention Policy
- Observability Runtime Models
- Web API Client & Document Types
- Agent Artifacts (Scaffold)
- Retrieval Errors
- Documents UI Components
- Input Validation Registry
- Runtime Validator Registry
- Chat UI Page
- Upload Pipeline Init
- Embedding Cache Composition
- Vector Store Base Provider
- Guardrail Artifacts
- Rate Limit Guardrail
- Vector Store Record Model
- Usage Reporting API
- Retrieval Service Composition
- Memory Extraction Orchestrator
- Research Escalation & Rate Limits
- Research Repository
- Memory Type Enums
- SQLAlchemy Base Models
- Research Feed Page
- Context Guardrails
- App Exceptions Base
- Budget Guardrail
- Query Embedding Cache
- Semantic Cache Provider
- Sparse Embedding & Retrieval Registry
- Research Run Dispatch Repository
- Web TS Config
- Streaming Cache Models
- User Memory Profile Service
- Generation Provider Base
- Research Runtime Graph (LangGraph)
- Guardrail Risk Scoring
- Memory Service Backend
- Research Report Download Service
- Guardrail Fail Policy
- Embedding Cache Keys & Chunk Artifact
- Prometheus Observability Composition
- Input Validator Interface
- Web App Shell & Auth Callback
- Research Markdown & Citations UI
- Session Artifacts (Scaffold)
- Guardrail Artifact Builder
- Embedding Artifact Builder
- Streaming Artifact Models
- FastEmbed Sparse Provider
- Retrieval Config Models
- Upload Validation
- Documents Schema & API
- File Hashing
- User Repository
- Research Replay Service (Scaffold)
- Indexing Errors
- Streaming Serializer Interface
- Memory API Endpoints
- CORS Middleware
- Prompt Templates (Chat/Research/Summary)
- Knowledge Embeddings
- Knowledge Processing
- Repositories
- Runtime Chat
- Generation Prompts
- Artifacts Generation
- Knowledge Embeddings
- Knowledge Vectorstores
- Generation Observability
- V1
- Components Landing
- Artifacts Evaluation
- Runtime Events
- Generation Prompts
- Routing Strategies
- Tools Paper Search
- Artifacts Observability
- Generation Observability
- Generation Prompts
- Core
- Infrastructure AWS
- Worker
- AI Artifacts
- Guardrails Trust
- Knowledge Retrieval
- Runtime Research
- Providers Helpers
- Schemas
- Observability Prometheus
- Runtime Events
- Generation Catalog
- Generation Providers
- Generation Structured Output
- Runtime Contracts
- Core
- Artifacts Conversation
- Artifacts Streaming
- Knowledge Embeddings
- Generation Providers
- Generation Streaming
- Generation Structured Output
- Guardrails Generation
- Knowledge Embeddings
- Observability Metrics
- Generation Langchain
- Generation Prompts
- Guardrails Retrieval
- Knowledge Upload
- Generation Catalog
- Generation Routing
- Routing Scoring
- Generation Routing
- Generation Structured Output
- Structured Output Schemas
- Retrieval Fusion
- AI Memory
- Generation Providers
- Features Dashboard
- Artifacts Replay
- Guardrails Runtime
- Observability Prometheus
- Generation Policies
- Routing Scoring
- Services
- App Root
- Guardrails Trust
- Cache Query Embeddings
- Generation Prompts
- Core
- Memory Retrieval
- Generation Caching
- Generation Prompts
- Generation Routing
- Generation Streaming
- Validation Input
- Infrastructure Queue
- App Root
- AI Config
- Knowledge Retrieval
- Observability Metrics
- Events Agent
- Events Tool
- Structured Output Schemas
- Structured Output Schemas
- Runtime Research
- DB
- Worker
- Knowledge Embeddings
- Knowledge Processing
- Retrieval Fusion
- Events Provider
- Structured Output Parsers
- Structured Output Parsers
- Structured Output Parsers
- Structured Output Parsers
- AI Artifacts
- Processing Adapters
- Metadata Providers
- Knowledge Upload
- AI Memory
- Memory Policy
- Memory Retrieval
- Research Reporting
- Middleware
- App Root
- App Root
- App Root
- App Root

## God Nodes (most connected - your core abstractions)
1. `GenerationResult` - 151 edges
2. `GenerationRequest` - 150 edges
3. `User` - 69 edges
4. `ContextChunk` - 59 edges
5. `ProcessedDocument` - 57 edges
6. `GenerationService` - 57 edges
7. `MemoryService` - 55 edges
8. `ValidatorOutcome` - 55 edges
9. `ResearchRun` - 55 edges
10. `GuardrailIssue` - 54 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `create_research_runtime_worker()`  [INFERRED]
  worker/research_runtime_main.py → api/app/bootstrap/worker.py
- `main()` --calls--> `create_processing_worker()`  [INFERRED]
  worker/main.py → api/app/bootstrap/worker.py
- `ProcessingWorker` --uses--> `QueuedDocumentProcessingService`  [INFERRED]
  worker/processing_worker.py → api/app/services/queued_document_processing_service.py
- `create_processing_worker()` --references--> `ProcessingWorker`  [EXTRACTED]
  api/app/bootstrap/worker.py → worker/processing_worker.py
- `create_research_runtime_worker()` --references--> `ResearchRuntimeWorker`  [EXTRACTED]
  api/app/bootstrap/worker.py → worker/research_runtime_worker.py

## Import Cycles
- 3-file cycle: `api/app/db/base.py -> api/app/models/__init__.py -> api/app/models/user.py -> api/app/db/base.py`
- 3-file cycle: `api/app/db/base.py -> api/app/models/__init__.py -> api/app/models/generation_usage.py -> api/app/db/base.py`
- 3-file cycle: `api/app/db/base.py -> api/app/models/__init__.py -> api/app/models/document.py -> api/app/db/base.py`
- 3-file cycle: `api/app/db/base.py -> api/app/models/__init__.py -> api/app/models/research_run_dispatch.py -> api/app/db/base.py`
- 3-file cycle: `api/app/db/base.py -> api/app/models/__init__.py -> api/app/models/research_run_event.py -> api/app/db/base.py`
- 3-file cycle: `api/app/db/base.py -> api/app/models/__init__.py -> api/app/models/conversation.py -> api/app/db/base.py`
- 3-file cycle: `api/app/db/base.py -> api/app/models/__init__.py -> api/app/models/memory.py -> api/app/db/base.py`
- 3-file cycle: `api/app/db/base.py -> api/app/models/__init__.py -> api/app/models/research.py -> api/app/db/base.py`
- 3-file cycle: `api/app/db/base.py -> api/app/models/__init__.py -> api/app/models/research_proposal.py -> api/app/db/base.py`
- 3-file cycle: `api/app/db/base.py -> api/app/models/__init__.py -> api/app/models/research_run.py -> api/app/db/base.py`

## Hyperedges (group relationships)
- **RAG Context Injection Pattern ({context} placeholder across templates)** — apps_api_app_ai_runtime_generation_prompts_templates_chat_v1_prompt_template, apps_api_app_ai_runtime_generation_prompts_templates_chat_v2_prompt_template, apps_api_app_ai_runtime_generation_prompts_templates_chat_v3_prompt_template, apps_api_app_ai_runtime_generation_prompts_templates_research_v1_prompt_template, apps_api_app_ai_runtime_generation_prompts_templates_research_v2_prompt_template [INFERRED 0.85]
- **Few-Shot Enabled Template Configs** — apps_api_app_ai_runtime_generation_prompts_templates_chat_v2_metadata_config, apps_api_app_ai_runtime_generation_prompts_templates_chat_v3_metadata_config, apps_api_app_ai_runtime_generation_prompts_templates_research_v2_metadata_config, apps_api_app_ai_runtime_generation_prompts_templates_summary_v2_metadata_config [INFERRED 0.75]

## Communities (338 total, 24 thin omitted)

### Community 0 - "Knowledge Artifact Builders & Writers"
Cohesion: 0.04
Nodes (95): ChunkArtifactBuilder, Builds the canonical ChunkArtifact., ChunkArtifactWriter, Persists chunk artifacts., EmbeddingArtifactBuilder, Builds the canonical EmbeddingArtifact., EmbeddingArtifactWriter, Persists embedding artifacts. (+87 more)

### Community 1 - "Duplicate Detection"
Cohesion: 0.03
Nodes (77): DuplicateDetectionError, DuplicateHashingError, Exception, Exceptions raised by the duplicate detection module., Raised when a file hash cannot be computed., Base exception for duplicate detection., DuplicateDetector, ABC (+69 more)

### Community 2 - "Chunk Artifact Models"
Cohesion: 0.04
Nodes (66): Chunk artifact builder. Builds the canonical ChunkArtifact from a collection of…, Build a ChunkArtifact from generated chunks. Args: chunks: Generated chunks for…, ChunkArtifactDocument, ChunkArtifactEvaluation, ChunkArtifactStatistics, ChunkArtifactStrategy, BaseModel, Canonical chunk artifact models. A ChunkArtifact represents a complete chunking… (+58 more)

### Community 3 - "Chunking Strategies & Config"
Cohesion: 0.03
Nodes (66): BaseChunkingConfig, FixedChunkingConfig, HierarchicalChunkingConfig, MarkdownChunkingConfig, BaseModel, model_validator, Chunking configuration models. These configuration models define the behavior…, Configuration for the Hierarchical (Parent/Child) Chunking provider. Documents… (+58 more)

### Community 4 - "Document Processing Core"
Cohesion: 0.04
Nodes (65): DocumentFormat, ParserType, ProcessingStage, ProcessingStatus, StrEnum, Processing domain enumerations. These enums define the lifecycle and supported…, Lifecycle status of a document processing job., Supported parser implementations. These values identify parser implementations… (+57 more)

### Community 5 - "Chat Web Search & Research Evidence"
Cohesion: 0.05
Nodes (68): ChatWebSearchOutcome, ChatWebSource, _format_web_context(), BaseModel, Toggle-gated, no-approval web search for one Chat turn. Reuses the same…, Lightweight source descriptor for the frontend -- deliberately not the full…, BaseModel, Immutable, compact evidence artifact persistence through the Artifact Platform. (+60 more)

### Community 6 - "Context Compression"
Cohesion: 0.05
Nodes (44): create_compression_service(), CompressionService, CompressionStrategy, StrEnum, CompressionError, CompressionProviderError, CompressionTimeoutError, Exception (+36 more)

### Community 7 - "Generation Interfaces & Errors"
Cohesion: 0.05
Nodes (45): GenerationValidationError, Default implementation. Providers with native structured output support should…, Standard text generation., GenerationRequest, GenerationResult, model_validator, GenerationExecutionContext, BaseModel (+37 more)

### Community 8 - "Research Orchestration"
Cohesion: 0.06
Nodes (39): create_prompt_formatter_service(), PromptFormatStrategy, StrEnum, PromptFormatterProvider, ABC, PromptFormattingResult, BaseModel, AgentFormatterProvider (+31 more)

### Community 9 - "Reranking Providers"
Cohesion: 0.06
Nodes (47): BaseRerankingProvider, ABC, Base reranking provider., CrossEncoderConfig, BaseModel, Reranking configuration models., VoyageRerankerConfig, create_reranking_registry() (+39 more)

### Community 10 - "Research Events & Checkpointing"
Cohesion: 0.05
Nodes (48): StrEnum, Reserved for the future Research Runtime. Nothing in the Streaming Platform…, ResearchEventType, postgres_checkpoint_url(), postgres_checkpointer(), provision_postgres_checkpoints(), Postgres checkpoint construction; not wired to application startup yet., Translate SQLAlchemy async URLs to the psycopg URL expected by LangGraph. (+40 more)

### Community 11 - "Paper Search Caching"
Cohesion: 0.06
Nodes (44): create_paper_search_cache(), Paper search cache composition root (mirrors…, Return a NullPaperSearchCache (fully disabling caching) when…, PaperSearchCache, ABC, Paper search result cache interface (mirrors…, Return a cached result, or None on a miss., build_paper_search_cache_key() (+36 more)

### Community 12 - "Processing Queue Infra"
Cohesion: 0.05
Nodes (50): _get_processing_queue(), Return the configured processing queue., Create the configured processing queue. The queue implementation is selected…, Exception, QueueAcknowledgeError, QueueConnectionError, QueueDequeueError, QueueEnqueueError (+42 more)

### Community 13 - "Research Artifacts & Evidence"
Cohesion: 0.05
Nodes (58): BaseModel, Serializes `payload` to indented, `None`-stripped JSON and uploads it to `key`.…, write_json_artifact(), BaseModel, Citation-safe synthesis input: references/excerpts only, no raw contexts., ResearchEvidenceBundle, BaseModel, UUID (+50 more)

### Community 14 - "Indexing Artifacts"
Cohesion: 0.06
Nodes (53): Indexing Artifact Builder. Transforms canonical indexing models into immutable…, Build an IndexingArtifact. Parameters ---------- execution Execution metadata…, IndexingArtifact, IndexingArtifactExecution, BaseModel, Canonical Indexing Artifact models. The Indexing Artifact records the outcome…, Execution metadata for an indexing operation., Artifact describing a completed vector indexing operation. (+45 more)

### Community 15 - "Metadata Providers"
Cohesion: 0.04
Nodes (44): BaseMetadataProvider, ABC, Base implementation for metadata providers. Concrete metadata providers should…, Base class for metadata providers. Provides a common inheritance point for all…, MetadataProvider, ABC, Path, Interfaces for the metadata enrichment platform. Metadata providers enrich the… (+36 more)

### Community 16 - "Vector Store Registry"
Cohesion: 0.04
Nodes (42): create_vectorstore_registry(), Vector Store Platform composition root. Assembles the Vector Store Platform by…, Create a fully configured VectorStoreRegistry. This is the single place where…, StrEnum, Vector Store Platform enumerations. These enums define the canonical concepts…, Supported vector store providers. The provider identifies the implementation…, Supported vector store operations. Used for runtime metrics, artifact…, VectorOperation (+34 more)

### Community 17 - "Web Search Tool Platform"
Cohesion: 0.06
Nodes (42): Web Search Tool Platform composition root. Registers Tavily only when…, StrEnum, Canonical enums for the Web Search Tool Platform…, WebSearchDepth, Exception, Canonical Web Search Tool Platform exceptions. Providers must translate…, Base error for the Web Search Tool Platform., A configured provider call failed (network, auth, malformed payload). (+34 more)

### Community 18 - "Conversation & Memory Composition"
Cohesion: 0.06
Nodes (62): ConversationTurnArtifactBuilder, build_memory_extraction_service(), build_session_state_updater_service(), _cheap_memory_providers(), GenerationProvider, Prefer inexpensive structured-output providers for background memory work --…, UUID, Best-effort: any failure here degrades to "no web search for this turn", never… (+54 more)

### Community 19 - "Research Runtime Contracts"
Cohesion: 0.10
Nodes (60): StrEnum, Minimal, framework-independent contracts for the Research Runtime., Durable outbox state; distinct from the public run lifecycle., ResearchProposalStatus, ResearchRunDispatchStatus, ResearchRunStatus, ResearchRuntimeStatus, create_research_proposal() (+52 more)

### Community 20 - "Context Artifacts & Parent Expansion"
Cohesion: 0.06
Nodes (48): create_chunk_artifact_reader(), ChunkArtifactReader, Reads chunk artifacts from storage., ParentExpansionService, Parent context expansion. Transforms retrieved child chunks into richer context…, Expands retrieved chunks using parent chunks., create_context_builder(), create_parent_expansion_service() (+40 more)

### Community 21 - "Chat Paper Query Extraction"
Cohesion: 0.06
Nodes (39): create_paper_query_extraction_service(), PaperQueryExtractionResult, BaseModel, UUID, Lightweight query extraction for paper search. Distills a Chat turn's raw…, Best-effort: any failure falls back to the raw (truncated) prompt, never raises…, BaseGenerationConfig, ClaudeGenerationConfig (+31 more)

### Community 22 - "Context Builders"
Cohesion: 0.05
Nodes (34): GuardrailBlockedError, GuardrailError, GuardrailPolicyError, GuardrailProviderNotFoundError, Exception, Guardrails exceptions., Raised when a registry lookup finds no provider/check registered., Raised when a policy configuration is invalid. (+26 more)

### Community 23 - "Input Guardrails"
Cohesion: 0.05
Nodes (30): GuardrailArtifactWriter, BaseModel, Persists guardrail artifacts., Persist a guardrail artifact. Storage layout (PRD §16): guardrails/ {run_id}/…, create_guardrail_artifact_writer(), create_guardrail_registry(), GuardrailRegistry, FaithfulnessGuardrail (+22 more)

### Community 24 - "Research Runtime (Core)"
Cohesion: 0.07
Nodes (35): ContextBuilderInterface, _format_entries(), format_memory_context(), Shared prompt-injection helpers (Runtime Memory Injection Pipeline) -- used by…, GenerationRuntimeInterface, Canonical contract for the Generation Runtime Platform's single entrypoint (PRD…, RuntimeError, Classified Research Runtime execution failures, distinct from generic errors. (+27 more)

### Community 25 - "Runtime Validation Contracts"
Cohesion: 0.06
Nodes (23): ConsistencyValidator, Checks `GenerationResult.parsed_output` for invalid cross-references between…, AgentRuntimeContract, Agent Runtime Contract — requires a non-empty `reasoning` field, a…, BaseRuntimeContract, Shared plumbing for runtime contracts (PRD §15-§19): runs the generic runtime…, The generic runtime validators (PRD §14) this contract composes., MCPRuntimeContract (+15 more)

### Community 26 - "Embedding Models"
Cohesion: 0.07
Nodes (37): Embedding cache key derivation. The cache key is derived from the chunk text…, Query embedding cache key generation., Canonical embedding artifact models. An EmbeddingArtifact represents a complete…, Base embedding provider. Provides common functionality shared by all embedding…, EmbeddingProvider, StrEnum, Embedding domain enumerations. These enums define the supported embedding…, Supported embedding providers. The provider identifies the implementation… (+29 more)

### Community 27 - "Generation Caching"
Cohesion: 0.06
Nodes (27): build_exact_cache_key(), hash_context(), hash_prompt(), hash_schema(), GenerationProvider, Hashes the fully-rendered `PromptContext.context` string. Used both as part of…, NullExactCacheProvider, No-op provider, used when `settings.exact_cache_enabled` is `False`. (+19 more)

### Community 28 - "Auth Providers"
Cohesion: 0.05
Nodes (29): authenticate_token(), get_current_user(), get_jwt_verifier(), AsyncSession, Verifies a bearer token and returns the synced ResearchMind user. Shared by…, Authenticate the current request and return the authenticated ResearchMind user., JWTVerifier, Any (+21 more)

### Community 29 - "Web UI Components"
Cohesion: 0.07
Nodes (37): FEATURES, Drawer(), ActivityIcon(), base, ChevronRightIcon(), CloseIcon(), CpuIcon(), DatabaseIcon() (+29 more)

### Community 30 - "Service Dependency Wiring"
Cohesion: 0.07
Nodes (41): get_artifact_policy_service(), get_guardrail_service(), get_observability_service(), Observability Platform composition root., get_metrics_recorder(), Returns the application-wide `MetricsRecorder`. `NoOpMetricsRecorder` when…, get_event_adapter(), Return the singleton StreamChunk -> StreamEvent adapter. One adapter serves… (+33 more)

### Community 31 - "Retrieval Providers"
Cohesion: 0.07
Nodes (32): ABC, BaseRetrievalProvider, ABC, Base Retrieval Provider. Provides common functionality shared by all retrieval…, Base class for retrieval providers. Shared responsibilities: - provider…, Provider implementation version., Stable fingerprint uniquely identifying the provider configuration. Useful for:…, Fuse dense, sparse, and optional metadata-filtered retrieval results. (+24 more)

### Community 32 - "Embedding Configs"
Cohesion: 0.06
Nodes (38): BaseEmbeddingConfig, OpenAIEmbeddingConfig, BaseModel, Embedding configuration models. These configuration models define the behavior…, Base configuration shared by all embedding providers., Configuration for the Sentence Transformers provider., Configuration for the Voyage AI embedding provider., Configuration for the OpenAI embedding provider. (+30 more)

### Community 33 - "Memory & Query Embedding Composition"
Cohesion: 0.09
Nodes (43): create_query_embedding_service(), Create dense query embedding service., QueryEmbeddingService, Generates embeddings for retrieval queries., MemoryArtifactWriter, build_memory_service(), create_memory_artifact_writer(), create_memory_availability_client() (+35 more)

### Community 34 - "Research Planner Scheduling"
Cohesion: 0.07
Nodes (37): Plan validation and deterministic dependency-wave scheduling., dependency_waves(), Deterministic, dependency-aware task wave calculation without side effects., Return topological waves, ordered stably for reproducible graph fan-out. A task…, ValueError, Fail-fast validation for the planner's bounded execution DAG., A plan defect that must prevent retrieval from starting., Validate the full DAG rather than trusting a structured-model response. (+29 more)

### Community 35 - "LangSmith Observability Provider"
Cohesion: 0.07
Nodes (28): AbstractContextManager, get_langsmith_client(), LangSmith client factory (AI Runtime Observability PRD §11). LangSmith owns…, Lazily imports and constructs a `langsmith.Client`. Returns `None` (not…, create_langsmith_metrics_recorder(), create_runtime_tracer(), _langsmith_enabled(), LangSmith provider composition root. (+20 more)

### Community 36 - "Retrieval Statistics & Reports"
Cohesion: 0.08
Nodes (37): BaseModel, RetrievalMetricsSnapshot, _fmt_count(), _fmt_ms(), Retrieval Report builder (AI Runtime Observability PRD §7 "Retrieval Report").…, RetrievalReportBuilder, _fmt(), _fmt_pct() (+29 more)

### Community 37 - "Runtime Caching Platform"
Cohesion: 0.07
Nodes (23): build_runtime_cache_profiles(), create_exact_cache_provider(), create_session_cache_provider(), Redis, Runtime Caching Platform composition root. Assembles L1/L2/L3 providers and the…, CacheLevel, CachePolicy, CacheRuntime (+15 more)

### Community 38 - "Validation Policies"
Cohesion: 0.08
Nodes (26): FailFastPolicy, BaseModel, Decides whether an input-stage `ValidationResult` should stop generation before…, BaseModel, Decides whether a failed runtime-stage `ValidationResult` (a…, RuntimeValidationPolicy, aggregate_outcomes(), crash_outcome() (+18 more)

### Community 39 - "Research API Endpoints"
Cohesion: 0.09
Nodes (44): ResearchWebSearchInspectionService, approve_research_proposal(), cancel_research_run(), _check_deep_research_approval_rate_limit(), get_research(), get_research_conversation(), get_research_conversation_cost(), get_research_report_download() (+36 more)

### Community 40 - "Generation Errors"
Cohesion: 0.05
Nodes (20): GenerationError, GenerationProviderNotFoundError, GuardrailViolationError, OutputValidationError, PromptValidationError, Exception, GenerationProviderInterface, ABC (+12 more)

### Community 41 - "Processing Statistics Providers"
Cohesion: 0.06
Nodes (28): BaseStatisticsProvider, ABC, Base implementation for statistics providers. Concrete statistics providers…, Base class for statistics providers. Provides a common inheritance point for…, ABC, Path, Interfaces for the statistics enrichment platform. Statistics providers enrich…, Contract implemented by every statistics provider. (+20 more)

### Community 42 - "Metrics Recorder"
Cohesion: 0.05
Nodes (19): Structured-log metrics until the shared Prometheus backend is introduced., Emit stable metric events without adding a memory-specific backend. The…, StructuredMemoryMetricsRecorder, EmbeddingProvider, MemoryVectorIndex, PostgresMemoryStore, PostgresMemoryStore, Redis (+11 more)

### Community 43 - "Web App Package Config"
Cohesion: 0.05
Nodes (43): autoprefixer, eslint, eslint-config-next, framer-motion, next, postcss, react, react-dom (+35 more)

### Community 44 - "Deep Research UI Components"
Cohesion: 0.09
Nodes (35): TargetIcon(), BUDGET_HINT, DeepResearchBlock(), STATUS_LABEL, DraftReview(), PlanGoalReview(), renderAnswer(), ResearchBlock() (+27 more)

### Community 45 - "Generation Enums"
Cohesion: 0.11
Nodes (24): GenerationOperation, GenerationProvider, PromptStrategy, StrEnum, ResponseFormat, GenerationExecutionError, LangChain-backed structured output generation. Uses each provider's LangChain…, ModelMetadata (+16 more)

### Community 46 - "Conversation Artifact Writers"
Cohesion: 0.09
Nodes (31): ConversationIdentity, Written once as `conversation.json` -- mirrors the `Conversation` row., ConversationArtifactWriter, Conversation artifact writer., Writes `conversation.json` exactly once. Guarded by an `exists()` check on top…, create_artifact_storage(), create_conversation_artifact_writer(), create_generation_artifact_writer() (+23 more)

### Community 47 - "Research Outcomes & Routing"
Cohesion: 0.16
Nodes (20): Result of a completed (non-streaming) research run. Bundles everything…, ResearchOutcome, Task-oriented routing objectives. Callers (agents, planners, runtime services)…, RoutingStrategy, Raised when a run exceeds its bounded duration or cost policy., ResearchRunBudgetExceededError, Any, Exception (+12 more)

### Community 48 - "Output Validation Rules"
Cohesion: 0.14
Nodes (11): What a single validator returns from `validate()`. `score` is optional — most…, ValidationIssue, ValidationSeverity, ValidatorOutcome, FormattingValidator, Checks `GenerationResult.content` is well-formed for the response format that…, get_field(), get_list_field() (+3 more)

### Community 49 - "Repositories Core"
Cohesion: 0.07
Nodes (22): ConversationRepository, AsyncSession, datetime, UUID, Return one newest-first cursor page, presented oldest first., Repository responsible for Conversation/Message persistence. This class…, Load uncompacted messages oldest first; used only for compaction., Return the question that started a conversation. (+14 more)

### Community 50 - "Conversation Artifact Readers"
Cohesion: 0.07
Nodes (28): ConversationArtifactReader, UUID, Conversation artifact reader -- reconstructs conversation history from…, Enumerates every persisted turn via `storage.list_keys()` (no mutable index…, ArtifactError, ArtifactNotFoundError, ArtifactReadError, ArtifactWriteError (+20 more)

### Community 51 - "Conversation & Message Services"
Cohesion: 0.09
Nodes (25): Conversation, Message, A chat conversation owned by a ResearchMind user. Holds no messages itself --…, A single turn (user prompt or assistant reply) within a Conversation., ConversationPage, ConversationService, MessagePage, PersistedConversationTurn (+17 more)

### Community 52 - "Memory Artifact Builders"
Cohesion: 0.11
Nodes (23): MemoryArtifactBuilder, UUID, Memory artifact builders. Pure -- no knowledge of storage., MemoryContextArtifact, MemorySearchArtifact, BaseModel, Canonical memory artifact models (PRD §22). Serialized to S3 under:…, Memory artifact writer. Persists memory artifacts using the application's… (+15 more)

### Community 53 - "Artifact Retention Policy"
Cohesion: 0.13
Nodes (23): ArtifactCategory, ArtifactPolicy, ArtifactRuntime, StrEnum, Which kind of artifact is being persisted -- mirrors the S3 prefixes in PRD §12…, Which runtime is issuing the execution being considered for persistence, for…, How long a category of artifact should be retained (PRD §8). `NEVER` means "do…, ArtifactPolicyRule (+15 more)

### Community 54 - "Observability Runtime Models"
Cohesion: 0.08
Nodes (20): ArtifactMetric, PipelineRuntimeMetrics, BaseModel, Size information for a generated artifact., Canonical runtime metrics for an entire processing pipeline execution., Runtime metrics collected for a single pipeline stage., RuntimeStageMetric, Collects runtime metrics for a processing pipeline. (+12 more)

### Community 55 - "Web API Client & Document Types"
Cohesion: 0.08
Nodes (34): ADR-0028, ChatConversationListResponse, ChatConversationResponse, ChatConversationSummaryResponse, ChatMessageResponse, ChatStreamOptions, DeepResearchDraftCitation, DeepResearchDraftFinding (+26 more)

### Community 56 - "Agent Artifacts (Scaffold)"
Cohesion: 0.10
Nodes (24): AgentArtifactBuilder, Any, UUID, Agent artifact builder -- scaffold-only, see `models.py` docstring., AgentArtifact, AgentArtifactMetadata, BaseModel, Agent artifact models (PRD §18) -- scaffold-only. No runtime emits or consumes… (+16 more)

### Community 57 - "Retrieval Errors"
Cohesion: 0.08
Nodes (24): Supported retrieval providers., RetrievalProvider, Exception, Retrieval Platform exceptions., Raised when a provider cannot be resolved., Raised when retrieval inputs are invalid., Raised when retrieval execution fails., Base retrieval exception. (+16 more)

### Community 58 - "Documents UI Components"
Cohesion: 0.11
Nodes (27): Badge(), BadgeTone, Pill(), TONE_STYLES, EmptyState(), formatDate(), RecentUploads(), STATUS_TONE (+19 more)

### Community 59 - "Input Validation Registry"
Cohesion: 0.08
Nodes (15): create_validation_registry(), get_validation_service(), ContextValidator, Data-quality checks on `request.prompt_context` — empty chunks, duplicate…, ProviderLimitsValidator, Checks the request against what the resolved provider's `ProviderCapabilities`…, 1 token ≈ 0.75 words — matches `TokenCounter._count_approximate`., Checks the estimated prompt size against the resolved provider's context… (+7 more)

### Community 60 - "Runtime Validator Registry"
Cohesion: 0.08
Nodes (12): The underlying per-`RuntimeType` registry (PRD §8) — used by…, StrEnum, Which runtime is consuming a `GenerationResult` — resolved from…, RuntimeType, ABC, A single, reusable runtime-stage check (PRD §9) — e.g. completeness,…, Defines what constitutes a valid output for one `RuntimeType` (PRD §8) — e.g.…, RuntimeContractInterface (+4 more)

### Community 61 - "Chat UI Page"
Cohesion: 0.09
Nodes (26): ChatPage(), AlertIcon(), BookIcon(), MessageIcon(), ChatComposer(), ChatSidebar(), formatWhen(), EmptyChat() (+18 more)

### Community 62 - "Upload Pipeline Init"
Cohesion: 0.07
Nodes (12): DocumentStorage, ABC, BinaryIO, Return whether a document exists., Generate a temporary download URL., Abstract interface for document storage providers., Amazon S3 document storage., S3StorageService (+4 more)

### Community 63 - "Embedding Cache Composition"
Cohesion: 0.09
Nodes (21): create_embedding_cache(), Embedding cache composition root. Selects and constructs the configured…, Create the configured EmbeddingCache. Returns a NullEmbeddingCache (fully…, EmbeddingCache, ABC, Embedding cache interface. The Embedding Cache sits between the…, Base interface for embedding cache backends., Resolve cached vectors for the given cache keys. Args: keys: Cache keys to look… (+13 more)

### Community 64 - "Vector Store Base Provider"
Cohesion: 0.09
Nodes (27): BaseVectorStoreProvider, ABC, ConfigT, Base Vector Store provider. Provides common functionality shared by all vector…, Base class for all vector store providers. Responsibilities: - provider…, Version of the provider implementation., Provider configuration., Stable fingerprint representing the provider configuration. Used for… (+19 more)

### Community 65 - "Guardrail Artifacts"
Cohesion: 0.23
Nodes (12): Canonical guardrail artifact models. A GuardrailArtifact represents a complete…, Guardrail artifact writer. Persists guardrail artifacts using the application's…, GuardrailAction, GuardrailCategory, GuardrailSeverity, StrEnum, GuardrailIssue, GuardrailResult (+4 more)

### Community 66 - "Rate Limit Guardrail"
Cohesion: 0.08
Nodes (13): RateLimitGuardrail, Foundation only (PRD §8/§21) -- no request-counting state exists anywhere in…, GenerationGuardrailInterface, InputGuardrailInterface, ABC, A single input-stage guardrail check, run before retrieval/generation. Should…, A single retrieval-stage guardrail check, run over retrieved chunks., A single generation-stage guardrail check, run over a completed result. (+5 more)

### Community 67 - "Vector Store Record Model"
Cohesion: 0.08
Nodes (20): Supported vector similarity metrics. The Embedding Platform recommends which…, VectorDistanceMetric, Index vector records into a collection. Existing vectors should be replaced if…, Canonical vector record. Represents one vector ready to be indexed into a…, VectorStoreRecord, QdrantVectorStoreProvider, Determine whether a collection exists., Convert the canonical distance metric into the corresponding Qdrant distance… (+12 more)

### Community 68 - "Usage Reporting API"
Cohesion: 0.10
Nodes (20): generation_usage_summary(), get, Authenticated generation-usage reporting endpoints., get_generation_usage_repository(), AsyncSession, Request-scoped dependencies for generation usage reporting., GenerationUsageRepository, AsyncSession (+12 more)

### Community 69 - "Retrieval Service Composition"
Cohesion: 0.14
Nodes (28): create_retrieval_service(), Create a fully configured RetrievalService., Orchestrates retrieval execution., RetrievalService, post, Sparse retrieval using SPLADE., Hybrid retrieval using: Dense Search + Sparse Search ↓ Reciprocal Rank Fusion…, Scope retrieval filters to the authenticated user. owner_id is always… (+20 more)

### Community 70 - "Memory Extraction Orchestrator"
Cohesion: 0.12
Nodes (19): MemoryExtractionOrchestrator, Redis, Shared post-turn memory processing for Chat and Research., Memory Platform metric names (PRD §22). `*_LATENCY` values are…, Redis, UUID, Cheap, privacy-scoped promotion of repeated research-topic engagement., Return a small ordered set of meaningful lexical topic candidates. (+11 more)

### Community 71 - "Research Escalation & Rate Limits"
Cohesion: 0.09
Nodes (27): _check_deep_research_proposal_rate_limit(), _check_linear_research_rate_limit(), check_research_escalation(), create_research(), _escalation_reason(), StreamingResponse, Deterministic, user-safe justification derived from the plan's own fields --…, Shared by `/research`, `/research/stream`, `/research/citations` -- one bucket… (+19 more)

### Community 72 - "Research Repository"
Cohesion: 0.09
Nodes (19): get_research_repository(), Return a request-scoped ResearchRepository bound to this request's database…, A continuing research thread, owned by a ResearchMind user -- groups multiple…, ResearchConversation, AsyncSession, UUID, Most recently updated `limit` conversations for `owner_id`, newest first -- the…, Repository responsible for ResearchSession/ResearchConversation persistence.… (+11 more)

### Community 73 - "Memory Type Enums"
Cohesion: 0.10
Nodes (20): MemoryOperation, MemoryType, StrEnum, PRD §12/§13 API surface. Used for logging and metrics labeling only -- not…, PRD §11. Each type routes to a different storage backend -- see `create.py` and…, ExtractedMemoryBatch, _ExtractedMemoryLLM, BaseModel (+12 more)

### Community 74 - "SQLAlchemy Base Models"
Cohesion: 0.14
Nodes (19): Base, Base class for all SQLAlchemy ORM models. All database entities in ResearchMind…, Adds creation and update timestamps to a model., TimestampMixin, GenerationUsage, Durable, owner-scoped accounting records for completed generations., One immutable usage record per generation request. ``request_id`` is unique so…, ResearchMind ORM models. Import all ORM models here so SQLAlchemy metadata is… (+11 more)

### Community 75 - "Research Feed Page"
Cohesion: 0.10
Nodes (24): FeedItem, formatCost(), ResearchPage(), SearchIcon(), DEEP_SUGGESTIONS, EmptyWorkspace(), LINEAR_SUGGESTIONS, LINEAR_SUGGESTIONS_NO_DOCS (+16 more)

### Community 76 - "Context Guardrails"
Cohesion: 0.12
Nodes (16): create_context_guardrail_service(), ChunkRiskLevel, GuardrailStrategy, StrEnum, GuardrailProvider, ABC, GuardrailResult, GuardrailStatistics (+8 more)

### Community 77 - "App Exceptions Base"
Cohesion: 0.12
Nodes (15): AppException, ConflictException, Exception, RateLimitExceededException, Base application exception. All custom exceptions should inherit from this…, ServiceUnavailableException, UnauthorizedException, ValidationException (+7 more)

### Community 78 - "Budget Guardrail"
Cohesion: 0.12
Nodes (15): BudgetGuardrail, Runtime budget enforcement (PRD §11, P1 -- "implement immediately"):…, BudgetPolicy, ExecutionState, BaseModel, Statically configured runtime limits (PRD §11) — set once per run/agent, not…, Live accumulator describing a run's progress so far. The Guardrails Platform…, LoopDetectionGuardrail (+7 more)

### Community 79 - "Query Embedding Cache"
Cohesion: 0.11
Nodes (16): create_query_embedding_cache(), Query embedding cache composition root. Selects and constructs the configured…, Create the configured QueryEmbeddingCache. Returns a NullQueryEmbeddingCache…, ABC, QueryEmbeddingCache, Query embedding cache interfaces., Cache for query embeddings., Return cached embedding. (+8 more)

### Community 80 - "Semantic Cache Provider"
Cohesion: 0.09
Nodes (14): create_semantic_cache_provider(), Returns a `NullSemanticCacheProvider` when semantic caching is disabled, so L2…, L2 Semantic Cache backend contract. `context_hash` must be folded into whatever…, Returns `(result, similarity)` on a hit above threshold, else `None`.…, SemanticCacheProviderInterface, OpenAISemanticCacheEmbeddings, OpenAI, Thin `langchain_core.embeddings.Embeddings` adapter over the OpenAI embeddings… (+6 more)

### Community 81 - "Sparse Embedding & Retrieval Registry"
Cohesion: 0.10
Nodes (18): create_sparse_embedding_provider(), Create a fully configured FastEmbedSparseEmbeddingProvider., create_fusion_service(), create_retrieval_registry(), create_sparse_query_embedding_service(), Retrieval Platform composition root. Assembles the Retrieval Platform by…, Create a fully configured RetrievalRegistry., Create sparse query embedding service. (+10 more)

### Community 82 - "Research Run Dispatch Repository"
Cohesion: 0.09
Nodes (13): Auto-cancel runs left sitting at AWAITING_APPROVAL past the TTL. Without this,…, AsyncSession, UUID, Transactional outbox persistence for Research Runtime workers., PENDING + RUNNING dispatch rows -- work not yet completed by any worker lane.…, Re-queue an existing (`run_id` is the dispatch's own primary key, one row per…, ResearchRunDispatchRepository, timedelta (+5 more)

### Community 83 - "Web TS Config"
Cohesion: 0.07
Nodes (26): dom, dom.iterable, esnext, next-env.d.ts, .next/types/**/*.ts, node_modules, **/*.ts, **/*.tsx (+18 more)

### Community 84 - "Streaming Cache Models"
Cohesion: 0.13
Nodes (15): BaseModel, Carried in the START StreamEvent's metadata (`metadata["cache"]`) so a consumer…, StreamCacheOutcome, get_structured_output_registry(), get_structured_output_service(), OutputParserInterface, ABC, Any (+7 more)

### Community 85 - "User Memory Profile Service"
Cohesion: 0.13
Nodes (12): MemoryRecord, Any, PostgresMemoryStore, UUID, User Memory Service (PRD §9.3) -- preference management and profile updates:…, UserMemoryService, Any, UUID (+4 more)

### Community 86 - "Generation Provider Base"
Cohesion: 0.10
Nodes (8): GenerationExecution, GenerationStatistics, BaseGenerationProvider, ABC, Any, ConfigT, Parser fallback for structured generation. Native schema-constrained decoding…, Placeholder. Future: - routing - context compression - budgeting

### Community 87 - "Research Runtime Graph (LangGraph)"
Cohesion: 0.13
Nodes (20): compile_research_runtime_graph(), _complete(), initial_state(), _initialize(), Any, Minimal compiled LangGraph workflow used only by Phase 1 tests/services., Compile the deterministic walking skeleton with an injected saver., LangGraph execution foundation for the future Research Runtime. This package is… (+12 more)

### Community 88 - "Guardrail Risk Scoring"
Cohesion: 0.16
Nodes (13): GuardrailStage, compute_overall_risk(), Weighted average of whichever stage risk scores are actually available (PRD…, GuardrailService, Any, Citation, GuardrailResult, UUID (+5 more)

### Community 89 - "Memory Service Backend"
Cohesion: 0.12
Nodes (12): MemoryValidationError, Raised when a `remember()`/`update_memory()` payload is invalid., _MemoryBackend, Any, UUID, The `remember()` shape shared by `UserMemoryService`, `SemanticMemoryService`,…, Returns `None` (skipping persistence) when the computed/supplied importance…, Persist an extracted durable memory without duplicating facts. Exact normalized… (+4 more)

### Community 90 - "Research Report Download Service"
Cohesion: 0.11
Nodes (14): UUID, Owner-scoped authorization for final Research Runtime report downloads., Returns a short-lived PDF URL only for the run owner., ResearchReportDownloadService, get_research_report_download_service(), Authorize short-lived download URLs without exposing storage keys., AsyncSession, datetime (+6 more)

### Community 91 - "Guardrail Fail Policy"
Cohesion: 0.10
Nodes (18): FailPolicy, is_blocking_crash(), StrEnum, Whether a crashed check should force `GuardrailResult.blocked=True`., How `GuardrailService` should treat a guardrail check that crashes (PRD §12). A…, BaseModel, Whether a generation-stage failure should trigger `GuardrailAction. REGENERATE`…, RegenerationPolicy (+10 more)

### Community 92 - "Embedding Cache Keys & Chunk Artifact"
Cohesion: 0.09
Nodes (15): build_embedding_cache_key(), EmbeddingProvider, Build a stable cache key for a chunk's embedding. Args: provider: Embedding…, ChunkArtifact, Canonical persistence model representing a chunking execution. This model is…, Chunk artifact writer. Persists chunk artifacts using the application's storage…, Persist a chunk artifact. Storage layout: documents/ {owner_id}/ {document_id}/…, UUID (+7 more)

### Community 93 - "Prometheus Observability Composition"
Cohesion: 0.12
Nodes (15): get_metrics_asgi_app(), get_prometheus_metric_registry(), ASGIApp, Prometheus platform composition root (Prometheus Grafana Observability PRD…, `None` when Prometheus is disabled -- the composition root then skips mounting…, build_metrics_asgi_app(), ASGIApp, `GET /metrics` (Prometheus Grafana Observability PRD §11). Built against this… (+7 more)

### Community 94 - "Input Validator Interface"
Cohesion: 0.12
Nodes (9): InputValidatorInterface, OutputValidatorInterface, ABC, A single input validation check, run before generation. Receives the…, A single output (or hallucination-stage) validation check. Receives the full…, CompletenessValidator, Checks `GenerationResult.parsed_output` for empty sections, missing summaries,…, Dynamic validator registration (PRD §13). Groups validators by stage so… (+1 more)

### Community 95 - "Web App Shell & Auth Callback"
Cohesion: 0.14
Nodes (15): AppShell(), CallbackHandler(), NAV_ITEMS, Sidebar(), AuthContext, AuthProvider(), AuthState, useAuth() (+7 more)

### Community 96 - "Research Markdown & Citations UI"
Cohesion: 0.14
Nodes (17): ClockIcon(), FileTextIcon(), NetworkIcon(), BASE_COMPONENTS, CitationBadge(), Markdown(), remarkCitations(), visitTextNodes() (+9 more)

### Community 97 - "Session Artifacts (Scaffold)"
Cohesion: 0.17
Nodes (16): UUID, Session artifact builder -- scaffold-only, see `models.py` docstring., SessionArtifactBuilder, BaseModel, Session artifact models (PRD §16). Reserved for a future Session Runtime.…, Container so `timeline.json` holds one JSON object, not a bare list., SessionArtifact, SessionArtifactMetadata (+8 more)

### Community 98 - "Guardrail Artifact Builder"
Cohesion: 0.14
Nodes (19): GuardrailArtifactBuilder, UUID, Guardrail artifact builder. Builds the canonical GuardrailArtifact from a…, Builds the canonical GuardrailArtifact., GuardrailArtifact, BaseModel, Canonical persistence model representing a guardrail evaluation run., GuardrailReport (+11 more)

### Community 99 - "Embedding Artifact Builder"
Cohesion: 0.13
Nodes (18): Embedding artifact builder. Builds the canonical EmbeddingArtifact from a…, Build an EmbeddingArtifact. Args: chunk_artifact: Source chunk artifact.…, EmbeddingArtifact, EmbeddingArtifactChunking, EmbeddingArtifactDocument, EmbeddingArtifactEvaluation, EmbeddingArtifactExecution, EmbeddingArtifactStatistics (+10 more)

### Community 100 - "Streaming Artifact Models"
Cohesion: 0.15
Nodes (17): BaseModel, Streaming artifact models (PRD §14). Storage layout:…, Container so `events.json` holds one JSON object, not a bare list., Container so `timeline.json` holds one JSON object, not a bare list., Canonical persistence model representing one completed stream., StreamArtifact, StreamEventsFile, StreamMetrics (+9 more)

### Community 101 - "FastEmbed Sparse Provider"
Cohesion: 0.10
Nodes (14): FastEmbedSparseEmbeddingConfig, FastEmbedSparseEmbeddingProvider, BaseModel, FastEmbed SPLADE sparse embedding provider. Generates sparse neural retrieval…, Provider configuration., Stable fingerprint uniquely identifying the provider configuration., Generate sparse SPLADE vectors for the supplied texts. The resulting vectors…, Configuration for the FastEmbed SPLADE sparse embedding provider. (+6 more)

### Community 102 - "Retrieval Config Models"
Cohesion: 0.11
Nodes (17): BaseRetrievalConfig, BaseModel, QdrantRetrievalConfig, Retrieval Platform configuration models. These configuration models define the…, Base configuration shared by all retrieval providers., Configuration for Qdrant retrieval., StrEnum, Retrieval Platform enumerations. (+9 more)

### Community 103 - "Upload Validation"
Cohesion: 0.16
Nodes (18): get_extension(), Return a lowercase file extension., EmptyFileError, FileTooLargeError, InvalidFilenameError, Exception, Raised when an uploaded file is empty., Raised when an uploaded file exceeds the maximum size. (+10 more)

### Community 104 - "Documents Schema & API"
Cohesion: 0.12
Nodes (20): document_knowledge_stats(), list_documents(), get, post, Upload a document to ResearchMind. Synchrounous Workflow (previous): 1.…, List documents owned by the authenticated user, paginated. Newest first. Scoped…, Return exact owner-scoped counts of indexed chunks and embeddings. Each indexed…, upload_document() (+12 more)

### Community 105 - "File Hashing"
Cohesion: 0.13
Nodes (15): get_file_hasher(), _get_hasher(), Create the configured file hasher., Return the configured file hasher., HashingError, Exception, Base hashing exception., FileHasher (+7 more)

### Community 106 - "User Repository"
Cohesion: 0.10
Nodes (12): AsyncSession, UUID, Flush pending changes. The transaction is not committed here., Repository responsible for User persistence. This class contains only database…, Delete a user. The transaction is not committed here., Persist a new user. The transaction is not committed here., Retrieve a user by primary key., Retrieve a user by email. (+4 more)

### Community 107 - "Research Replay Service (Scaffold)"
Cohesion: 0.16
Nodes (14): UUID, Research Replay (PRD §21) -- scaffold-only. No Research Runtime exists yet to…, ResearchReplayService, Any, UUID, Research artifact builder, see `models.py` docstring., ResearchArtifactBuilder, BaseModel (+6 more)

### Community 108 - "Indexing Errors"
Cohesion: 0.13
Nodes (20): IndexAlreadyExistsError, IndexArtifactError, IndexingError, IndexingExecutionError, IndexNotFoundError, IndexNotSupportedError, IndexProviderError, InvalidIndexingRequestError (+12 more)

### Community 109 - "Streaming Serializer Interface"
Cohesion: 0.14
Nodes (14): ABC, Any, Converts a canonical StreamEvent into whatever wire format a transport needs.…, StreamSerializerInterface, JsonSerializer, Any, JSON-frame representation of a StreamEvent, used by the WebSocket transport…, serialize_json() (+6 more)

### Community 110 - "Memory API Endpoints"
Cohesion: 0.22
Nodes (19): forget_memory(), get_memory_context(), get, post, UUID, Returns `null` when the memory's importance score falls below the configured…, recall_memory(), remember() (+11 more)

### Community 111 - "CORS Middleware"
Cohesion: 0.13
Nodes (12): get_cors_middleware(), FastAPI, Register all application middleware. Middleware execution order is important.…, register_middlewares(), BaseHTTPMiddleware, RequestIDMiddleware, LoggingMiddleware, BaseHTTPMiddleware (+4 more)

### Community 112 - "Prompt Templates (Chat/Research/Summary)"
Cohesion: 0.13
Nodes (20): Chat v1 Config (Conversational RAG Assistant), Chat v1 Prompt Template, Chat v2 Config (Memory Aware Conversational Assistant), Chat v2 Prompt Template, Chat v3 Config (Agentic Conversational Assistant), Chat v3 Prompt Template, Research v1 Config (Quick Research Response), Research v1 Prompt Template (+12 more)

### Community 113 - "Knowledge Embeddings"
Cohesion: 0.14
Nodes (11): EmbeddingRegistry, EmbeddingProvider, Remove all registered providers., Registered providers. Returns a shallow copy to prevent external mutation., Return all registered embedding providers., Registry of available embedding providers., Register an embedding provider. Raises: ValueError: If a provider for the…, Resolve a registered embedding provider. Raises:… (+3 more)

### Community 114 - "Knowledge Processing"
Cohesion: 0.12
Nodes (12): Resolve a document format from a MIME content type. Raises: ValueError: If the…, ParseRequest, BaseModel, Canonical request passed through the document processing pipeline. The…, Parse a document into the canonical ProcessedDocument model. The…, FilteringBoundLogger, Process a document through the complete processing pipeline., Build and persist processing artifacts. This stage serializes the canonical… (+4 more)

### Community 115 - "Repositories"
Cohesion: 0.13
Nodes (11): MemoryVectorIndex, MemoryRepository, AsyncSession, datetime, UUID, Delete a memory row. The transaction is not committed here., Repository responsible for `Memory` persistence. This class contains only…, Persist a new memory row. The transaction is not committed here. (+3 more)

### Community 116 - "Runtime Chat"
Cohesion: 0.15
Nodes (16): PaperQueryExtractionService, GenerationProvider, Falls through to `fallback_generation_runtime` (shared production runtime,…, ChatPaperSearchOutcome, ChatPaperSource, _format_paper_context(), BaseModel, UUID (+8 more)

### Community 117 - "Generation Prompts"
Cohesion: 0.16
Nodes (5): PromptRegistry, Path, Canonical registry for all prompt templates. Structure: { "research": { "v1":…, Register a single prompt directory. Example: templates/research/v1/, Recursively register all prompts. Structure: templates/ research/ v1/ v2/ chat/…

### Community 118 - "Artifacts Generation"
Cohesion: 0.18
Nodes (14): GenerationArtifactBuilder, UUID, Generation artifact builder. Pure -- no knowledge of storage., Builds the canonical GenerationArtifact from a completed GenerationResult., GenerationArtifact, GenerationCacheSnapshot, GenerationResponseSnapshot, GenerationRoutingSnapshot (+6 more)

### Community 119 - "Knowledge Embeddings"
Cohesion: 0.12
Nodes (10): EmbeddingBatcher, Embedding batching utilities. Provides reusable batching helpers for embedding…, Splits an iterable into fixed-size batches. Batches are generated lazily to…, Configured batch size., Yield batches of items. Args: items: Iterable of items to batch. Yields: Lists…, Generate embeddings for every chunk in the supplied chunk artifact. Args:…, SentenceTransformer, Lazily construct and cache the SentenceTransformer model. (+2 more)

### Community 120 - "Knowledge Vectorstores"
Cohesion: 0.15
Nodes (15): BaseVectorStoreConfig, ChromaVectorStoreConfig, PgVectorStoreConfig, PineconeVectorStoreConfig, BaseModel, QdrantVectorStoreConfig, Vector Store configuration models. These configuration models define the…, Configuration for the Weaviate provider. (+7 more)

### Community 121 - "Generation Observability"
Cohesion: 0.17
Nodes (11): normalize_model_family(), Shared bounded-label normalization helpers (Prometheus Grafana Observability…, Maps an arbitrary model string to one of a small, fixed set of families so the…, _fmt(), GenerationReportBuilder, Generation Report builder (AI Runtime Observability PRD §7 "Generation…, build_generation_metrics_snapshot(), GenerationMetricsSnapshot (+3 more)

### Community 122 - "V1"
Cohesion: 0.16
Nodes (13): callback(), me(), get, post, Exchange a Cognito authorization code for tokens. The frontend calls this after…, Return the authenticated user., CallbackRequest, BaseModel (+5 more)

### Community 123 - "Components Landing"
Cohesion: 0.15
Nodes (11): metadata, LoginButton(), LoginButtonProps, ArchitectureSection(), STAGES, FeaturesSection(), Hero(), STRIP (+3 more)

### Community 124 - "Artifacts Evaluation"
Cohesion: 0.21
Nodes (11): EvaluationArtifactBuilder, Any, UUID, Evaluation artifact builder -- scaffold-only, see `models.py` docstring., EvaluationArtifact, EvaluationArtifactMetadata, BaseModel, Evaluation artifact models (PRD §19) -- scaffold-only. No runtime emits or… (+3 more)

### Community 125 - "Runtime Events"
Cohesion: 0.17
Nodes (13): CoreEventType, EventCategory, StrEnum, The only event-type enum the canonical StreamEvent model depends on. Every…, Which domain a StreamEvent belongs to. Distinct from `StreamEvent.type`, which…, _pump(), StreamingResponse, Wraps a StreamEvent iterator as a `text/event-stream` FastAPI response.… (+5 more)

### Community 126 - "Generation Prompts"
Cohesion: 0.19
Nodes (6): PromptRenderRequest, PromptService, Any, BaseMessage, GenerationProvider, Temporary model selection. Later this should come from: - Routing Platform -…

### Community 127 - "Routing Strategies"
Cohesion: 0.17
Nodes (8): StrEnum, Capability gates a caller can require of a routed model. Each value maps to a…, RequiredCapability, Everything strategy resolution needs to know about a `RoutingStrategy`: how to…, RoutingStrategyProfile, BaseModel, Per-dimension weights the scoring engine blends into a single score for a…, ScoringWeights

### Community 128 - "Tools Paper Search"
Cohesion: 0.19
Nodes (9): create_paper_search_service(), Research Intelligence MCP (paper search) Tool Platform composition root.…, PaperSearchPolicy, BaseModel, Paper-search execution policy -- budgets/limits, settings-driven.…, PaperSearchProviderRegistry, PaperSearchService, False when the platform is disabled or no provider is configured (e.g. a… (+1 more)

### Community 129 - "Artifacts Observability"
Cohesion: 0.16
Nodes (10): JsonDictFile, BaseModel, Generic single-object wrapper so a loosely-typed `dict[str, Any]` artifact…, ObservabilityArtifact, BaseModel, Canonical persistence model for one observability record (PRD §8)., ObservabilityArtifactReader, UUID (+2 more)

### Community 130 - "Generation Observability"
Cohesion: 0.23
Nodes (6): GenerationProvider, Groq uses OpenAI compatible tokenization., Provider-aware token counter. Accuracy: OpenAI -> Excellent Groq -> Excellent…, Local models differ. Approximation is safest., Rough estimate: 1 token ≈ 0.75 words, TokenCounter

### Community 131 - "Generation Prompts"
Cohesion: 0.23
Nodes (7): PromptRegistryInterface, PromptServiceInterface, ABC, PromptFactory, PromptRenderResult, PromptTemplate, ChatPromptTemplate

### Community 132 - "Core"
Cohesion: 0.21
Nodes (11): lifespan(), FastAPI, _run_migrations(), configure_logging(), Configure structlog as the primary logging system. In development: coloured…, create_qdrant_client(), AsyncQdrantClient, Create the application's Qdrant client. The client is created during FastAPI… (+3 more)

### Community 133 - "Infrastructure AWS"
Cohesion: 0.17
Nodes (8): BaseSettings, Application configuration. Values are loaded from the local `.env` file during…, Settings, AwsSession, AWS session management., Factory for AWS service clients., Create an Amazon S3 client., field_validator

### Community 134 - "Worker"
Cohesion: 0.14
Nodes (9): Worker runtime metrics. These metrics provide lightweight observability for the…, In-memory processing worker metrics., Average processing duration., WorkerMetrics, ProcessingWorker, Background worker for asynchronous document processing. The worker continuously…, Request a graceful worker shutdown. The worker finishes the current job before…, Background worker responsible for consuming processing jobs. (+1 more)

### Community 135 - "AI Artifacts"
Cohesion: 0.16
Nodes (10): ArtifactBuilderInterface, ArtifactReaderInterface, ArtifactWriterInterface, Any, UUID, Builds a canonical artifact from runtime state. Pure -- no knowledge of storage…, Persists a canonical artifact via the application's storage abstraction. Raises…, Reconstructs a canonical artifact previously persisted by a matching… (+2 more)

### Community 136 - "Guardrails Trust"
Cohesion: 0.20
Nodes (6): Flags retrieved chunks from low-trust sources (PRD §9, P1). `ContextChunk` has…, SourceTrustGuardrail, StrEnum, SourceType, Static trust-score-by-source-type lookup (PRD §9)., TrustRegistry

### Community 137 - "Knowledge Retrieval"
Cohesion: 0.24
Nodes (8): Statistics describing a retrieval execution., RetrievalStatistics, Validate retrieval inputs. Future: - prompt injection detection - jailbreak…, Normalize the incoming query. Future: - unicode normalization - query rewriting…, Execute sparse retrieval., Execute metadata-filtered retrieval. Pure attribute/filter lookup -- no query…, Execute hybrid retrieval. Workflow Query ↓ Dense Retrieval ⎫ Sparse Retrieval ⎬…, Execute retrieval. Workflow Query ↓ Validation ↓ Normalization ↓ Query…

### Community 138 - "Runtime Research"
Cohesion: 0.25
Nodes (9): BaseModel, Canonical, provider-independent event emitted by any runtime. `type` is a plain…, StreamEvent, LangGraphResearchEventAdapter, UUID, ResearchMind-owned event adaptation for LangGraph execution updates., Maps selected graph updates to stable public runtime events. Internal node…, Adapt only recognized lifecycle updates; omit arbitrary graph data. (+1 more)

### Community 139 - "Providers Helpers"
Cohesion: 0.23
Nodes (13): build_claude_json_instruction(), build_claude_output_config(), build_gemini_generation_config(), build_groq_response_format(), build_ollama_format(), build_openai_text_config(), Any, OpenAI's `text.format: json_schema` (Responses API) is strict-mode-only: every… (+5 more)

### Community 140 - "Schemas"
Cohesion: 0.31
Nodes (12): health(), live(), get, Request, ready(), SuccessResponse, HealthServices, HealthStatus (+4 more)

### Community 141 - "Observability Prometheus"
Cohesion: 0.26
Nodes (6): MetricSpec, Central, bounded metric registry (Prometheus Grafana Observability PRD…, PrometheusMetricsRecorder, `MetricsRecorder` implementation backed by Prometheus (Prometheus Grafana…, Filters to the metric's declared label schema and fills any missing declared…, _resolve_labels()

### Community 142 - "Runtime Events"
Cohesion: 0.22
Nodes (8): GenericStreamChunkAdapter, UUID, Single adapter shared by every generation provider. Every provider's `stream()`…, Runtime Event Platform composition root., ProviderEventAdapterInterface, ABC, UUID, Converts a provider's normalized StreamChunk into a canonical StreamEvent.…

### Community 143 - "Generation Catalog"
Cohesion: 0.26
Nodes (5): ModelCatalogRegistry, GenerationProvider, ModelMetadata, Lookup surface over the model catalog. Holds no routing logic itself —…, Models that have not been hard-disabled. Still includes `experimental`/`local`…

### Community 144 - "Generation Providers"
Cohesion: 0.22
Nodes (4): OllamaProvider, Any, GenerationProvider, Native `format: <json_schema>` (wired in `_create_chat` / `stream` via…

### Community 145 - "Generation Structured Output"
Cohesion: 0.23
Nodes (5): Any, Converts: { "a":1, } into: { "a":1 }, Converts: {'a':'b'} into: {"a":"b"} This is intentionally conservative., Attempts to repair common LLM structured output mistakes. Supported repairs: -…, StructuredOutputRepair

### Community 146 - "Runtime Contracts"
Cohesion: 0.18
Nodes (5): PlannerRuntimeContract, Planner Runtime Contract — requires a non-empty `goal` field, at least one…, DependencyValidator, DFS cycle detection over the id -> depends_on graph., Checks that a list field of dependency-carrying items (e.g. a planner's…

### Community 147 - "Core"
Cohesion: 0.28
Nodes (9): configure_application(), FastAPI, Configure the FastAPI application. Registers middleware, exception handlers,…, FastAPI, Register all application exception handlers., register_exception_handlers(), ErrorDetail, ErrorResponse (+1 more)

### Community 148 - "Artifacts Conversation"
Cohesion: 0.23
Nodes (8): UUID, Conversation artifact builder. Pure -- no knowledge of storage., ConversationArtifactMetadata, ConversationTurnArtifact, BaseModel, Conversation artifact models (PRD §15, adapted). Storage layout:…, Canonical persistence model for one completed user/assistant exchange. A fresh…, Writes a fresh, never-overwritten `turns/{turn_id}/turn.json` per completed…

### Community 149 - "Artifacts Streaming"
Cohesion: 0.29
Nodes (8): datetime, GenerationProvider, UUID, Streaming artifact builder. Pure -- no knowledge of storage., Builds the canonical StreamArtifact from the events accumulated over one…, StreamArtifactBuilder, StreamArtifactMetadata, StreamTimelineEntry

### Community 150 - "Knowledge Embeddings"
Cohesion: 0.18
Nodes (8): BaseEmbeddingProvider, ABC, ConfigT, EmbeddingProvider, Base class for all embedding providers. Responsibilities: - provider…, Provider implementation version., Provider configuration., Stable fingerprint representing the provider configuration.

### Community 151 - "Generation Providers"
Cohesion: 0.23
Nodes (4): GeminiProvider, GenerationProvider, Native `response_mime_type` + `response_json_schema` (wired in…, GenerateContentConfig

### Community 152 - "Generation Streaming"
Cohesion: 0.26
Nodes (5): Any, datetime, GenerationProvider, Best-effort (Artifact Platform PRD §24): mirrors `GenerationService.…, Best-effort statistics: today's provider `stream()` implementations only yield…

### Community 153 - "Generation Structured Output"
Cohesion: 0.35
Nodes (5): BaseModel, StructuredOutputRequest, StructuredOutputResult, BaseModel, StructuredOutputService

### Community 154 - "Guardrails Generation"
Cohesion: 0.25
Nodes (5): AlwaysAllowModerationProvider, ModerationGuardrail, ModerationProvider, ABC, Foundation only -- PRD §21 explicitly skips advanced moderation for MVP ("Not…

### Community 155 - "Knowledge Embeddings"
Cohesion: 0.24
Nodes (10): EmbeddingError, EmbeddingGenerationError, EmbeddingProviderNotFoundError, EmbeddingValidationError, Exception, Embedding domain exceptions., Raised when an embedding provider cannot be resolved., Raised when embeddings cannot be generated from the provided input. (+2 more)

### Community 156 - "Observability Metrics"
Cohesion: 0.20
Nodes (9): build_research_metrics_snapshot(), BaseModel, Canonical Research Metrics Platform (AI Runtime Observability PRD §5.4). PRD-…, Pure derivation from a completed `ResearchOutcome`. `research_duration_ms` is…, ResearchMetricsSnapshot, BaseModel, Research Service internal models (research_api_prd.md §9/§10)., A single retrieved-and-cited source (research_api_prd.md §9). Built from a… (+1 more)

### Community 157 - "Generation Langchain"
Cohesion: 0.22
Nodes (11): _build_chat_model(), generate_structured(), generate_structured_from_request(), BaseModel, GenerationProvider, Generates structured output via LangChain's `with_structured_output()`.…, Convenience wrapper over `generate_structured()` that pulls the schema and…, _secret() (+3 more)

### Community 158 - "Generation Prompts"
Cohesion: 0.33
Nodes (10): FewShotConfig, PromptArtifactsConfig, PromptContextConfig, PromptEvaluationConfig, PromptFutureConfig, PromptGenerationConfig, PromptMemoryConfig, PromptRoutingConfig (+2 more)

### Community 159 - "Guardrails Retrieval"
Cohesion: 0.27
Nodes (6): AccessControlGuardrail, AccessControlProvider, PermissiveAccessControlProvider, ABC, Foundation only (PRD §9/§17) -- "implement interfaces now, complex logic…, Default provider -- allows everything. No tenant isolation / document ACL /…

### Community 160 - "Knowledge Upload"
Cohesion: 0.27
Nodes (8): StrEnum, Indicates where the upload originated., Represents the current state of a document upload., UploadSource, UploadStatus, BaseModel, Domain model representing a document uploaded into the Knowledge Platform., UploadDocument

### Community 161 - "Generation Catalog"
Cohesion: 0.24
Nodes (7): ModelMetadata, BaseModel, Canonical model metadata. Used by: - Routing - Benchmarking - Cost estimation -…, get_model_catalog_registry(), build_strategy_profiles(), create_routing_service(), Routing Platform composition root. Assembles the catalog registry, scoring…

### Community 162 - "Generation Routing"
Cohesion: 0.36
Nodes (6): ABC, Canonical contract for resolving a `RoutingRequest` into a `RoutingDecision`.…, RoutingServiceInterface, BaseModel, RoutingDecision, RoutingRequest

### Community 163 - "Routing Scoring"
Cohesion: 0.38
Nodes (5): BaseModel, ScoredModel, ModelMetadata, Min-max normalizes blended cost (inverted — cheaper is higher) and context…, ScoringService

### Community 164 - "Generation Routing"
Cohesion: 0.36
Nodes (4): ModelMetadata, AUTO hard-defaults to Groq rather than the scoring engine's own top pick -- the…, Fills fallback slots preferring a provider not already used — by the primary…, RoutingService

### Community 165 - "Generation Structured Output"
Cohesion: 0.29
Nodes (3): OutputFormat, StrEnum, StructuredOutputRegistry

### Community 166 - "Structured Output Schemas"
Cohesion: 0.31
Nodes (9): AgentActionType, AgentExecutionResult, AgentPlan, AgentResponse, AgentReview, AgentStep, BaseModel, StrEnum (+1 more)

### Community 167 - "Retrieval Fusion"
Cohesion: 0.28
Nodes (6): FusionStrategy, ABC, Retrieval fusion interfaces. Fusion combines multiple retrieval result sets…, Base interface for retrieval fusion strategies., Fuse multiple retrieval result sets into a single ranked result. Parameters…, Reciprocal Rank Fusion (RRF). RRF is a robust ranking algorithm that combines…

### Community 168 - "AI Memory"
Cohesion: 0.28
Nodes (8): MemoryError, MemoryNotFoundError, MemoryStorageError, Exception, Memory Platform exceptions., Raised when a memory lookup by id finds nothing owned by the caller., Raised when a storage backend (Valkey/Postgres/Qdrant) operation fails., Base exception for the Memory Platform.

### Community 169 - "Generation Providers"
Cohesion: 0.31
Nodes (3): GroqProvider, GenerationProvider, Native `response_format: json_schema` (wired in `_create_completion` via…

### Community 170 - "Features Dashboard"
Cohesion: 0.22
Nodes (8): PlatformService, RECENT_QUESTIONS, RecentQuestion, ResearchSessionSummary, ServiceStatus, STATIC_SERVICES, SUGGESTED_RESEARCH, SuggestedResearch

### Community 171 - "Artifacts Replay"
Cohesion: 0.32
Nodes (5): UUID, Stream Replay (PRD §21): Stored Events -> Re-Emit SSE Events., Re-emits a previously persisted `StreamArtifact`'s events in original order --…, StreamReplayService, StreamArtifactReader

### Community 172 - "Guardrails Runtime"
Cohesion: 0.39
Nodes (6): ApprovalGateInterface, ApprovalRequest, ApprovalResponse, ABC, BaseModel, Interfaces only (PRD §19) -- the future LangGraph-interrupt seam for human-in-…

### Community 173 - "Observability Prometheus"
Cohesion: 0.39
Nodes (6): PrometheusHTTPMiddleware, Reconstructs the templated path (e.g. `/api/v1/research/{research_id}`, never a…, _route_template(), Receive, Scope, Send

### Community 174 - "Generation Policies"
Cohesion: 0.29
Nodes (6): AcceptanceDecision, AcceptancePolicy, BaseModel, StrEnum, What `GenerationService` should do with a generated result, given its…, Decides Accept/Reject/Regenerate for a completed generation attempt, given its…

### Community 175 - "Routing Scoring"
Cohesion: 0.29
Nodes (5): ABC, ModelMetadata, Blends a candidate model's catalog scores into a single ranking number for a…, Scores every model in `models` against `weights` and returns them sorted best-…, ScoringEngineInterface

### Community 176 - "Services"
Cohesion: 0.33
Nodes (6): MessageRole, Who authored a chat Message., compact_conversation_history(), _excerpt(), Deterministic, zero-provider-cost compaction for Chat prompt history., Create a bounded structured record without an additional LLM call. The…

### Community 177 - "App Root"
Cohesion: 0.29
Nodes (5): fraunces, geistMono, inter, metadata, viewport

### Community 178 - "Guardrails Trust"
Cohesion: 0.40
Nodes (4): BaseModel, SourceTrust, compute_trust_score(), Deterministic trust score (PRD §9, Principle 3 -- no ML): the source type's…

### Community 179 - "Cache Query Embeddings"
Cohesion: 0.33
Nodes (5): build_query_embedding_cache_key(), EmbeddingProvider, Build stable cache key., EmbeddingProvider, Generate query embedding.

### Community 180 - "Generation Prompts"
Cohesion: 0.47
Nodes (3): PromptBuilder, Path, PromptMetadata

### Community 181 - "Core"
Cohesion: 0.73
Nodes (5): get_health_status(), postgres_health(), Request, qdrant_health(), valkey_health()

### Community 183 - "Generation Caching"
Cohesion: 0.50
Nodes (4): CacheBackendUnavailableError, CachingError, Exception, Raised by a provider constructor when a required backend (e.g. the semantic…

### Community 184 - "Generation Prompts"
Cohesion: 0.60
Nodes (3): get_prompt_registry(), get_prompt_service(), get_token_counter()

### Community 185 - "Generation Routing"
Cohesion: 0.50
Nodes (4): NoEligibleModelsError, Exception, Raised when capability and policy filtering leave no candidate models for a…, RoutingError

### Community 186 - "Generation Streaming"
Cohesion: 0.50
Nodes (4): StrEnum, Validation is a Generation Platform concern (see…, StreamTransport, ValidationEventType

### Community 188 - "Infrastructure Queue"
Cohesion: 0.40
Nodes (4): StrEnum, QueueProvider, Queue provider types., Supported queue providers.

### Community 189 - "App Root"
Cohesion: 0.40
Nodes (4): compat, __dirname, eslintConfig, __filename

### Community 190 - "AI Config"
Cohesion: 0.50
Nodes (3): AISettings, BaseSettings, AI Core configuration.

### Community 192 - "Observability Metrics"
Cohesion: 0.50
Nodes (3): AgentMetricsSnapshot, BaseModel, Canonical Agent Metrics Platform (AI Runtime Observability PRD §5.5). PRD-…

### Community 193 - "Events Agent"
Cohesion: 0.50
Nodes (3): AgentEventType, StrEnum, Reserved for the future Agent Runtime. Nothing in the Streaming Platform emits…

### Community 194 - "Events Tool"
Cohesion: 0.50
Nodes (3): StrEnum, Reserved for the future Tool Runtime. Nothing in the Streaming Platform emits…, ToolEventType

### Community 195 - "Structured Output Schemas"
Cohesion: 0.67
Nodes (3): Citation, CitationCollection, BaseModel

### Community 196 - "Structured Output Schemas"
Cohesion: 0.67
Nodes (3): PlannerOutput, PlannerStep, BaseModel

### Community 197 - "Runtime Research"
Cohesion: 0.50
Nodes (3): ResearchPlanInspectionService, get_research_plan_inspection_service(), Stateless, mirrors `get_research_draft_inspection_service`.

### Community 198 - "DB"
Cohesion: 0.50
Nodes (3): create_postgres_engine(), AsyncEngine, Create the application's PostgreSQL engine. The engine is created during the…

### Community 199 - "Worker"
Cohesion: 0.50
Nodes (3): main(), Entry point for the document processing worker. This process continuously…, Start the processing worker.

## Knowledge Gaps
- **133 isolated node(s):** `__filename`, `__dirname`, `compat`, `eslintConfig`, `nextConfig` (+128 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GenerationRequest` connect `Generation Interfaces & Errors` to `Chat Web Search & Research Evidence`, `Context Compression`, `Research Orchestration`, `Providers Helpers`, `Research Artifacts & Evidence`, `Generation Providers`, `Conversation & Memory Composition`, `Context Artifacts & Parent Expansion`, `Chat Paper Query Extraction`, `Input Guardrails`, `Generation Providers`, `Generation Streaming`, `Generation Caching`, `Generation Langchain`, `Research Planner Scheduling`, `Validation Policies`, `Generation Errors`, `Generation Providers`, `Generation Enums`, `Output Validation Rules`, `Conversation Artifact Readers`, `Artifact Retention Policy`, `Agent Artifacts (Scaffold)`, `Input Validation Registry`, `Validation Input`, `Guardrail Artifacts`, `Rate Limit Guardrail`, `Memory Type Enums`, `Generation Provider Base`, `Guardrail Risk Scoring`, `Input Validator Interface`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `GenerationResult` connect `Generation Interfaces & Errors` to `Generation Providers`, `Chat Paper Query Extraction`, `Input Guardrails`, `Generation Streaming`, `Generation Providers`, `Guardrails Generation`, `Generation Caching`, `Runtime Validation Contracts`, `Service Dependency Wiring`, `Runtime Caching Platform`, `Validation Policies`, `Generation Providers`, `Generation Enums`, `Output Validation Rules`, `Conversation Artifact Readers`, `Artifact Retention Policy`, `Input Validation Registry`, `Runtime Validator Registry`, `Guardrail Artifacts`, `Rate Limit Guardrail`, `Usage Reporting API`, `Semantic Cache Provider`, `Generation Provider Base`, `Guardrail Risk Scoring`, `Input Validator Interface`, `Artifacts Generation`, `Generation Observability`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `DocumentRepository` connect `Duplicate Detection` to `Documents Schema & API`, `Knowledge Artifact Builders & Writers`, `Repositories Core`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `User` (e.g. with `TimestampMixin` and `UserRepository`) actually correct?**
  _`User` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `__filename`, `__dirname`, `compat` to the rest of the system?**
  _133 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Knowledge Artifact Builders & Writers` be split into smaller, more focused modules?**
  _Cohesion score 0.03793103448275862 - nodes in this community are weakly interconnected._
- **Should `Duplicate Detection` be split into smaller, more focused modules?**
  _Cohesion score 0.02902418682235196 - nodes in this community are weakly interconnected._
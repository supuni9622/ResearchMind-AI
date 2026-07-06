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
│   │   └── 1b6e40f3a754_split_document_status_into_upload_.py  # Splits status into upload_status + processing_status
│   ├── env.py                   # Alembic runtime config (async engine, model imports)
│   ├── script.py.mako           # Migration file template
│   └── README                   # Alembic usage notes
│
├── apps/                        # Deployable applications
│   ├── api/                     # FastAPI backend
│   │   └── app/
│   │       ├── ai/              # AI subsystem
│   │       │   ├── config/
│   │       │   │   └── settings.py          # AI-specific configuration
│   │       │   ├── guardrails/
│   │       │   │   ├── policies.py          # Content policy definitions
│   │       │   │   └── scanners.py          # Input/output scanners
│   │       │   ├── knowledge/               # RAG knowledge pipeline
│   │       │   │   ├── cache/               # Semantic caching (planned)
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
│   │       │   │   ├── embeddings/          # Embedding generation pipeline
│   │       │   │   │   ├── artifacts/
│   │       │   │   │   │   ├── builder.py          # EmbeddingArtifactBuilder — builds EmbeddingArtifact from a ChunkArtifact + generated embeddings
│   │       │   │   │   │   ├── models.py           # EmbeddingArtifact + sub-models (document, chunking, execution, statistics, evaluation)
│   │       │   │   │   │   └── writer.py           # EmbeddingArtifactWriter — persists EmbeddingArtifact to storage (S3)
│   │       │   │   │   ├── providers/
│   │       │   │   │   │   └── sentence_transformers.py  # SentenceTransformerEmbeddingProvider — real SentenceTransformers model
│   │       │   │   │   ├── base.py                 # BaseEmbeddingProvider — generic base (config, version, fingerprint)
│   │       │   │   │   ├── config.py               # BaseEmbeddingConfig + SentenceTransformer/VoyageAI/OpenAI configs
│   │       │   │   │   ├── create.py               # create_embedding_registry() / create_embedding_service() — composition root
│   │       │   │   │   ├── enums.py                # EmbeddingProvider
│   │       │   │   │   ├── exceptions.py           # EmbeddingError hierarchy
│   │       │   │   │   ├── factory.py              # EmbeddingFactory — canonical Embedding mapper used by every provider
│   │       │   │   │   ├── interfaces.py           # EmbeddingProvider ABC
│   │       │   │   │   ├── models.py               # Embedding + sub-models (vector, provenance, provider, statistics, experiment)
│   │       │   │   │   ├── registry.py             # EmbeddingRegistry — provider → implementation resolution
│   │       │   │   │   └── service.py              # EmbeddingService — validates chunk artifact, delegates to provider
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
│   │       │   │   │   ├── service.py              # ProcessingService — orchestrates the full pipeline (parse → enrich → artifacts → chunk → chunk artifacts → embed → embedding artifacts)
│   │       │   │   │   └── temporary_file_manager.py  # Temp file lifecycle for downloaded documents
│   │       │   │   ├── reranking/           # Result reranking (planned)
│   │       │   │   ├── retrieval/           # Vector retrieval (planned)
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
│   │       │   │   └── vectorstores/        # Vector store abstractions (planned)
│   │       │   ├── quality/                 # Evaluation and quality (planned)
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
│   │       │   ├── runtime/                 # Inference runtime (planned)
│   │       │   │   ├── prompts/
│   │       │   │   ├── providers/
│   │       │   │   ├── registry/
│   │       │   │   ├── routing/
│   │       │   │   ├── streaming/
│   │       │   │   └── structured_output/
│   │       │   └── shared/                  # Shared AI types and interfaces
│   │       │       ├── exceptions.py        # AI-specific exceptions
│   │       │       ├── interfaces.py        # Abstract AI interfaces
│   │       │       ├── models.py            # Shared AI data models
│   │       │       └── types.py             # Shared type definitions
│   │       │
│   │       ├── api/             # Route layer
│   │       │   ├── deps.py              # Shared route dependencies
│   │       │   └── v1/                  # API version 1
│   │       │       ├── api.py           # Router aggregator
│   │       │       ├── admin.py         # Admin endpoints
│   │       │       ├── auth.py          # Auth endpoints (callback, me)
│   │       │       ├── chat.py          # Chat endpoints
│   │       │       ├── documents.py     # Document management endpoints
│   │       │       ├── evaluation.py    # Evaluation endpoints
│   │       │       ├── feedback.py      # Feedback endpoints
│   │       │       ├── health.py        # Health check endpoints
│   │       │       └── reports.py       # Report endpoints
│   │       │
│   │       ├── auth/            # Authentication layer
│   │       │   ├── dependencies.py      # get_current_user FastAPI dependency
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
│   │       │   ├── settings.py          # Pydantic settings (env-driven; incl. queue_provider, sqs_queue_url, queue_max_attempts)
│   │       │   └── setup.py             # App factory / setup helpers
│   │       │
│   │       ├── bootstrap/       # Composition roots shared across entry points
│   │       │   └── worker.py            # create_processing_worker() — wires the worker's object graph (incl. Chunking and Embedding Platforms)
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
│   │       │   ├── settings.py          # Settings dependency
│   │       │   ├── upload.py            # Upload/processing service dependencies (incl. processing queue, worker, chunking and embedding service/artifact builder/writer)
│   │       │   └── vector_store.py      # Vector store dependency
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
│   │       │       ├── interfaces.py    # DocumentStorage abstract interface
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
│   │       │   ├── document.py          # Document model — upload_status + processing_status lifecycle columns
│   │       │   ├── enums.py             # DocumentUploadStatus, DocumentProcessingStatus (split lifecycle)
│   │       │   └── user.py              # User model
│   │       │
│   │       ├── repositories/    # Data access layer
│   │       │   ├── document.py          # DocumentRepository (CRUD operations)
│   │       │   └── user.py              # UserRepository (CRUD operations)
│   │       │
│   │       ├── schemas/         # Pydantic request/response schemas
│   │       │   ├── auth.py              # Auth schemas (CallbackRequest, TokenResponse)
│   │       │   ├── chat.py              # Chat schemas
│   │       │   ├── common.py            # Shared/generic schemas
│   │       │   ├── document.py          # Document schemas
│   │       │   ├── error.py             # Error response schemas
│   │       │   ├── health.py            # Health response schemas
│   │       │   └── report.py            # Report schemas
│   │       │
│   │       ├── services/        # Business logic layer
│   │       │   ├── auth.py                        # OAuth code exchange with Cognito
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
│   │   ├── metrics.py                       # (empty) — planned shared metrics helpers
│   │   ├── report.py                        # (empty) — superseded by models/report.py
│   │   └── timer.py                         # (empty) — planned timing helper
│   ├── datasets/
│   │   ├── README.md                        # Dataset philosophy — deterministic, version-controlled, immutable
│   │   └── research-papers/
│   │       ├── paper-001/processed_document.json
│   │       ├── paper-002/processed_document.json
│   │       ├── paper-003/processed_document.json
│   │       ├── paper-004/processed_document.json
│   │       └── paper-005/processed_document.json
│   ├── embeddings/
│   │   └── benchmark.py                     # (empty) — planned embedding provider benchmark
│   ├── interfaces/
│   │   └── benchmark.py                     # Benchmark ABC — name, run(dataset_path) -> BenchmarkReport
│   ├── models/
│   │   └── report.py                        # BenchmarkCandidate, BenchmarkDataset, BenchmarkReport
│   ├── pipeline/
│   │   └── benchmark.py                     # (empty) — planned end-to-end pipeline benchmark
│   ├── reports/
│   │   └── .gitkeep                         # Keeps the default --output directory tracked
│   ├── reranking/
│   │   └── benchmark.py                     # (empty) — planned reranker benchmark
│   ├── retrieval/
│   │   └── benchmark.py                     # (empty) — planned retrieval strategy benchmark
│   ├── README.md                             # Platform overview, philosophy, workflow, usage
│   ├── factory.py                            # create_benchmark_registry() — composition root
│   ├── registry.py                           # BenchmarkRegistry — name → benchmark resolution
│   └── runner.py                             # CLI entry point (python -m benchmarks.runner <name> --dataset <path>)
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
│   │   └── ADR-014-chunking-provider-architecture.md
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
│   │   ├── evaluation-platform.md            # Runtime Evaluation Platform (planned)
│   │   ├── evaluation-strategy.md            # Why three evaluation layers (Benchmarks / Runtime Eval / Experimentation)
│   │   ├── experimentation-platform.md       # Experimentation Platform (planned)
│   │   ├── identity-architecture.md
│   │   ├── knowledge-platform-roadmap.md     # Full Knowledge Platform subsystem breakdown
│   │   ├── observability-strategy.md
│   │   ├── project-constitution.md
│   │   ├── repository-structure.md
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
│   │       └── 2026-07-05-fixed-chunking.md  # Fixed Chunking Platform milestone retrospective (Phase 2.3.3)
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
│   │   ├── langsmith.md
│   │   ├── otel.md
│   │   └── prometheus.md
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
│   └── dev.sh                   # Runs migrations then starts uvicorn dev server
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
│   │   └── test_health.py                   # Health endpoint smoke tests
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
│   │   │   └── test_processing_service.py   # Full DoclingParser → ProcessingService pipeline (incl. chunking + embedding stages)
│   │   ├── ai/knowledge/upload/
│   │   │   └── test_duplicate_detection.py  # Real UploadService + DuplicateDetectionService against Postgres
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
│   │   ├── ai/knowledge/embeddings/
│   │   │   ├── artifacts/
│   │   │   │   ├── test_builder.py          # EmbeddingArtifactBuilder — statistics aggregation, metadata derivation, empty-collection guard
│   │   │   │   └── test_writer.py           # EmbeddingArtifactWriter — storage key layout, serialized payload, error propagation
│   │   │   ├── test_factory.py              # EmbeddingFactory — provenance/statistics/vector mapping from a Chunk
│   │   │   ├── test_registry.py             # EmbeddingRegistry registration, lookup, deduplication
│   │   │   └── test_service.py              # EmbeddingService orchestration — delegation and validation failures
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
│   │   ├── infrastructure/storage/
│   │   │   └── test_s3_storage.py           # S3StorageService — boto3 ClientError → typed StorageError mapping
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
├── alembic.ini                  # Alembic configuration file
├── CHANGELOG.md                 # Version changelog
├── DEV_GUIDE.md                 # Step-by-step local development guide
├── docker-compose.yml           # Local dev stack (PostgreSQL, Valkey, Qdrant)
├── FILES.md                     # Complete file and folder map
├── LICENSE
├── PROJECT_STATUS.md            # Current project status and progress
├── pyproject.toml               # Python project config, deps, and tool settings
├── README.md                    # Project overview and quickstart
├── ROADMAP.md                   # Feature and milestone roadmap
├── SECURITY.md                  # Security policy
├── setup_commands.md            # Makefile-style shortcut commands (docker compose up/down)
├── STRUCTURE.md                 # This file
├── test.txt                     # Stray scratch file — can be deleted
└── uv.lock                      # Locked dependency versions (uv)
```

## Key Boundaries

| Layer | Location | Purpose |
|---|---|---|
| API app | `apps/api/` | FastAPI server — routes, middleware, models, schemas |
| Frontend | `apps/web/` | Next.js 15 App Router — Cognito auth, dashboard, documents, research |
| Processing pipeline | `apps/api/app/ai/knowledge/processing/` | Docling parser, metadata/statistics enrichment, artifact builder/writer, registry, service |
| Chunking pipeline | `apps/api/app/ai/knowledge/chunking/` | Transforms a `ProcessedDocument` into retrieval-ready `Chunk`s via a registry-based provider strategy (Fixed implemented), builds/persists the canonical `ChunkArtifact` (`chunks.json`) |
| Embedding pipeline | `apps/api/app/ai/knowledge/embeddings/` | Transforms a `ChunkArtifact` into vector `Embedding`s via a registry-based provider strategy (Sentence Transformers implemented), builds/persists the canonical `EmbeddingArtifact` (`embeddings.json`) |
| Upload pipeline | `apps/api/app/ai/knowledge/upload/` | File validation, duplicate detection, S3 upload, checksum hashing, enqueues async processing job |
| Async worker | `apps/worker/` | Standalone process consuming the queue, running `DocumentProcessingService` per job, retry/dead-letter handling |
| Engineering benchmarks | `benchmarks/` | Offline, manually-run comparison of competing AI implementations (currently: chunking strategies) against version-controlled datasets — independent from tests and from production infrastructure |
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

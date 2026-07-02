# Project Structure

Complete folder and file structure of the ResearchMind-AI monorepo.

```
ResearchMind-AI/
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
│   │   ├── 43dc35ceb875_debug.py              # Initial migration: creates users table + updated_at trigger
│   │   └── a97b3b8eee9f_create_documents_table.py  # Creates documents table with processing lifecycle columns
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
│   │       │   │   ├── chunking/            # Document chunking strategies (planned)
│   │       │   │   ├── embeddings/          # Embedding generation (planned)
│   │       │   │   ├── processing/          # Document processing pipeline
│   │       │   │   │   ├── adapters/
│   │       │   │   │   │   └── docling.py          # Docling adapter (alternative entry point)
│   │       │   │   │   ├── parsers/
│   │       │   │   │   │   ├── base.py             # BaseDocumentParser abstract class
│   │       │   │   │   │   └── docling.py          # Docling-backed parser implementation
│   │       │   │   │   ├── artifact_builder.py     # Builds ProcessingArtifacts from ProcessedDocument
│   │       │   │   │   ├── artifact_writer.py      # Persists artifacts to storage (S3)
│   │       │   │   │   ├── artifacts.py            # ProcessingArtifact / ProcessingArtifacts models
│   │       │   │   │   ├── enums.py                # DocumentFormat, ParserType, ProcessingStatus, ProcessingStage
│   │       │   │   │   ├── exceptions.py           # ProcessingError hierarchy
│   │       │   │   │   ├── interfaces.py           # DocumentParser ABC, ParseRequest
│   │       │   │   │   ├── models.py               # ProcessedDocument, block types, ProcessingResult
│   │       │   │   │   ├── registry.py             # ParserRegistry — format → parser resolution
│   │       │   │   │   └── service.py              # ProcessingService — orchestrates the full pipeline
│   │       │   │   ├── reranking/           # Result reranking (planned)
│   │       │   │   ├── retrieval/           # Vector retrieval (planned)
│   │       │   │   ├── upload/              # Document upload handling
│   │       │   │   │   ├── constants.py     # Upload limits and allowed MIME types
│   │       │   │   │   ├── enums.py         # Upload-specific enums
│   │       │   │   │   ├── exceptions.py    # Upload exceptions
│   │       │   │   │   ├── interfaces.py    # Upload abstract interfaces
│   │       │   │   │   ├── models.py        # Upload domain models
│   │       │   │   │   ├── schemas.py       # Upload Pydantic schemas
│   │       │   │   │   ├── service.py       # UploadService orchestration
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
│   │       │   ├── settings.py          # Pydantic settings (env-driven)
│   │       │   └── setup.py             # App factory / setup helpers
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
│   │       │   ├── upload.py            # Upload service dependency
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
│   │       │   ├── document.py          # Document model (upload + processing lifecycle columns)
│   │       │   ├── enums.py             # DocumentUploadStatus, DocumentProcessingStatus
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
│   │   │       └── auth.ts                  # Cognito URL builders, token storage (sessionStorage)
│   │   ├── .env.local                       # Cognito client ID, domain, redirect URI, API URL
│   │   ├── next.config.ts                   # Next.js configuration
│   │   ├── package.json                     # Next.js 15, React 19, Tailwind 3, TypeScript
│   │   ├── tailwind.config.ts               # Custom palette: ink, stone, sage, amber scales
│   │   └── README.md                        # Setup instructions and auth flow diagram
│   │
│   └── worker/                  # Background worker app (planned)
│
├── benchmarks/                  # Performance benchmarks (planned)
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
│   │   └── ADR-009-identity-architecture
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
│   │   ├── agent-architecture.md
│   │   ├── ai-architecture.md
│   │   ├── backend-architecture.md
│   │   ├── coding-standards.md
│   │   ├── database-design.md
│   │   ├── db-sessions.md
│   │   ├── decision-boundaries.md
│   │   ├── decision-history.md
│   │   ├── engineering-principles.md
│   │   ├── evaluation-strategy.md
│   │   ├── frontend-architecture.md
│   │   ├── identity-architecture.md
│   │   ├── mcp-architecture.md
│   │   ├── observability-strategy.md
│   │   ├── project-constitution.md
│   │   ├── quality-strategy.md
│   │   ├── repository-structure.md
│   │   ├── scalability.md
│   │   ├── security.md
│   │   ├── system-overview.md
│   │   └── tech-stack.md
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
│   │       └── 0.31-engineering-quality.md
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
│   │   └── chat-handoff2.md
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
│   ├── project-constitution.md  # Project principles and goals
│   └── project-handbook.md      # Working agreements and practices
│
├── examples/                    # Usage examples and notebooks (planned)
├── experiments/                 # Experimental code and prototypes (planned)
│
├── infrastructure/              # Infrastructure-as-code
│   ├── database/                # DB provisioning scripts
│   ├── deployment/              # Deployment manifests (k8s, etc.)
│   ├── docker/                  # Dockerfile definitions
│   ├── monitoring/              # Monitoring stack config
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
│   │   ├── ai/knowledge/processing/
│   │   │   └── test_processing_service.py   # Full DoclingParser → ProcessingService pipeline
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
│   │   ├── ai/knowledge/processing/
│   │   │   ├── test_docling_parser.py       # DoclingParser parse() with real PDF fixture
│   │   │   ├── test_models.py               # ProcessedDocument, block types, discriminated union
│   │   │   ├── test_registry.py             # ParserRegistry registration, lookup, deduplication
│   │   │   └── test_service.py              # ProcessingService orchestration with FakeParser
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
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── docker-compose.yml           # Local dev stack (PostgreSQL, Valkey, Qdrant)
├── LICENSE
├── PROJECT_STATUS.md            # Current project status and progress
├── pyproject.toml               # Python project config, deps, and tool settings
├── README.md                    # Project overview and quickstart
├── ROADMAP.md                   # Feature and milestone roadmap
├── SECURITY.md                  # Security policy
├── STRUCTURE.md                 # This file
└── uv.lock                      # Locked dependency versions (uv)
```

## Key Boundaries

| Layer | Location | Purpose |
|---|---|---|
| API app | `apps/api/` | FastAPI server — routes, middleware, models, schemas |
| Frontend | `apps/web/` | Next.js 15 App Router — Cognito auth, dashboard, documents, research |
| Processing pipeline | `apps/api/app/ai/knowledge/processing/` | Docling parser, artifact builder/writer, registry, service |
| Upload pipeline | `apps/api/app/ai/knowledge/upload/` | File validation, S3 upload, checksum hashing |
| Infrastructure | `apps/api/app/infrastructure/` | S3 storage, SHA-256 hashing, metrics adapters |
| Application services | `apps/api/app/services/` | Auth, user lifecycle, document processing orchestration |
| Agents | `agents/` | Autonomous AI agents (planned) |
| Services | `services/` | Internal service modules — retrieval, ingestion, etc. (planned) |
| Shared | `shared/` | Cross-cutting code shared by apps and services (planned) |
| Infrastructure IaC | `infrastructure/` | Docker, deployment configs |
| Migrations | `alembic/` | PostgreSQL schema migrations via Alembic |
| Tests | `tests/` | Unit, integration, e2e, evaluation, performance |
| Docs | `docs/` | All project documentation |

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
│   │   └── 43dc35ceb875_debug.py  # Initial migration: creates users table + updated_at trigger
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
│   │       │   ├── knowledge/               # RAG knowledge pipeline (planned)
│   │       │   │   ├── cache/               # Semantic caching
│   │       │   │   ├── chunking/            # Document chunking strategies
│   │       │   │   ├── documents/           # Document processing
│   │       │   │   ├── embeddings/          # Embedding generation
│   │       │   │   ├── reranking/           # Result reranking
│   │       │   │   ├── retrieval/           # Vector retrieval
│   │       │   │   ├── upload/              # Document upload handling
│   │       │   │   └── vectorstores/        # Vector store abstractions
│   │       │   ├── quality/                 # Evaluation and quality (planned)
│   │       │   │   ├── benchmarks/          # Performance benchmarks
│   │       │   │   ├── evaluation/          # LLM evaluation framework
│   │       │   │   ├── experiments/         # Experiment tracking
│   │       │   │   ├── regression/          # Regression test suite
│   │       │   │   ├── telemetry/           # Metrics and telemetry
│   │       │   │   └── tracing/             # LangSmith / OTEL tracing
│   │       │   ├── registry/                # Model and provider registries
│   │       │   │   ├── embeddings.py        # Embedding model registry
│   │       │   │   ├── evaluators.py        # Evaluator registry
│   │       │   │   ├── mcp.py               # MCP server registry
│   │       │   │   ├── models.py            # LLM model registry
│   │       │   │   ├── prompts.py           # Prompt template registry
│   │       │   │   ├── providers.py         # LLM provider registry
│   │       │   │   └── rerankers.py         # Reranker registry
│   │       │   ├── runtime/                 # Inference runtime (planned)
│   │       │   │   ├── prompts/             # Runtime prompt management
│   │       │   │   ├── providers/           # Runtime provider adapters
│   │       │   │   ├── registry/            # Runtime model registry
│   │       │   │   ├── routing/             # Request routing logic
│   │       │   │   ├── streaming/           # Streaming response handling
│   │       │   │   └── structured_output/   # Structured output parsing
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
│   │       │   ├── lifespan.py          # FastAPI lifespan (startup/shutdown)
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
│   │       ├── middleware/      # HTTP middleware
│   │       │   ├── cors.py              # CORS configuration
│   │       │   ├── register.py          # Middleware registration helper
│   │       │   ├── request_id.py        # Injects X-Request-ID header
│   │       │   ├── request_logging.py   # Structured request/response logging with correlation
│   │       │   └── request_timing.py    # Request duration (X-Process-Time header)
│   │       │
│   │       ├── models/          # SQLAlchemy ORM models
│   │       │   ├── __init__.py          # Exports all models (required for Alembic)
│   │       │   └── user.py              # User model
│   │       │
│   │       ├── repositories/    # Data access layer
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
│   │       │   ├── auth.py              # OAuth code exchange with Cognito
│   │       │   └── user.py              # User sync, creation, and lifecycle
│   │       │
│   │       └── main.py          # FastAPI app entry point
│   │
│   ├── web/                     # Frontend app (planned)
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
│   │   ├── identity-architecture.md  # Auth flow, Cognito setup, testing guide
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
│   │   ├── concepts/            # Deep-dives on specific concepts
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
│   │   └── milestones/          # Milestone retrospectives
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
├── scripts/                     # Developer utility scripts (planned)
│
├── services/                    # Internal service modules (planned)
│   ├── cache/                   # Caching service
│   ├── evaluation/              # Evaluation pipeline
│   ├── ingestion/               # Document ingestion
│   ├── mcp/                     # MCP server integrations
│   ├── memory/                  # Agent memory service
│   ├── observability/           # Tracing and metrics
│   ├── providers/               # LLM provider abstractions
│   ├── reporting/               # Report generation service
│   └── retrieval/               # Vector retrieval service
│
├── shared/                      # Code shared across apps and services (planned)
│   ├── config/                  # Shared configuration
│   ├── constants/               # Shared constants
│   ├── exceptions/              # Shared exception types
│   ├── interfaces/              # Shared abstract interfaces
│   ├── prompts/                 # Shared prompt templates
│   ├── schemas/                 # Shared Pydantic schemas
│   └── utils/                   # Shared utility functions
│
├── tests/                       # Test suite
│   ├── api/
│   │   └── test_health.py       # Health endpoint tests
│   ├── e2e/                     # End-to-end tests (planned)
│   ├── evaluation/              # Evaluation tests (planned)
│   ├── integration/             # Integration tests (planned)
│   ├── performance/             # Performance tests (planned)
│   ├── security/                # Security tests (planned)
│   ├── unit/
│   │   └── test_settings.py     # Settings unit tests
│   └── conftest.py              # Shared pytest fixtures
│
├── tools/                       # Developer tooling (planned)
│
├── .editorconfig                # Editor formatting rules
├── .env                         # Local environment variables (gitignored)
├── .env.example                 # Environment variable template
├── .gitignore
├── .pre-commit-config.yaml      # Pre-commit hooks (ruff, mypy, etc.)
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
| Agents | `agents/` | Autonomous AI agents (planned) |
| Services | `services/` | Internal service modules — retrieval, ingestion, etc. |
| Shared | `shared/` | Cross-cutting code shared by apps and services |
| Infrastructure | `infrastructure/` | IaC, Docker, deployment configs |
| Migrations | `alembic/` | PostgreSQL schema migrations via Alembic |
| Tests | `tests/` | Unit, integration, e2e, evaluation, performance |
| Docs | `docs/` | All project documentation |

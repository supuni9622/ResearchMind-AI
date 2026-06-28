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
| `CODE_OF_CONDUCT.md` | (empty) |
| `CONTRIBUTING.md` | (empty) |
| `docker-compose.yml` | Local dev stack — PostgreSQL (5432), Valkey (6379), Qdrant (6333/6334) |
| `FILES.md` | This file — complete file and folder map |
| `LICENSE` | Project license |
| `PROJECT_STATUS.md` | Current milestone and progress tracker |
| `pyproject.toml` | Python project config: dependencies, ruff, mypy, pytest settings |
| `README.md` | Project overview, quickstart, auth guide, Alembic troubleshooting |
| `ROADMAP.md` | Feature and milestone roadmap |
| `SECURITY.md` | (empty) |
| `STRUCTURE.md` | High-level folder/file structure with layer descriptions |
| `DEV_GUIDE.md` | Step-by-step local development guide — setup, Alembic issues, Docker rules, auth testing |
| `test.txt` | Stray scratch file — can be deleted |

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

---

## `apps/`

### `apps/api/app/`

#### `ai/`

AI subsystem. Most subdirectories are scaffolded but empty — only `knowledge/upload/` and `infrastructure/` are implemented.

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
| `cache/` | (empty) — planned semantic caching |
| `chunking/` | (empty) — planned document chunking |
| `documents/` | (empty) — planned document processing |
| `embeddings/` | (empty) — planned embedding generation |
| `reranking/` | (empty) — planned result reranking |
| `retrieval/` | (empty) — planned vector retrieval |
| `vectorstores/` | (empty) — planned vector store abstraction |

##### `ai/knowledge/upload/` — **Implemented**

| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `constants.py` | Upload limits: max file size, allowed MIME types |
| `enums.py` | `UploadStatus` (pending/validated/stored/failed), `UploadSource` (api/web/cli/system) |
| `exceptions.py` | Upload-specific exceptions |
| `interfaces.py` | Abstract interfaces for the upload pipeline |
| `models.py` | Upload-related data models |
| `schemas.py` | Pydantic schemas for upload requests and responses |
| `service.py` | `UploadService` — orchestrates validate → hash → S3 upload → DB write; logs `document.uploaded` with duration, `document.upload_failed` with traceback |
| `storage.py` | Upload-specific storage helpers |
| `types.py` | Type aliases used across the upload module |
| `validators.py` | `UploadValidator` — validates filename, content type, file size; logs `upload.validation_failed` with `reason` field for each rule |

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
| `v1/documents.py` | `POST /documents/upload` — validates filename, measures file size, delegates to `UploadService` |
| `v1/evaluation.py` | (empty) |
| `v1/feedback.py` | (empty) |
| `v1/health.py` | `GET /health` — checks PostgreSQL, Valkey, Qdrant connectivity |
| `v1/reports.py` | (empty) |

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
| `settings.py` | Pydantic `Settings` — all env vars; includes `auto_migrate` flag (default `false`) |
| `setup.py` | App factory and setup helpers |

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
| `upload.py` | FastAPI dependency providers for the upload workflow: `get_document_storage`, `get_file_hasher`, `get_document_repository`, `get_upload_service` |
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
| `document.py` | `Document` SQLAlchemy model — id, owner_id (FK→users), filename, storage_key, content_type, size_bytes, checksum, status |
| `enums.py` | `DocumentStatus` StrEnum — uploaded, processing, ready, failed, deleted |
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

---

#### `services/`

| File | Description |
|------|-------------|
| `__init__.py` | Package marker |
| `auth.py` | `AuthService.exchange_code()` — POSTs to Cognito `/oauth2/token`, supports PKCE and confidential clients; logs exchange start/success/failure |
| `user.py` | `UserService` — `sync_user`, `create_user`, `get_user_by_id/email`, `update_last_login`, `deactivate_user`; logs all lifecycle events including `user.not_found` and `user.deactivated` |

---

## `apps/web/`

Empty — planned Next.js frontend.

## `apps/worker/`

Empty — planned background worker.

---

## `benchmarks/`

Empty — planned performance benchmarks.

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
| `agent-architecture.md` | (empty) |
| `ai-architecture.md` | (empty) |
| `backend-architecture.md` | FastAPI backend architecture overview |
| `coding-standards.md` | (empty) |
| `database-design.md` | (empty) |
| `db-sessions.md` | SQLAlchemy session management patterns |
| `decision-boundaries.md` | (empty) |
| `decision-history.md` | History of architectural decisions |
| `engineering-principles.md` | (empty) |
| `evaluation-strategy.md` | (empty) |
| `frontend-architecture.md` | (empty) |
| `identity-architecture.md` | **Full auth architecture** — Cognito flow, per-request auth, implementation table, manual testing guide, AWS Console setup, common errors, issues encountered |
| `mcp-architecture.md` | (empty) |
| `observability-strategy.md` | (empty) |
| `project-constitution.md` | Project principles, goals, and constraints |
| `quality-strategy.md` | (empty) |
| `repository-structure.md` | Repository layer patterns |
| `scalability.md` | (empty) |
| `security.md` | (empty) |
| `system-overview.md` | High-level system overview |
| `tech-stack.md` | (empty) |

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

All empty — planned developer guides.

| File | Purpose |
|------|---------|
| `coding-standards.md` | (empty) |
| `contributing.md` | (empty) |
| `debugging.md` | (empty) |
| `style-guide.md` | (empty) |
| `testing.md` | (empty) |

---

### `docs/handoff/`

| File | Description |
|------|-------------|
| `chat-handoff1.md` | Context handoff document from session 1 |
| `chat-handoff2.md` | Context handoff document from session 2 |

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

### `docs/product/`

All empty — planned product docs.

| File | Purpose |
|------|---------|
| `faq.md` | (empty) |
| `features.md` | (empty) |
| `getting-started.md` | (empty) |
| `release-notes.md` | (empty) |

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
| `project-constitution.md` | Project principles and goals |
| `project-handbook.md` | Working agreements and team practices |

---

## `examples/`

Empty — planned usage examples and notebooks.

## `experiments/`

Empty — planned experimental code and prototypes.

---

## `infrastructure/`

| Path | Description |
|------|-------------|
| `database/` | Empty — planned DB provisioning scripts |
| `deployment/` | Empty — planned deployment manifests (k8s, etc.) |
| `docker/` | Empty — planned Dockerfiles |
| `monitoring/` | Empty — planned monitoring stack config |
| `scripts/` | Empty — planned infrastructure automation |
| `s3_configuration_guide.md` | Guide for configuring AWS S3 for document storage |

---

## `scripts/`

| File | Description |
|------|-------------|
| `dev.sh` | Dev startup script — runs `alembic upgrade head` then `uvicorn --reload`; prevents hot-reload from interrupting migrations |

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
| `conftest.py` | Shared pytest fixtures: `client` (TestClient), `test_engine` (async engine against `researchmind_test`), `db_session` |
| `api/test_health.py` | Tests `GET /api/v1/health` returns `healthy` when all services are up |
| `integration/test_user_repository.py` | Integration tests: create, get by email, exists, delete user via `UserRepository` |
| `integration/test_user_service.py` | Integration tests: create user, duplicate email conflict, not found, sync existing, deactivate |
| `integration/test_document_repository.py` | (empty) |
| `integration/test_document_service.py` | (empty) |
| `integration/test_memory.py` | (empty) |
| `integration/test_retriever.py` | (empty) |
| `integration/test_vector_store.py` | (empty) |
| `unit/test_settings.py` | Unit tests for Pydantic settings loading |
| `unit/test_prompt_builder.py` | (empty) |
| `evaluation/test_faithfulness.py` | (empty) |
| `evaluation/test_groundedness.py` | (empty) |
| `evaluation/test_reranking.py` | (empty) |
| `evaluation/test_retrieval_precision.py` | (empty) |
| `performance/test_embedding_speed.py` | (empty) |
| `performance/test_latency.py` | (empty) |
| `performance/test_qdrant_speed.py` | (empty) |
| `security/test_jailbreaks.py` | (empty) |
| `security/test_prompt_injection.py` | (empty) |
| `research/test_utils.py` | (empty) |

---

## `tools/`

Empty — planned developer tooling.

# ResearchMind AI — Local Development Guide

Step-by-step guide to get the project running locally from scratch. Covers every
issue encountered during initial setup so you don't hit them again.

---

## Prerequisites

Install these before starting:

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12.x (exactly) | `uv python install 3.12` |
| uv | latest | https://docs.astral.sh/uv/getting-started/installation/ |
| Docker Desktop | latest | https://www.docker.com/products/docker-desktop/ |
| Git | any | https://git-scm.com |

Verify:
```bash
python --version    # Python 3.12.x
uv --version
docker --version
```

---

## Step 1 — Clone and enter the repo

```bash
git clone <repo-url>
cd ResearchMind-AI
```

---

## Step 2 — Pin Python and create the virtual environment

```bash
uv python pin 3.12
uv venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows
```

---

## Step 3 — Install all dependencies

```bash
uv sync --all-groups
```

This installs both runtime and development dependencies (ruff, mypy, pytest, etc.).

---

## Step 4 — Configure the environment

```bash
cp .env.example .env
```

Open `.env` and fill in the required values. Minimum needed to run locally:

```env
DATABASE_URL=postgresql+psycopg://researchmind:researchmind@localhost:5432/researchmind
VALKEY_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
SECRET_KEY=any-random-string-here

# AWS Cognito — required for authentication endpoints
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=<your-pool-id>
COGNITO_APP_CLIENT_ID=<your-app-client-id>
COGNITO_DOMAIN=https://<your-prefix>.auth.us-east-1.amazoncognito.com

# AWS S3 — required for document upload endpoints
AWS_S3_BUCKET=<your-bucket-name>
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>

# Leave these blank (not empty string) if not using a custom S3 endpoint
# AWS_S3_ENDPOINT_URL=
```

> **Important:** Leave optional fields commented out or remove them entirely.
> An empty value like `AWS_S3_ENDPOINT_URL=` is read as an empty string `""`
> by pydantic, which causes boto3 to crash with `ValueError: Invalid endpoint: `.
> Either fill it in or leave the line out.

---

## Step 5 — Start infrastructure services

```bash
docker compose up -d
```

This starts three services using named Docker volumes (data persists across restarts):

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL 17 | 5432 | Primary database |
| Valkey (Redis) | 6379 | Cache / task queue |
| Qdrant | 6333, 6334 | Vector store |

Verify containers are running:
```bash
docker compose ps
```

---

## Step 6 — Create the test database

The integration test suite uses a separate `researchmind_test` database.
Create it once:

```bash
docker exec researchmind-postgres \
  psql -U researchmind -c "CREATE DATABASE researchmind_test;"
```

---

## Step 7 — Run database migrations

```bash
uv run alembic upgrade head
```

This applies all pending migrations in order. On a fresh database you should see:

```
INFO  Running upgrade  -> 43dc35ceb875, create users table (initial)
INFO  Running upgrade 43dc35ceb875 -> a97b3b8eee9f, create documents table
```

Verify tables exist:
```bash
psql postgresql://researchmind:researchmind@localhost:5432/researchmind -c "\dt"
```

Expected output:
```
 Schema |      Name       | Type  |    Owner
--------+-----------------+-------+-----------
 public | alembic_version | table | researchmind
 public | documents       | table | researchmind
 public | users           | table | researchmind
```

---

## Step 8 — Start the development server

Always use the startup script — **never run uvicorn directly** when developing
(see the Alembic section below for why):

```bash
./scripts/dev.sh
```

This runs `alembic upgrade head` first, then starts `uvicorn --reload`.
Migrations complete before the server starts, so hot-reload can never interrupt them.

The API is now available at:

| URL | Description |
|-----|-------------|
| http://localhost:8000 | API root |
| http://localhost:8000/docs | Swagger UI (interactive) |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/api/v1/health | Health check |

---

## Step 9 — Test authentication (no frontend needed)

The API uses AWS Cognito JWTs. To test auth endpoints from the terminal:

**1. Get an authorization code — open this URL in your browser:**
```
https://<COGNITO_DOMAIN>/login?client_id=<COGNITO_APP_CLIENT_ID>&response_type=code&scope=openid+email+profile&redirect_uri=http://localhost:3000/auth/callback
```

Log in. The browser will try to redirect to `http://localhost:3000/auth/callback?code=XXXX`.
That page won't load (no frontend), but **copy the `code` value from the URL bar**.

**2. Exchange the code for tokens:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/callback \
  -H "Content-Type: application/json" \
  -d '{"code": "PASTE_CODE_HERE", "redirect_uri": "http://localhost:3000/auth/callback"}'
```

**3. Use the `id_token` (not `access_token`) as the Bearer token:**
```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <id_token>"
```

Or paste the `id_token` into the **Authorize** button in Swagger UI.

> The authorization code is **single-use** and **expires in ~10 minutes**.
> If you get `401 invalid_grant`, get a fresh code from step 1.

---

## Alembic — Common Issues

### Issue 1: "Target database is not up to date"

```
ERROR [alembic.util.messaging] Target database is not up to date.
```

**Cause:** You tried to create a new migration with `alembic revision` but there
are unapplied migrations already in `alembic/versions/`. Alembic refuses to
generate a new migration on top of a stale database.

**Fix:** Apply pending migrations first, then generate:
```bash
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "your migration name"
```

---

### Issue 2: Table missing but Alembic says "head"

```
sqlalchemy.exc.ProgrammingError: relation "users" does not exist
```

Yet `alembic current` reports:
```
43dc35ceb875 (head)
```

**Cause:** The `alembic_version` table was stamped with the migration ID but the
actual DDL (CREATE TABLE) was never committed. This happens when:
- Docker was stopped mid-migration
- A hot-reload interrupted the migration (see Issue 3)
- `alembic stamp` was run manually by mistake

**Fix:**
```bash
uv run alembic stamp base   # clear the false stamp
uv run alembic upgrade head # actually run all migrations
```

Verify:
```bash
psql postgresql://researchmind:researchmind@localhost:5432/researchmind -c "\dt"
```

---

### Issue 3: Hot-reload interrupts migration

**Symptom:** Server starts, begins running a migration, then immediately restarts:
```
INFO  Running upgrade  -> 43dc35ceb875, create users table (initial)
WARNING:  WatchFiles detected changes in 'apps/api/app/core/lifespan.py'. Reloading...
INFO  Running upgrade  -> 43dc35ceb875, create users table (initial)   ← runs again!
```

**Cause:** Previously, migrations ran inside the FastAPI lifespan — meaning they
ran inside `uvicorn --reload`. When watchfiles detected a file change (e.g. you
just saved `lifespan.py`), it killed the process mid-migration, leaving the
database in a broken state.

**Fix (permanent):** Migrations no longer run in the lifespan. Use `./scripts/dev.sh`
which runs migrations first, then starts the server. The two processes are
cleanly separated.

```bash
# DO NOT do this:
uv run uvicorn app.main:app --reload   # ← migrations can be interrupted

# DO this instead:
./scripts/dev.sh   # ← migrations finish before uvicorn starts
```

---

### Issue 4: asyncpg connects to IPv6 but PostgreSQL is on IPv4

```
OSError: Multiple exceptions: [Errno 61] Connect call failed ('::1', 5432, ...)
```

**Cause:** On macOS, `localhost` resolves to `::1` (IPv6) first. asyncpg uses
this, but Docker only exposes PostgreSQL on `127.0.0.1` (IPv4).

**Fix:** Use `127.0.0.1` instead of `localhost` in `.env.test`:
```env
DATABASE_URL=postgresql+psycopg://researchmind:researchmind@127.0.0.1:5432/researchmind_test
VALKEY_URL=redis://127.0.0.1:6379
QDRANT_URL=http://127.0.0.1:6333
```

This only affects tests. The dev `.env` uses the psycopg driver which handles
the IPv6 fallback correctly.

---

## Docker — Data Persistence Rules

All three services use **named Docker volumes**, so data survives container restarts:

| Command | Effect on data |
|---------|---------------|
| `docker compose stop` | Containers stop — **data preserved** |
| `docker compose start` | Containers resume — **data intact** |
| `docker compose down` | Containers removed — **data preserved** (volumes kept) |
| `docker compose down -v` | Containers + volumes removed — **all data wiped** |

Only use `docker compose down -v` when you want a fully clean slate.
After running it, migrations will re-apply automatically via `./scripts/dev.sh`.

---

## AWS Cognito Setup

The API validates Cognito-issued JWTs. Full setup:

**In AWS Console → Cognito → User Pools → your pool → App clients → your client:**

| Setting | Required value |
|---------|---------------|
| OAuth 2.0 grant types | Authorization code grant ✓ |
| OpenID Connect scopes | openid, email, profile ✓ |
| Allowed callback URLs | `http://localhost:3000/auth/callback` |
| Client secret | Leave empty (public client) |

**Common token exchange errors:**

| Error | Cause | Fix |
|-------|-------|-----|
| `unauthorized_client` | Authorization code grant not enabled | Enable it in app client OAuth settings |
| `invalid_grant` | Code expired (>10 min) or already used | Get a fresh code |
| `invalid_grant` | `redirect_uri` mismatch | Ensure URI matches exactly (no trailing slash) |
| `401 Invalid token type` | Sent `access_token` instead of `id_token` | Use the `id_token` from the response |

---

## AWS S3 Setup (Document Uploads)

Required to use the `/api/v1/documents/upload` endpoint.

1. Create an S3 bucket in AWS Console
2. Create an IAM user with `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` on that bucket
3. Generate access keys for the IAM user
4. Add to `.env`:

```env
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

> **Do not** set `AWS_S3_ENDPOINT_URL` unless you are using a local S3 emulator
> (e.g. MinIO). Leave the line out entirely — an empty string breaks boto3.

---

## Running Tests

Tests use a separate `researchmind_test` database and must be run with `ENVIRONMENT=test`:

```bash
# All tests
ENVIRONMENT=test uv run pytest

# With coverage
ENVIRONMENT=test uv run pytest --cov=apps --cov-report=term-missing

# Integration tests only
ENVIRONMENT=test uv run pytest tests/integration/

# Single file
ENVIRONMENT=test uv run pytest tests/integration/test_user_service.py -v
```

> Tests require Docker to be running (PostgreSQL must be reachable).

---

## Code Quality

Run before committing:

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Both together (auto-fix + format)
uv run ruff check --fix . && uv run ruff format .

# Type check
uv run mypy apps/
```

Pre-commit hooks run these automatically on `git commit`:
```bash
# Install hooks (one-time setup)
uv run pre-commit install
```

---

## Adding a New Database Migration

1. Edit or create a SQLAlchemy model in `apps/api/app/models/`
2. Make sure the model is exported from `apps/api/app/models/__init__.py`
3. Generate the migration:
   ```bash
   uv run alembic revision --autogenerate -m "describe your change"
   ```
4. Review the generated file in `alembic/versions/` — always check autogenerated migrations before applying
5. Apply it:
   ```bash
   uv run alembic upgrade head
   ```

---

## Quick Reference

```bash
# Start everything from scratch
docker compose up -d
./scripts/dev.sh

# Fix broken migration state
uv run alembic stamp base && uv run alembic upgrade head

# Check current migration state
uv run alembic current

# Check what tables exist
psql postgresql://researchmind:researchmind@localhost:5432/researchmind -c "\dt"

# Run tests
ENVIRONMENT=test uv run pytest

# Lint + type check
uv run ruff check --fix . && uv run ruff format . && uv run mypy apps/
```

# ResearchMind AI

> Production-grade AI Research & Intelligence Platform

ResearchMind is an AI-powered research platform designed to help users search, analyze, reason over, and generate reports from both internal knowledge and external intelligence sources.

The platform combines:

- Retrieval-Augmented Generation (RAG)
- LangGraph Agent Workflows
- Persistent Memory
- Semantic Caching
- Model Context Protocol (MCP) Integration
- AI Evaluation Framework
- Observability & Monitoring
- Production-grade Architecture

---

## Project Status

Currently Under Active Development

Current Milestone: **Milestone 0.1 – Backend Foundation**

---

## Planned Architecture

```text
                     User
                      │
                      ▼
                Next.js Frontend
                      │
                      ▼
               FastAPI API Gateway
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   PostgreSQL      Valkey       Qdrant
                      │
                      ▼
              LangGraph Runtime
                      │
          ┌───────────┼────────────┐
          ▼           ▼            ▼
      RAG Engine   AI Agents   MCP Manager
                                      │
                     ┌────────────────┼────────────────┐
                     ▼                ▼                ▼
              Research MCP     Climate MCP    Earthquake MCP
```

---

## Tech Stack

### Backend

- Python 3.12
- FastAPI
- uv
- SQLAlchemy
- Alembic

### AI

- LangGraph
- LlamaIndex
- LangSmith

### Frontend

- Next.js
- TypeScript
- Tailwind CSS

### Infrastructure

- Docker
- PostgreSQL
- Valkey
- Qdrant

---

## Repository Structure

```text
apps/
agents/
services/
shared/
docs/
tests/
infrastructure/
datasets/
experiments/
benchmarks/
scripts/
tools/
```

---

## Roadmap

- Project Planning
- Architecture Design
- Backend Foundation (in progress)
- RAG Pipeline
- AI Agents
- MCP Integration
- Evaluation Framework
- Production Deployment

---

## Quick Start

### Prerequisites

- Git
- Docker Desktop
- Python 3.12
- Node.js 22 LTS
- uv

Verify your installation:

```bash
python --version
node -v
docker --version
uv --version
```

---

### 1. Clone the Repository

```bash
git clone <repo-url>
cd ResearchMind-AI
```

---

### 2. Install Python

```bash
uv python install 3.12
uv python pin 3.12
```

---

### 3. Create Virtual Environment

```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

---

### 4. Install Dependencies

```bash
uv sync --all-groups
```

---

### 5. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values. With the default Docker setup:

```env
DATABASE_URL=postgresql+psycopg://researchmind:researchmind@localhost:5432/researchmind
VALKEY_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
SECRET_KEY=<generate a random string>
```

---

### 6. Start Infrastructure

```bash
docker compose up -d
```

This starts PostgreSQL (5432), Valkey (6379), and Qdrant (6333/6334).

---

### 7. Create the Test Database

The integration tests run against a separate database. Create it once:

```bash
docker exec researchmind-postgres \
  psql -U researchmind -c "CREATE DATABASE researchmind_test;"
```

---

### 8. Run Database Migrations

```bash
uv run alembic upgrade head
```

### fix alembic issues
```
uv run alembic stamp base && uv run alembic upgrade head 2>&1
```

---

### 9. Start the Backend

```bash
./scripts/dev.sh
```

### 10. Run workers locally
```bash
python -m apps.worker.main
```

This runs migrations first, then starts the server with hot-reload. Running migrations inside `uvicorn --reload` directly causes hot-reload to interrupt the migration mid-run — always use this script for local development.

`dev.sh` also runs `alembic check` before starting the server, so it will fail fast if your models have drifted from the last migration.

**From now on: whenever you change a model, run `uv run alembic revision --autogenerate -m "..."`, read the generated file, then `./scripts/dev.sh` as usual.**

---

### Open

| URL | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:6333/dashboard | Qdrant Dashboard |

---

## Testing

Tests require `ENVIRONMENT=test` so they connect to `researchmind_test` instead of the development database.

### Run all tests

```bash
ENVIRONMENT=test uv run pytest
```

### Run with coverage report

```bash
ENVIRONMENT=test uv run pytest --cov=apps --cov-report=term-missing
```

### Run only unit tests

```bash
ENVIRONMENT=test uv run pytest tests/unit/
```

### Run only integration tests

```bash
ENVIRONMENT=test uv run pytest tests/integration/
```

### Run a single test file

```bash
ENVIRONMENT=test uv run pytest tests/integration/test_user_service.py -v
```

---

## Code Quality

### Lint

```bash
uv run ruff check .
```

### Format

```bash
uv run ruff format .
```

### Lint and format together

```bash
uv run ruff check --fix . && uv run ruff format .
```

### Type check

```bash
uv run mypy apps/
```

---

## Database Migrations

### Apply all pending migrations

```bash
uv run alembic upgrade head
```

### Create a new migration (auto-generated from model changes)

```bash
uv run alembic revision --autogenerate -m "describe your change"
```

### Check current migration state

```bash
uv run alembic current
```

### Roll back one migration

```bash
uv run alembic downgrade -1
```

### Generate the Migration for documents table
```
uv run alembic revision --autogenerate -m "create documents table"
```

### Apply the Migration
```
uv run alembic stamp base
uv run alembic upgrade head
```

### Check that the table exists:
```
docker exec -it researchmind-postgres psql -U researchmind -d researchmind

\d documents
```

### Troubleshooting: table missing but Alembic says "head"

If `alembic current` reports the migration as applied but queries fail with
`relation "X" does not exist`, the `alembic_version` table was stamped without
the migration actually running. Fix it by clearing the stamp and re-applying:

```bash
uv run alembic stamp base   # remove the false stamp
uv run alembic upgrade head # run the migration for real
```

Verify tables exist:

```bash
psql postgresql://researchmind:researchmind@localhost:5432/researchmind -c "\dt"
```

---

## Docker Data Persistence

PostgreSQL, Valkey, and Qdrant all use **named Docker volumes** so data survives container restarts.

| Command | Effect on data |
|---------|---------------|
| `docker compose stop` | Containers stop — **data preserved** |
| `docker compose start` | Containers resume — **data intact** |
| `docker compose down` | Containers removed — **data preserved** (volumes kept) |
| `docker compose down -v` | Containers + volumes removed — **all data wiped** |

Only use `docker compose down -v` when you want a completely clean slate (e.g. resetting a corrupted DB).

**Migrations run automatically on startup.** The API calls `alembic upgrade head` during the lifespan startup sequence, so even after a full `down -v`, just run `docker compose up -d` and start the backend — tables will be recreated automatically.

---

## Benchmark reports running

1. Chunking
```
uv run python -m benchmarks.runner chunking --dataset benchmarks/datasets/research-papers --output benchmarks/chunking/reports

# optionally: --output benchmarks/chunking/reports
```

2. Retrieval (dense vs. sparse vs. hybrid)
```
uv run python -m benchmarks.runner retrieval --dataset benchmarks/datasets/research-papers
```

Builds a dedicated `benchmark_retrieval` Qdrant collection from the
benchmark corpus (dropped and recreated on every run, so it never
touches production data), then evaluates dense (Voyage AI), sparse
(SPLADE), and hybrid (Reciprocal Rank Fusion of dense + sparse)
retrieval against the 20-query ground truth set in
`benchmarks/datasets/research-papers/retrieval_queries.json`, reporting
Recall@5/10/20, Precision@5/10, MRR, and avg/P95/P99 latency per ADR-020.
Requires a reachable Qdrant instance and a configured Voyage AI API key,
and makes real embedding API calls — unlike the chunking benchmark, it
is not a purely offline/local run. Report written to
`benchmarks/reports/retrieval/`.

**Current results (5 documents, 20 queries) are not conclusive, and RRF
did not improve anything on this dataset.** Dense, sparse, and hybrid
all hit Recall@5/10/20 = 1.0 and Precision@5/10 = 0.2/0.1 identically.
Hybrid's MRR (0.925) was actually slightly *lower* than both dense
(0.95) and sparse (0.975) alone, and its latency (~324ms avg) is
dominated by the dense leg since hybrid still pays the Voyage API call
plus local sparse inference plus fusion overhead. This is exactly the
outcome ADR-020's Decision Gate warns about: with only 5 topically
distinct documents, every query has one obviously-correct answer, so
there's no ranking ambiguity for RRF to actually resolve — fusing two
retrievers that already agree can only add latency, not lift. See the
TODO below; this does **not** mean Hybrid is a dead end, it means this
dataset can't yet tell us whether it is.

### TODO: Improve the retrieval benchmark dataset

- **Increase documents:** 5 → 20-50. A 5-document corpus makes it
  trivial to find the right document regardless of retrieval strategy.
- **Increase queries:** 20 → 100.
- **Add harder query categories** — the current set is too easy:
  - *Semantic, no lexical overlap* — e.g. "How can retrieval systems
    improve factual grounding?" where the source document never uses
    the phrase "factual grounding." Dense should win.
  - *Exact/rare acronym* — e.g. "BM42." Sparse should win.
  - *Multi-hop* — e.g. "Compare sparse and dense retrieval tradeoffs."
    Both retrievers may struggle; useful for spotting real weaknesses.
  - *Broad/architectural* — e.g. "Explain modern RAG architectures."
    Dense should dominate.
- **Most important improvement: move to chunk-level relevance**
  (`relevant_chunk_ids` instead of `relevant_documents`, per
  `docs/architecture/retrieval-benchmarking-strategy.md`'s Dataset
  Format v2). Document-level relevance inflates scores whenever a query
  has only a handful of candidate documents to choose from, exactly
  what's happening now.

**Hybrid Retrieval (RRF fusion) is now implemented** (`/api/v1/retrieve/hybrid`,
`RetrievalService.search_hybrid`), so this is no longer a build decision —
it's a tuning question. The dataset improvements above are what's needed
to find out whether RRF actually helps in this system, and if so, under
which query categories.

---

## Authentication (AWS Cognito)

ResearchMind uses AWS Cognito Hosted UI for authentication. The API validates
Cognito-issued JWTs on every protected request — it never handles passwords or
sessions itself.

See [`docs/architecture/identity-architecture.md`](docs/architecture/identity-architecture.md)
for the full flow, implementation details, and AWS Console setup checklist.

### Required `.env` values

```env
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=<your-pool-id>
COGNITO_APP_CLIENT_ID=<your-app-client-id>
COGNITO_DOMAIN=https://<your-prefix>.auth.us-east-1.amazoncognito.com
```

`COGNITO_DOMAIN` is the Hosted UI domain — find it in the AWS Console under
**User Pools → App integration → Domain**.

### Testing auth without a frontend

You can exercise the full auth flow using only a browser and curl:

1. Open the Cognito login URL in your browser, log in, and copy the `?code=`
   from the redirect URL bar (the page won't load — no frontend — but the code is there).

2. Exchange the code:

```bash
curl -X POST http://localhost:8000/api/v1/auth/callback \
  -H "Content-Type: application/json" \
  -d '{"code": "PASTE_CODE_HERE", "redirect_uri": "http://localhost:3000/auth/callback"}'
```

3. Use the returned `id_token` (not `access_token`) as the Bearer token:

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <id_token>"
```

Or paste the `id_token` into the **Authorize** button in Swagger at
`http://localhost:8000/docs`.

---

## Inspect queues in valkey locally

```
docker ps
docker exec -it researchmind-valkey valkey-cli
```

### Inspect the queue
```
LRANGE document-processing 0 -1
```

## License

MIT License

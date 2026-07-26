# ResearchMind AI

> An AI research platform that retrieves, reasons over, and reports on both your own documents and the live web — with grounded citations and a human approving every consequential step.

ResearchMind lets you upload documents, chat with them, and escalate any question into a multi-step **Deep Research** run: the system plans a research task, gathers evidence across multiple waves of retrieval (and, with your approval, live web search), synthesizes a cited draft, reviews it against the evidence for unsupported claims, and produces a downloadable PDF report — pausing for your approval at each consequential step along the way.

## Meet ResearchMind
![research_mind_landing](docs/images/image.png)

## Your analytics, at a glance
![research_mind_dashboard](docs/images/image-1.png)

## Build your paper library
![document_ingestion](docs/images/image-12.png)

## Brainstorm, search the web, find papers
![chat_view](docs/images/image-2.png)

## Ask your papers, get a grounded answer
![linear_research](docs/images/image-3.png)

## Go deep: multi-step reasoning, web access, related papers
![deep_research_plan_approval](docs/images/image-4.png)

## Approve web search — or skip approval entirely
![web_search_approval_step](docs/images/image-5.png)

## Review the summary before the report drops
![summary_approval](docs/images/image-6.png)

## Every claim, cited
![cited_sources](docs/images/image-7.png)

## Discover related papers
![related_paper_search](docs/images/image-8.png)
![research_papers](docs/images/image-11.png)

## Your research report, ready
![research_report](docs/images/image-9.png)
---

## Project Status

Active development. The backend (`apps/api`) is well past scaffolding — retrieval, generation, Deep Research, memory, guardrails, and observability are all implemented and covered by a real test suite (~1,160+ tests). See `docs/project/01-current-state.md` and `docs/adrs/` for the detailed, up-to-date build log.

---

## Core Capabilities

| Area | What's implemented |
|---|---|
| **Three research surfaces** | Chat (conversational, optional live web search), Linear Research (single-shot grounded Q&A with citations), Deep Research (multi-wave planning + evidence gathering + synthesis + review + PDF) — see `docs/workflows/research-workflow.md` |
| **Human-in-the-loop checkpoints** | Deep Research pauses for explicit approval at 3 points: plan approval, web-search approval, report approval — never escalates or spends a web search without consent |
| **Retrieval** | Qdrant-native hybrid retrieval (dense Voyage AI embeddings + sparse SPLADE, Reciprocal Rank Fusion), reranking platform, metadata filtering |
| **Document ingestion** | Async pipeline: upload → storage → queue → worker → parse (Docling: PDF/DOCX/Markdown/TXT) → metadata/statistics enrichment → chunk → embed → index — see `docs/workflows/document-ingestion.md` |
| **Generation runtime** | Multi-provider (Groq, others) with routing strategies, 3-tier semantic caching, schema/hallucination/runtime validation, and a guardrails layer (input/retrieval/generation/runtime stages) that can warn, block, escalate, or trigger regeneration |
| **Memory** | Session, user, semantic, and research memory (Valkey + PostgreSQL + Qdrant), injected into prompts and extracted from completed turns |
| **Web search & MCP** | Tavily web search (shared by Chat and Deep Research, approval-gated in Deep Research); MCP client to an external Research Intelligence paper-search server |
| **Observability** | Structured logs (`structlog`, request-id correlated), LangSmith tracing per generation, Prometheus + Grafana (4 dashboards, 5 alert rules) — see `docs/monitoring/` |
| **Evaluation & benchmarking** | Deterministic groundedness/hallucination detection live in production; offline engineering benchmarks for chunking/embeddings/retrieval/reranking/generation with regression detection — see `docs/evaluation/` |
| **Auth** | AWS Cognito Hosted UI, JWT-validated on every protected request |

---

## Architecture

```text
                          User
                           │
                           ▼
                    Next.js Frontend  (apps/web)
                           │
                           ▼
                  FastAPI API Gateway  (apps/api)
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                   ▼
   PostgreSQL           Valkey              Qdrant
  (relational,      (cache, queues,     (vector store,
   memory, usage)    rate limits)        hybrid retrieval)
                           │
                           ▼
                  AI Platform  (app/ai/)
                           │
   ┌───────────┬───────────┼───────────┬────────────┐
   ▼           ▼           ▼           ▼            ▼
Knowledge   Generation   Research    Memory      Guardrails
(ingest/   Runtime      Runtime    Platform    & Validation
retrieve)  (routing,    (LangGraph                 │
           caching,      multi-wave                ▼
           validation)   Deep Research)      Observability
                           │                  (LangSmith,
                           ▼                   Prometheus,
                    External tools:             Grafana)
                 Tavily Web Search,
              Research Intelligence MCP
```

Background workers (`apps/worker/`) run document processing and Deep Research execution independently of the API process.

---

## Tech Stack

### Backend

- Python 3.12, `uv`, FastAPI, SQLAlchemy, Alembic
- LangGraph (Deep Research state machine), LangSmith (tracing)
- Groq (generation), Voyage AI (dense embeddings), FastEmbed/SPLADE (sparse embeddings)
- Qdrant (vector store), PostgreSQL (relational + memory), Valkey (cache/queue/rate-limit), Docling (document parsing)
- `mcp` client, Tavily (web search)
- Prometheus + Grafana (metrics/dashboards), `structlog` (structured logging)

### Frontend

- Next.js 15, React 19, TypeScript, Tailwind CSS

### Infrastructure

- Docker Compose (PostgreSQL, Valkey, Qdrant, Prometheus, Grafana)
- AWS Cognito (auth), AWS S3 (document storage)

---

## Repository Structure

```text
apps/
  api/          FastAPI backend — app/ai/ (retrieval, generation, research, memory, guardrails,
                observability), app/api/v1/ (routes), app/services/, app/repositories/
  worker/       Background workers: document processing, Deep Research execution
  web/          Next.js frontend
alembic/        Database migrations
benchmarks/     Offline engineering benchmarks (chunking/embeddings/retrieval/reranking/generation)
datasets/       Golden/raw/processed benchmark datasets
docs/           ADRs, architecture, workflows, evaluation, monitoring, runbooks, guides
infra/          Prometheus/Grafana provisioning and dashboards
prds/           Product/design requirement docs
scripts/        Dev/setup/benchmark scripts
tests/          unit/, integration/, api/, evaluation/, security/, performance/
```

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

This runs migrations first, then starts the server with hot-reload. Running migrations inside `uvicorn --reload` directly causes hot-reload to interrupt the migration mid-run — always use this script for local development.

`dev.sh` also runs `alembic check` before starting the server, so it will fail fast if your models have drifted from the last migration.

### 10. Run workers locally

Document processing worker:

```bash
python -m apps.worker.main
```

Approved Deep Research Runtime worker:

```bash
python -m apps.worker.research_runtime_main
```

This process runs `RESEARCH_RUNTIME_WORKER_CONCURRENCY` (default `1`) concurrent claim lanes, each with its own DB session. The Postgres outbox (`SELECT ... FOR UPDATE SKIP LOCKED`) also makes it safe to run multiple copies of this same process/container for true horizontal scaling — both knobs compose.

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

---

## Documentation

Start here, depending on what you need:

| I want to... | Look at |
|---|---|
| Understand a specific design decision | `docs/adrs/` (37+ ADRs, e.g. ADR-034 Deep Research routing, ADR-036 web search, ADR-037 MCP paper search) |
| Understand how a platform is built | `docs/platforms/`, `docs/architecture/` |
| Understand an end-to-end flow | `docs/workflows/` (research, document ingestion, report generation, feedback loop) |
| Check what's actually tested/evaluated | `docs/evaluation/`, `docs/guides/testing.md` |
| Set up or debug Prometheus/Grafana/LangSmith | `docs/monitoring/`, `docs/runbooks/prometheus-grafana-observability.md` |
| Debug a running instance | `docs/guides/debugging.md`, `docs/runbooks/troubleshooting.md` |
| Follow repo coding conventions | `docs/guides/coding-standards.md` |
| See current build status / what's next | `docs/project/01-current-state.md`, `docs/roadmap/` |

### Monitoring dashboards

```bash
docker compose up -d prometheus grafana
```

| Service | URL | Credentials |
|---|---|---|
| Grafana | http://localhost:3001 | `admin` / `admin` (`GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`) |
| Prometheus | http://localhost:9090 | — |
| Raw metrics exposition | http://localhost:8000/metrics | — |

Dashboards, datasource, and alert rules are all auto-provisioned from `infra/observability/` — nothing to click together by hand. Four dashboards ship under the **ResearchMind** folder: Overview, Generation Runtime, Research Tools, Memory Runtime. See `docs/monitoring/grafana.md` and `docs/runbooks/prometheus-grafana-observability.md` for the full panel/alert reference.

![grafana dashboard](docs/images/image-10.png)

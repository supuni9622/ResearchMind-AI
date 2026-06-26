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

---

### 9. Start the Backend

```bash
uv run uvicorn app.main:app --reload
```

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

---

## License

MIT License

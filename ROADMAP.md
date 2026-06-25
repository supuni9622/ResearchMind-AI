# ResearchMind AI

> Production-grade AI Research & Intelligence Platform

ResearchMind is an AI-powered research platform designed to help users search, analyze, reason over, and generate reports from both internal knowledge and external intelligence sources.

The platform combines:

- 📚 Retrieval-Augmented Generation (RAG)
- 🤖 LangGraph Agent Workflows
- 🧠 Persistent Memory
- ⚡ Semantic Caching
- 🔌 Model Context Protocol (MCP) Integration
- 📊 AI Evaluation Framework
- 📈 Observability & Monitoring
- 🔒 Production-grade Architecture

---

## Project Status

🚧 **Currently Under Active Development**

Current Milestone:

> **Milestone 0.1 – Backend Foundation**

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

- ✅ Project Planning
- ✅ Architecture Design
- 🚧 Backend Foundation
- ⏳ RAG Pipeline
- ⏳ AI Agents
- ⏳ MCP Integration
- ⏳ Evaluation Framework
- ⏳ Production Deployment

---

## 🚀 Quick Start

### Prerequisites

Before starting, install:

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

### Clone the Repository

```bash
git clone <repo-url>

cd ResearchMind-AI
```

---

### Install Python

```bash
uv python install 3.12
uv python pin 3.12
```

---

### Create Virtual Environment

```bash
uv venv

source .venv/bin/activate
```

---

### Install Dependencies

```bash
uv sync
```

---

### Configure Environment

```bash
cp .env.example .env
```

---

### Start Infrastructure

```bash
docker compose up -d
```

---

### Run the Backend

```bash
uv run uvicorn app.main:app \
    --reload \
    --app-dir apps/api
```

---

### Open

Swagger

```
http://localhost:8000/docs
```

Qdrant Dashboard

```
http://localhost:6333/dashboard
```

## License

MIT License
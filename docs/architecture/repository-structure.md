# Repository Structure

## Overview

ResearchMind AI is organized as a monorepo.

The repository separates applications, shared libraries, infrastructure, documentation, datasets, and experiments into independent top-level directories.

This structure keeps responsibilities clear while allowing the project to grow without frequent restructuring.

---

# Top-Level Structure

```text
ResearchMind-AI/

├── apps/
├── agents/
├── benchmarks/
├── datasets/
├── docs/
├── examples/
├── experiments/
├── infrastructure/
├── scripts/
├── services/
├── shared/
├── tests/
├── tools/
│
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
├── README.md
├── ROADMAP.md
└── PROJECT_STATUS.md
```

---

# Directory Responsibilities

## apps/

Contains deployable applications.

Current

- api/
- web/ (planned)

---

## agents/

AI agent implementations.

Examples

- Research Agent
- Planner Agent
- Report Agent
- Evaluation Agent

---

## services/

Business logic.

Responsibilities

- RAG
- AI orchestration
- Memory
- Reports

---

## shared/

Reusable utilities shared across applications.

Examples

- Common models
- Utilities
- Shared types

---

## infrastructure/

Infrastructure configuration.

Examples

- Docker
- Monitoring
- Deployment

---

## datasets/

Sample documents and datasets for development and testing.

---

## benchmarks/

Evaluation reports and performance benchmarks.

---

## docs/

Project documentation.

---

## tests/

Automated tests.

---

## scripts/

Developer automation scripts.

---

## experiments/

Research prototypes that are not production-ready.

---

# Design Principles

The repository follows several guiding principles.

- Separation of concerns
- Modular architecture
- Independent evolution
- Clear ownership
- Production readiness

---

# Future Growth

The current repository structure is designed to support future applications and services without major restructuring.

Examples

- Mobile application
- MCP SDK
- CLI tools
- Worker processes
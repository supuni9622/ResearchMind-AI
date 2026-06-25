# Documentation Standards

## Purpose

This document defines the documentation standards for the ResearchMind AI repository.

The goal is to ensure that every document follows a consistent structure, writing style, and level of technical quality.

Documentation should evolve alongside the codebase and always reflect the current implementation.

---

# Documentation Principles

ResearchMind documentation should be:

- Accurate
- Concise
- Practical
- Version controlled
- Easy to navigate
- Written for engineers
- Maintained together with the code

Documentation is considered part of the product.

A feature is **not complete** until its documentation has been updated.

---

# Documentation Categories

The repository is organized into several documentation categories.

```
docs/

architecture/
engineering-journal/
concepts/
api/
deployment/
runbooks/
adrs/
standards/
```

Each category has a specific responsibility.

---

# Architecture

Purpose

Explain **how the system is designed**.

Examples

- Backend Architecture
- System Architecture
- Repository Structure
- AI Pipeline
- MCP Architecture

Architecture documents answer:

> Why is the system designed this way?

---

# Engineering Journal

Purpose

Record implementation progress.

Each milestone has its own engineering journal.

Example

```
030-backend-foundation.md
```

Engineering journals answer:

- What was implemented?
- Why was it implemented?
- Lessons learned
- Important design decisions

These documents should be chronological.

---

# Concepts

Purpose

Explain important engineering concepts learned during implementation.

Examples

- FastAPI Lifespan
- SQLAlchemy Engine
- Dependency Injection
- API Contracts

Concept documents should teach the concept independently of the project.

---

# ADRs

Architecture Decision Records.

Purpose

Record important architectural decisions.

Each ADR should include:

- Context
- Decision
- Consequences

ADRs describe **why** a decision was made.

---

# API Documentation

Purpose

Document public API endpoints.

Include:

- Endpoint
- Method
- Request
- Response
- Status Codes
- Example Payloads

API documentation complements OpenAPI documentation.

---

# Runbooks

Purpose

Operational procedures.

Examples

- Local Development
- Troubleshooting
- Production Deployment
- Backup & Recovery

Runbooks explain operational tasks.

---

# Markdown Standards

Use ATX headings.

Correct

```markdown
# Title

## Section

### Subsection
```

Avoid skipping heading levels.

---

# Line Length

Aim for readable paragraphs.

Avoid excessively long lines.

Wrap long code examples when appropriate.

---

# Lists

Use unordered lists for collections.

Example

```markdown
- PostgreSQL
- Valkey
- Qdrant
```

Use ordered lists only when sequence matters.

---

# Code Blocks

Always specify the language.

Correct

````markdown
```python
print("Hello")
```
# Decision History

## Purpose

This document records important architectural decisions made during the evolution of ResearchMind AI.

Unlike Architecture Decision Records (ADRs), this document provides a chronological summary of design changes and the reasoning behind them.

---

# Decision 001

## Monorepo Architecture

Decision

ResearchMind will use a monorepo.

Reason

- Shared code
- Simplified development
- Easier dependency management
- Centralized documentation

---

# Decision 002

## Independent MCP Repositories

Decision

External MCP servers will live in separate repositories.

Reason

- Loose coupling
- Independent deployment
- Independent versioning
- Reusability

ResearchMind acts as an MCP client rather than an MCP server.

---

# Decision 003

## FastAPI

Decision

FastAPI was selected as the backend framework.

Reason

- Excellent async support
- Dependency Injection
- Automatic OpenAPI generation
- Strong typing
- Production maturity

---

# Decision 004

## Lifespan over Global Objects

Decision

Application resources are initialized using FastAPI Lifespan.

Reason

- Better lifecycle management
- Predictable startup
- Graceful shutdown
- Easier testing

---

# Decision 005

## app.state

Decision

Infrastructure clients are stored in `app.state`.

Reason

- Eliminates global singletons
- Centralized ownership
- Request-safe resource sharing

---

# Decision 006

## Configuration Separation

Decision

Application constants and environment configuration are separated.

```
constants.py
settings.py
```

Reason

Configuration changes between environments.

Constants describe the application itself.

---

# Decision 007

## Middleware Registration

Decision

Middleware registration is centralized.

```
middleware/register.py
```

Reason

- Cleaner application bootstrap
- Easier maintenance
- Explicit middleware ordering

---

# Decision 008

## API Contracts

Decision

Every endpoint returns standardized Pydantic response models.

Reason

- Consistent frontend integration
- Strong typing
- Better documentation
- Simplified testing

---

# Decision 009

## Global Exception Handling

Decision

Application exceptions are handled centrally.

Reason

- Consistent error responses
- Cleaner business logic
- Centralized logging

---

# Future Decisions

Future architectural decisions will be captured both here and as individual ADRs where appropriate.

This document provides a high-level evolution of the system, while ADRs preserve detailed decision context.
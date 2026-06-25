# ADR-004: FastAPI Application State for Shared Infrastructure Resources

## Status

Accepted

---

## Date

2026-06-25

---

## Authors

ResearchMind AI Engineering Team

---

# Related ADRs

- ADR-002: FastAPI as the Backend Framework
- ADR-003: FastAPI Lifespan for Application Resource Management
- ADR-005: API Contracts

---

# Related Concepts

- 001 FastAPI Lifespan
- 004 Dependency Injection
- 007 FastAPI Application State

---

# Related Architecture Documents

- Backend Architecture
- Decision History

---

# Context

ResearchMind AI depends on several long-lived infrastructure components that should be shared across the entire application.

Current infrastructure includes:

- PostgreSQL Engine
- Valkey Client
- Qdrant Client

Future infrastructure will include:

- LangSmith Client
- MCP Client Registry
- Celery Application
- Object Storage Client
- LLM Provider Registry
- Background Scheduler

These resources are expensive to create and should not be recreated for every incoming request.

A consistent mechanism is required to store and access these shared resources throughout the application lifecycle.

---

# Problem Statement

Where should application-wide infrastructure resources be stored after they are initialized?

The solution should:

- avoid global variables
- support dependency injection
- clearly define ownership
- simplify testing
- support future infrastructure
- integrate naturally with FastAPI

---

# Decision

ResearchMind AI stores shared infrastructure resources inside **FastAPI's application state** (`app.state`).

Resources are created during application startup by the Lifespan manager and attached to the application instance.

Example:

```python
app.state.engine = engine
app.state.valkey = valkey_client
app.state.qdrant = qdrant_client
```

Application state becomes the central location for shared infrastructure.

---

# Why This Decision Was Made

## Explicit Ownership

Resources belong to the application itself.

Instead of existing as hidden global variables, infrastructure becomes an explicit part of the FastAPI application instance.

Ownership is therefore clear.

```
FastAPI Application
        │
        ▼
app.state
        │
        ├── PostgreSQL
        ├── Valkey
        └── Qdrant
```

---

## Better Testability

Each test can create an isolated FastAPI application with its own application state.

Example:

```
Test A

FastAPI Instance A

↓

app.state.engine

--------------------

Test B

FastAPI Instance B

↓

app.state.engine
```

Resources remain isolated between tests.

---

## Elimination of Global Singletons

Global variables create hidden dependencies.

Example:

```python
engine = create_async_engine(...)
```

Every module can access the engine without knowing where it came from.

This makes testing and dependency management difficult.

Application state removes this problem by making dependencies explicit.

---

## Integration with Dependency Injection

Application state works naturally with FastAPI's dependency injection system.

Typical flow:

```
Application Startup
        │
        ▼
Lifespan
        │
        ▼
Create Resources
        │
        ▼
app.state
        │
        ▼
Dependency
        │
        ▼
Route Handler
```

Infrastructure remains centralized while requests receive only the resources they need.

---

## Future Expansion

The application state can grow as the platform evolves.

Future shared resources may include:

- LLM Client Manager
- MCP Registry
- Prompt Registry
- Embedding Models
- Feature Flags
- Metrics Registry

The architecture remains unchanged regardless of the number of resources.

---

# Alternatives Considered

## Global Variables

Example

```python
engine = create_async_engine(...)
```

### Advantages

- Very simple
- Minimal code

### Disadvantages

- Hidden dependencies
- Difficult testing
- Resource ownership unclear
- Complicated cleanup
- Poor scalability

Rejected.

---

## Singleton Classes

Example

```python
Database.get_instance()
```

### Advantages

- Shared resource
- Familiar design pattern

### Disadvantages

- Global mutable state
- Difficult mocking
- Tight coupling
- Hidden lifecycle

Rejected.

---

## Creating Resources Per Request

Example

```
Request

↓

Create Engine

↓

Create Session

↓

Query

↓

Destroy
```

### Advantages

- No shared state

### Disadvantages

- Extremely inefficient
- High latency
- Increased connection overhead

Rejected.

---

# Consequences

## Positive

- Explicit ownership
- Improved testability
- Better dependency management
- Cleaner architecture
- Easier future expansion
- Natural FastAPI integration

---

## Negative

- Developers must understand `app.state`
- Requires proper initialization during startup
- Resources must be attached before requests are served

These trade-offs are considered acceptable because they significantly improve maintainability.

---

# Relationship with Lifespan

Application state does **not** create resources.

Its responsibility is only to store them.

```
Lifespan

↓

Create Resources

↓

app.state

↓

Dependency Injection

↓

Application
```

This separation of responsibilities makes the architecture easier to understand and maintain.

---

# Relationship with Dependency Injection

Dependencies retrieve resources from the application state.

Example flow:

```
Request

↓

Depends(get_db)

↓

app.state.engine

↓

Create AsyncSession

↓

Route Handler
```

This allows request-scoped objects to reuse application-scoped infrastructure.

---

# ResearchMind Implementation

Current shared resources include:

- PostgreSQL Engine
- Valkey Client
- Qdrant Client

Future milestones will extend the application state to include:

- LangSmith
- Celery
- MCP Registry
- LLM Registry
- Background Scheduler

No architectural changes will be required.

---

# Implementation Notes

Application state is accessed through the FastAPI application instance.

Infrastructure resources are attached during application startup and remain available until shutdown.

Business logic never creates these resources directly.

Instead, it consumes them through dependency injection.

This separation keeps responsibilities clear throughout the backend.

---

# Future Considerations

Future improvements may include:

- Typed application state
- Resource registry
- Automatic startup validation
- Lazy initialization for optional services
- Health verification during startup

The current architecture supports these improvements without modification.

---

# Decision Summary

ResearchMind AI stores long-lived infrastructure resources inside FastAPI's `app.state`.

This approach eliminates global state, improves testability, integrates naturally with dependency injection, and provides a scalable foundation for managing shared infrastructure as the platform evolves.

The combination of **Lifespan**, **Application State**, and **Dependency Injection** establishes a clear ownership model that will support every future subsystem within ResearchMind AI.
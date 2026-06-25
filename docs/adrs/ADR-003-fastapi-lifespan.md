# ADR-003: FastAPI Lifespan for Application Resource Management

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
- ADR-004: Application State
- ADR-007: Middleware Registration

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

ResearchMind AI depends on several infrastructure services that are expensive to initialize and should remain available throughout the lifetime of the application.

Current infrastructure includes:

- PostgreSQL
- Valkey
- Qdrant

Future infrastructure will include:

- LangSmith
- Celery
- Background Workers
- Object Storage
- External MCP Clients
- LLM Providers

These resources should be initialized once when the application starts and released gracefully when the application shuts down.

The application requires a predictable lifecycle for creating and cleaning up these shared resources.

---

# Problem Statement

How should application-wide resources be initialized and managed throughout the lifetime of the FastAPI application?

The solution should:

- initialize resources once
- share resources safely
- support graceful shutdown
- simplify testing
- avoid global state
- scale as the platform grows

---

# Decision

ResearchMind AI uses **FastAPI Lifespan** to manage the application's lifecycle.

Infrastructure resources are created during application startup and released during application shutdown.

FastAPI's `lifespan` context manager becomes the single entry point for application initialization.

Example:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    ...
    yield
    ...
```

---

# Why This Decision Was Made

## Predictable Startup

Application startup follows a well-defined sequence.

```
Application Starts
        │
        ▼
Load Configuration
        │
        ▼
Configure Logging
        │
        ▼
Initialize PostgreSQL
        │
        ▼
Initialize Valkey
        │
        ▼
Initialize Qdrant
        │
        ▼
Application Ready
```

Every resource is available before the first request is processed.

---

## Graceful Shutdown

When the application terminates, infrastructure resources are released in an orderly manner.

```
Shutdown
    │
    ▼
Close Database Connections
    │
    ▼
Disconnect Valkey
    │
    ▼
Close Qdrant Client
    │
    ▼
Exit
```

This prevents resource leaks and incomplete shutdowns.

---

## Centralized Resource Management

All shared resources are initialized from one location.

Instead of spreading initialization across multiple modules, the application lifecycle is defined in a single place.

Benefits include:

- easier maintenance
- easier debugging
- predictable startup
- simplified onboarding

---

## Better Testability

Tests can create isolated application instances with their own lifespan.

Resources are initialized only when needed and cleaned up automatically after each test.

This reduces shared state between tests.

---

## Future Scalability

As ResearchMind evolves, additional infrastructure can be added without changing the overall application architecture.

Future additions may include:

- Celery workers
- LangGraph runtime
- LangSmith
- Object storage
- Redis Streams
- External MCP clients
- AI model clients

The lifespan mechanism scales naturally with these additions.

---

# Alternatives Considered

## Global Variables

Example

```python
engine = create_async_engine(...)
```

### Advantages

- Simple implementation
- Minimal code

### Disadvantages

- Difficult to test
- No clear ownership
- Hard to clean up
- Hidden dependencies
- Resource lifecycle unmanaged

Rejected.

---

## Lazy Initialization

Resources are created on first use.

### Advantages

- Faster startup
- Resources created only if needed

### Disadvantages

- Increased latency on first request
- Harder error handling
- Inconsistent application state

Rejected.

---

## Separate Startup Modules

Each infrastructure component manages its own startup.

### Advantages

- Clear separation

### Disadvantages

- Startup order becomes harder to control
- Multiple initialization entry points
- More difficult debugging

Rejected.

---

# Consequences

## Positive

- Predictable application startup
- Predictable shutdown
- Centralized infrastructure management
- Better testing support
- Reduced resource leaks
- Improved maintainability
- Clean separation of concerns

---

## Negative

- Developers must understand asynchronous context managers
- Startup sequence becomes more explicit
- New infrastructure must be registered in the lifespan

These trade-offs are acceptable because they significantly improve reliability.

---

# Relationship with Application State

The lifespan is responsible for creating shared resources.

These resources are then stored in the FastAPI application state.

```
Lifespan
    │
    ▼
Create Resources
    │
    ▼
app.state
    │
    ▼
Dependency Injection
    │
    ▼
Business Logic
```

The lifespan owns resource creation.

`app.state` owns resource storage.

Dependency injection provides controlled access.

Each component has a distinct responsibility.

---

# Relationship with Dependency Injection

Request-scoped dependencies obtain infrastructure resources that were initialized during startup.

Example flow:

```
Application Startup
        │
        ▼
Lifespan
        │
        ▼
Create PostgreSQL Engine
        │
        ▼
Store in app.state
        │
        ▼
Dependency Injection
        │
        ▼
Async Database Session
        │
        ▼
Route Handler
```

This avoids creating expensive resources for every request.

---

# ResearchMind Implementation

Current resources managed through the lifespan:

- PostgreSQL Engine
- Valkey Client
- Qdrant Client

Future resources:

- LangSmith Client
- Celery
- Background Scheduler
- MCP Client Registry
- LLM Client Manager

The application lifecycle will remain the central point for infrastructure initialization.

---

# Implementation Notes

The lifespan implementation is located in:

```
apps/api/app/core/lifespan.py
```

It is registered during application creation:

```
FastAPI(
    lifespan=lifespan
)
```

This keeps application initialization explicit and centralized.

---

# Future Considerations

Future milestones may extend the lifespan to include:

- Startup validation
- Health verification
- Configuration validation
- Database migrations
- Cache warming
- AI model loading
- External service connectivity checks

The architecture already supports these enhancements without modification.

---

# Decision Summary

ResearchMind AI uses FastAPI Lifespan as the single mechanism for managing application-wide resources.

This approach provides predictable startup and shutdown behavior, centralized infrastructure management, improved testability, and a scalable foundation for future AI services and infrastructure components.

It establishes a clear ownership model where the lifespan initializes resources, `app.state` stores them, and dependency injection provides controlled access throughout the application.
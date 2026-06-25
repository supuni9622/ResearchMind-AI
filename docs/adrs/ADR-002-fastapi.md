# ADR-002: FastAPI as the Backend Framework

## Status

Accepted

---

## Date

2026-06-25

---

## Authors

ResearchMind AI Engineering Team

---

# Context

ResearchMind AI is designed as a production-grade AI Research & Intelligence Platform.

The backend is responsible for much more than exposing REST APIs. It will eventually orchestrate AI agents, interact with vector databases, communicate with external MCP servers, manage long-running workflows, stream responses, and integrate with multiple infrastructure services.

The chosen backend framework must therefore support:

- High-performance asynchronous request handling
- Strong typing
- Automatic validation
- Excellent developer experience
- Scalable architecture
- Production readiness
- Modern Python ecosystem compatibility

Several backend frameworks were evaluated before implementation began.

---

# Problem Statement

Which Python web framework provides the best foundation for building a scalable AI platform that will evolve from a simple REST API into a distributed, agent-driven system?

The framework should:

- Support asynchronous programming
- Encourage clean architecture
- Integrate well with SQLAlchemy
- Generate API documentation automatically
- Work well with dependency injection
- Be widely adopted
- Have a strong community

---

# Decision

ResearchMind AI will use **FastAPI** as the primary backend framework.

FastAPI serves as the HTTP gateway between clients and the platform's internal services.

It is responsible for:

- HTTP routing
- Request validation
- Response serialization
- Dependency injection
- Middleware execution
- Application lifecycle
- OpenAPI generation

Business logic is intentionally kept outside the routing layer.

---

# Why This Decision Was Made

## Native Asynchronous Support

ResearchMind performs many I/O-bound operations.

Examples include:

- Database queries
- Vector searches
- External API requests
- MCP communication
- LLM inference
- File processing

FastAPI is built on ASGI and provides first-class async support.

Example

```python
@router.get("/health")
async def health():
    ...
```

This enables efficient handling of concurrent requests without blocking the application.

---

## Strong Typing

FastAPI embraces Python type hints.

Example

```python
async def get_document(
    document_id: UUID
) -> DocumentResponse:
    ...
```

Benefits include:

- Better IDE support
- Static analysis
- Automatic validation
- Clear API contracts

---

## Automatic Validation

FastAPI integrates tightly with Pydantic.

Incoming requests are validated automatically.

Example

```python
class CreateDocumentRequest(BaseModel):
    title: str
    content: str
```

Invalid requests are rejected before reaching business logic.

This reduces boilerplate validation code.

---

## Automatic OpenAPI Documentation

FastAPI generates interactive documentation automatically.

ResearchMind exposes:

```
/docs

/redoc

/openapi.json
```

This provides:

- Interactive testing
- API exploration
- Contract visibility
- Easier frontend integration

---

## Dependency Injection

FastAPI provides a lightweight dependency injection system.

ResearchMind uses dependencies for:

- Database sessions
- Authentication (future)
- Current user (future)
- AI clients (future)

Example

```python
async def get_db():
    ...
```

Dependencies improve modularity and testability.

---

## Middleware Support

FastAPI allows middleware to be composed into a request pipeline.

ResearchMind currently uses middleware for:

- CORS
- Request IDs
- Request logging
- Request timing

Future middleware will include:

- Authentication
- Rate limiting
- Security headers
- Tenant context

---

## Lifespan Support

FastAPI provides a structured application lifecycle.

ResearchMind initializes shared infrastructure during startup.

Examples include:

- PostgreSQL
- Valkey
- Qdrant

Resources are cleaned up automatically during shutdown.

This avoids global singleton objects and improves resource management.

---

# Alternatives Considered

## Flask

Advantages

- Mature ecosystem
- Large community
- Simple learning curve

Disadvantages

- Limited async support
- Manual validation
- Manual OpenAPI generation
- Additional extensions required

---

## Django

Advantages

- Batteries included
- Powerful ORM
- Authentication system

Disadvantages

- Heavy framework
- Monolithic architecture
- Less suitable for an AI orchestration platform
- More difficult to keep backend modular

---

## Litestar

Advantages

- Modern architecture
- High performance
- Type-safe

Disadvantages

- Smaller ecosystem
- Less community adoption
- Fewer AI engineering examples

---

## Starlite (Legacy)

Was considered historically but ultimately replaced by Litestar.

Not selected.

---

# Consequences

## Positive

- Excellent async performance
- Strong typing
- Automatic API documentation
- Built-in validation
- Clean dependency injection
- Excellent SQLAlchemy integration
- Large community
- Mature ecosystem

---

## Negative

- Requires understanding asynchronous programming
- Dependency injection introduces a learning curve
- Pydantic models require additional boilerplate

These trade-offs are acceptable because they improve long-term maintainability.

---

# Role Within ResearchMind

FastAPI is **not** responsible for AI reasoning.

Instead, it serves as the application's HTTP interface.

Its responsibilities include:

```
Client
    │
    ▼
FastAPI
    │
    ▼
Service Layer
    │
    ▼
AI Components
```

Future AI components include:

- LangGraph
- RAG pipelines
- Memory systems
- MCP orchestration
- Report generation
- Evaluation

FastAPI coordinates these services without embedding business logic into route handlers.

---

# Implementation Notes

Current implementation includes:

- Modular routers
- API versioning
- Lifespan management
- Dependency injection
- Middleware registration
- Global exception handling
- Typed response models
- Health endpoints

Future milestones will build upon this foundation rather than modifying it.

---

# Related Documents

- Backend Architecture
- Repository Structure
- ADR-003 FastAPI Lifespan
- ADR-004 Application State
- Engineering Journal – Backend Foundation

---

# Decision Summary

FastAPI was selected because it provides the best balance of performance, developer experience, asynchronous programming support, strong typing, and production-ready features for building ResearchMind AI.

It forms the foundation of the platform's backend while allowing AI capabilities, infrastructure integrations, and future services to evolve independently through a clean and modular architecture.
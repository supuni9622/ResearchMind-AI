# ADR-008: Typed API Schemas as the Single Source of Truth

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
- ADR-005: Standardized API Contracts
- ADR-006: Separation of Environment Configuration and Application Constants
- ADR-007: Centralized Middleware Registration

---

# Related Concepts

- 009 API Contracts
- 010 Global Exception Handling
- 011 Pydantic Response Models

---

# Related Architecture Documents

- Backend Architecture
- Backend API Documentation
- Decision History

---

# Context

Every API exchanges structured data with its clients.

Examples include:

- Request payloads
- Response payloads
- Validation errors
- Authentication requests
- Pagination
- Streaming events
- Search results

Without a centralized schema system, applications typically rely on:

- raw dictionaries
- handwritten JSON
- duplicated field definitions
- inconsistent validation

As the number of endpoints grows, maintaining consistency becomes increasingly difficult.

ResearchMind AI requires a single source of truth for every API contract.

---

# Problem Statement

How should API payloads be defined so that:

- request validation is consistent
- response serialization is predictable
- OpenAPI documentation remains accurate
- frontend integration is simplified
- business logic remains independent from serialization

The solution should support future expansion without introducing duplicated schema definitions.

---

# Decision

ResearchMind AI adopts **typed Pydantic schemas** as the single source of truth for all API contracts.

Every request and response exchanged through the API must be represented by a Pydantic model.

Examples include:

- Request Models
- Response Models
- Error Models
- Generic Response Wrappers
- Pagination Models
- Domain Models
- Event Models (future)

No endpoint should return arbitrary dictionaries or accept unvalidated payloads.

---

# Why This Decision Was Made

## Strong Typing

Schemas define the expected structure of every payload.

Example

```python
class CreateDocumentRequest(BaseModel):
    title: str
    content: str
```

The schema documents the API while enforcing validation.

---

## Single Source of Truth

Instead of duplicating field definitions across:

- backend
- frontend
- documentation
- tests

the schema becomes the authoritative definition.

```
Schema

↓

Validation

↓

Serialization

↓

OpenAPI

↓

Documentation
```

Every layer references the same model.

---

## Automatic Validation

Incoming requests are validated before reaching business logic.

Example

```
Client

↓

JSON

↓

Pydantic Validation

↓

Route

↓

Service
```

Invalid requests never reach the service layer.

---

## Automatic Serialization

Route handlers return model instances rather than manually constructing JSON.

Example

```python
return SuccessResponse(
    data=HealthStatus(...)
)
```

FastAPI converts the model into JSON automatically.

---

## Improved OpenAPI Documentation

Schemas are automatically reflected in Swagger.

Example

```python
@router.get(
    "/health",
    response_model=SuccessResponse[HealthStatus]
)
```

Swagger displays the exact response structure without additional configuration.

---

## Better IDE Support

Typed schemas provide:

- autocompletion
- static analysis
- refactoring support
- compile-time feedback

This reduces development errors.

---

# Schema Organization

Schemas are organized by feature.

```
schemas/

common.py

error.py

health.py

auth.py

documents.py

chat.py

reports.py
```

Each feature owns its own models.

Shared models remain centralized.

---

# Generic Response Models

Reusable generic wrappers reduce duplication.

Example

```
SuccessResponse[T]
```

This allows every endpoint to return the same outer contract while varying the payload.

Example

```
SuccessResponse[HealthStatus]

SuccessResponse[UserResponse]

SuccessResponse[DocumentResponse]
```

The API remains consistent without creating duplicate wrappers.

---

# Error Models

Errors are also represented by typed schemas.

Example

```
ErrorResponse

↓

ErrorDetail
```

This ensures that success and failure responses follow equally well-defined contracts.

---

# Future Expansion

Additional schemas will be introduced for:

- Pagination
- Cursor-based Pagination
- Batch Operations
- Streaming Events
- WebSocket Messages
- MCP Messages
- Evaluation Results
- Report Generation

The schema architecture already supports these additions.

---

# Alternatives Considered

## Raw Dictionaries

Example

```python
return {
    "status": "ok"
}
```

### Advantages

- Minimal code

### Disadvantages

- No validation
- Poor documentation
- Inconsistent structure
- Difficult maintenance

Rejected.

---

## Dataclasses

Advantages

- Lightweight

Disadvantages

- Limited validation
- No native FastAPI integration
- Less expressive

Rejected.

---

## Manual Serialization

Advantages

- Full control

Disadvantages

- Repetitive
- Error-prone
- Difficult to maintain
- No automatic OpenAPI support

Rejected.

---

# Consequences

## Positive

- Strong typing
- Automatic validation
- Automatic serialization
- Accurate OpenAPI documentation
- Better IDE support
- Reusable schemas
- Cleaner business logic
- Improved maintainability

---

## Negative

- Additional schema classes
- Slight increase in boilerplate
- Developers must maintain schema definitions

These trade-offs are acceptable because they provide significant long-term benefits.

---

# Relationship with API Contracts

API contracts define **how** responses should look.

Typed schemas define **what** those responses contain.

```
API Contract

↓

SuccessResponse[T]

↓

HealthStatus

↓

JSON
```

The contract and schema system work together to produce consistent APIs.

---

# Relationship with Business Logic

Business logic should never construct JSON directly.

Instead:

```
Business Logic

↓

Domain Object

↓

Pydantic Schema

↓

FastAPI

↓

JSON
```

This separation keeps business logic independent from transport concerns.

---

# ResearchMind Implementation

Current implementation includes:

```
schemas/

common.py

error.py

health.py
```

Future milestones will introduce:

```
auth.py

documents.py

research.py

reports.py

chat.py

memory.py
```

Every API feature will define its own schemas while adhering to the standardized response contract.

---

# Implementation Guidelines

Every new endpoint must follow these rules:

- Define request models.
- Define response models.
- Reuse shared wrappers where appropriate.
- Avoid raw dictionaries.
- Keep schemas focused on data representation.
- Do not embed business logic inside schemas.

These guidelines ensure consistency across the platform.

---

# Future Considerations

As ResearchMind evolves, schema generation may be shared with frontend applications through OpenAPI code generation.

This will allow:

- Type-safe frontend clients
- Reduced duplication
- Automatic SDK generation
- Improved API consistency

The current schema architecture supports this evolution.

---

# Decision Relationship

```
ADR-001 Monorepo
        │
        ▼
ADR-002 FastAPI
        │
        ▼
ADR-003 FastAPI Lifespan
        │
        ▼
ADR-004 Application State
        │
        ▼
ADR-005 API Contracts
        │
        ▼
ADR-006 Settings vs Constants
        │
        ▼
ADR-007 Middleware Registration
        │
        ▼
ADR-008 Typed API Schemas
```

---

# Decision Summary

ResearchMind AI adopts typed Pydantic schemas as the single source of truth for all API contracts.

Every request, response, and error exchanged through the platform is represented by strongly typed schemas, ensuring consistent validation, serialization, documentation, and developer experience.

This decision establishes a scalable foundation for future features while keeping the API predictable, maintainable, and aligned with modern backend engineering practices.
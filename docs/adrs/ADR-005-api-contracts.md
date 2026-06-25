# ADR-005: Standardized API Contracts

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
- ADR-004: FastAPI Application State
- ADR-008: Typed Response Models

---

# Related Concepts

- 008 API Versioning
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

ResearchMind AI exposes a REST API that will be consumed by multiple clients.

Current consumers include:

- Next.js Web Application

Future consumers include:

- Mobile Applications
- MCP Clients
- CLI Tools
- Third-party Integrations
- Internal Services

Without a standardized API contract, different endpoints may return different response structures.

For example:

```json
{
    "status": "ok"
}
```

Another endpoint may return:

```json
{
    "message": "Success"
}
```

While another returns:

```json
{
    "result": {}
}
```

Although these responses all indicate success, they create unnecessary complexity for API consumers.

The frontend must implement different parsing logic for each endpoint.

As the platform grows, this inconsistency becomes increasingly difficult to maintain.

---

# Problem Statement

How should API responses be structured to ensure consistency, maintainability, and ease of integration across all clients?

The solution should:

- provide one response format
- support strong typing
- improve frontend development
- simplify testing
- integrate with OpenAPI
- remain extensible

---

# Decision

ResearchMind AI standardizes all API responses using two reusable response contracts.

## Success Response

```json
{
    "success": true,
    "data": {}
}
```

---

## Error Response

```json
{
    "success": false,
    "error": {
        "code": "RESOURCE_NOT_FOUND",
        "message": "Document not found.",
        "details": {}
    }
}
```

Every endpoint in the platform must follow one of these two contracts.

---

# Why This Decision Was Made

## Consistency

Every successful request returns exactly the same top-level structure.

Example

```
Success

↓

success

↓

data
```

Likewise, every failed request returns the same error structure.

```
Failure

↓

success

↓

error
```

Developers no longer need to remember endpoint-specific response formats.

---

## Better Frontend Integration

The frontend can process every response using the same logic.

Example:

```typescript
if (response.success) {
    // Handle data
} else {
    // Handle error
}
```

No endpoint-specific parsing is required.

This greatly simplifies frontend code.

---

## Strong Typing

ResearchMind implements reusable generic response models.

Example:

```python
SuccessResponse[HealthStatus]
```

This provides:

- compile-time validation
- IDE autocompletion
- reusable response types
- improved maintainability

---

## Better OpenAPI Documentation

FastAPI generates documentation directly from the response models.

Swagger accurately displays:

- success schema
- error schema
- nested models

The API documentation always reflects the implementation.

---

## Easier Testing

Tests can validate one response format instead of many.

Example assertions become predictable.

```
assert response["success"] is True
```

instead of checking different field names for each endpoint.

---

## Future Extensibility

Additional metadata can be introduced without changing the overall contract.

Future fields may include:

```json
{
    "success": true,
    "data": {},
    "meta": {
        "request_id": "...",
        "processing_time": "...",
        "pagination": {}
    }
}
```

Because every response shares the same structure, extensions remain backward compatible.

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

- Simple
- Minimal code

### Disadvantages

- No validation
- No consistency
- Poor documentation
- Difficult frontend integration

Rejected.

---

## HTTP Status Codes Only

Example

```
200 OK

404 Not Found

500 Internal Server Error
```

### Advantages

- Standard HTTP semantics

### Disadvantages

- No structured application errors
- Difficult frontend messaging
- Cannot include application-specific error codes

Rejected.

---

## Endpoint-Specific Responses

Each endpoint defines its own response structure.

### Advantages

- Flexible

### Disadvantages

- Inconsistent
- Harder to maintain
- Increased frontend complexity

Rejected.

---

# Consequences

## Positive

- Consistent API behavior
- Better developer experience
- Cleaner frontend implementation
- Strong typing
- Improved OpenAPI documentation
- Easier automated testing
- Simpler future maintenance

---

## Negative

- Slightly more boilerplate
- Requires reusable response models
- All endpoints must follow the standard

These trade-offs are acceptable because they improve long-term maintainability.

---

# Relationship with Exception Handling

API contracts and exception handling work together.

```
Route

↓

Business Logic

↓

Success

↓

SuccessResponse
```

or

```
Route

↓

Business Logic

↓

Exception

↓

Global Exception Handler

↓

ErrorResponse
```

Regardless of outcome, the client always receives a predictable response structure.

---

# Relationship with Response Models

The API contract is implemented using reusable Pydantic models.

Current implementation includes:

```
SuccessResponse[T]

ErrorResponse

ErrorDetail
```

These models act as the single source of truth for all API responses.

---

# ResearchMind Implementation

Current endpoints following this contract include:

```
GET /api/v1/health

GET /api/v1/health/live

GET /api/v1/health/ready
```

Future endpoints for authentication, documents, chat, reports, and research sessions will follow the same structure.

No feature-specific endpoint is allowed to return arbitrary JSON.

---

# Implementation Notes

The standardized response models are located in:

```
apps/api/app/schemas/

common.py
error.py
```

Global exception handlers ensure that all application errors automatically conform to the error contract.

FastAPI response models ensure that successful responses conform to the success contract.

This guarantees consistency across the entire backend.

---

# Future Considerations

Future enhancements may include:

- Pagination metadata
- Request identifiers
- Trace identifiers
- Processing time
- API version metadata
- Warnings
- Deprecation notices

These additions can be introduced without changing the existing response contract.

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
ADR-008 Typed Response Models
```

---

# Decision Summary

ResearchMind AI standardizes all API responses using reusable success and error contracts.

This decision establishes a single, predictable interface between the backend and every client application. It improves developer experience, frontend integration, API documentation, automated testing, and long-term maintainability while providing a scalable foundation for future platform capabilities.
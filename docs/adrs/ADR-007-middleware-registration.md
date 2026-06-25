# ADR-007: Centralized Middleware Registration

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
- ADR-004: Application State
- ADR-006: Separation of Environment Configuration and Application Constants
- ADR-008: Typed Response Models

---

# Related Concepts

- 006 FastAPI Middleware
- 007 FastAPI Application State

---

# Related Architecture Documents

- Backend Architecture
- Decision History

---

# Context

FastAPI applications typically register middleware directly inside `main.py`.

Example:

```python
app.add_middleware(CORSMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestTimingMiddleware)
```

This approach works well for small applications.

However, ResearchMind AI is expected to grow into a production platform containing:

- Authentication
- Authorization
- Rate Limiting
- Security Headers
- Tenant Resolution
- Compression
- Metrics
- Tracing
- Audit Logging
- Feature Flags

As more middleware is introduced, `main.py` becomes increasingly difficult to understand and maintain.

---

# Problem Statement

How should middleware be organized so that:

- application bootstrap remains simple
- middleware order is explicit
- new middleware can be added safely
- responsibilities remain separated

The solution should support future growth without requiring major refactoring.

---

# Decision

ResearchMind AI centralizes middleware registration inside a dedicated module.

```
app/

middleware/

register.py
```

Application startup simply delegates middleware registration.

Example:

```python
configure_application(app)
```

which internally performs:

```python
register_middlewares(app)
```

The application entry point no longer needs to know which middleware exists.

---

# Why This Decision Was Made

## Clean Application Bootstrap

Instead of:

```
main.py

↓

FastAPI

↓

Middleware

↓

Exception Handlers

↓

Routers

↓

Startup Tasks
```

the application startup becomes:

```
FastAPI

↓

configure_application(app)

↓

Application Ready
```

The entry point remains small and easy to understand.

---

## Explicit Ownership

Middleware registration has one owner.

```
middleware/

register.py
```

Developers immediately know where middleware should be added.

No searching through multiple files is required.

---

## Easier Maintenance

Adding middleware becomes straightforward.

Current implementation:

```
Request ID

Request Logging

Request Timing

CORS
```

Future additions:

```
Authentication

Authorization

Rate Limiting

Security Headers

Compression

Metrics

Tracing
```

Only one file changes.

---

## Improved Readability

Application setup becomes easier to follow.

```
main.py

↓

configure_application()

↓

register_middlewares()

↓

register_exception_handlers()

↓

include_router()
```

Each step has a single responsibility.

---

## Better Testing

Middleware registration can be tested independently.

Different middleware configurations can be created for testing without modifying the application entry point.

---

# Middleware Execution Order

Middleware execution order is important.

FastAPI executes middleware as nested layers.

Example registration:

```python
app.add_middleware(A)
app.add_middleware(B)
app.add_middleware(C)
```

Execution order:

```
Incoming Request

↓

C

↓

B

↓

A

↓

Route

↓

A

↓

B

↓

C

↓

Outgoing Response
```

Understanding this behavior is essential when introducing authentication, logging, and metrics.

---

# Current Middleware Stack

Current request flow:

```
Client

↓

CORS

↓

Request ID

↓

Request Logging

↓

Request Timing

↓

API Router

↓

Response
```

Future middleware will extend this pipeline without changing the overall architecture.

---

# Alternatives Considered

## Register Middleware in main.py

Advantages

- Simple
- Common FastAPI pattern
- Fewer files

Disadvantages

- Entry point grows continuously
- Mixed responsibilities
- Harder maintenance
- Difficult onboarding

Rejected.

---

## Register Middleware Inside Individual Modules

Example:

```
auth/

middleware.py

documents/

middleware.py
```

Advantages

- Feature ownership

Disadvantages

- Registration becomes fragmented
- Execution order becomes difficult to reason about
- Increased startup complexity

Rejected.

---

## Automatic Middleware Discovery

Advantages

- Minimal manual registration

Disadvantages

- Hidden behavior
- Harder debugging
- Less predictable startup

Rejected.

---

# Consequences

## Positive

- Cleaner application bootstrap
- Explicit middleware ownership
- Easier onboarding
- Improved maintainability
- Better scalability
- Simpler testing

---

## Negative

- One additional module
- Developers must remember to register new middleware

These trade-offs are acceptable because they significantly improve long-term maintainability.

---

# ResearchMind Implementation

Current implementation:

```
app/

middleware/

├── cors.py
├── request_id.py
├── request_logging.py
├── request_timing.py
└── register.py
```

Application startup:

```
main.py

↓

configure_application(app)

↓

register_middlewares(app)
```

This keeps the application bootstrap clean while allowing the middleware stack to evolve independently.

---

# Future Considerations

Future middleware may include:

- Authentication
- Authorization
- Rate Limiting
- Tenant Context
- Security Headers
- Compression
- Prometheus Metrics
- OpenTelemetry Tracing
- Request Correlation
- Feature Flags

The centralized registration mechanism already supports these additions without architectural changes.

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

ResearchMind AI centralizes middleware registration in a dedicated module to keep application startup simple, make middleware ownership explicit, and ensure the request pipeline remains scalable as new infrastructure and cross-cutting concerns are introduced.

This decision keeps the application's entry point focused on assembling the application while allowing the middleware stack to evolve independently throughout the lifetime of the project.
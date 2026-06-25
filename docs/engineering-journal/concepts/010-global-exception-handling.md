# 010 - Global Exception Handling

## Overview

Exception handling is the process of managing unexpected situations that occur while an application is running.

Instead of allowing exceptions to propagate directly to the client, the application converts them into meaningful API responses.

---

# Why Global Exception Handling Exists

Without centralized exception handling, each endpoint must manually catch exceptions.

Example:

```python
try:
    ...
except Exception:
    ...
```

This results in duplicated logic throughout the application.

Global exception handlers solve this problem by handling exceptions in one place.

---

# Request Lifecycle

```
Request
    │
    ▼
Route Handler
    │
    ▼
Business Logic
    │
    ▼
Exception?
    │
    ▼
Global Exception Handler
    │
    ▼
Standard Error Response
```

---

# ResearchMind Exception Hierarchy

ResearchMind defines a custom exception hierarchy.

```
AppException
│
├── NotFoundException
├── ValidationException
├── ConflictException
└── UnauthorizedException
```

Every application-specific exception inherits from `AppException`.

---

# Error Flow

When an exception is raised:

```
Route

↓

Service

↓

AppException

↓

Exception Handler

↓

JSON Response
```

The frontend always receives the same error contract.

---

# Validation Errors

FastAPI generates validation errors automatically.

ResearchMind overrides the default response so that validation errors also follow the standard error contract.

---

# Unexpected Exceptions

Unexpected exceptions are handled by a global fallback handler.

The client receives a generic message while the full stack trace is written to the application logs.

This prevents leaking implementation details.

---

# Benefits

- Consistent error responses
- Cleaner endpoint code
- Easier debugging
- Better frontend integration
- Improved security

---

# Best Practices

- Create a base exception class.
- Log unexpected exceptions.
- Avoid exposing internal errors.
- Return consistent error responses.
- Register exception handlers centrally.

---

# Common Mistakes

- Catching every exception inside endpoints.
- Returning stack traces to clients.
- Using inconsistent error messages.
- Mixing HTTP status codes and application error codes.

---

# Key Takeaways

- Exception handling belongs at the application level.
- Custom exceptions improve readability.
- Standardized errors simplify frontend development.
- Unexpected exceptions should always be logged.

---

# Related Concepts

- 009 API Contracts
- 011 Pydantic Response Models
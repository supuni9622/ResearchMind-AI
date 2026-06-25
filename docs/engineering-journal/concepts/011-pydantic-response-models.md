# 011 - Pydantic Response Models

## Overview

Pydantic response models define the structure of data returned by an API.

Instead of returning arbitrary dictionaries, endpoints return strongly typed objects.

FastAPI automatically converts these objects into JSON responses.

---

# Why Use Response Models

Returning dictionaries provides no guarantees about structure.

Example:

```python
return {
    "status": "ok"
}
```

Nothing prevents another endpoint from returning a completely different structure.

Response models enforce consistency.

---

# ResearchMind Implementation

ResearchMind uses reusable response models.

Example:

```
SuccessResponse[T]
```

```
ErrorResponse
```

Feature-specific schemas are organized by domain.

```
schemas/

common.py
error.py
health.py
chat.py
document.py
report.py
```

---

# Request Flow

```
Route
    │
    ▼
Pydantic Model
    │
    ▼
JSON Response
```

FastAPI automatically serializes the model into JSON.

---

# Benefits

- Strong typing
- Automatic validation
- Better IDE support
- Cleaner code
- Improved Swagger documentation
- Reusable schemas

---

# OpenAPI Integration

FastAPI uses response models to generate API documentation automatically.

Example:

```python
@router.get(
    "/health",
    response_model=SuccessResponse[HealthStatus],
)
```

Swagger displays the exact response schema without additional documentation.

---

# Best Practices

- Return models instead of dictionaries.
- Reuse common response models.
- Create feature-specific schemas.
- Keep models small and focused.
- Document public APIs through response models.

---

# Common Mistakes

- Returning raw dictionaries.
- Reusing one model for unrelated features.
- Embedding business logic inside schemas.
- Duplicating response models.

---

# Key Takeaways

- Response models define the API contract.
- FastAPI generates documentation automatically.
- Strong typing improves maintainability.
- Pydantic models become the single source of truth for API responses.

---

# Related Concepts

- 009 API Contracts
- 010 Global Exception Handling
- 008 API Versioning
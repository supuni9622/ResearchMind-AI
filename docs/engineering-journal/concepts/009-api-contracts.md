# 009 - API Contracts

## Overview

An API contract defines the structure of communication between a client and a server.

It specifies:

- Request format
- Response format
- Status codes
- Validation rules
- Error format

The API contract acts as an agreement between frontend and backend developers.

---

# Why API Contracts Exist

Without a defined contract, different endpoints may return different response structures.

Example:

Endpoint A

```json
{
    "status": "ok"
}
```

Endpoint B

```json
{
    "success": true,
    "result": {}
}
```

Endpoint C

```json
{
    "message": "done"
}
```

Although all three responses represent success, the frontend must handle each one differently.

A consistent API contract eliminates this inconsistency.

---

# ResearchMind API Contract

Every successful response follows the same structure.

```json
{
    "success": true,
    "data": {}
}
```

Every error response follows the same structure.

```json
{
    "success": false,
    "error": {
        "code": "",
        "message": "",
        "details": {}
    }
}
```

This contract is used across the entire application.

---

# Benefits

A standardized contract provides:

- Consistent frontend integration
- Predictable API behavior
- Easier testing
- Better API documentation
- Simplified error handling
- Strong typing

---

# Success Response

Successful requests always return:

```json
{
    "success": true,
    "data": {}
}
```

The `data` field contains the actual payload.

---

# Error Response

Failed requests always return:

```json
{
    "success": false,
    "error": {
        "code": "",
        "message": "",
        "details": {}
    }
}
```

The `error` object contains information describing what went wrong.

---

# ResearchMind Implementation

ResearchMind defines reusable response models.

```
schemas/

common.py
error.py
```

All API endpoints return these models instead of raw dictionaries.

---

# Best Practices

- Keep one response structure.
- Standardize error responses.
- Use typed response models.
- Document the API contract.
- Avoid returning arbitrary JSON.

---

# Common Mistakes

- Returning different success formats.
- Mixing error response structures.
- Embedding HTTP status codes inside JSON.
- Returning raw dictionaries.

---

# Key Takeaways

- An API contract defines communication between client and server.
- Every endpoint should follow the same response structure.
- Consistency reduces frontend complexity.
- Typed contracts improve maintainability.

---

# Related Concepts

- 008 API Versioning
- 010 Global Exception Handling
- 011 Pydantic Response Models
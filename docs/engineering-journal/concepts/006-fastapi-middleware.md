# 006 - FastAPI Middleware

## Overview

Middleware is software that executes before and after every HTTP request.

It acts as a pipeline that processes incoming requests before they reach the application and outgoing responses before they are returned to the client.

```
Client
    │
    ▼
Middleware
    │
    ▼
Route Handler
    │
    ▼
Business Logic
    │
    ▼
Response
```

Middleware is commonly used for concerns that apply to every request rather than individual endpoints.

---

# Why Middleware Exists

Without middleware, every endpoint would need to repeat common logic.

Example:

- Logging
- Authentication
- Request timing
- Request IDs
- CORS
- Rate limiting

Instead of duplicating this logic, middleware applies it automatically.

---

# Middleware in ResearchMind

ResearchMind currently uses the following middleware:

- CORS
- Request ID
- Request Logging
- Request Timing

Future middleware will include:

- Authentication
- Authorization
- Rate Limiting
- Security Headers
- Tenant Context
- Compression

---

# Request Lifecycle

```
Client
    │
    ▼
CORS
    │
    ▼
Request ID
    │
    ▼
Request Logging
    │
    ▼
Request Timing
    │
    ▼
API Router
    │
    ▼
Service Layer
    │
    ▼
Database
```

---

# Middleware Execution Order

Middleware behaves like nested layers.

The last middleware registered executes first on incoming requests and last on outgoing responses.

```
Request

↓

Middleware C

↓

Middleware B

↓

Middleware A

↓

Route

↓

Middleware A

↓

Middleware B

↓

Middleware C

↓

Response
```

This ordering is important when combining authentication, logging, and security middleware.

---

# Best Practices

- Each middleware should have a single responsibility.
- Keep middleware lightweight.
- Avoid database queries inside middleware unless necessary.
- Register middleware centrally.
- Document middleware order.

---

# Common Mistakes

- Putting business logic inside middleware.
- Logging sensitive information.
- Registering middleware in multiple places.
- Ignoring middleware execution order.

---

# How ResearchMind Uses It

Middleware registration is centralized in:

```
app/middleware/register.py
```

This keeps `main.py` clean and ensures the request pipeline is defined in one location.
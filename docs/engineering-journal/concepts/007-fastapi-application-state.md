# 007 - FastAPI Application State

## Overview

FastAPI provides `app.state` as a place to store application-wide resources.

These resources are created once during startup and shared throughout the lifetime of the application.

Examples include:

- Database engines
- Redis or Valkey clients
- Vector database clients
- Machine learning models

---

# Why Application State Exists

Creating expensive resources for every request is inefficient.

Instead:

```
Application Starts
        │
        ▼
Create Resources
        │
        ▼
Store in app.state
        │
        ▼
Reuse for every request
```

This reduces startup overhead and improves performance.

---

# ResearchMind Implementation

ResearchMind stores infrastructure clients inside `app.state`.

Current resources include:

- PostgreSQL Engine
- Valkey Client
- Qdrant Client

These resources are initialized during the FastAPI lifespan.

---

# Why Not Use Global Variables?

Global variables:

- Are difficult to test.
- Make dependency management harder.
- Can lead to resource leaks.
- Hide application dependencies.

`app.state` keeps ownership inside the FastAPI application.

---

# Relationship with Lifespan

Resources are created during startup.

```
Application Startup
        │
        ▼
Lifespan
        │
        ▼
Initialize Clients
        │
        ▼
Store in app.state
```

When the application shuts down, these resources are closed gracefully.

---

# Best Practices

- Store only long-lived shared resources.
- Do not store request-specific data.
- Initialize resources during startup.
- Clean up resources during shutdown.

---

# Common Mistakes

- Storing user sessions.
- Storing request objects.
- Creating database engines per request.
- Using global singleton objects instead of `app.state`.

---

# ResearchMind Benefits

Using `app.state` provides:

- Centralized resource management
- Easier testing
- Cleaner architecture
- Predictable application lifecycle
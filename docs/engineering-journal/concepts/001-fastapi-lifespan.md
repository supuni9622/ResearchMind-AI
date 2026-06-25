# FastAPI Lifespan

## Overview

FastAPI provides a **Lifespan** mechanism for managing resources that should exist for the entire lifetime of an application.

Instead of creating resources when Python imports a module, FastAPI allows us to explicitly initialize them during application startup and clean them up during shutdown.

ResearchMind uses Lifespan to manage all infrastructure services.

---

## Why Does Lifespan Exist?

Every application has a lifecycle:

```
Application Starts
        │
        ▼
Initialize Resources
        │
        ▼
Serve Requests
        │
        ▼
Release Resources
        │
        ▼
Application Stops
```

Without Lifespan, resources are often created during module import, making startup, shutdown, testing, and dependency management more difficult.

---

## How ResearchMind Uses Lifespan

During startup:

- Configure logging
- Create PostgreSQL Engine
- Create Valkey Client
- Create Qdrant Client
- Store them in `app.state`

During shutdown:

- Dispose PostgreSQL Engine
- Close Valkey Client
- Close Qdrant Client

---

## Why We Refactored

### Before

```
Import Module

↓

Engine Created

↓

Redis Created

↓

Qdrant Created
```

Problems:

- Resources created too early
- Difficult to test
- No centralized cleanup
- Harder to control startup order

---

### After

```
FastAPI Starts

↓

lifespan()

↓

Initialize Resources

↓

Store in app.state

↓

Serve Requests

↓

Shutdown

↓

Dispose Resources
```

Benefits:

- Predictable startup
- Proper cleanup
- Easier testing
- Production-ready lifecycle management

---

## Key Takeaways

- Lifespan manages application resources.
- Startup creates shared infrastructure.
- Shutdown releases resources.
- Resource ownership belongs to the application.
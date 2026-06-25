# 008 - API Versioning

## Overview

API versioning allows an application to evolve without breaking existing clients.

ResearchMind exposes its API under:

```
/api/v1
```

Future versions can be introduced as:

```
/api/v2
```

while keeping previous versions available.

---

# Why Version APIs?

Applications change over time.

Examples:

- Response formats evolve.
- New fields are added.
- Authentication changes.
- Old endpoints are removed.

Versioning allows these changes without disrupting users.

---

# ResearchMind Structure

```
app/api/

└── v1/
    ├── api.py
    ├── health.py
    ├── chat.py
    ├── documents.py
    └── reports.py
```

Each version owns its own routes.

---

# Router Registration

ResearchMind uses a central router.

```
main.py
      │
      ▼
api_router
      │
      ▼
Health
Chat
Documents
Reports
```

This keeps route registration centralized and easy to extend.

---

# Benefits

- Backward compatibility
- Cleaner organization
- Easier migrations
- Predictable API evolution

---

# Best Practices

- Version public APIs.
- Avoid breaking changes within a version.
- Keep versioning consistent.
- Register routers centrally.

---

# Common Mistakes

- Mixing multiple versions in the same router.
- Changing response contracts without versioning.
- Hardcoding routes throughout the application.

---

# ResearchMind Design

ResearchMind defines the API prefix as an application constant.

```
API_V1_PREFIX = "/api/v1"
```

This keeps the API contract consistent across the application while allowing future versions to coexist.
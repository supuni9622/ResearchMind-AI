# ADR-006: Separation of Environment Configuration and Application Constants

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
- ADR-005: Standardized API Contracts
- ADR-007: Middleware Registration

---

# Related Concepts

- 001 FastAPI Lifespan
- 004 Dependency Injection

---

# Related Architecture Documents

- Backend Architecture
- Repository Structure
- Decision History

---

# Context

Every backend application contains values that control application behavior.

Examples include:

- Database URLs
- API Keys
- Environment names
- Application name
- API prefixes
- Pagination defaults
- File size limits
- Supported MIME types

Initially, these values were placed together in a single configuration class.

As the application grows, this approach becomes increasingly difficult to maintain because values with different responsibilities become mixed together.

---

# Problem Statement

How should configuration values be organized so that developers can immediately understand:

- which values change between environments
- which values are fixed application constants
- where new values should be added

The solution should:

- reduce ambiguity
- improve maintainability
- support future growth
- simplify onboarding

---

# Decision

ResearchMind separates configuration into two categories.

## Environment Configuration

Stored in:

```
app/core/settings.py
```

These values are loaded from environment variables.

Examples include:

- Database URL
- Valkey URL
- Qdrant URL
- Environment
- Debug Mode
- API Keys
- Secrets
- Frontend URL

These values may differ between:

- Local Development
- Testing
- Staging
- Production

---

## Application Constants

Stored in:

```
app/core/constants.py
```

These values are part of the application itself and do not change between environments.

Examples include:

- Application Name
- Application Version
- API Prefix
- Default Pagination Size
- Supported File Types
- Default Timeouts
- Maximum Upload Size

Application constants are committed to source control.

---

# Why This Decision Was Made

## Clear Ownership

Each value has exactly one home.

Questions become easy to answer.

"Does this value change between environments?"

Yes

↓

`settings.py`

No

↓

`constants.py`

This simple rule removes uncertainty during development.

---

## Improved Maintainability

Environment variables remain focused on deployment concerns.

Constants remain focused on application behavior.

Each file has a single responsibility.

---

## Cleaner Configuration

Instead of:

```python
class Settings:
    database_url
    app_name
    api_prefix
    version
    qdrant_url
    max_upload_size
```

Configuration becomes:

```
settings.py

↓

Environment

constants.py

↓

Application
```

Each file remains small and focused.

---

## Easier Testing

Tests can override environment configuration without modifying application constants.

For example:

- Use a temporary PostgreSQL database
- Use an in-memory Valkey instance
- Enable debug mode

Application constants remain unchanged.

---

## Better Scalability

As ResearchMind grows, feature-specific constants can live alongside the feature they belong to.

Example:

```
documents/
    constants.py

auth/
    constants.py

chat/
    constants.py
```

This prevents a single global constants file from becoming excessively large.

---

# Configuration Categories

ResearchMind follows the following hierarchy.

```
Environment Configuration

↓

settings.py
```

Examples

- Database URL
- Secrets
- API Keys
- Environment

---

```
Application Constants

↓

core/constants.py
```

Examples

- App Name
- Version
- API Prefix

---

```
Feature Constants

↓

feature/constants.py
```

Examples

- Upload Limits
- Prompt Templates
- File Types
- Retry Counts

Each category has a clearly defined responsibility.

---

# Alternatives Considered

## Everything Inside Settings

Advantages

- One configuration file

Disadvantages

- Mixed responsibilities
- Difficult navigation
- Larger configuration class
- Harder onboarding

Rejected.

---

## Everything as Environment Variables

Advantages

- Fully configurable

Disadvantages

- Excessive deployment configuration
- Harder local development
- Values that never change become unnecessarily configurable

Rejected.

---

## Global Constants Module

Example

```
constants.py
```

containing every constant in the project.

Advantages

- Centralized

Disadvantages

- File grows continuously
- Poor feature ownership
- Difficult maintenance

Rejected.

---

# Consequences

## Positive

- Clear separation of concerns
- Easier maintenance
- Simpler onboarding
- Cleaner architecture
- Better feature organization
- Reduced configuration ambiguity

---

## Negative

- Developers must decide where a value belongs
- Slightly more files

These trade-offs are acceptable because they improve long-term maintainability.

---

# ResearchMind Implementation

Current implementation:

```
app/core/

settings.py

constants.py
```

Future implementation:

```
app/

auth/
    constants.py

documents/
    constants.py

chat/
    constants.py

reports/
    constants.py
```

Feature-specific values remain close to the code that uses them.

---

# Implementation Guidelines

When adding a new value, ask the following question:

> Does this value change between environments?

If **yes**, place it in:

```
settings.py
```

If **no**, place it in:

```
constants.py
```

If the value belongs only to one feature, place it in:

```
feature/constants.py
```

This decision tree should be followed consistently throughout the project.

---

# Future Considerations

As ResearchMind evolves, additional configuration mechanisms may be introduced.

Examples include:

- Feature Flags
- Runtime Configuration
- Tenant Configuration
- Remote Configuration Services

The distinction between environment configuration and application constants should remain unchanged.

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

ResearchMind AI separates environment-specific configuration from application constants to establish a clear ownership model for configuration values.

Environment-dependent values are managed through `settings.py`, application-wide constants are stored in `constants.py`, and feature-specific constants live alongside their respective modules.

This approach keeps the configuration system scalable, maintainable, and easy to understand as the platform evolves.
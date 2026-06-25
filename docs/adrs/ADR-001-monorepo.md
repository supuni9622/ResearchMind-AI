# ADR-001: Monorepo Repository Architecture

## Status

Accepted

---

## Date

2026-06-25

---

## Authors

ResearchMind AI Engineering Team

---

# Context

ResearchMind AI is intended to become a long-term production platform rather than a single demonstration project.

The platform will eventually contain multiple applications, shared libraries, AI services, infrastructure configuration, documentation, datasets, benchmarks, and developer tooling.

During the initial design phase, two repository strategies were considered:

1. Multiple independent repositories
2. A single monorepository

The decision needed to balance developer productivity, maintainability, scalability, and future open-source collaboration.

---

# Problem Statement

How should the ResearchMind AI codebase be organized to support long-term growth while maintaining a productive development experience?

The repository should:

- support multiple applications
- support shared code
- minimize dependency duplication
- simplify onboarding
- scale with future services
- remain easy to maintain

---

# Decision

ResearchMind AI will use a **monorepo architecture**.

The repository will contain all components required to build and operate the platform.

Example:

```text
ResearchMind-AI/

apps/
agents/
services/
shared/
docs/
tests/
datasets/
infrastructure/
scripts/
tools/
```

Each directory has a clearly defined responsibility while remaining part of a single repository.

External MCP servers are **not** included in this monorepo.

They are maintained as independent repositories.

---

# Why This Decision Was Made

A monorepo provides several advantages for this project.

## Shared Code

Applications can reuse:

- utilities
- models
- configuration
- common libraries

without publishing internal packages.

---

## Unified Versioning

The backend, frontend, documentation, and infrastructure evolve together.

A single Git tag represents the state of the entire platform.

---

## Simplified Development

Developers clone one repository.

No additional dependency management is required between internal projects.

---

## Documentation

All documentation remains alongside the implementation.

Documentation changes are reviewed together with code changes.

---

## Future Expansion

The repository can naturally grow to include:

- worker services
- AI agents
- frontend applications
- CLI tools
- evaluation tools

without changing repository organization.

---

# Alternatives Considered

## Multiple Repositories

Example

```text
researchmind-api

researchmind-web

researchmind-common

researchmind-docs
```

### Advantages

- independent releases
- smaller repositories

### Disadvantages

- duplicated configuration
- dependency management overhead
- difficult cross-repository changes
- fragmented documentation

---

## Hybrid Repository

A hybrid model combining multiple repositories with Git submodules was also considered.

This approach introduces unnecessary complexity for a project of this size.

---

# Consequences

## Positive

- single source of truth
- easier onboarding
- shared tooling
- centralized documentation
- simplified dependency management
- easier refactoring
- consistent engineering standards

---

## Negative

- repository size will grow over time
- CI pipelines may become more complex
- requires clear ownership of directories

These trade-offs are acceptable given the long-term vision of the platform.

---

# Relationship with MCP Servers

Although ResearchMind uses a monorepo, external MCP servers are intentionally excluded.

Each MCP is maintained in its own repository.

Example

```text
ResearchMind-AI/

Research-MCP/

Climate-Intelligence-MCP/

Earthquake-Intelligence-MCP/
```

ResearchMind consumes MCPs through the Model Context Protocol rather than containing them internally.

This preserves loose coupling and independent deployment.

---

# Implementation Notes

The repository currently follows this structure.

```text
apps/
agents/
services/
shared/
docs/
tests/
datasets/
infrastructure/
scripts/
tools/
```

Future additions should fit naturally into this structure without requiring major reorganization.

---

# Related Documents

- Repository Structure
- Backend Architecture
- ADR-002 FastAPI
- Project Roadmap

---

# Decision Summary

ResearchMind AI adopts a monorepo architecture because it provides the best balance between scalability, maintainability, developer productivity, and long-term project evolution while allowing external MCP servers to remain independently deployable and reusable.
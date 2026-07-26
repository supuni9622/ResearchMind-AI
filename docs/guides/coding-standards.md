# Coding Standards

Conventions actually enforced/observed in this codebase — sourced from `pyproject.toml`, `.pre-commit-config.yaml`, and patterns consistent across `apps/api/app/`. Not aspirational.

---

## Enforced (lint / type-check / pre-commit)

| Tool | Config | Enforces |
|---|---|---|
| Ruff (lint) | `[tool.ruff.lint]`, `pyproject.toml` | Rule sets `E, W, F, I, B, UP, SIM`; ignores `UP046`, `B008`; line length 100; `target-version = py312` |
| Ruff (format) | default (no `[tool.ruff.format]` override) | Standard Ruff formatting |
| mypy | `[tool.mypy]` | `python_version = 3.12`, `pydantic.mypy` plugin, `warn_return_any`, `warn_unused_ignores`, `check_untyped_defs`, `no_implicit_optional`; `alembic/` excluded |
| pre-commit | `.pre-commit-config.yaml` | `ruff check --fix` → `ruff format` → `mypy .` → `pytest`, on every commit |
| CI | `.github/workflows/ci.yml` | `ruff format --check`, `ruff check`, `mypy .`, `pytest`, coverage — all must pass |

Run locally before committing:

```bash
uv run ruff format .
uv run ruff check --fix .
uv run mypy .
uv run pytest
```

## Python conventions

- `from __future__ import annotations` at the top of every module (universal — used for forward references and lighter-weight typing).
- Async-first: application services, repositories, and route handlers are `async def`; `AsyncSession` throughout.
- `enum.StrEnum` for all status/kind/category enums (38+ across `app/ai/`), not plain `str, Enum`.
- Pydantic models: `ConfigDict(extra="forbid")` on almost every model (85+ occurrences) — unexpected fields are a hard error, not silently dropped.
- One parameter per line with a trailing comma on multi-argument function signatures and constructor calls — consistent across the codebase, not just where Ruff would force a wrap.

## Architectural patterns (by convention, not tooling)

| Pattern | Example | Purpose |
|---|---|---|
| Per-subpackage file split | `interfaces.py`, `models.py`, `service.py`, `enums.py`, `registry.py`, `exceptions.py` | Consistent shape across `app/ai/guardrails/`, `.../validation/`, `.../processing/`, `.../indexing/`, etc. |
| `create.py` factory modules | 32 across `app/ai/` (e.g. `runtime/generation/create.py`) | Wires real vs. no-op implementations; keeps constructors free of environment-sensing logic |
| No-op collaborators | `NoOpTracer`, `NoOpMetricsRecorder` | Every optional integration (LangSmith, Prometheus, etc.) degrades to a no-op rather than branching call sites on `if configured` |
| Repository pattern | `app/repositories/*.py` | All persistence access goes through a repository, never raw session queries from a service |
| FastAPI DI via `app/dependencies/` | `app/dependencies/research.py`, `generation.py`, etc. | Route handlers depend on factory functions, not on constructing services inline |
| Artifact builder/writer split | `*ArtifactBuilder` / `*ArtifactWriter` (guardrails, processing, indexing) | Building a serializable artifact is separated from persisting it |

## Comments and docstrings

- No comments restating *what* code does — names carry that.
- Comments/docstrings exist only for non-obvious *why*: a PRD/ADR cross-reference (`# PRD §10, P1`), a deliberate tradeoff, or a bug this code specifically works around.
- Module/class docstrings frequently cite the originating PRD section or ADR number rather than re-describing behavior in prose.

## Testing

See `docs/guides/testing.md` for full detail. In short: `tests/unit/` (mocked dependencies, no external services), `tests/integration/` (real Postgres), `tests/api/` (FastAPI `TestClient`) — `pytest` with `asyncio_mode = "auto"`.

## Not enforced / no formal standard yet

- No `ruff.format` customization — house style is whatever Ruff's default formatter produces
- No docstring-coverage or docstring-style linter (e.g. `pydocstyle`) — the "why not what" rule above is convention, not tooled
- No commit-message linting (e.g. commitlint/conventional commits) configured

# Testing Guide

## Purpose

This document describes how to run the ResearchMind test suite and catalogs
what is actually covered today, organized by feature area. It reflects the
current state of the code, not the target state — gaps are called out
explicitly rather than implied to be covered.

---

# Running Tests

```bash
uv run pytest
```

`tests/conftest.py` forces `ENVIRONMENT=test` before any application module
is imported, so `Settings` always loads `.env.test` and every DB-backed test
runs against `researchmind_test`, never the dev database. You do not need to
set `ENVIRONMENT` yourself.

Useful variants:

```bash
uv run pytest tests/unit                          # unit tests only, no DB required
uv run pytest tests/unit/ai/knowledge/upload/      # one feature area
uv run pytest -k document_processing               # filter by name
uv run pytest -v                                    # verbose per-test output
```

---

# Test Layout

```
tests/
  unit/            # no external services; dependencies are mocked
  integration/     # exercises real Postgres (researchmind_test)
  api/              # FastAPI TestClient, black-box HTTP tests
  evaluation/       # scaffolding only, see docs/evaluation/strategy.md
  security/         # scaffolding only, see docs/evaluation/strategy.md
  performance/      # latency/throughput benchmarks
```

---

# Authentication

Source: `app/auth/`, `app/api/v1/auth.py`, `app/services/auth.py`,
`app/services/user.py`.

## Covered

`tests/integration/test_user_service.py` and
`tests/integration/test_user_repository.py` exercise the identity layer
against a real database:

- Creating a user for a given `(auth_provider, provider_user_id)` pair
- Duplicate email on creation raises `ConflictException`
- Looking up an unknown user by email raises `NotFoundException`
- `sync_user` returns the existing user on a second call instead of creating
  a duplicate (idempotent first-login / repeat-login behavior)
- Deactivating a user flips `is_active` to `False`
- Repository-level CRUD: create, get by email, exists-by-email, delete

## Not covered

There is currently no direct unit or integration test for:

- `JWTVerifier.verify` — signature verification, expired/invalid
  token handling, wrong `token_use`, audience/issuer mismatch
  (`app/auth/jwt.py`)
- `CognitoAuthenticationProvider.normalize_claims` — Cognito claim mapping
  (`app/auth/providers/cognito.py`)
- `get_current_user` — the FastAPI dependency that ties bearer-token
  extraction, JWT verification, and user sync together
  (`app/auth/dependencies.py`)
- `AuthService.exchange_code` — the Cognito OAuth code exchange, including
  the confidential-client Basic-auth path and the `AUTH_MISCONFIGURED` /
  `AUTH_CODE_EXCHANGE_FAILED` error paths (`app/services/auth.py`)
- The `/auth/callback` and `/auth/me` endpoints (`app/api/v1/auth.py`)

These are coverage gaps, not confirmed-safe code paths — the JWT/Cognito
integration in particular should be prioritized, since it's the only thing
standing between an unauthenticated request and every protected endpoint.

---

# Document Upload & Processing

Source: `app/ai/knowledge/upload/`, `app/ai/knowledge/processing/`,
`app/services/document_processing_service.py`,
`app/infrastructure/storage/s3.py`.

## Upload validation — `test_validators.py`

- Blank/whitespace-only filename rejected
- Unknown or missing extension rejected (including `archive.tar.gz`,
  which is judged on `.gz`, not `.tar`)
- Extension case-insensitivity (`.PDF` == `.pdf`)
- Unsupported / mismatched MIME type rejected
- Zero-byte and negative-size files rejected
- File-size boundary: exactly `MAX_UPLOAD_SIZE_BYTES` (50 MB) accepted,
  one byte over rejected
- Every supported `(extension, content_type)` pair accepted

## Upload orchestration — `test_service.py` (`UploadService`)

- **Invalid files**: validation failures short-circuit before the hasher,
  storage, or repository are ever touched
- **Large files**: the size boundary is enforced before any I/O
- **Storage failures**:
  - Hashing failure never reaches storage
  - `storage.upload()` failure does not attempt a compensating delete
    (nothing was ever written)
  - DB persist failure *after* a successful upload triggers cleanup of the
    orphaned storage object
  - A failure in the cleanup delete itself does not mask the original error
  - A commit failure after a successful upload also triggers cleanup
- **Concurrency**: concurrent uploads produce independent document IDs and
  storage keys; one invalid upload among several concurrent requests fails
  on its own without affecting the others

## Processing pipeline — `test_service.py`, `test_service_resilience.py` (`ProcessingService`)

- Parser routing by document format (PDF vs text), including
  parser-not-found and wrong-format cases
- Exceptions raised by a parser propagate unchanged
- **Storage failures**: a download failure propagates without ever calling
  the parser; an artifact-write failure propagates after a successful parse
  (the document was parsed, only persistence failed)
- **Concurrency**: 10 documents processed concurrently each resolve to
  their own result; one failure among several concurrent requests is
  isolated from its siblings

## Document lifecycle orchestration — `test_document_processing_service.py` (`DocumentProcessingService`)

- Status transitions (`PROCESSING` → `COMPLETED`) are both flushed *and
  committed* — this is a regression test for a real bug where status was
  only flushed, so a processing failure's `FAILED` state was silently lost
  when the request-scoped session closed
- A processing failure marks the document `FAILED` and persists the error
  message (truncated to 2000 chars)
- If persisting the `FAILED` status itself fails (e.g. DB unreachable), the
  *original* processing error still propagates rather than being replaced
  by the persistence error
- Concurrent processing of multiple documents, including a mixed
  success/failure batch, updates each document's status independently

## S3 storage layer — `test_s3_storage.py` (`S3StorageService`)

- `ClientError` from boto3 is wrapped into typed `StorageUploadError` /
  `StorageDownloadError` / `StorageDeleteError` on the respective operations
- `exists()`: a 404 `ClientError` returns `False`; any other error code
  raises `StorageNotFoundError`
- Concurrent uploads all reach the underlying client; one failure among
  several concurrent downloads is isolated

## Temporary file manager — `test_temporary_file_manager.py`

- The temp file is created and readable while the context is open
- Written contents match exactly what was passed in
- The original filename's extension is preserved
- The file is deleted once the context exits
- The file is still deleted if an exception is raised inside the context
- Cleanup does not raise if the file was already removed

## Docling parser — `test_docling_parser.py`, integration `test_processing_service.py`

- Happy-path PDF parsing only (`tests/fixtures/sample.pdf`) — asserts
  markdown/raw text are non-empty, statistics are populated, metadata title
  is derived from the filename

## Not covered

- Corrupted-but-correctly-typed files (e.g. a `.pdf` extension with
  non-PDF bytes) failing inside `DoclingParser`
- DOCX/Markdown/plain-text parsing (only PDF has a parser test)
- The `/documents/upload` HTTP endpoint end-to-end (auth + upload +
  processing wired together through `TestClient`)
- Checksum-based deduplication (the repository method exists;
  `UploadService` has the lookup commented out as a future enhancement)

---

# Known Gaps Summary

| Area | Status |
|---|---|
| User CRUD / identity sync | Covered |
| JWT verification / Cognito claims / token exchange | **Not covered** |
| Upload validation | Covered |
| Upload storage failures & cleanup | Covered |
| Processing pipeline storage failures | Covered |
| Document status persistence on failure | Covered |
| Concurrency (upload, processing, lifecycle, S3) | Covered |
| S3 error wrapping | Covered |
| Non-PDF parsers (DOCX/MD/TXT) | **Not covered** |
| Full upload endpoint (auth + upload + processing) | **Not covered** |
| RAG evaluation (faithfulness, groundedness, retrieval) | **Not implemented** — see `docs/evaluation/strategy.md` |
| Security evaluation (jailbreaks, prompt injection) | **Not implemented** — see `docs/evaluation/strategy.md` |

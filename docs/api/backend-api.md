# Backend API Reference

## Overview

This document describes the public REST API exposed by ResearchMind AI.

The backend currently exposes infrastructure endpoints used for monitoring and development.

As the platform evolves, this document will expand to include authentication, document management, AI research workflows, report generation, and MCP integrations.

---

# Base URL

Local Development

```
http://localhost:8000
```

API Version

```
/api/v1
```

---

# API Response Contract

Every endpoint follows one of two response contracts.

## Success Response

```json
{
    "success": true,
    "data": {}
}
```

---

## Error Response

```json
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Description",
        "details": {}
    }
}
```

No endpoint should return arbitrary JSON outside these contracts.

---

# Health Endpoints

These endpoints are primarily used for infrastructure monitoring.

---

## GET /api/v1/health

Returns the overall health of the application and connected infrastructure.

### Response

```json
{
    "success": true,
    "data": {
        "status": "healthy",
        "services": {
            "postgres": "healthy",
            "valkey": "healthy",
            "qdrant": "healthy"
        }
    }
}
```

---

## GET /api/v1/health/live

Liveness probe.

Used by orchestration platforms to determine whether the application process is running.

### Response

```json
{
    "success": true,
    "data": {
        "status": "alive"
    }
}
```

---

## GET /api/v1/health/ready

Readiness probe.

Used to determine whether the application is ready to receive requests.

### Response

```json
{
    "success": true,
    "data": {
        "status": "ready"
    }
}
```

---

# HTTP Status Codes

The backend uses standard HTTP status codes.

| Status | Meaning |
|---------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

# Authentication

Current Status

Not yet implemented.

Authentication will be introduced in Milestone 1.

Planned authentication:

- JWT Access Tokens
- Refresh Tokens
- Protected Endpoints
- Role-Based Authorization

---

# OpenAPI

Interactive documentation is available at:

```
/docs
```

Alternative documentation:

```
/redoc
```

OpenAPI specification:

```
/openapi.json
```

These endpoints are automatically generated from the application's Pydantic schemas.

---

# Future API Modules

The API will expand with future milestones.

Planned modules include:

- Authentication
- Users
- Documents
- Research Sessions
- Reports
- Chat
- Memory
- Evaluation
- MCP Integration

Each module will follow the standardized API contracts defined by ADR-005.
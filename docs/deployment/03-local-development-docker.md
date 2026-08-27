# ResearchMind --- Full Local Development with Docker

## Purpose

Docker Compose is the primary daily development environment.

Cost:

``` text
$0
```

## Full local stack

``` text
Docker Compose
|
+-- Next.js frontend
+-- FastAPI API
+-- document worker
+-- Research Runtime worker
+-- evaluation worker
+-- memory lifecycle worker
+-- Postgres
+-- Valkey
+-- Qdrant
+-- Redis Stack semantic cache
+-- Prometheus
+-- Grafana
```

## Docker images

### Backend

`docker/backend.Dockerfile`

One shared image is used by:

-   API;
-   document worker;
-   Research Runtime worker;
-   evaluation worker;
-   memory lifecycle worker.

The container command selects the process.

### Frontend

`docker/web.Dockerfile`

Uses the existing Next.js standalone build.

## Why this remains the primary development mode

Local Docker provides:

-   fast feedback;
-   reproducibility;
-   service isolation;
-   local dependency parity;
-   production-like container images;
-   a common image format for ECS and EKS.

## Deployment relationship

``` text
Local Docker
     |
     +--> same backend image --> ECS/Fargate
     |
     +--> same backend image --> EKS/Fargate
```

The local environment should not be replaced by AWS.

AWS is used to validate infrastructure, deployment, networking,
reliability, scaling and security.

## Local observability

Keep:

``` text
Prometheus
Grafana
```

locally for development and debugging.

## Daily workflow

``` text
Code
 ↓
Docker Compose
 ↓
Test
 ↓
Prometheus/Grafana
 ↓
Commit
```

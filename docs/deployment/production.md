# Production Deployment

> Production deployment strategy for ResearchMind.

## Status

🚧 Planned

This document will evolve throughout the project.

---

## Target Architecture

The decided production architecture is AWS ECS/Fargate for the API and four
workers, fronted by an ALB, with AWS Amplify Hosting for the Next.js
frontend:

- ECS/Fargate (API + document/research-runtime/evaluation/memory-lifecycle
  workers), behind an ALB
- AWS Amplify Hosting (frontend, deployed independently of the backend)
- RDS PostgreSQL, ElastiCache Valkey, S3, SQS, Cognito (existing), Secrets
  Manager
- Qdrant Cloud Free Tier (not self-hosted)
- A separate ECS/Fargate service for the `research-intelligence-mcp` server
- CloudWatch logs/metrics as the first observability layer (Prometheus/
  Grafana stay local-only for now)

This is deliberately an **ephemeral** environment
(`terraform apply` → test/demo → `terraform destroy`), not a 24/7 deployment —
ResearchMind is a portfolio/interview project with a hard **~$5/month**
persistent-cost target, not real production traffic. See
[`../../AWS_Deployment.md`](../../AWS_Deployment.md) and
[`01-deployment-options-and-decisions.md`](01-deployment-options-and-decisions.md)
through
[`06-frontend-amplify-deployment.md`](06-frontend-amplify-deployment.md) for
the full architecture and the reasoning behind each choice.

Local/dev-parity containerization (Dockerfiles + full `docker-compose.yml`
for the API, all four workers, and the frontend) is done — see
[`local.md`](local.md). None of the AWS infrastructure above is provisioned
yet (no Terraform, no ECR pushes, no live ECS/RDS/ElastiCache) — see
[`../todo/aws-ecs-fargate-production-deployment.md`](../todo/aws-ecs-fargate-production-deployment.md)
for the implementation checklist and its two remaining open questions
(semantic-cache ElastiCache-Valkey compatibility, NAT Gateway cost/VPC
endpoint strategy); worker scaling, Qdrant persistence, frontend hosting,
secrets management, and the CI/CD shape are already decided there.

Future milestones will define:

- CI/CD
- Scaling
- High Availability
- Backup Strategy
- Disaster Recovery
- Kubernetes (optional)

---

## Memory lifecycle worker

### Memory export, erasure, and failure policy

Apply the governance migration before enabling the M14-M15 UI:

```bash
DEBUG=false uv run alembic upgrade head
DEBUG=false uv run alembic current
```

The expected head is `c8d9e0f1a2b3`. Deployments that start the API before
this revision fail deletion preview with `UndefinedTable` for
`memory_deletion_confirmations`. `DEBUG` is a boolean setting; environments
that export values such as `DEBUG=release` must remove that value or override
it with `DEBUG=false` for Alembic and application processes.

Exports use `researchmind.memory.export.v1` and include user-safe scope,
provenance, confidence, and timestamps. They exclude owner IDs, raw metadata,
prompts, diagnostics, and secrets. Confirmation tokens expire after
`MEMORY_DELETION_CONFIRMATION_TTL_SECONDS` (five minutes by default) and are
single use. Erasure is immediate; there is no application undo/tombstone copy.
Content-free audit jobs retain only identifiers, scope, counts, stage, and
timestamps.

| Dependency | Normal memory behavior | Export/erasure behavior |
|---|---|---|
| PostgreSQL | Durable reads/writes fail closed | Export and canonical deletion fail closed |
| Qdrant | Retrieval fails open to no vector matches | Vector deletion must finish before canonical deletion |
| Valkey | SESSION reads and availability hints fail open | Whole-scope erasure fails closed and is retryable |
| Embeddings | Semantic operations preserve the documented caller fallback | Not used by export/erasure |
| LLM provider | Extraction/supersession falls back or skips | Not used by export/erasure |
| Artifact storage | Trace persistence fails open on the answer path | Selected and whole-scope erasure conservatively purge the scope's derived memory artifacts; failure is recorded and retryable |

Encrypted backups may retain deleted bytes until the configured backup expiry.
They must not be restored except for disaster recovery; after restoration,
replay completed governance audit jobs before serving traffic. Publish the
provider-specific backup expiry in the retention policy and incident runbook.

`MEMORY_SCOPE_MAX_DURABLE_RECORDS` defaults to 10,000 per owner/scope. At the
limit, new durable writes fail with an actionable error while reads, export,
and deletion remain available. Calibrate the value with staging load tests.

Before deploying the M5 scope-aware API or workers, apply the database migration:

```bash
DEBUG=false uv run alembic upgrade head
```

The migrations create the minimal `projects` and `project_memberships`
authorization foundation, add scope columns/indexes to memory, backfill
existing memories as personal, and create `memory_scope_settings` for M12's
independent capture/retrieval controls. No new environment variables are
required. Deploy migrated database -> API -> workers; do not activate
Project-scoped traffic until all components run the scope-aware version.

Run memory retention as a separate, long-lived process alongside the API and
the other workers:

```bash
uv run python -m apps.worker.memory_lifecycle_main
```

The deployment platform must supervise and restart this process. Use one
replica per environment. A token-safe Valkey lock prevents overlapping sweeps
during deployments or accidental duplicate starts, but it is not a reason to
scale this worker horizontally.

The worker requires network access and credentials for PostgreSQL, Valkey, and
Qdrant. It runs once immediately after startup and then on the configured
interval.

Recommended initial production configuration:

```env
MEMORY_LIFECYCLE_ENABLED=true
MEMORY_LIFECYCLE_DRY_RUN=true
MEMORY_LIFECYCLE_INTERVAL_SECONDS=86400
MEMORY_LIFECYCLE_LOCK_TTL_SECONDS=1800
MEMORY_LIFECYCLE_BATCH_SIZE=500
MEMORY_LIFECYCLE_WORKER_METRICS_PORT=8011

MEMORY_LIFECYCLE_USER_STALE_AFTER_DAYS=365
MEMORY_LIFECYCLE_USER_MAX_IMPORTANCE=0.1
MEMORY_LIFECYCLE_SEMANTIC_STALE_AFTER_DAYS=90
MEMORY_LIFECYCLE_SEMANTIC_MAX_IMPORTANCE=0.3
MEMORY_LIFECYCLE_RESEARCH_STALE_AFTER_DAYS=180
MEMORY_LIFECYCLE_RESEARCH_MAX_IMPORTANCE=0.2
```

Rollout procedure:

1. Deploy one worker replica with dry-run enabled.
2. Observe candidate counts over several scheduled runs.
3. Review the selected records and retention thresholds.
4. Confirm the registered lifecycle Prometheus metrics are exposed on port
   `8011`, including the scheduled storage/inventory gauges for PostgreSQL
   rows/bytes/age/distribution and Qdrant points/drift. Confirm the lifecycle,
   inventory-freshness, failure, and vector-drift alerts are loaded. A
   `prometheus.metric.unregistered` lifecycle message is not expected after
   the current metric registration changes.
5. Set `MEMORY_LIFECYCLE_DRY_RUN=false` and restart the worker.
6. Monitor examined, deleted, and failed counts, run duration, last-success
   time, absolute storage growth, oldest-row age, distribution percentiles,
   and PostgreSQL/Qdrant consistency in the Memory Runtime dashboard.

For ECS/Fargate, give this process its own service/task definition and restart
policy. The target process topology is:

```text
API service
Document-processing worker
Research-runtime worker
Evaluation-scoring worker
Memory-lifecycle worker
```

Do not enable real deletion in production until staging dry runs and lifecycle
alerts have been verified.

---

## TODO

- [ ] Infrastructure
- [ ] Secrets Management
- [ ] Production Environment Variables
- [ ] Deployment Pipeline
- [ ] Monitoring
- [ ] Register memory lifecycle Prometheus metrics and missed-run alerts
- [ ] Validate lifecycle dry runs before enabling production deletion
- [ ] Scaling
- [ ] Security

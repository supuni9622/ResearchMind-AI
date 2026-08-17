# Production Deployment

> Production deployment strategy for ResearchMind.

## Status

🚧 Planned

This document will evolve throughout the project.

---

## Target Architecture

ResearchMind will support production deployment using:

- Docker
- Reverse Proxy
- PostgreSQL
- Valkey
- Qdrant
- Monitoring
- Observability

Future milestones will define:

- CI/CD
- Scaling
- High Availability
- Backup Strategy
- Disaster Recovery
- Kubernetes (optional)

---

## Memory lifecycle worker

Before deploying the M5 scope-aware API or workers, apply the database migration:

```bash
uv run alembic upgrade head
```

The migration creates the minimal `projects` and `project_memberships`
authorization foundation, adds scope columns and indexes to memory, and
backfills existing memories as personal. M5 adds no required environment
variables. Deploy migrated database -> API -> workers; do not activate
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

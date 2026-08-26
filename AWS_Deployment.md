# ResearchMind AWS Deployment — Architecture & Implementation Plan

We are now ready to start implementing the AWS deployment architecture for ResearchMind.

IMPORTANT:
Do not redesign the application architecture unnecessarily.
Do not replace working application components.
Do not introduce Kubernetes into the ECS implementation.
Do not self-host Qdrant.
Do not optimize for imaginary production traffic.
The goal is production-grade architecture + real infrastructure learning while keeping AWS costs extremely low.

============================================================
1. PROJECT CONTEXT
============================================================

ResearchMind AI is a production-grade AI research platform.

Current repository:

ResearchMind-AI

Current implementation:

- Next.js 15 / React 19 frontend
- FastAPI API
- 4 independently runnable workers:
  1. document processing worker
  2. Research Runtime worker
  3. online evaluation scoring worker
  4. memory lifecycle worker
- PostgreSQL
- Valkey
- Qdrant
- Redis Stack semantic cache
- S3
- SQS
- Cognito
- Prometheus
- Grafana
- LangSmith
- external AI/tool providers
- separate Research Intelligence MCP server

The local Docker containerization is already completed and verified.

Current Docker architecture:

docker/backend.Dockerfile
    -> shared backend image
    -> API and all four workers use the same image
    -> ECS/task command determines the process role

docker/web.Dockerfile
    -> Next.js standalone build

docker-compose.yml
    -> Postgres
    -> Valkey
    -> Qdrant
    -> Redis Stack semantic cache
    -> API
    -> 4 workers
    -> Next.js frontend
    -> Prometheus
    -> Grafana

Do not break the existing local Docker Compose setup.

============================================================
2. IMPORTANT DEPLOYMENT MODES
============================================================

We have explicitly decided that ResearchMind will have THREE deployment/learning modes.

------------------------------------------------------------
MODE 1 — LOCAL DEVELOPMENT
------------------------------------------------------------

This is the everyday development environment.

Everything runs locally with Docker Compose:

    Next.js
       |
    FastAPI
       |
    4 workers
       |
    Postgres
    Valkey
    Qdrant
    Redis Stack semantic cache
    Prometheus
    Grafana

Cost:

    $0

This is the primary development environment.

Do not replace this with AWS.

The current Docker Compose setup is considered the local/dev-parity implementation and should remain working.

------------------------------------------------------------
MODE 2 — AWS ECS/FARGATE PRODUCTION-LIKE TEST ENVIRONMENT
------------------------------------------------------------

This is our real AWS production architecture.

The purpose is:

- learn Terraform
- learn AWS networking
- learn ECS/Fargate
- learn ALB
- learn IAM
- learn Secrets Manager
- learn ECR
- learn ECS service/task definitions
- learn worker deployment
- learn service discovery
- learn scaling
- learn health checks
- learn CloudWatch
- perform realistic production deployment/failure/load testing

BUT:

This environment is NOT intended to run 24/7.

Because ResearchMind is a portfolio/interview project and has almost no production traffic, we cannot afford a permanently running ECS/RDS/ElastiCache environment.

The intended lifecycle is:

    terraform apply
         |
         v
    full AWS environment
         |
         v
    test / demo / load test / observe
         |
         v
    terraform destroy

Therefore:

    ECS/Fargate = ephemeral production-like environment

NOT:

    ECS/Fargate = permanent $100+ monthly environment

We have a hard target of approximately $5/month for persistent AWS usage.

Do not assume that the full ECS environment can remain running for $5/month.

------------------------------------------------------------
MODE 3 — AWS EKS/FARGATE KUBERNETES LEARNING ENVIRONMENT
------------------------------------------------------------

This is a separate learning environment.

It is NOT the primary ResearchMind production architecture.

Purpose:

- learn Kubernetes
- learn EKS
- learn Kubernetes Deployments
- learn Services
- learn ConfigMaps
- learn Secrets
- learn probes
- learn resource requests/limits
- learn horizontal scaling
- learn rolling deployments
- learn Kubernetes networking
- learn Kubernetes operational concepts
- understand EKS/Fargate
- compare Kubernetes orchestration with ECS

Lifecycle:

    terraform apply
         |
         v
    EKS + Fargate
         |
         v
    deploy ResearchMind
         |
         v
    experiment / scale / observe
         |
         v
    terraform destroy

This environment should only exist while learning/testing.

Do NOT mix EKS resources into the ECS production Terraform environment.

There should be a clear separation between:

    terraform/environments/ecs-demo

and:

    terraform/environments/eks-lab

The same ResearchMind Docker images can be used in both environments.

============================================================
3. FINAL HIGH-LEVEL ARCHITECTURE
============================================================

The primary AWS architecture is:

                         USER
                           |
                           v
                    Next.js Frontend
                           |
                           v
                    AWS Amplify
                           |
                        HTTPS
                           |
                           v
                     AWS ALB
                           |
                           v
                    ECS / Fargate
                      FastAPI API
                           |
            +--------------+--------------+
            |              |              |
            v              v              v
          RDS          ElastiCache       SQS
       PostgreSQL         Valkey           |
                                           |
                              +------------+-----------+
                              |            |           |
                              v            v           v
                         document      research      eval
                          worker        worker       worker

                    memory lifecycle worker
                           |
                           v
                         Valkey

Qdrant is NOT self-hosted in AWS.

Use:

    Qdrant Cloud Free Tier

as the managed vector database.

This is a deliberate architectural choice.

Do NOT implement:

    Qdrant on ECS
    Qdrant on EC2
    Qdrant on EFS
    Qdrant on EBS

for the current project.

The Qdrant Cloud Free Tier currently provides a small single-node cluster suitable for our low-traffic portfolio/demo environment.

Qdrant Cloud is the one deliberate external managed dependency in the otherwise AWS-centered infrastructure.

============================================================
4. SEPARATE MCP SERVER
============================================================

ResearchMind uses a separate repository:

    research-intelligence-mcp

This is NOT part of the ResearchMind backend repository.

It is a separate MCP service.

Production-like AWS architecture:

    research-intelligence-mcp
             |
             v
        Docker image
             |
             v
            ECR
             |
             v
       ECS / Fargate
             |
             v
       ResearchMind API

The ResearchMind API communicates with the MCP server through:

    MCP_PAPERS_SERVER_URL

Keep this service independently deployable.

Do not merge the MCP server into the ResearchMind backend repository.

Do not turn MCP functionality into one of the four ResearchMind workers.

============================================================
5. FRONTEND DECISION
============================================================

The frontend is:

    apps/web

It is:

    Next.js 15
    React 19
    TypeScript
    Tailwind

The current Next.js configuration uses:

    output: "standalone"

Do NOT change this to static export unless we explicitly decide to do so later.

The frontend should NOT run on ECS/Fargate.

Deploy the frontend independently using:

    AWS Amplify Hosting

The intended architecture is:

    GitHub
       |
       v
    AWS Amplify
       |
       v
    Next.js

The frontend communicates with the ECS API through HTTPS.

Production environment variables will need to be configured for:

    NEXT_PUBLIC_API_URL
    NEXT_PUBLIC_BASE_URL
    NEXT_PUBLIC_REDIRECT_URI
    Cognito-related public configuration

Cognito callback/logout URLs must be updated to the production frontend URL.

============================================================
6. AWS SERVICES WE ARE USING
============================================================

Primary AWS services:

    VPC
    ECS
    Fargate
    ECR
    ALB
    CloudFront
    RDS PostgreSQL
    ElastiCache for Valkey
    S3
    SQS
    Cognito
    IAM
    Secrets Manager
    CloudWatch

External managed service:

    Qdrant Cloud Free Tier

Do not introduce additional AWS services unless there is a clear architectural reason.

============================================================
7. NETWORKING
============================================================

Target:

    One VPC
    Two Availability Zones

Public subnets:

    ALB only

Private subnets:

    ECS tasks
    RDS
    ElastiCache

Qdrant Cloud is external.

The initial production-like architecture should follow proper private/public subnet separation.

However, COST IS A FIRST-CLASS CONSTRAINT.

Do not automatically create a NAT Gateway without analyzing the cost.

NAT Gateway is one of the biggest recurring cost risks for this project.

We need to investigate:

    VPC endpoints for AWS services
    controlled external egress
    NAT Gateway requirements for external AI APIs

External services include:

    Groq
    OpenAI
    Voyage AI
    Tavily
    LangSmith

AWS-native services include:

    ECR
    S3
    SQS
    CloudWatch
    Secrets Manager

Use VPC endpoints where appropriate to avoid unnecessary NAT traffic/cost.

Before implementing a NAT Gateway, document:

    why it is required
    what traffic goes through it
    estimated hourly cost
    estimated monthly cost
    cheaper alternatives

Do not hide NAT Gateway cost.

============================================================
8. SEMANTIC CACHE DECISION
============================================================

The local stack currently uses:

    redis-stack-server

because:

    langchain_redis.RedisSemanticCache

requires Redis search/vector functionality.

We previously identified this as an architectural blocker for plain ElastiCache Redis/Valkey.

Before implementing a separate Redis Stack ECS service, investigate whether the current ElastiCache Valkey version and feature set can support the actual semantic-cache operations required by ResearchMind.

Specifically validate:

    FT.CREATE
    FT.SEARCH
    vector search
    required Redis data structures
    compatibility with langchain_redis.RedisSemanticCache

Do NOT assume compatibility.

Do NOT assume incompatibility.

Perform a real compatibility test.

Preferred outcome:

    ElastiCache Valkey
          |
          +-- L1 cache
          +-- rate limiting
          +-- session/memory use
          +-- semantic cache

If compatibility is proven, remove the need for a separate Redis Stack service in AWS.

If compatibility is not proven, document the result before introducing another service.

Local Docker Compose must continue using Redis Stack if required.

============================================================
9. RDS
============================================================

Replace local:

    postgres

with:

    Amazon RDS PostgreSQL

in the ECS environment.

The application already uses PostgreSQL extensively.

RDS is the canonical relational database.

Do not move relational application data to another database.

Do not redesign the data layer.

Use Terraform.

Database credentials must NOT be hardcoded.

Use:

    AWS Secrets Manager

for database credentials/secrets.

Database migrations must be handled safely.

The current local project already has Alembic migrations.

Do not invent a new migration system.

============================================================
10. ELASTICACHE
============================================================

Replace local:

    valkey

with:

    ElastiCache for Valkey

Use it for the existing Valkey responsibilities.

Do not blindly introduce Redis and Valkey as separate AWS systems.

First determine whether semantic-cache compatibility allows one Valkey service.

============================================================
11. SQS
============================================================

SQS already exists as an AWS dependency.

Carry it forward.

Do not recreate the application's queue architecture.

The document-processing pipeline already depends on asynchronous processing.

ECS workers consume/process work.

Use SQS where the existing implementation already expects it.

============================================================
12. S3
============================================================

S3 already exists.

Use the existing S3 architecture for:

    documents
    processing artifacts
    chunking/embedding artifacts
    observability artifacts
    generated artifacts where already implemented

Do not redesign storage.

Do not move document storage into EFS.

============================================================
13. COGNITO
============================================================

Cognito already exists.

Do not rebuild authentication.

Use the existing Cognito User Pool.

The API validates Cognito JWTs.

Frontend uses the Cognito Hosted UI.

Terraform should manage infrastructure that is appropriate to manage, but do not accidentally destroy or recreate the existing production/user identity pool.

Be extremely careful with Cognito state.

If the existing Cognito resources are outside Terraform, initially treat them as existing resources and reference/import them safely rather than recreating them.

============================================================
14. ECS SERVICES
============================================================

Create an ECS cluster.

API:

    researchmind-api

Workers:

    researchmind-worker-processing
    researchmind-worker-research-runtime
    researchmind-worker-eval-scoring
    researchmind-worker-memory-lifecycle

Starting desired count:

    API = 1
    processing worker = 1
    research runtime worker = 1
    evaluation worker = 1
    memory lifecycle worker = 1

Do NOT start with multiple replicas everywhere.

The Research Runtime worker already supports:

    RESEARCH_RUNTIME_WORKER_CONCURRENCY

and uses PostgreSQL outbox claiming / SELECT FOR UPDATE SKIP LOCKED.

This means:

    process concurrency
    +
    ECS horizontal scaling

can both be used.

Start conservatively and test.

Memory lifecycle:

    exactly one replica

The existing Valkey singleton lock protects deployment overlap.

Do not horizontally scale it by default.

============================================================
15. ECS API
============================================================

The API is the only request/response ECS service.

Architecture:

    Internet
       |
       v
      ALB
       |
       v
    ECS Fargate
       |
       v
    FastAPI

Use:

    health checks
    CloudWatch logs
    appropriate CPU/memory limits
    graceful shutdown
    ECS restart behavior

Do not assume ECS HTTP health checks can be applied to workers in the same way as the API.

Workers are long-running consumer processes.

Worker supervision/restart must be designed separately.

============================================================
16. WORKER HEALTH / SCALING
============================================================

For workers:

    document processing
    research runtime
    evaluation scoring
    memory lifecycle

do not invent HTTP health endpoints unless the application actually supports them.

ECS needs a sensible way to determine task/process failure.

Use:

    process exit codes
    ECS task health/restart behavior
    CloudWatch logs
    application metrics

where appropriate.

For queue-driven workloads, scaling should eventually consider:

    SQS queue depth
    processing latency
    CPU
    memory

Do not implement sophisticated autoscaling before the basic service is working.

============================================================
17. ECR
============================================================

Create ECR repositories for:

    researchmind-backend
    research-intelligence-mcp

researchmind-web does NOT need an ECR repository. AWS Amplify Hosting for a
Next.js app builds directly from the connected GitHub source using its own
build environment -- it never pulls a pre-built Docker image from ECR. The
Docker-image-via-ECR path in Amplify's own docs refers to a different,
older feature (Amplify's multi-container Fargate hosting), which is not
what section 5's decision uses and would contradict "the frontend should
NOT run on ECS/Fargate." docker/web.Dockerfile remains real and necessary
for local Docker Compose dev-parity; it has no role in the AWS deployment
path.

The backend repository uses one image for:

    API
    all four workers

The ECS task definition determines the command.

Do not create five backend images unless there is a demonstrated reason.

============================================================
18. SECRETS
============================================================

Use AWS Secrets Manager for actual secrets.

Examples:

    GROQ_API_KEY
    OPENAI_API_KEY
    ANTHROPIC/CLAUDE credentials if used
    VOYAGE_API_KEY
    TAVILY_API_KEY
    LANGSMITH_API_KEY
    database credentials
    other sensitive provider credentials

Do NOT put secrets into:

    Terraform source
    terraform.tfvars committed to git
    Dockerfiles
    ECS task definitions as plaintext
    GitHub source files

Non-sensitive configuration can remain normal environment variables.

============================================================
19. OBSERVABILITY
============================================================

Local development keeps:

    Prometheus
    Grafana

The local dashboards are already implemented.

For the first AWS implementation, prefer:

    CloudWatch logs
    ECS metrics
    ALB metrics
    RDS metrics
    ElastiCache metrics

Do not immediately deploy Prometheus + Grafana into ECS unless there is a clear need.

Do not create unnecessary observability infrastructure.

Later we can evaluate:

    Amazon Managed Prometheus
    Amazon Managed Grafana

============================================================
20. TERRAFORM STRUCTURE
============================================================

Create a clean Terraform structure.

Suggested:

infra/
  terraform/
    modules/
      vpc/
      iam/
      ecr/
      ecs/
      alb/
      rds/
      elasticache/
      secrets/
      s3/
      sqs/

    environments/
      ecs-demo/
        main.tf
        variables.tf
        outputs.tf
        terraform.tfvars.example

      eks-lab/
        ...

Do not create unnecessary modules.

Use modules where they provide meaningful reuse.

The ECS environment and EKS environment MUST be separated.

============================================================
21. ECS DEMO ENVIRONMENT
============================================================

The ECS environment is our production-like architecture.

Expected lifecycle:

    terraform apply
    |
    deploy
    |
    test
    |
    observe
    |
    scale
    |
    failure testing
    |
    terraform destroy

We should be able to demonstrate:

    API deployment
    worker deployment
    MCP deployment
    database connectivity
    Valkey connectivity
    SQS processing
    S3 access
    Qdrant Cloud access
    Cognito authentication
    external AI APIs
    CloudWatch logs
    ECS task restart
    worker failure/recovery
    scaling

This is the environment we will use for portfolio/interview demonstrations.

============================================================
22. EKS LAB ENVIRONMENT
============================================================

Do NOT implement this as part of the first ECS deployment.

EKS is a separate learning track.

Architecture:

    Terraform
       |
       v
    EKS cluster
       |
       v
    EKS Fargate profiles
       |
       v
    Kubernetes
       |
       +-- Deployment: API
       +-- Deployment: document worker
       +-- Deployment: research worker
       +-- Deployment: eval worker
       +-- Deployment: memory worker
       +-- MCP service/deployment
       +-- Kubernetes Services
       +-- ConfigMaps
       +-- Secrets
       +-- probes
       +-- resource requests/limits

Use the SAME Docker images built for ECS.

The purpose is to compare:

    ECS/Fargate
vs
    Kubernetes/EKS/Fargate

Do not unnecessarily duplicate application implementation.

Terraform should be able to create the EKS learning environment and destroy it afterwards.

============================================================
23. COST CONSTRAINT
============================================================

HARD CONSTRAINT:

    approximately $5/month maximum persistent AWS spend

ResearchMind is NOT a business product with real production traffic.

This is an AI engineering portfolio/project.

Therefore:

Permanent/low-cost services should be limited to things such as:

    Cognito
    S3
    SQS
    ECR
    IAM
    minimal CloudWatch
    Qdrant Cloud Free Tier

Expensive compute infrastructure should NOT remain running continuously.

Especially:

    ECS Fargate
    ALB
    RDS
    ElastiCache
    NAT Gateway
    EKS

must be treated as ephemeral/demo/learning infrastructure unless we explicitly decide otherwise.

The system must make it difficult to accidentally leave expensive resources running.

Document cost risks prominently.

============================================================
24. COST SAFETY
============================================================

Add documentation for:

    terraform apply
    terraform destroy

and make the destroy workflow obvious.

Document the most dangerous forgotten resources:

    NAT Gateway
    ALB
    RDS
    ElastiCache
    Fargate tasks
    EKS cluster

Before applying expensive resources, provide an estimated cost.

Do NOT claim the entire AWS architecture costs $5/month while running continuously.

The $5 constraint applies to our realistic persistent usage.

============================================================
25. CI/CD
============================================================

Eventually implement:

GitHub
   |
   v
tests
   |
   v
lint/typecheck
   |
   v
Docker build
   |
   v
ECR
   |
   v
ECS deployment

The backend Docker image should be built once and reused for:

    API
    processing worker
    research worker
    evaluation worker
    memory worker

The frontend image can be built separately.

MCP has its own repository and CI/CD lifecycle.

Terraform infrastructure deployment should remain separate from application image deployment.

Do not combine every concern into one giant GitHub Actions workflow.

============================================================
26. IMPLEMENTATION ORDER
============================================================

Do NOT immediately create the whole AWS infrastructure.

Work in this order:

PHASE 0 — VALIDATION

1. Inspect current Dockerfiles.
2. Inspect docker-compose.yml.
3. Inspect existing AWS integration.
4. Inspect current environment variables.
5. Inspect existing Cognito/S3/SQS usage.
6. Validate ElastiCache Valkey semantic-cache compatibility.
7. Decide NAT/VPC endpoint strategy.
8. Confirm Qdrant Cloud integration.
9. Determine minimum CPU/memory requirements for API/workers.
10. Document findings.

PHASE 1 — TERRAFORM FOUNDATION

Create:

    provider
    backend/state strategy
    VPC
    subnets
    route tables
    security groups
    IAM roles

Do not create ECS services yet.

PHASE 2 — ECR

Create ECR repositories.

Build/push:

    backend
    web
    MCP

PHASE 3 — DATA LAYER

Create/configure:

    RDS PostgreSQL
    ElastiCache Valkey
    S3
    SQS
    Secrets Manager

Qdrant remains Qdrant Cloud Free Tier.

PHASE 4 — ECS API

Create:

    ECS cluster
    task definition
    API service
    ALB
    target group
    listener
    health check

Get API working before workers.

PHASE 5 — WORKERS

Deploy:

    document worker
    research runtime worker
    evaluation worker
    memory lifecycle worker

Start with one task each.

PHASE 6 — MCP

Deploy:

    research-intelligence-mcp

as a separate ECS service.

Connect ResearchMind API to it.

PHASE 7 — FRONTEND

Deploy Next.js through:

    AWS Amplify

Configure:

    API URL
    Cognito callback
    Cognito logout
    production frontend URL

PHASE 8 — OBSERVABILITY

CloudWatch logs/metrics.

Verify:

    API
    workers
    ALB
    RDS
    Valkey
    ECS

PHASE 9 — CI/CD

GitHub Actions:

    test
    build
    push ECR
    deploy ECS

PHASE 10 — TESTING

Test:

    authentication
    API
    document upload
    document processing
    retrieval
    chat
    Linear Research
    Deep Research
    MCP paper search
    worker processing
    generated report
    S3
    SQS
    database
    cache

PHASE 11 — FAILURE TESTING

Deliberately:

    kill API task
    kill worker task
    stop/restart MCP
    introduce queue backlog
    test worker restart
    test API restart
    test database connectivity failure

Observe recovery.

PHASE 12 — SCALING TESTS

Test progressively:

    low traffic
    moderate traffic
    high traffic

Observe:

    ALB
    ECS
    CPU
    memory
    RDS
    Valkey
    SQS
    worker concurrency
    external API latency

============================================================
27. DOCUMENTATION REQUIREMENT
============================================================

Every architectural decision should be documented.

Create/update:

    docs/deployment/aws-architecture.md

and document:

    Local mode
    ECS/Fargate mode
    EKS/Fargate mode

Also document why:

    Qdrant Cloud Free Tier
    Amplify
    ECS/Fargate
    RDS
    ElastiCache
    SQS
    S3
    Secrets Manager
    Terraform

were selected.

Document rejected alternatives:

    Vercel
    self-hosted Qdrant
    ECS + EC2
    EKS production
    permanent Fargate
    permanent NAT Gateway

only where relevant.

============================================================
28. IMPORTANT ENGINEERING PRINCIPLE
============================================================

Do not over-engineer.

This project exists to demonstrate:

    AI engineering
    production architecture
    cloud infrastructure
    containers
    Terraform
    orchestration
    scaling
    reliability
    observability
    security

It does NOT exist to demonstrate:

    maximum AWS complexity.

Every infrastructure component must have a reason.

If a simpler architecture provides the same learning/product value, choose the simpler architecture.

============================================================
29. BEFORE WRITING CODE
============================================================

First inspect the existing repository and produce:

1. Current architecture summary
2. Existing Docker/Compose architecture
3. Existing AWS dependencies
4. Required environment variables
5. Existing health endpoints
6. Worker commands
7. MCP integration
8. Current Cognito integration
9. Current S3/SQS integration
10. Risks/blockers for ECS deployment

Then propose the exact Terraform implementation plan.

DO NOT start creating Terraform resources until this inspection is complete.

We will review the plan before the first terraform apply.

============================================================
30. FINAL ARCHITECTURAL DECISION
============================================================

The architecture we are converging on is:

LOCAL:

    Docker Compose
    $0

AWS PRODUCTION-LIKE:

    Amplify
       |
    ALB
       |
    ECS/Fargate API
       |
    +-- ECS/Fargate worker-processing
    +-- ECS/Fargate worker-research
    +-- ECS/Fargate worker-evaluation
    +-- ECS/Fargate worker-memory
       |
    RDS PostgreSQL
    ElastiCache Valkey
    SQS
    S3
    Secrets Manager
    Cognito
    Qdrant Cloud Free Tier
    separate ECS/Fargate MCP server

    Managed through Terraform.

    Apply -> test -> destroy.

KUBERNETES LEARNING:

    Terraform
       |
    EKS
       |
    Fargate
       |
    Kubernetes
       |
    same ResearchMind Docker images

    Apply -> learn/test -> destroy.

ECS and EKS are separate environments.

Do not mix them.

============================================================
31. SUCCESS CRITERIA
============================================================

We are successful when:

[x] Local Docker Compose still works.

[x] ResearchMind backend builds successfully.

[x] Frontend builds successfully.

[ ] MCP builds successfully.

[x] ECR repositories exist.

[x] Terraform can create the AWS environment.

[ ] API runs on ECS/Fargate.

[ ] All four workers run independently.

[ ] MCP runs independently.

[ ] RDS works.

[ ] ElastiCache works.

[ ] SQS works.

[ ] S3 works.

[ ] Cognito authentication works.

[ ] Qdrant Cloud works.

[ ] Frontend runs through Amplify.

[ ] Secrets are not hardcoded.

[ ] CloudWatch provides useful logs/metrics.

[ ] Terraform destroy removes expensive infrastructure.

[ ] ECS environment can be recreated from scratch.

[ ] Same application can later be deployed to EKS/Fargate.

[x] Architecture and tradeoffs are documented.

Most importantly:

The deployment should demonstrate genuine production engineering knowledge without creating unnecessary cloud complexity or violating the project's ~$5/month persistent-cost constraint.

One thing I'd add to this plan

I would make the three modes visually explicit in the repository, because this will help you later when you're learning and also when explaining ResearchMind in an interview:

ResearchMind
│
├── Local Development
│   └── Docker Compose
│
├── AWS Production-like
│   ├── Terraform
│   ├── ECS
│   └── Fargate
│
└── Kubernetes Learning Lab
    ├── Terraform
    ├── EKS
    └── Fargate

The key concept is:

Mode	Purpose	Lifecycle	Cost target
Local	Daily development	Always available locally	$0
ECS + Fargate	Production architecture/demo	apply → test → destroy	Ephemeral
EKS + Fargate	Kubernetes learning	apply → learn → destroy	Ephemeral

And Qdrant Cloud Free Tier sits outside all three compute environments:

                ResearchMind
                     │
        ┌────────────┼────────────┐
        │            │            │
      Local         ECS          EKS
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
             Qdrant Cloud
              Free Tier

============================================================
32. MANUAL TODO — BEFORE FIRST END-TO-END TEST
============================================================

Not automated on purpose (real AWS cost, real secret values, a real
external account). Do these only when actually ready to test the ecs-demo
environment end-to-end.

[x] 1. Create a Qdrant Cloud Free Tier cluster (AWS_Deployment.md section 3
       -- Qdrant is external, Terraform does not provision it). Done --
       cluster and API key exist. Reminder for step 2 below: the cluster
       endpoint needs an explicit `:6333` port appended for `qdrant_url`
       (confirmed against Qdrant's own docs -- their client examples
       always include it; omitting it risks a connection error). The
       key/endpoint are not committed anywhere in this repo -- keep them
       out of any file that gets `git add`ed.

[ ] 2. Apply Phase 3 + 4 + 5 together (RDS, ElastiCache, Secrets Manager
       containers, ECS cluster, API service, ALB, all four worker
       services) -- applying Phase 3 alone first would pay for
       RDS/ElastiCache with nothing yet able to connect to them:

    cd infra/terraform/environments/ecs-demo
    AWS_PROFILE=researchmind-deploy terraform apply \
      -var="backend_image_tag=bc623c6" \
      -var="qdrant_url=<your Qdrant Cloud cluster URL, with :6333 appended>"

    Expect 38 resources to add (with the default `enable_mcp=false` --
    MCP is skipped entirely rather than deployed-and-broken until
    research-intelligence-mcp has a real image, see section 34): RDS+
    ElastiCache+10 secrets (18, including the always-created
    mcp-auth-token placeholder), ECS cluster+ALB+CloudFront+API service
    (8), 4 worker services (12). Starts real ongoing cost (~$21-27/month
    RDS+ElastiCache, plus ALB/Fargate billing for 5 running tasks, plus
    ~$4/month for 10 Secrets Manager secrets -- see
    infra/terraform/README.md's cost table). `backend_image_tag` must be
    an existing tag in the researchmind-backend ECR repo (currently
    `bc623c6`; push a new one first if the code has moved on -- the SAME
    tag deploys to all 5 services, one shared image). Run
    `terraform destroy` when done testing.

[ ] 3. Populate the 10 Secrets Manager containers Phase 3 created (real
       values, never through Terraform/tfstate) -- ALL 10 need at least
       one version set, even if empty, or every task (API and all four
       workers, since their task definitions reference all of them via
       `local.common_secrets`) fails at launch with
       `ResourceNotFoundException` (Secrets Manager has no AWSCURRENT
       version to resolve) -- this is not optional cleanup, a
       never-populated secret blocks every service, not just the one
       that would have used it. If `research-intelligence-mcp` turns out
       not to need `mcp-auth-token` (section 34), set it to an explicit
       empty string, don't leave it unset:

    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/groq-api-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/openai-api-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/anthropic-api-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/voyage-api-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/tavily-api-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/langsmith-api-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/app-secret-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/cognito-client-secret --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/qdrant-api-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/mcp-auth-token --secret-string "<value, or \"\" if unused>"

    RDS's DATABASE_URL secret is NOT in this list -- Terraform generates
    and owns that value itself (modules/rds), you never touch it.

    After populating secrets, force a fresh deployment on all five
    services so they pick up the new values (ECS resolves secrets once
    per task, not continuously):

    for svc in api worker-processing worker-research-runtime worker-eval-scoring worker-memory-lifecycle; do
      AWS_PROFILE=researchmind-deploy aws ecs update-service \
        --cluster researchmind-ecs-demo-cluster \
        --service "researchmind-ecs-demo-$svc" \
        --force-new-deployment --region us-east-1
    done

[ ] 4. Verify the API directly (HTTP, via the ALB):

    curl http://$(cd infra/terraform/environments/ecs-demo && AWS_PROFILE=researchmind-deploy terraform output -raw api_url | sed 's#http://##')/api/v1/health/live

    Then verify the HTTPS front door (CloudFront, Phase 7 -- this is the
    URL Amplify actually uses):

    curl $(cd infra/terraform/environments/ecs-demo && AWS_PROFILE=researchmind-deploy terraform output -raw api_https_url)/api/v1/health/live

    (CloudFront distributions take 5-15 minutes to deploy after apply --
    if this curl fails right after `terraform apply`, that's likely why;
    retry rather than assuming something's broken.) Verify the workers by
    checking CloudWatch Logs (`/ecs/researchmind-ecs-demo-worker-*`) or,
    for research-runtime/memory-lifecycle, hitting their `/metrics` port
    directly if reachable.

[ ] 5. Apply the frontend (Amplify, Phase 7) using the `api_https_url`
       from step 4 -- see section 35 for the full walkthrough (GitHub
       connection, the two-phase `base_url` apply, Cognito callback/logout
       URLs). Do this as part of the same testing session, not a separate
       later thing to remember, since the API isn't actually reachable
       from a browser (mixed content) until CloudFront exists anyway.

    ⚠️  DO NOT run `terraform destroy` in `environments/frontend`. Unlike
    Phase 3-5 above, Amplify is meant to stay up between sessions --
    destroying it is NOT part of the normal end-of-session cleanup. See
    the cost note at the end of section 35 and
    infra/terraform/README.md's "Working with the frontend environment".

When you're done testing, `terraform destroy` in `environments/ecs-demo`
only (Phase 3-5, and Phase 6 if `enable_mcp=true` was used) -- leave
`environments/frontend` applied. Until Phase 3-5 above are done,
they stay as validated-but-unapplied Terraform code (see
infra/terraform/README.md "Current status").

============================================================
33. CLOUDFRONT — HTTPS FOR THE ALB
============================================================

The ALB (Phase 4) is HTTP-only, since there is no custom domain to put a
real ACM certificate on. This blocks Phase 7: the Amplify frontend is
HTTPS, and every modern browser blocks an HTTPS page from calling an HTTP
API as mixed content.

DECISION: put an Amazon CloudFront distribution in front of the ALB.

    Browser (HTTPS)
         |
         v
    CloudFront
      *.cloudfront.net
      (AWS-provided cert, automatic)
         |
       HTTP (internal AWS traffic, not internet-exposed)
         |
         v
    ALB (stays HTTP-only, unchanged)
         |
         v
    ECS/Fargate API

Why this over a custom domain:

    - CloudFront terminates TLS on its own *.cloudfront.net domain using
      an AWS-provided certificate automatically. No domain ownership, no
      DNS validation, no Route 53 hosted zone needed.
    - Cost is effectively $0 at this project's traffic level -- well
      within CloudFront's free tier (1TB/month data transfer, 10M
      requests/month).
    - CloudFront -> ALB over HTTP is fine: that leg never leaves AWS's
      network and is not exposed to the browser. The browser only ever
      sees the HTTPS CloudFront URL.
    - It is a legitimate, common production pattern (CDN in front of an
      ALB) worth having in the architecture for the "production
      engineering" story this project exists to tell.

Rejected/deferred alternative: a real custom domain (Route 53 domain
registration + hosted zone + ACM certificate + alias record to the ALB).
More "real" and gives a stable, brandable URL for demos/interviews, but
costs ~$12/year domain registration + ~$0.50/month hosted zone -- would
join Cognito/S3/ECR as an accepted low-cost *persistent* item rather than
something torn down each cycle. Worth reconsidering later if a stable
public URL becomes valuable; not needed to unblock Phase 7.

Implementation: done, in `environments/ecs-demo` (`modules/cloudfront`),
not a separate state -- CloudFront's whole purpose is fronting THIS
cycle's ALB, which gets a new DNS name every time ecs-demo is destroyed
and reapplied, so it shares that lifecycle rather than Amplify's (see
section 35). Caching is disabled (AWS managed `CachingDisabled` policy --
this fronts a dynamic JSON API, not static assets). Output
`api_https_url` is what feeds `environments/frontend`'s `api_url`
variable. Not yet applied -- see section 32's manual TODO (Phase 3-5) and
section 35 (Amplify) for the actual apply steps.

============================================================
34. REMAINING WORK IN research-intelligence-mcp (SEPARATE REPO)
============================================================

Phase 6 (MCP) is split across two repositories. Everything on the
ResearchMind-AI side is done in Terraform: the ECS service/task
definition, Cloud Map service discovery so the API/Research Runtime
worker can resolve it privately, the security group rule allowing that
traffic, and `MCP_PAPERS_SERVER_URL`/`MCP_PAPERS_ENABLED` wired into the
shared environment. None of it can run yet, because the
research-intelligence-mcp repository itself needs:

[ ] 1. A Dockerfile (same idea as this repo's docker/backend.Dockerfile --
       one image, `python:3.12-slim`-style base, whatever the MCP
       server's actual entrypoint/command is). Does not exist yet as far
       as this repository can see.

[ ] 2. Build and push that image to the ECR repository Terraform already
       created here (Phase 2):

    AWS_PROFILE=researchmind-deploy aws ecr get-login-password --region us-east-1 \
      | docker login --username AWS --password-stdin 232727982313.dkr.ecr.us-east-1.amazonaws.com
    docker build -t 232727982313.dkr.ecr.us-east-1.amazonaws.com/research-intelligence-mcp:<tag> .
    docker push 232727982313.dkr.ecr.us-east-1.amazonaws.com/research-intelligence-mcp:<tag>

    The repo is immutable-tagged (same reasoning as researchmind-backend,
    see section 17) -- use a real tag (e.g. that repo's own git short SHA),
    not `latest`.

[ ] 3. Confirm the MCP server actually listens on port 8080 and speaks
       plain HTTP inside the VPC (matches this repo's
       `MCP_PAPERS_SERVER_URL=http://127.0.0.1:8080/mcp` local default,
       and what the Terraform here assumes -- `container_port = 8080`,
       no TLS, since it's never internet-exposed, only reachable from the
       API/worker security group over Cloud Map's private DNS).

[ ] 4. Confirm whether the MCP server actually requires
       `MCP_PAPERS_AUTH_TOKEN` for anything -- this repo's Terraform
       already provisions an `mcp-auth-token` Secrets Manager container
       for it either way. It still needs a value set (even an explicit
       empty string) before any task can launch -- see section 32 step 3;
       a secret with zero versions breaks every service's task launch,
       not just the one that would have used it.

[ ] 5. Once pushed, apply Phase 6 here with the real tag and
       `enable_mcp=true` (without it, MCP is skipped entirely regardless
       of what's in ECR -- see the enable_mcp variable in
       environments/ecs-demo/variables.tf):

    cd infra/terraform/environments/ecs-demo
    AWS_PROFILE=researchmind-deploy terraform apply \
      -var="backend_image_tag=bc623c6" \
      -var="qdrant_url=<your Qdrant Cloud cluster URL>" \
      -var="enable_mcp=true" \
      -var="mcp_image_tag=<research-intelligence-mcp tag>"

This section exists so the "what's left" list isn't only in chat history.
Update the checkboxes here as each step happens in the other repo.

============================================================
35. PHASE 7 — FRONTEND (AMPLIFY) MANUAL SETUP
============================================================

`infra/terraform/environments/frontend` creates the Amplify app shell
(name, platform=WEB_COMPUTE, monorepo build spec targeting apps/web,
environment variables) in its OWN Terraform state -- deliberately
separate from ecs-demo. Amplify is meant to outlive the backend's
apply/destroy cycles (section 5 / docs/deployment/06's cost strategy:
"Amplify frontend remains available" while "ECS backend: apply ->
test/demo -> destroy"); keeping it in ecs-demo's state would mean
`terraform destroy` there tears down the frontend too, which isn't the
intent.

What Terraform does NOT do: connect the GitHub repository. That needs a
real OAuth handshake (Amplify's GitHub App -- the modern recommended
flow, not a raw personal access token sitting in Terraform state/config).
Also unresolved without a live app: the build_spec's monorepo
`appRoot: apps/web` config is a first attempt based on AWS's documented
syntax, not something that could be verified without an actual build
(apps/web has no root-level package.json/workspace config for Amplify to
auto-detect, so this couldn't just be left to auto-detection either) --
watch the first build log and adjust if it fails.

[ ] 1. Apply the app shell (first pass, base_url left empty -- see
       environments/frontend/main.tf's comment on why it can't be
       derived automatically in one apply):

    cd infra/terraform/environments/frontend
    AWS_PROFILE=researchmind-deploy terraform apply \
      -var="api_url=<ecs-demo's api_https_url output>"

    Amplify Hosting's own idle cost is negligible (pay for build minutes
    + data served + storage, not idle compute) -- this one is fine to
    leave applied, unlike the ecs-demo resources.

[ ] 2. Console -> Amplify -> the new `researchmind-web` app -> connect
       the GitHub repository and branch (`main`) through the console's
       own flow -- this is the real OAuth handshake, Terraform can't do
       it. Save and deploy; watch the first build log (see the
       appRoot/monorepo caveat above).

[ ] 3. Once the first build succeeds, get the real app_id from Terraform
       and set base_url, then apply again so
       NEXT_PUBLIC_BASE_URL/NEXT_PUBLIC_REDIRECT_URI are wired in:

    AWS_PROFILE=researchmind-deploy terraform output app_id
    AWS_PROFILE=researchmind-deploy terraform apply \
      -var="api_url=<same as step 1>" \
      -var="base_url=https://main.<app_id from above>.amplifyapp.com"

    This triggers an Amplify redeploy (environment variable change).

[ ] 4. Add the frontend's callback/logout URLs to the EXISTING Cognito
       app client -- Cognito is treated as an existing/external resource
       here (section 13), not Terraform-managed, so this is a CLI step
       that ADDS to the current callback/logout URL lists, it does not
       replace them (check current values first so you don't drop the
       local-dev ones):

    AWS_PROFILE=researchmind-deploy aws cognito-idp describe-user-pool-client \
      --user-pool-id us-east-1_9chS0pt6P --client-id 1r4at7v1s9nr9jqots6gl15ht \
      --query "UserPoolClient.{Callbacks:CallbackURLs,Logouts:LogoutURLs}"

    AWS_PROFILE=researchmind-deploy terraform output cognito_callback_url_to_add
    AWS_PROFILE=researchmind-deploy terraform output cognito_logout_url_to_add

    Then re-run `update-user-pool-client` with the FULL merged list
    (existing URLs + the new one) for both `--callback-urls` and
    `--logout-urls` -- the API replaces the whole list, it does not
    append.

[ ] 5. Verify: open the Amplify app's URL in a browser, confirm Cognito
       Hosted UI login redirects back correctly, and confirm the frontend
       can reach the API through CloudFront without a mixed-content error
       in the browser console.

Cost note: unlike sections 32/34, none of this needs to be destroyed
between sessions -- Amplify Hosting and CloudFront are both effectively
free at this project's traffic level. What DOES need updating is
`api_url` (and therefore step 3's redeploy) whenever ecs-demo's
CloudFront distribution is destroyed and recreated with a new domain.

============================================================
36. PHASE 9 — CI/CD SETUP
============================================================

`infra/terraform/environments/cicd` provisions a GitHub Actions OIDC
provider and two least-privilege IAM roles (`ecr-push`, `ecs-deploy`) --
no long-lived AWS access keys ever sit in GitHub secrets; both workflows
exchange GitHub's own workflow-scoped OIDC token for short-lived AWS
credentials at runtime. Separate, persistent state from ecs-demo, same
reasoning as `environments/frontend` -- CI should be able to push images
to ECR regardless of whether ecs-demo happens to be applied right now.

Three workflows:

    .github/workflows/ci.yml
        tests/lint/mypy (already existed) + a new frontend-quality job
        (lint/type-check/build for apps/web). Runs on every push/PR to
        main/develop. No AWS access at all.

    .github/workflows/build-and-push.yml
        Builds docker/backend.Dockerfile, pushes to the researchmind
        -backend ECR repo tagged with the git short SHA. Auto-triggered
        on push to main when backend-relevant paths change, plus manual
        dispatch. Uses the ecr-push role.

    .github/workflows/deploy.yml
        Swaps the image in each of the 5 ECS task definitions (api + 4
        workers) to a given tag, registers a new revision, updates the
        service. MANUAL DISPATCH ONLY, never automatic -- ecs-demo may
        not even exist between sessions (see the ephemeral-environment
        model, section 2), so auto-deploying on every merge would either
        fail loudly or start Fargate tasks nobody asked for. Terraform
        still owns the *shape* of each task definition (CPU/memory, env
        vars, secrets, roles) -- this workflow only swaps the image
        within that shape; re-run `terraform apply` if the shape itself
        needs to change, not this workflow. Uses the ecs-deploy role.

[ ] 1. Apply the cicd environment (idle cost: negligible -- an OIDC
       provider and two IAM roles have no meaningful cost regardless):

    cd infra/terraform/environments/cicd
    AWS_PROFILE=researchmind-deploy terraform apply
    AWS_PROFILE=researchmind-deploy terraform output

[ ] 2. In the GitHub repo (supuni9622/ResearchMind-AI) -> Settings ->
       Secrets and variables -> Actions -> **Variables** tab (not
       Secrets -- these are role ARNs, not credentials) -> create:

    AWS_ECR_PUSH_ROLE_ARN  = <ecr_push_role_arn output>
    AWS_ECS_DEPLOY_ROLE_ARN = <ecs_deploy_role_arn output>

[ ] 3. Push a change touching a backend path (or use "Run workflow" on
       build-and-push.yml manually) and confirm it builds and pushes a
       new `researchmind-backend:<short-sha>` tag to ECR.

[ ] 4. Once ecs-demo is applied (section 32) and you want to deploy a
       newer image than the one Terraform originally deployed with:
       Actions -> "Deploy to ECS" -> Run workflow -> paste the tag from
       step 3. Watch the 5 parallel jobs (one per service).

Not done here, deliberately out of scope for this project's size: a
staging/production environment split, approval gates, or canary/blue
-green deployment -- ecs-demo is a single ephemeral demo environment, not
a multi-stage pipeline target. Revisit only if that changes.

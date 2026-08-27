# ResearchMind --- Deployment Options & Architecture Decisions

## Goal

ResearchMind is a portfolio/interview project with production-grade
architecture but almost no real traffic. The priorities are:

-   production-grade reliability and scalability patterns;
-   Terraform and AWS infrastructure learning;
-   Kubernetes learning using the real application;
-   minimal persistent cloud cost;
-   a hard target of about **\$5/month** for persistent usage.

The key distinction is **production-grade architecture ≠ 24/7 production
infrastructure**.

## Options considered

  ----------------------------------------------------------------------------------------
  Option            Strengths             Weaknesses                     Decision
  ----------------- --------------------- ------------------------------ -----------------
  **Lambda**        Very low idle cost,   Less natural for long-running  Not core runtime;
                    automatic scaling,    AI workflows/workers; requires useful for small
                    event-driven          function-oriented design       event-driven jobs

  **ECS + Fargate** Docker-native,        Always-running tasks have real **Current
                    long-running          cost                           production
                    processes, simple                                    architecture**
                    operations, no EC2                                   
                    management                                           

  **ECS + EC2**     Better economics at   EC2                            Future
                    high predictable      patching/capacity/operations   optimization
                    utilization; host                                    
                    control                                              

  **EKS + Fargate** Kubernetes ecosystem  Kubernetes complexity + EKS    **Learning/lab
                    without managing      cost                           environment**
                    worker nodes                                         

  **EKS + EC2**     Maximum               Highest operational complexity Future option for
                    Kubernetes/hardware                                  substantial
                    flexibility; strong                                  Kubernetes/GPU
                    GPU fit                                              needs
  ----------------------------------------------------------------------------------------

> EKS + EC2 is the Kubernetes + EC2 option considered. ECS/EKS are
> orchestrators; Fargate/EC2 are compute choices.

## Why not Lambda for the core system?

ResearchMind contains a FastAPI API plus four long-running workers:

1.  document processing;
2.  Research Runtime;
3.  online evaluation scoring;
4.  memory lifecycle.

Research workflows can involve planning, retrieval, tools, agent loops,
external providers, synthesis and streaming. Lambda can complement the
system, but making the entire runtime Lambda-based would add
architectural complexity without a strong benefit.

## Why ECS + Fargate?

The existing Docker architecture maps directly to ECS:

``` text
Docker image → ECR → ECS task definition → Fargate
```

Benefits:

-   long-running FastAPI and workers;
-   independent worker services;
-   horizontal scaling;
-   ECS task replacement/restart;
-   ALB integration;
-   IAM and CloudWatch integration;
-   no EC2 server management;
-   direct integration with S3, SQS, Cognito, RDS and ElastiCache;
-   Terraform can provision the infrastructure.

Reliability comes from the surrounding design, not Fargate alone:

``` text
ALB
 ├── Fargate task / AZ-A
 └── Fargate task / AZ-B

SQS → independently supervised workers
RDS → relational persistence
Valkey → cache/locking
CloudWatch → logs/metrics
Terraform → reproducibility
```

For this project the full environment is **ephemeral**:

``` text
terraform apply → test/demo/scale → terraform destroy
```

## When would ECS + EC2 make sense?

Move when:

-   utilization is high and predictable;
-   Fargate becomes a meaningful recurring cost;
-   workloads run continuously;
-   specialized host/instance control is required;
-   GPU or other hardware requirements favor EC2;
-   better container density/bin-packing is important.

Tradeoff: EC2 introduces capacity planning, patching, AMIs, instance
scaling and host failure management.

## When would ECS + Fargate move to EKS + Fargate?

Move when Kubernetes provides capabilities worth its complexity:

  Scenario                                  Reason
  ----------------------------------------- ----------------------------------
  Organization standardizes on Kubernetes   Platform consistency
  Many teams/services                       Shared platform
  Helm/operators/CRDs                       Kubernetes ecosystem
  GitOps                                    Argo CD/Flux
  Advanced scheduling                       Kubernetes scheduling primitives
  Hybrid/multi-cloud                        Kubernetes portability
  Kubernetes-native AI/GPU ecosystem        Platform capabilities
  Existing Kubernetes platform team         Lower operational penalty

This is primarily a **platform capability decision**, not a cost
optimization.

## When would ECS + Fargate move to EKS + EC2?

Consider it when both Kubernetes and direct compute control are
required:

-   GPU model inference;
-   specialized hardware;
-   high sustained utilization;
-   node-level agents/DaemonSets;
-   advanced scheduling;
-   storage/networking requirements needing node control;
-   mature Kubernetes platform operations.

## Terraform

Terraform is part of the real ResearchMind deployment.

It will provision infrastructure such as:

``` text
VPC
subnets/routing
security groups
IAM
ECR
ECS/Fargate
ALB
RDS
ElastiCache
Secrets Manager
```

The same application is used in three modes:

``` text
Local        → Docker Compose
AWS demo     → Terraform → ECS/Fargate
Kubernetes   → Terraform → EKS/Fargate
```

## Final decisions

-   **Daily development:** Docker Compose.
-   **Production-like AWS:** ECS + Fargate + Terraform, ephemeral.
-   **Kubernetes learning:** EKS + Fargate + Terraform, ephemeral.
-   **Frontend:** AWS Amplify.
-   **Vector DB:** Qdrant Cloud Free Tier.
-   **Database:** RDS PostgreSQL.
-   **Cache:** ElastiCache Valkey, subject to semantic-cache
    compatibility validation.
-   **Queue:** SQS.
-   **Object storage:** S3.
-   **Auth:** existing Cognito.
-   **Secrets:** Secrets Manager.
-   **MCP:** separate ECS/Fargate service from its own repository.

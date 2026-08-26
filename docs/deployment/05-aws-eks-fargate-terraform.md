# ResearchMind --- AWS EKS/Fargate + Terraform Kubernetes Lab

## Purpose

This is a separate Kubernetes learning environment.

It is **not** the primary production architecture.

Goals:

-   learn EKS;
-   learn Kubernetes;
-   use Terraform;
-   deploy the real ResearchMind images;
-   practice scaling and failure recovery;
-   compare Kubernetes with ECS.

## Lifecycle

``` text
terraform apply
   ↓
EKS + Fargate
   ↓
Kubernetes deployment
   ↓
learn / test / scale / break
   ↓
terraform destroy
```

Never treat this as a permanent environment.

## Architecture

``` text
EKS
|
+-- namespace: researchmind
|
+-- Deployment: API
+-- Deployment: document worker
+-- Deployment: Research Runtime worker
+-- Deployment: evaluation worker
+-- Deployment: memory lifecycle worker
+-- Deployment/Service: MCP
+-- Services
+-- ConfigMaps
+-- Secrets
+-- health probes
```

## Reuse the same images

``` text
researchmind-backend
research-intelligence-mcp
```

The frontend has no Kubernetes Deployment in this lab either -- it stays on
Amplify Hosting regardless of which backend compute environment (ECS or
EKS) is active, matching `AWS_Deployment.md`'s closing diagram where
Amplify/Qdrant Cloud sit outside all three compute environments.

Do not rewrite the application for Kubernetes.

The backend image remains shared across API and the four workers.

## External services

Do not recreate every dependency inside Kubernetes.

Use:

``` text
RDS PostgreSQL
ElastiCache Valkey
S3
SQS
Cognito
Qdrant Cloud
```

where appropriate.

The purpose is to learn Kubernetes orchestration, not duplicate managed
services.

## Kubernetes concepts to learn

Start with:

-   Pods;
-   Deployments;
-   Services;
-   Namespaces;
-   ConfigMaps;
-   Secrets;
-   resource requests/limits;
-   liveness/readiness probes;
-   rolling deployments;
-   Horizontal Pod Autoscaler.

Later:

-   scheduling;
-   affinity;
-   taints/tolerations;
-   Ingress;
-   network policies;
-   Helm;
-   GitOps.

## Experiments

### Scaling

``` text
API: 1 pod → 3 pods
```

Observe scheduling and request distribution.

### Failure recovery

Delete a pod and observe Kubernetes recreate it.

### Rolling deployment

Deploy a new image and observe:

``` text
new pods
   ↓
healthy
   ↓
old pods removed
```

### Resource management

Experiment with:

``` text
CPU requests
memory requests
CPU limits
memory limits
```

## ECS vs EKS comparison

  Area                     ECS/Fargate       EKS/Fargate
  ------------------------ ----------------- ---------------------
  Orchestrator             ECS               Kubernetes
  Compute                  Fargate           Fargate
  Images                   Same              Same
  API                      Same              Same
  Workers                  Same              Same
  Scaling                  ECS autoscaling   Kubernetes HPA/etc.
  Service discovery        ECS/Cloud Map     Kubernetes Services
  Configuration            ECS config        ConfigMaps
  Operational complexity   Lower             Higher
  Kubernetes ecosystem     No                Yes

The experiment should answer:

> What does Kubernetes give us that justifies its additional complexity?

## Terraform separation

Use:

``` text
infra/terraform/environments/ecs-demo
infra/terraform/environments/eks-lab
```

Do not mix EKS resources into the ECS environment.

## Future EKS + EC2 learning

Later, if needed, compare EKS/Fargate with EKS/EC2 for:

-   GPU inference;
-   specialized hardware;
-   sustained high utilization;
-   node-level control;
-   advanced scheduling.

Do not introduce EKS/EC2 without a concrete learning objective.

# ResearchMind — Terraform

Two environments, kept deliberately separate (`AWS_Deployment.md` section 20):

```text
infra/terraform/
  bootstrap/              one-time: S3 state bucket + DynamoDB lock table
  modules/                 shared building blocks (vpc, iam, ...)
  environments/
    ecs-demo/              production-like ECS/Fargate environment (ephemeral)
    eks-lab/                Kubernetes learning environment (ephemeral, not yet started)
```

For the full architecture and *why* each service was chosen, see
[`../../AWS_Deployment.md`](../../AWS_Deployment.md),
[`../../docs/deployment/`](../../docs/deployment/) (01-06), and the Phase 0
validation findings in
[`../../docs/deployment/07-phase0-validation-findings.md`](../../docs/deployment/07-phase0-validation-findings.md).
This file is only about the apply/destroy workflow.

## Cost — read this before running `apply`

**Hard target: ~$5/month persistent spend.** `ecs-demo` is ephemeral by
design:

```text
terraform apply  →  deploy/test/demo  →  terraform destroy
```

Resources here are **not** meant to run 24/7. The dangerous ones to forget
running are, in rough order of how expensive "leave it on by accident" is:

| Resource | Cost if left running | Notes |
|---|---|---|
| RDS PostgreSQL | ~$12-15/mo+ (smallest instance) | Created in Phase 3 |
| ElastiCache Valkey | ~$9-12/mo+ (`cache.t4g.micro`) | Created in Phase 3 |
| ALB | ~$16-20/mo + LCU usage | Created in Phase 4 |
| ECS/Fargate tasks | Billed per vCPU/GB-hour while running | Created in Phase 4-5 |
| NAT Gateway | **Not created by default** — see Phase 0 finding §11; only ever added temporarily, never left running | |

None of these exist yet as of this commit — only the Phase 1 foundation
(VPC, subnets, security groups, IAM roles) does, and none of those four
resource types have a meaningful idle cost.

**Before every `apply`:** know what you're about to create and roughly what
it costs. **After every session:** run `terraform destroy` on `ecs-demo`
unless you have a specific reason to keep it up (see below for what's safe
to leave running).

Low-cost/persistent-by-design and **not** part of this destroy workflow: the
`bootstrap` state bucket/lock table (fractions of a cent/month), Cognito, S3,
SQS, ECR repositories (storage only, cheap), IAM, Qdrant Cloud Free Tier.

## One-time setup: bootstrap the state backend

```bash
cd infra/terraform/bootstrap
terraform init
terraform apply
terraform output   # note state_bucket_name and lock_table_name
```

Then fill in `environments/ecs-demo/providers.tf`'s `backend "s3"` block
(`bucket` and `dynamodb_table`) with those two output values. This only
needs to happen once per AWS account; never run `terraform destroy` in
`bootstrap/` while `ecs-demo` (or `eks-lab`) still has state stored there.

## Working with an environment

```bash
cd infra/terraform/environments/ecs-demo
cp terraform.tfvars.example terraform.tfvars   # adjust if needed, gitignored
terraform init
terraform plan     # review before every apply -- know what's about to be billed
terraform apply
```

When you're done testing/demoing:

```bash
terraform destroy
```

`terraform plan` before `apply` and reading what `destroy` is about to remove
before confirming are not optional steps for this project — the whole point
of the ephemeral-environment model is that nothing expensive survives a
session by accident.

## Current status

Phase 1 only (`AWS_Deployment.md` section 26): VPC, public/private subnets
across 2 AZs, route tables, security groups (ALB/ECS-tasks/RDS/ElastiCache,
chained by reference), and IAM roles (ECS task execution + task role, scoped
to the existing S3 bucket and SQS queues from Phase 0 validation). No ECS
cluster, ALB, RDS, ElastiCache, or ECR yet — those are later phases, built on
this foundation, reviewed before their own first `apply`.

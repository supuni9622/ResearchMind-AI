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
| RDS PostgreSQL | ~$12-15/mo+ (`db.t4g.micro`) | Terraform written (Phase 3) — not yet applied |
| ElastiCache Valkey | ~$9-12/mo+ (`cache.t4g.micro`) | Terraform written (Phase 3) — not yet applied |
| ALB | ~$16-20/mo + LCU usage | Created in Phase 4 |
| ECS/Fargate tasks | Billed per vCPU/GB-hour while running | Created in Phase 4-5 |
| NAT Gateway | **Not created by default** — see Phase 0 finding §11; only ever added temporarily, never left running | |

Live as of this commit: Phase 1 (VPC, subnets, security groups, IAM roles)
and Phase 2 (ECR repositories, `researchmind-backend` image pushed) — none
of those have a meaningful ongoing cost. Phase 3's RDS/ElastiCache Terraform
exists but has not been applied; applying it starts the ~$12-15/mo +
~$9-12/mo clock above.

**Before every `apply`:** know what you're about to create and roughly what
it costs. **After every session:** run `terraform destroy` on `ecs-demo`
unless you have a specific reason to keep it up (see below for what's safe
to leave running).

Low-cost/persistent-by-design and **not** part of this destroy workflow: the
`bootstrap` state bucket/lock table (fractions of a cent/month), Cognito, S3,
SQS, ECR repositories (storage only, cheap), IAM, Qdrant Cloud Free Tier.

## One-time setup: a deploy IAM user

Terraform needs broader permissions than the app's own runtime credentials
(`researchmind-api-dev`, used by `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`
in `.env`) — that user is deliberately scoped down and can't create a VPC,
IAM roles, RDS, etc. Keep the two separate; don't widen the app's runtime
user.

1. Console → **IAM** → **Users** → **Create user** → name
   `researchmind-terraform-deploy`, no console access (programmatic only).
2. Attach `AdministratorAccess` (single-tenant portfolio account; a hand
   -scoped policy isn't worth maintaining across every phase below). A
   tighter alternative is `PowerUserAccess` + `IAMFullAccess`.
3. That user → **Security credentials** → **Create access key** → CLI use
   case → copy the key ID/secret.
4. Configure a **named profile** locally (don't overwrite `default`, which
   stays the scoped-down app credential):

   ```bash
   aws configure --profile researchmind-deploy
   # Access key / secret from step 3, region us-east-1, output json
   ```

5. Verify:

   ```bash
   AWS_PROFILE=researchmind-deploy aws sts get-caller-identity
   # Arn should end in :user/researchmind-terraform-deploy
   ```

Every `terraform` command below runs with `AWS_PROFILE=researchmind-deploy`
set. When you're not actively deploying, you can deactivate (not delete)
that access key from the IAM console — same "don't leave things running
unnecessarily" spirit as the cost rules above.

## One-time setup: bootstrap the state backend

```bash
cd infra/terraform/bootstrap
AWS_PROFILE=researchmind-deploy terraform init
AWS_PROFILE=researchmind-deploy terraform apply
AWS_PROFILE=researchmind-deploy terraform output   # note state_bucket_name and lock_table_name
```

Then fill in `environments/ecs-demo/providers.tf`'s `backend "s3"` block
(`bucket` and `dynamodb_table`) with those two output values. This only
needs to happen once per AWS account; never run `terraform destroy` in
`bootstrap/` while `ecs-demo` (or `eks-lab`) still has state stored there.

Already done for this project's AWS account (232727982313, us-east-1):

```text
state_bucket_name = "researchmind-terraform-state-232727982313"
lock_table_name   = "researchmind-terraform-locks"
```

`environments/ecs-demo/providers.tf` already points at these — skip this
section unless bootstrapping a different AWS account.

## Working with an environment

```bash
cd infra/terraform/environments/ecs-demo
cp terraform.tfvars.example terraform.tfvars   # adjust if needed, gitignored
AWS_PROFILE=researchmind-deploy terraform init
AWS_PROFILE=researchmind-deploy terraform plan     # review before every apply -- know what's about to be billed
AWS_PROFILE=researchmind-deploy terraform apply
```

When you're done testing/demoing:

```bash
AWS_PROFILE=researchmind-deploy terraform destroy
```

`terraform plan` before `apply` and reading what `destroy` is about to remove
before confirming are not optional steps for this project — the whole point
of the ephemeral-environment model is that nothing expensive survives a
session by accident.

## Current status

**Phase 1 is applied and live** in this project's AWS account (232727982313,
us-east-1): VPC (`vpc-0bc248f2a870a8d8b`), public/private subnets across 2
AZs, route tables, security groups (ALB/ECS-tasks/RDS/ElastiCache, chained by
reference), and IAM roles (ECS task execution + task role, scoped to the
existing S3 bucket and SQS queues from Phase 0 validation). Run
`terraform output` in `environments/ecs-demo` for current resource IDs.

None of these resources have an ongoing cost, so there's no urgency to
destroy them — but `terraform destroy` still removes them cleanly when no
longer needed.

No ECS cluster, ALB, RDS, ElastiCache, or ECR yet — those are later phases,
built on this foundation, reviewed before their own first `apply`.

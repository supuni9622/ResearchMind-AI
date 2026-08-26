# ResearchMind — Terraform

Three environments/states, kept deliberately separate:

```text
infra/terraform/
  bootstrap/              one-time: S3 state bucket + DynamoDB lock table
  modules/                 shared building blocks (vpc, iam, ecs-service, ...)
  environments/
    ecs-demo/              production-like ECS/Fargate environment (ephemeral)
    frontend/               Amplify Hosting for apps/web (persistent -- outlives ecs-demo's cycles)
    eks-lab/                Kubernetes learning environment (ephemeral, not yet started)
```

`ecs-demo`/`eks-lab` are separated per `AWS_Deployment.md` section 20.
`frontend` is separate from `ecs-demo` for a different reason: Amplify is
meant to outlive the backend's apply/destroy cycles (section 5 /
docs/deployment/06's cost strategy), so it has its own state rather than
being destroyed alongside RDS/ElastiCache/ALB/ECS every cycle.

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
| ALB | ~$16-20/mo + LCU usage | Terraform written (Phase 4) — not yet applied |
| ECS/Fargate (API + 4 workers) | Billed per vCPU/GB-hour while running (2.5 vCPU / 6GB combined to start) | Terraform written (Phase 4-5) — not yet applied |
| NAT Gateway | **Not created by default** — see Phase 0 finding §11; only ever added temporarily, never left running | |

Live as of this commit: Phase 1 (VPC, subnets, security groups, IAM roles)
and Phase 2 (ECR repositories, `researchmind-backend` image pushed) — none
of those have a meaningful ongoing cost. Phase 3 (RDS/ElastiCache/Secrets
Manager), Phase 4 (ECS cluster/API service/ALB/CloudFront), Phase 5 (the
four worker services), and Phase 6 (MCP, behind an `enable_mcp` toggle --
see below) Terraform all exist in `ecs-demo` but have not been applied —
`terraform plan` shows 38 resources to add with the default
`enable_mcp=false` (43 with `enable_mcp=true`). Applying starts the
~$21-27/mo RDS+ElastiCache clock plus ALB/Fargate billing (5 Fargate
tasks, 6 once MCP is enabled) plus ~$0.40/mo per Secrets Manager secret
(10 of them = ~$4/mo — not negligible, this is why secrets are destroyed
with everything else, not left running). CloudFront itself adds ~$0 at
this traffic level (within its free tier). See `AWS_Deployment.md`
section 32 for the exact apply/secrets/verify steps, and section 34 for
what's still needed in the separate `research-intelligence-mcp` repo
before `enable_mcp=true` is useful.

`environments/frontend` (Amplify) is separate and near-$0 either way
(pay for build minutes + data served, not idle compute) — see "Working
with the frontend environment" below and `AWS_Deployment.md` section 35.

**Before every `apply`:** know what you're about to create and roughly what
it costs. **After every session:** run `terraform destroy` on `ecs-demo`
unless you have a specific reason to keep it up (see below for what's safe
to leave running). Do NOT run `terraform destroy` on `environments/frontend`
as part of this routine — Amplify is meant to stay up.

Low-cost/persistent-by-design and **not** part of `ecs-demo`'s destroy
workflow: the `bootstrap` state bucket/lock table (fractions of a
cent/month), Cognito, S3, SQS, ECR repositories (storage only, cheap),
IAM, Qdrant Cloud Free Tier, and everything in `environments/frontend`
(Amplify Hosting).

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

## Working with the frontend environment

Different lifecycle than `ecs-demo` -- apply once, leave it up, and only
reapply when `api_url` needs updating (whenever `ecs-demo`'s CloudFront
distribution is destroyed/recreated with a new domain) or when
`base_url` gets filled in after the first apply. See
`AWS_Deployment.md` section 35 for the full manual-setup walkthrough
(Amplify's GitHub connection needs a real OAuth handshake through the
Console, Terraform can't do it):

```bash
cd infra/terraform/environments/frontend
cp terraform.tfvars.example terraform.tfvars   # set api_url from ecs-demo's api_https_url output
AWS_PROFILE=researchmind-deploy terraform init
AWS_PROFILE=researchmind-deploy terraform plan
AWS_PROFILE=researchmind-deploy terraform apply
```

Do not run `terraform destroy` here as a matter of routine the way you
would for `ecs-demo` -- this environment is meant to stay applied.

## Current status

**Phase 1 is applied and live** in this project's AWS account (232727982313,
us-east-1): VPC (`vpc-0bc248f2a870a8d8b`), public/private subnets across 2
AZs, route tables, security groups (ALB/ECS-tasks/RDS/ElastiCache, chained by
reference), and IAM roles (ECS task execution + task role, scoped to the
existing S3 bucket and SQS queues from Phase 0 validation). Run
`terraform output` in `environments/ecs-demo` for current resource IDs.

**Phase 2 is also applied and live**: ECR repositories for
`researchmind-backend` and `research-intelligence-mcp`
(`researchmind-web` deliberately excluded — Amplify builds from GitHub
source, not ECR), with `researchmind-backend:bc623c6` pushed (877MB
compressed — see the Phase 2 commit for how it went from an initial 20GB
down to that).

None of Phase 1/2 has an ongoing cost, so there's no urgency to destroy
them — but `terraform destroy` still removes them cleanly when no longer
needed.

**Phase 3, 4, 5, and 6 are written and validated but NOT applied.** RDS,
ElastiCache, Secrets Manager containers, ECS cluster, API service,
ALB+CloudFront, all four worker services, and the MCP service/Cloud Map
wiring all exist in `environments/ecs-demo` as reviewed Terraform code
only. `terraform plan` shows 38 resources with the default
`enable_mcp=false` (MCP is skipped entirely, not just deployed-and-broken,
until `research-intelligence-mcp` actually has an image — see section
34), or 43 with `enable_mcp=true`. See `AWS_Deployment.md` section 32 for
the manual TODO to actually apply Phase 3-5 (needs a real Qdrant Cloud
cluster first, and the 10 secret values populated after apply), and
section 34 for what's left in the separate MCP repo before flipping
`enable_mcp` on.

**Phase 7 (`environments/frontend`, Amplify) is also written and
validated but NOT applied** — a separate state/lifecycle from `ecs-demo`
(see the top of this file for why). `terraform plan` shows 1 resource
(the Amplify app shell). See `AWS_Deployment.md` section 35 for the
manual walkthrough — the GitHub repo connection, the two-phase apply for
`base_url` (Amplify's own domain depends on an ID that isn't known until
after the first apply), and adding the frontend's callback/logout URLs
to the existing Cognito app client.

# Runbook: full lifecycle (spin up → verify → tear down) + known issues

This is the practical companion to `AWS_Deployment.md` (the phased build
plan) and `docs/deployment/01-06` (architecture/decisions). Use this file
when you actually want to bring the AWS demo environment up, test it, and
tear it back down to stay near the ~$5/month cost target.

**Current status (2026-08-26): `ecs-demo` is destroyed.** Confirmed clean
via `aws ecs list-clusters` / `aws rds describe-db-instances` / `aws
elasticache describe-replication-groups` / `aws ecr describe-repositories`
/ `aws ec2 describe-vpcs` — no RDS, ElastiCache, ECS cluster, ECR repo, or
VPC left for this project (RDS + ElastiCache were the only real ongoing
spend). `frontend` (Amplify, `app_id=dgje0byeua4jk`) and `cicd` were left
up as intended. Section 1.1's Cognito `invalid_client` bug was **not**
fixed before teardown — fix it first thing on the next spin-up, before
re-testing login. Use section 2 below to bring `ecs-demo` back.

**State layout** (`infra/terraform/environments/`):

| Environment | Lifecycle | Contains |
|---|---|---|
| `bootstrap` | Apply once, ever | S3 + DynamoDB remote-state backend |
| `ecs-demo` | Ephemeral — up/destroy per test cycle | VPC, ECR, RDS, ElastiCache, ECS cluster + 5 services, ALB, CloudFront, Secrets Manager, CloudWatch alarms |
| `frontend` | Persistent — never destroy routinely | Amplify Hosting app |
| `cicd` | Persistent — never destroy routinely | GitHub OIDC provider + IAM roles for Actions |

**Cost reality**: RDS and ElastiCache are the only always-on, always-billing
resources here. Amplify Hosting and the `cicd` IAM roles cost effectively
$0 while idle (no baseline fee, just per-build/per-request). So the actual
lever for "stop spending money" is destroying `ecs-demo` alone — `frontend`
and `cicd` can stay up indefinitely at negligible cost, and destroying them
means redoing manual GitHub-OAuth/Console steps that Terraform can't
automate (see section 35/36 of `AWS_Deployment.md`).

Cognito (`us-east-1_9chS0pt6P`) and the Qdrant Cloud cluster are **not**
Terraform-managed at all — they're pre-existing/external. Destroying
`ecs-demo` never touches either. If you want truly zero spend, pause or
delete the Qdrant Cloud cluster separately via its own console.

---

## 1. Known issues (open, unfixed as of 2026-08-26)

### 1.1 Cognito login: `invalid_client` on code exchange

**Symptom**: Cognito Hosted UI login redirects back to `/auth/callback`
with a valid `code`, CORS preflight succeeds, but the frontend shows
"Sign in failed — Failed to exchange authorization code." Backend logs
(`/ecs/researchmind-ecs-demo-api`) show:
```
{'cognito_error': 'invalid_client', 'event': 'auth.code_exchange_failed', ...}
```

**Root cause**: confirmed via
`aws cognito-idp describe-user-pool-client` — the app client
(`1r4at7v1s9nr9jqots6gl15ht`) is a **public client**
(`GenerateSecret: null`, no secret at all). But
`apps/api/app/services/auth.py` sends HTTP Basic Auth
(`client_id:client_secret`) to Cognito's `/oauth2/token` endpoint whenever
`settings.cognito_client_secret` is truthy — and it IS truthy, because
`environments/ecs-demo/main.tf` wires a real (non-empty) Secrets Manager
value into `COGNITO_CLIENT_SECRET` for every backend service:
```
main.tf:65:  COGNITO_CLIENT_SECRET = module.secrets.secret_arns["cognito-client-secret"]
main.tf:150: "cognito-client-secret",
```
Sending ANY client_secret to a public client makes Cognito reject the
whole request as `invalid_client`, regardless of whether the code itself
is valid.

**Fix (not yet applied)**: remove `COGNITO_CLIENT_SECRET` from
`local.common_secrets` (or from just the api service) in
`environments/ecs-demo/main.tf`, and drop `"cognito-client-secret"` from
the `module.secrets` list at line 150. `auth.py` already guards with
`if settings.cognito_client_secret:` — leaving the env var entirely unset
makes it `None` (the field's default) and the code correctly skips the
Basic Auth header for this public client. Rebuild is NOT required for
this fix (it's Terraform/secrets-only, not an app code change) — just
`terraform apply` after editing.

### 1.2 Cost/config gotchas fixed this session (for reference, not open issues)

These were real, live-reproduced bugs already fixed and committed —
listed here so a future spin-up doesn't need to rediscover them:

- **ElastiCache**: must use `aws_elasticache_replication_group`, not
  `aws_elasticache_cluster` (the latter's API doesn't support Valkey at
  all).
- **ECS/Fargate architecture mismatch**: images built on Apple Silicon are
  arm64-only; `runtime_platform.cpu_architecture` must match (module
  default is now `ARM64`, cheaper on Fargate anyway).
- **ALB killing healthy tasks**: `health_check_grace_period_seconds` must
  be set (now 120s on the API service) — without it, the ALB starts
  failing a new task before Fargate even finishes a cold image pull, and
  ECS kills a task that would have passed moments later.
- **CORS**: `FRONTEND_URL` must be a comma-separated list including BOTH
  `http://localhost:3000` and the Amplify app's domain — a single origin
  string blocks whichever one isn't listed. `cors.py`/`settings.py`
  already handle a comma-separated value.
- **Amplify Console drift**: once a human connects the GitHub repo via
  the Console, it silently rewrites `build_spec` and attaches an IAM
  service role, and later clobbers `repository`/`custom_rule` too.
  `aws_amplify_app.web` has `lifecycle.ignore_changes` covering all four
  — don't remove it.
- **Cognito `update-user-pool-client` is full-replace, not patch**: any
  call that doesn't re-specify `--allowed-o-auth-flows-user-pool-client`,
  `--allowed-o-auth-flows`, `--allowed-o-auth-scopes`, and
  `--supported-identity-providers` silently disables the OAuth flow
  entirely, breaking login for both environments at once. Always use the
  full command template in `AWS_Deployment.md` section 32 step 4 when
  adding a callback/logout URL.
- **ECR blocks `terraform destroy`**: a repo with images in it can't be
  deleted by default — every real teardown has pushed at least one tag
  first, so this stalled destroy at 71/72 resources. Fixed via
  `force_delete = true` on `modules/ecr`'s `aws_ecr_repository`. Caveat
  found live: on the repo that already existed *before* this fix was
  committed, `terraform plan -destroy` still didn't show `force_delete` in
  its diff at all (state predates the attribute) and the same
  `RepositoryNotEmptyException` recurred once. Worked around by deleting
  the images directly first (`aws ecr batch-delete-image --repository-name
  <repo> --image-ids $(aws ecr list-images --repository-name <repo>
  --query "imageIds[*].imageDigest" --output text | tr '\t' '\n' | sed
  's/^/imageDigest=/' | tr '\n' ' ')`), then re-running destroy. A repo
  created fresh under the new config (`force_delete = true` from the
  start) should not hit this — if it does anyway, use the same manual
  `batch-delete-image` fallback rather than debugging further.

---

## 2. Spin-up guide (from nothing to a working deployment)

Run everything with `AWS_PROFILE=researchmind-deploy` and `AWS_PAGER=""`.

1. **Bootstrap** (skip if already applied — check `infra/terraform/environments/bootstrap` has been applied before):
   ```
   cd infra/terraform/environments/bootstrap && terraform init && terraform apply
   ```

2. **ecs-demo, first apply** (creates VPC/ECR/RDS/ElastiCache/ECS/ALB/CloudFront — ECS services will fail to pull images until step 4, that's expected):
   ```
   cd infra/terraform/environments/ecs-demo
   terraform init
   terraform apply -var="qdrant_url=<your Qdrant Cloud cluster URL>"
   ```

3. **Populate secrets** in Secrets Manager (the DB password is
   auto-generated by Terraform; these are not):
   ```
   for name in openai-api-key anthropic-api-key groq-api-key langsmith-api-key voyage-api-key tavily-api-key qdrant-api-key app-secret-key; do
     aws secretsmanager put-secret-value \
       --secret-id researchmind/ecs-demo/$name \
       --secret-string "<real value from your local .env>" \
       --region us-east-1
   done
   ```
   (`mcp-auth-token` and `cognito-client-secret` also exist but are
   unused/placeholder-only right now — see section 1.1 above and section
   34 of `AWS_Deployment.md` for MCP.)

4. **Build, tag, push the backend image** (arm64 — matches the
   `runtime_platform` default):
   ```
   cd /Users/supunimanamperi/Projects/ResearchMind-AI
   docker build --platform linux/arm64 -f docker/backend.Dockerfile -t researchmind-backend:latest .
   TAG=$(git rev-parse --short HEAD)
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 232727982313.dkr.ecr.us-east-1.amazonaws.com
   docker tag researchmind-backend:latest 232727982313.dkr.ecr.us-east-1.amazonaws.com/researchmind-backend:$TAG
   docker push 232727982313.dkr.ecr.us-east-1.amazonaws.com/researchmind-backend:$TAG
   ```

5. **ecs-demo, second apply** — real image tag, services come up for real:
   ```
   terraform apply -var="backend_image_tag=$TAG" -var="qdrant_url=<same as step 2>"
   ```
   Verify:
   ```
   curl https://$(terraform output -raw api_https_url | sed 's|https://||')/api/v1/health
   # expect {"success":true,"data":{"status":"healthy",...}}
   ```

6. **frontend, first apply** (creates the Amplify app shell, `base_url=""`):
   ```
   cd ../frontend
   terraform init
   terraform apply -var="api_url=<ecs-demo's api_https_url output>"
   ```

7. **Connect GitHub via the Amplify Console** (cannot be done by
   Terraform — needs a real OAuth handshake). See `AWS_Deployment.md`
   section 35 for the exact screens. Note the resulting `app_id`.

8. **frontend, second apply** — now with the real Amplify domain:
   ```
   terraform apply -var="api_url=<same as step 6>" -var="base_url=https://main.<app_id>.amplifyapp.com"
   ```

9. **Cognito callback/logout URLs** — add BOTH the Amplify domain and
   `localhost:3000` using the FULL command template (see section 1.2
   above / `AWS_Deployment.md` section 32 step 4). Never call
   `update-user-pool-client` with just the URLs — it wipes the OAuth flow
   config.

10. **ecs-demo, third apply** — `frontend_url` var's default already
    includes the current known Amplify domain; if the app was recreated
    (new `app_id`), update the default in
    `environments/ecs-demo/variables.tf` and re-apply so `FRONTEND_URL`
    matches:
    ```
    cd ../ecs-demo
    terraform apply -var="backend_image_tag=$TAG" -var="qdrant_url=<same as before>"
    ```

11. **(Optional) cicd**: `cd ../cicd && terraform init && terraform apply`,
    then set `AWS_ECR_PUSH_ROLE_ARN` / `AWS_ECS_DEPLOY_ROLE_ARN` as GitHub
    repo variables (section 36 of `AWS_Deployment.md`).

12. **Test end-to-end**: visit the Amplify domain, log in via Cognito
    Hosted UI, confirm the callback completes (blocked right now by
    section 1.1's open issue — fix that first).

---

## 3. Tear-down guide (stop the spend)

**Only run `terraform destroy` in `ecs-demo`.** Never run it in
`frontend` or `cicd` as part of routine cleanup — they're cheap to leave
up and expensive (in manual Console/OAuth steps) to recreate.

```
cd infra/terraform/environments/ecs-demo
terraform destroy -var="backend_image_tag=<any value, unused by destroy>" -var="qdrant_url=<any value, unused by destroy>"
```

This deletes: VPC, ECR repos (and all pushed images), RDS instance (all
data lost — this is a demo DB, not backed up), ElastiCache, ECS
cluster/services/tasks, ALB, CloudFront distribution, Secrets Manager
entries, CloudWatch alarms/dashboard.

**Not touched by this destroy** (by design): the Cognito user pool
(external, pre-existing), the Qdrant Cloud cluster (external SaaS — pause
or delete separately if you want it at zero cost too), the Amplify app,
and the `cicd` IAM roles/OIDC provider.

To bring it back later: re-run the spin-up guide from step 2 (bootstrap
stays applied) — steps 6-9 (Amplify/Cognito URL wiring) don't need
repeating unless the Amplify app itself was also destroyed and recreated,
since `frontend`'s state and `app_id` persist independently.

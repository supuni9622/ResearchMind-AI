# AWS Amplify Hosting for apps/web (AWS_Deployment.md section 5). Deploys
# the Next.js frontend independently of the ECS backend -- see
# docs/deployment/06-frontend-amplify-deployment.md.
#
# What Terraform does NOT do here: connect the GitHub repository. That
# needs a real OAuth handshake (Amplify's GitHub App, the modern
# recommended flow -- not a raw personal access token sitting in
# Terraform state/config). Creating the app "shell" here and connecting
# the repo via the Amplify Console afterward is a standard, supported
# pattern -- see AWS_Deployment.md section 35's manual TODO for the exact
# steps.
#
# The build_spec below uses Amplify's monorepo `applications`/`appRoot`
# syntax (docs.aws.amazon.com/amplify -- Configuring monorepo build
# settings) because apps/web has no root-level package.json/workspace
# config for Amplify to auto-detect -- it's a plain subdirectory, not an
# npm/yarn/pnpm workspace. This is a first-attempt, unverified
# configuration (no way to test Amplify build behavior without actually
# running a build) -- watch the first build log and adjust if needed.

resource "aws_amplify_app" "web" {
  name     = var.app_name
  platform = "WEB_COMPUTE" # Next.js SSR (output: "standalone") -- plain "WEB" is static-only

  build_spec = <<-YAML
    version: 1
    applications:
      - appRoot: apps/web
        frontend:
          phases:
            preBuild:
              commands:
                - npm ci
            build:
              commands:
                - npm run build
          artifacts:
            baseDirectory: .next
            files:
              - '**/*'
          cache:
            paths:
              - node_modules/**/*
  YAML

  # NEXT_PUBLIC_BASE_URL/NEXT_PUBLIC_REDIRECT_URI depend on this app's own
  # ID (Amplify's default domain is https://main.<app-id>.amplifyapp.com)
  # -- a resource's own computed attribute can't feed back into its own
  # arguments in one apply (Terraform: "Cycle: aws_amplify_app.web,
  # local.base_url"), so var.base_url is a plain input, not derived from
  # aws_amplify_app.web.id. This means two applies to get fully wired:
  # first with base_url left "" (app gets created, app_id becomes known
  # from the output), then set base_url to
  # "https://main.<that app_id>.amplifyapp.com" and apply again. Same
  # two-phase shape as bootstrap -> ecs-demo's backend config.
  environment_variables = merge(
    {
      AMPLIFY_MONOREPO_APP_ROOT = "apps/web"

      NEXT_PUBLIC_API_URL           = var.api_url
      NEXT_PUBLIC_COGNITO_DOMAIN    = var.cognito_domain
      NEXT_PUBLIC_COGNITO_CLIENT_ID = var.cognito_app_client_id
    },
    var.base_url == "" ? {} : {
      NEXT_PUBLIC_BASE_URL     = var.base_url
      NEXT_PUBLIC_REDIRECT_URI = "${var.base_url}/auth/callback"
    }
  )

  # Found live, the hard way: connecting the GitHub repo through the
  # Console (Step 6) rewrites build_spec (adds its own npm cache flags,
  # restructures the monorepo YAML) and attaches an IAM service role we
  # never set here -- Terraform then saw that as drift from this file and
  # planned a REPLACE to force it back, which destroyed the whole app
  # (losing the just-configured GitHub connection/branch/service role,
  # since none of those are Terraform resources) rather than just
  # updating in place. Once a human has connected the branch via the
  # Console, the Console is the right place to manage these two fields,
  # not this seed config -- ignore future drift on them so this can't
  # happen again.
  lifecycle {
    ignore_changes = [build_spec, iam_service_role_arn]
  }
}

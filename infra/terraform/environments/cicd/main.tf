# GitHub Actions OIDC federation -- no long-lived AWS access keys stored
# as GitHub secrets. GitHub's workflow-scoped OIDC token gets exchanged
# for short-lived AWS credentials via these roles' trust policies, scoped
# to this exact repository (`repo:${var.github_repo}:*` in the `sub`
# condition below -- a workflow running anywhere else cannot assume them).
#
# Two roles, least-privilege, matching the two workflows that use them:
#   - github_actions_ecr_push: build-and-push.yml. ECR only.
#   - github_actions_ecs_deploy: deploy.yml. ECS task-def/service update
#     + iam:PassRole on exactly the two ecs-demo execution/task roles --
#     nothing else. Broader than ecr_push, but still nowhere near the
#     AdministratorAccess the human researchmind-terraform-deploy user
#     has; CI should never have Terraform-apply-level access.

data "tls_certificate" "github_actions" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github_actions" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github_actions.certificates[0].sha1_fingerprint]
}

data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:*"]
    }
  }
}

# --- ECR push --------------------------------------------------------

resource "aws_iam_role" "github_actions_ecr_push" {
  name               = "researchmind-github-actions-ecr-push"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json
}

data "aws_iam_policy_document" "ecr_push" {
  statement {
    sid       = "ECRAuth"
    actions   = ["ecr:GetAuthorizationToken"] # ECR requires this action to be unscoped ("*")
    resources = ["*"]
  }

  statement {
    sid = "ECRPush"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
    ]
    resources = ["arn:aws:ecr:${var.aws_region}:${data.aws_caller_identity.current.account_id}:repository/${var.ecr_backend_repo_name}"]
  }
}

resource "aws_iam_role_policy" "ecr_push" {
  name   = "ecr-push"
  role   = aws_iam_role.github_actions_ecr_push.id
  policy = data.aws_iam_policy_document.ecr_push.json
}

# --- ECS deploy --------------------------------------------------------

resource "aws_iam_role" "github_actions_ecs_deploy" {
  name               = "researchmind-github-actions-ecs-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json
}

data "aws_iam_policy_document" "ecs_deploy" {
  statement {
    sid = "TaskDefinitions"
    # ecs:*TaskDefinition actions don't support resource-level scoping at
    # all (confirmed against AWS's own IAM action reference) -- "*" here
    # isn't a shortcut, it's the only option AWS provides.
    actions = [
      "ecs:DescribeTaskDefinition",
      "ecs:RegisterTaskDefinition",
    ]
    resources = ["*"]
  }

  statement {
    sid = "ServiceUpdate"
    actions = [
      "ecs:UpdateService",
      "ecs:DescribeServices",
    ]
    resources = ["arn:aws:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:service/${var.ecs_cluster_name}/*"]
  }

  statement {
    sid       = "PassExecutionAndTaskRoles"
    actions   = ["iam:PassRole"]
    resources = [for name in var.ecs_task_role_names : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${name}"]
  }
}

resource "aws_iam_role_policy" "ecs_deploy" {
  name   = "ecs-deploy"
  role   = aws_iam_role.github_actions_ecs_deploy.id
  policy = data.aws_iam_policy_document.ecs_deploy.json
}

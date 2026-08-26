# ECS task execution role (pulls images, writes logs, injects secrets) and
# task role (the application's own runtime permissions: S3 + SQS, matching
# the only two boto3-backed AWS integrations found in Phase 0 validation --
# docs/deployment/07-phase0-validation-findings.md section 3). Neither
# creates the S3 bucket, SQS queue, or Secrets Manager secrets themselves;
# those already exist or are managed elsewhere per AWS_Deployment.md
# sections 11-13, 18.

data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# --- Task execution role ---------------------------------------------------
# What ECS itself uses to pull the image from ECR, write to CloudWatch Logs,
# and resolve `secrets:` entries in the task definition at container start.

resource "aws_iam_role" "execution" {
  name               = "${var.name_prefix}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "execution_secrets" {
  statement {
    sid       = "ReadTaskSecrets"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = var.secrets_manager_secret_arns
  }
}

resource "aws_iam_role_policy" "execution_secrets" {
  name   = "${var.name_prefix}-ecs-execution-secrets"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution_secrets.json
}

# --- Task role ---------------------------------------------------------
# What the application code itself assumes at runtime (boto3 inside the
# API/workers). Scoped to exactly the two AWS services the app's own code
# calls directly: S3 (documents) and SQS (processing queue). Cognito
# validation is JWT-based and needs no IAM permissions; Qdrant is external
# (Qdrant Cloud, API-key auth, not IAM).

resource "aws_iam_role" "task" {
  name               = "${var.name_prefix}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json

  tags = var.tags
}

data "aws_iam_policy_document" "task_permissions" {
  statement {
    sid = "DocumentsBucketObjects"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${var.s3_bucket_arn}/*"]
  }

  statement {
    sid       = "DocumentsBucketList"
    actions   = ["s3:ListBucket"]
    resources = [var.s3_bucket_arn]
  }

  statement {
    sid = "ProcessingQueue"
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
    ]
    resources = var.sqs_queue_arns
  }
}

resource "aws_iam_role_policy" "task_permissions" {
  name   = "${var.name_prefix}-ecs-task-permissions"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task_permissions.json
}

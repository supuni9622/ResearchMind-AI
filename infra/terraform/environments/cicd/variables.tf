variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "github_repo" {
  description = "owner/repo -- scopes the OIDC trust policy so only workflows running in this exact repository can assume these roles."
  type        = string
  default     = "supuni9622/ResearchMind-AI"
}

variable "ecr_backend_repo_name" {
  type    = string
  default = "researchmind-backend"
}

variable "ecs_cluster_name" {
  type    = string
  default = "researchmind-ecs-demo-cluster"
}

variable "ecs_task_role_names" {
  description = "Roles the deploy workflow needs iam:PassRole on to register a task definition revision -- must match environments/ecs-demo's IAM module naming."
  type        = list(string)
  default = [
    "researchmind-ecs-demo-ecs-execution",
    "researchmind-ecs-demo-ecs-task",
  ]
}

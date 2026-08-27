output "ecr_push_role_arn" {
  description = "Set as the AWS_ECR_PUSH_ROLE_ARN repository variable (Settings -> Secrets and variables -> Actions -> Variables) for build-and-push.yml."
  value       = aws_iam_role.github_actions_ecr_push.arn
}

output "ecs_deploy_role_arn" {
  description = "Set as the AWS_ECS_DEPLOY_ROLE_ARN repository variable for deploy.yml."
  value       = aws_iam_role.github_actions_ecs_deploy.arn
}

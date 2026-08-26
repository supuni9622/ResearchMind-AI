output "vpc_id" {
  value = module.vpc.vpc_id
}

output "public_subnet_ids" {
  value = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.vpc.private_subnet_ids
}

output "alb_security_group_id" {
  value = module.vpc.alb_security_group_id
}

output "ecs_tasks_security_group_id" {
  value = module.vpc.ecs_tasks_security_group_id
}

output "rds_security_group_id" {
  value = module.vpc.rds_security_group_id
}

output "elasticache_security_group_id" {
  value = module.vpc.elasticache_security_group_id
}

output "ecs_execution_role_arn" {
  value = module.iam.execution_role_arn
}

output "ecs_task_role_arn" {
  value = module.iam.task_role_arn
}

output "ecr_repository_urls" {
  value = module.ecr.repository_urls
}

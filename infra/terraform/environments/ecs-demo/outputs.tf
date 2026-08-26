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

output "rds_endpoint" {
  value = module.rds.endpoint
}

output "rds_database_url_secret_arn" {
  value = module.rds.database_url_secret_arn
}

output "elasticache_endpoint" {
  value = "${module.elasticache.endpoint}:${module.elasticache.port}"
}

output "secrets_manager_arns" {
  value = module.secrets.secret_arns
}

output "api_url" {
  description = "HTTP only -- see modules/alb/main.tf for why. Test with curl/Postman; not yet safe for the (HTTPS) Amplify frontend to call."
  value       = "http://${module.alb.dns_name}"
}

output "api_service_name" {
  value = module.api_service.service_name
}

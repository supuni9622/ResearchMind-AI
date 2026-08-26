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
  description = "Direct ALB, HTTP only -- see modules/alb/main.tf for why. Fine for curl/Postman; not safe for the (HTTPS) Amplify frontend to call."
  value       = "http://${module.alb.dns_name}"
}

output "api_https_url" {
  description = "Via CloudFront (Phase 7) -- this is the URL to use for environments/frontend's api_url variable / NEXT_PUBLIC_API_URL."
  value       = "https://${module.cloudfront.domain_name}"
}

output "api_service_name" {
  value = module.api_service.service_name
}

output "worker_service_names" {
  value = {
    processing       = module.worker_processing.service_name
    research_runtime = module.worker_research_runtime.service_name
    eval_scoring     = module.worker_eval_scoring.service_name
    memory_lifecycle = module.worker_memory_lifecycle.service_name
  }
}

output "mcp_service_name" {
  value = var.enable_mcp ? module.mcp_service[0].service_name : null
}

output "mcp_server_url" {
  description = "Internal-only Cloud Map DNS URL -- not reachable from outside the VPC, this is just what MCP_PAPERS_SERVER_URL resolves to for the API/Research Runtime worker."
  value       = local.mcp_server_url
}

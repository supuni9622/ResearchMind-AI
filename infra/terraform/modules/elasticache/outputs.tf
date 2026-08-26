output "endpoint" {
  value = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "port" {
  value = aws_elasticache_replication_group.this.port
}

output "cluster_id" {
  description = "For CloudWatch AWS/ElastiCache CacheClusterId dimension (modules/cloudwatch-alarms) -- ElastiCache publishes metrics per node, not per replication group, so this must be the individual member cluster's ID (e.g. \"...-valkey-001\"), not replication_group_id."
  value       = tolist(aws_elasticache_replication_group.this.member_clusters)[0] # member_clusters is a set, not a list -- can't index directly
}

output "endpoint" {
  value = aws_elasticache_cluster.this.cache_nodes[0].address
}

output "port" {
  value = aws_elasticache_cluster.this.port
}

output "cluster_id" {
  description = "For CloudWatch AWS/ElastiCache CacheClusterId dimension (modules/cloudwatch-alarms)."
  value       = aws_elasticache_cluster.this.cluster_id
}

# ElastiCache Valkey, replacing the Compose `valkey` service AND covering
# the L2 semantic cache -- AWS_Deployment.md section 10 and the Phase 0
# validation (docs/deployment/07-phase0-validation-findings.md section 10)
# confirmed ElastiCache Valkey 9.0+ supports the TEXT+NUMERIC+VECTOR index
# schema langchain_redis.RedisSemanticCache needs, so no separate
# redis-stack service is provisioned in AWS. Local Docker Compose keeps
# using redis-stack-server regardless (no OSS Valkey image ships the
# search module).
#
# Second real ongoing-cost resource in this project (~$9-12/mo for
# cache.t4g.micro) -- ephemeral, same apply/destroy lifecycle as RDS.

resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.name_prefix}-valkey"
  subnet_ids = var.private_subnet_ids

  tags = var.tags
}

# cache.t4g.micro needs its memory reserve raised to use search at all
# (AWS's own search-features-limits doc: >=50% for micro, >=30% for
# small) -- the default (25%) is too low. This does reduce usable cache
# memory on the cheapest node size; revisit node size if that becomes a
# real constraint once exercised.
resource "aws_elasticache_parameter_group" "this" {
  name   = "${var.name_prefix}-valkey9"
  family = "valkey9"

  parameter {
    name  = "reserved-memory-percent"
    value = "50"
  }

  tags = var.tags
}

# aws_elasticache_cluster (the classic CreateCacheCluster API) does NOT
# support the Valkey engine at all -- discovered via a real failed apply,
# not documentation: "InvalidParameterValue: This API doesn't support
# Valkey engine. Please use CreateReplicationGroup API for Valkey cluster
# creation." aws_elasticache_replication_group is the Terraform resource
# for that API. num_cache_clusters=1 + automatic_failover_enabled=false
# is the single-node, no-replica equivalent of what aws_elasticache_cluster
# would have given us -- not a functional change, just the correct
# resource for this engine.
resource "aws_elasticache_replication_group" "this" {
  replication_group_id = "${var.name_prefix}-valkey"
  description          = "${var.name_prefix} Valkey -- L1 cache, session/memory, semantic cache"

  engine         = "valkey"
  engine_version = var.engine_version
  node_type      = var.node_type

  num_cache_clusters         = 1
  automatic_failover_enabled = false # requires >=2 nodes; single-node here by design, see modules/rds's cost reasoning
  multi_az_enabled           = false

  port = 6379

  parameter_group_name = aws_elasticache_parameter_group.this.name
  subnet_group_name    = aws_elasticache_subnet_group.this.name
  security_group_ids   = [var.security_group_id]

  apply_immediately = true

  tags = var.tags
}

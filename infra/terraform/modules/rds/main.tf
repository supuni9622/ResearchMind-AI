# RDS PostgreSQL, replacing the Compose `postgres` service
# (AWS_Deployment.md section 9). This is the first real ongoing-cost
# resource in this project -- ~$12-15/mo for db.t4g.micro alone, before
# storage. It is meant to be created and destroyed with the rest of the
# ecs-demo environment, not left running.
#
# skip_final_snapshot=true and backup_retention_period=0 are deliberate,
# not oversights: a lingering final snapshot after `terraform destroy`
# would keep costing money and defeats the point of the ephemeral
# apply-destroy model. Data in this environment is disposable by design --
# do not point production data at this instance.

resource "aws_db_subnet_group" "this" {
  name       = "${var.name_prefix}-rds"
  subnet_ids = var.private_subnet_ids

  tags = var.tags
}

# AWS's own manage_master_user_password would keep Terraform out of the
# password entirely, but it stores separate username/password JSON fields
# -- the app expects one composed DATABASE_URL connection string
# (postgresql+psycopg://user:pass@host:port/db), which can't be built from
# a single ECS `secrets` JSON-key reference without an app code change.
# Simpler and just as standard: Terraform generates the password and owns
# a single composed-URL secret for the whole lifecycle, so there's no
# stale-secret risk from AWS rotating the password out from under a
# separately-derived value. The password does sit in Terraform state as a
# result (true of any Terraform-managed credential) -- protected by the
# same encrypted/versioned/non-public state bucket set up in bootstrap.
resource "random_password" "master" {
  length  = 32
  special = false # RDS also rejects '/','@','"',' ' in the password; simplest to skip special chars entirely
}

resource "aws_db_instance" "this" {
  identifier = "${var.name_prefix}-postgres"

  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage = var.allocated_storage_gb
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.database_name
  username = var.master_username
  password = random_password.master.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.security_group_id]
  publicly_accessible    = false
  multi_az               = false # cost: single-AZ for a low-traffic demo, not a production HA requirement

  backup_retention_period = 0
  skip_final_snapshot     = true
  deletion_protection     = false
  apply_immediately       = true

  tags = var.tags
}

resource "aws_secretsmanager_secret" "database_url" {
  name = "${var.secrets_path_prefix}/database-url"

  # See the same setting in modules/secrets/main.tf: immediate deletion,
  # not AWS's default 30-day recovery window, so `terraform destroy` then
  # `apply` doesn't fail trying to recreate this while an old one is
  # still pending deletion. Right tradeoff for an apply/destroy/reapply
  # environment; would not be for a real production secret.
  recovery_window_in_days = 0

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql+psycopg://${var.master_username}:${random_password.master.result}@${aws_db_instance.this.address}:${aws_db_instance.this.port}/${var.database_name}"
}

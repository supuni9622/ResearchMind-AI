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

  # RDS creates and rotates the master password in Secrets Manager itself --
  # Terraform never sees or stores the plaintext value.
  manage_master_user_password = true

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

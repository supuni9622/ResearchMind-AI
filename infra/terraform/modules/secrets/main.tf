# Empty Secrets Manager containers for provider API keys and other
# third-party secrets (AWS_Deployment.md section 18). Terraform creates
# only the container -- never a secret_version -- so no actual API key
# value is ever written to (or readable from) Terraform state. Populate
# real values after apply:
#
#   aws secretsmanager put-secret-value \
#     --secret-id researchmind/ecs-demo/groq-api-key \
#     --secret-string "..."
#
# The RDS master password is handled separately -- modules/rds owns a
# single composed DATABASE_URL secret for the whole lifecycle instead
# (see its main.tf for why).
#
# recovery_window_in_days=0 skips Secrets Manager's default 30-day
# soft-delete window. That window exists to protect against accidental
# deletion, which matters for a real production secret -- but this
# environment's whole point is apply -> destroy -> reapply, and secrets
# stuck in a 30-day pending-deletion state would break `terraform apply`
# on the very next cycle (recreating a same-named secret fails while an
# old one is still pending deletion). Immediate deletion is the right
# tradeoff here specifically.

resource "aws_secretsmanager_secret" "this" {
  for_each = toset(var.secret_names)

  name                    = "${var.path_prefix}/${each.value}"
  recovery_window_in_days = 0

  tags = merge(var.tags, { Name = "${var.path_prefix}/${each.value}" })
}

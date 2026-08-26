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
# The RDS master password is handled separately (aws_db_instance's
# manage_master_user_password) -- AWS creates and rotates that secret
# itself, Terraform never touches its value either.

resource "aws_secretsmanager_secret" "this" {
  for_each = toset(var.secret_names)

  name = "${var.path_prefix}/${each.value}"

  tags = merge(var.tags, { Name = "${var.path_prefix}/${each.value}" })
}

# ECR repositories (AWS_Deployment.md section 17).
#
# researchmind-web is deliberately NOT one of these -- Amplify Hosting
# builds the Next.js frontend directly from GitHub source, it never pulls a
# pre-built Docker image from ECR. See the correction in AWS_Deployment.md
# section 17 and docs/deployment/06-frontend-amplify-deployment.md.

resource "aws_ecr_repository" "this" {
  for_each = toset(var.repository_names)

  name                 = each.value
  image_tag_mutability = "IMMUTABLE" # a given tag (e.g. a git SHA) always points at the same image -- no silent overwrite

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(var.tags, { Name = each.value })
}

resource "aws_ecr_lifecycle_policy" "this" {
  for_each = aws_ecr_repository.this

  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the most recent ${var.max_image_count} tagged images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = var.max_image_count
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

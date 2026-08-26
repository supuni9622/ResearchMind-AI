# Separate state from ecs-demo, deliberately. Amplify is meant to outlive
# the backend's apply/destroy cycles (AWS_Deployment.md section 5 /
# docs/deployment/06-frontend-amplify-deployment.md's cost strategy: the
# frontend "remains available" while "ECS backend: apply -> test/demo ->
# destroy"). Keeping it in ecs-demo's state would mean `terraform destroy`
# there tears down the frontend too, which isn't the intent -- Amplify
# Hosting's own idle cost is negligible, there's no reason to destroy it
# on the same cadence as RDS/ElastiCache/ALB/ECS.

terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Same bootstrap bucket/table as ecs-demo (infra/terraform/bootstrap),
  # different state key.
  backend "s3" {
    bucket         = "researchmind-terraform-state-232727982313"
    key            = "frontend/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "researchmind-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "researchmind"
      Environment = "frontend"
      ManagedBy   = "terraform"
    }
  }
}

# Separate state, deliberately. This is CI/CD's AWS access (GitHub OIDC
# provider + two least-privilege IAM roles) -- persistent, independent of
# whether ecs-demo happens to be applied right now. CI should be able to
# push images to ECR (itself a persistent, low-cost resource) regardless.

terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket         = "researchmind-terraform-state-232727982313"
    key            = "cicd/terraform.tfstate"
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
      Environment = "cicd"
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

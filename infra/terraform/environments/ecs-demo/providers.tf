terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Created once via infra/terraform/bootstrap -- see ../../README.md.
  backend "s3" {
    bucket         = "researchmind-terraform-state-232727982313"
    key            = "ecs-demo/terraform.tfstate"
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
      Environment = "ecs-demo"
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

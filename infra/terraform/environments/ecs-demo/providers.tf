terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Bootstrap this backend once via infra/terraform/bootstrap (creates the
  # S3 bucket + DynamoDB lock table), then fill in `bucket`/`dynamodb_table`
  # below with that apply's outputs before running `terraform init` here.
  backend "s3" {
    bucket         = "REPLACE_WITH_bootstrap_state_bucket_name_output"
    key            = "ecs-demo/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "REPLACE_WITH_bootstrap_lock_table_name_output"
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

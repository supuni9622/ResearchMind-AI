# Terraform state backend bootstrap.
#
# This is the one piece of infrastructure that cannot itself live in remote
# state -- something has to create the S3 bucket and DynamoDB lock table
# before any other environment can point its backend at them. Apply this
# once, keep its own state local (it is not meant to change often), and
# never destroy it while the ecs-demo or eks-lab environments still have
# state stored in it.
#
# Usage:
#   cd infra/terraform/bootstrap
#   terraform init
#   terraform apply

terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "terraform_state" {
  # Bucket names are globally unique -- suffix with the account ID so this
  # is deterministic and never collides with another AWS account.
  bucket = "researchmind-terraform-state-${data.aws_caller_identity.current.account_id}"

  # Cost note: standard S3 storage for a handful of small state files is
  # fractions of a cent per month -- this bucket is one of the low-cost,
  # persistent resources this project accepts running 24/7 (AWS_Deployment.md
  # section 23), unlike the ECS/RDS/ElastiCache/NAT resources it will manage
  # state for.
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "terraform_lock" {
  name         = "researchmind-terraform-locks"
  billing_mode = "PAY_PER_REQUEST" # no fixed cost -- pay only for the rare lock read/write
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}

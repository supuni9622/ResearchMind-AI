# VPC foundation for a ResearchMind compute environment (ecs-demo or
# eks-lab). Two AZs, public subnets for the ALB *and* the ECS tasks
# themselves, private subnets for RDS/ElastiCache only.
#
# No NAT Gateway. Phase 0 validation (docs/deployment/07-phase0-validation-findings.md
# section 11) priced a NAT Gateway at ~$32.40/mo fixed + per-GB processing,
# established that VPC endpoints can't replace it anyway (external AI
# providers aren't AWS-native), and picked public-subnet ECS tasks with a
# locked-down security group instead -- RDS/ElastiCache still get genuine
# private subnets since neither needs internet egress. This is deliberate,
# not an oversight; do not add a NAT Gateway here without updating that
# decision record.

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-vpc"
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-igw"
  })
}

resource "aws_subnet" "public" {
  count = length(var.availability_zones)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-public-${var.availability_zones[count.index]}"
    Tier = "public"
  })
}

resource "aws_subnet" "private" {
  count = length(var.availability_zones)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-private-${var.availability_zones[count.index]}"
    Tier = "private"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-public-rt"
  })
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private route table has no internet route -- RDS/ElastiCache reach
# nothing outside the VPC, and nothing outside the VPC reaches them.
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-private-rt"
  })
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# --- Security groups -----------------------------------------------------
# Least-privilege, chained by reference (each SG only accepts traffic from
# the specific SG in front of it) rather than by CIDR, so later modules
# (alb, ecs, rds, elasticache) just attach to these instead of re-deriving
# the access rules.

resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb"
  description = "Application Load Balancer -- public HTTP/HTTPS ingress only"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "HTTP from the internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS from the internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "To ECS tasks"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-alb" })
}

resource "aws_security_group" "ecs_tasks" {
  name        = "${var.name_prefix}-ecs-tasks"
  description = "API + worker ECS tasks -- inbound only from the ALB on the API port; egress open for ECR pulls and external AI/tool providers"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "API port from the ALB only"
    from_port       = var.api_container_port
    to_port         = var.api_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "ECR image pulls, RDS/ElastiCache/Qdrant Cloud, external AI/tool providers"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-ecs-tasks" })
}

resource "aws_security_group" "rds" {
  name        = "${var.name_prefix}-rds"
  description = "RDS PostgreSQL -- inbound only from ECS tasks, no internet egress"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "PostgreSQL from ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-rds" })
}

resource "aws_security_group" "elasticache" {
  name        = "${var.name_prefix}-elasticache"
  description = "ElastiCache Valkey -- inbound only from ECS tasks, no internet egress"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "Valkey from ECS tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-elasticache" })
}

# Generic ECS/Fargate task definition + service, reused for the API
# (Phase 4), the four workers (Phase 5), and MCP (Phase 6) -- one backend
# image, role selected via `command`, matching docker-compose.yml and
# AWS_Deployment.md section 17.
#
# No ECS container-level health check is configured here. The API's
# liveness is checked by the ALB target group instead (modules/alb); the
# workers have no HTTP surface to check at all (see docs/deployment/
# 07-phase0-validation-findings.md section 5) and rely on ECS's default
# process-exit-code task replacement instead of an invented HTTP endpoint,
# per AWS_Deployment.md section 16.

resource "aws_cloudwatch_log_group" "this" {
  name              = "/ecs/${var.name_prefix}-${var.service_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_ecs_task_definition" "this" {
  family                   = "${var.name_prefix}-${var.service_name}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = var.service_name
      image     = var.image
      essential = true
      command   = var.command

      portMappings = var.container_port == null ? [] : [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        for name, value in var.environment : { name = name, value = value }
      ]

      secrets = [
        for name, arn in var.secrets : { name = name, valueFrom = arn }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.this.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = var.service_name
        }
      }
    }
  ])

  tags = var.tags
}

resource "aws_ecs_service" "this" {
  name            = "${var.name_prefix}-${var.service_name}"
  cluster         = var.cluster_id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = true # public subnets, no NAT -- see the Phase 0 decision this module's variables.tf references
  }

  dynamic "load_balancer" {
    for_each = var.target_group_arn == null ? [] : [var.target_group_arn]
    content {
      target_group_arn = load_balancer.value
      container_name   = var.service_name
      container_port   = var.container_port
    }
  }

  dynamic "service_registries" {
    for_each = var.service_registry_arn == null ? [] : [var.service_registry_arn]
    content {
      registry_arn = service_registries.value
    }
  }

  tags = var.tags
}

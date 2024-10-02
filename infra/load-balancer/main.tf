variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "subnet_ids" {
  description = "IDs of the subnets where the ALB will be deployed"
  type        = list(string)
}

variable "apps" {
  description = "List of applications to deploy"
  type = list(object({
    name           = string
    container_port = number
    path_pattern   = string
  }))
}

resource "aws_security_group" "alb" {
  name        = "ecs-alb-sg"
  description = "Allow inbound traffic to ALB"
  vpc_id      = var.vpc_id

  ingress {
    protocol    = "tcp"
    from_port   = 80
    to_port     = 80
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "main" {
  name               = "ecs-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.subnet_ids

  enable_deletion_protection = false
}

resource "aws_lb_listener" "front_end" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Not Found"
      status_code  = "404"
    }
  }
}

resource "aws_lb_target_group" "apps" {
  count       = length(var.apps)
  name        = "${var.apps[count.index].name}-tg"
  port        = var.apps[count.index].container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/${var.apps[count.index].name}/docs"
    port                = var.apps[count.index].container_port
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 60
    interval            = 300
    matcher             = "200"
  }
}

resource "aws_lb_listener_rule" "app_rules" {
  count        = length(var.apps)
  listener_arn = aws_lb_listener.front_end.arn
  priority     = 100 + count.index

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.apps[count.index].arn
  }

  condition {
    path_pattern {
      values = [var.apps[count.index].path_pattern]
    }
  }
}

output "alb_dns_name" {
  value       = aws_lb.main.dns_name
  description = "The DNS name of the load balancer"
}

output "alb_security_group_id" {
  value = aws_security_group.alb.id
}

output "lb_listener" {
  value = aws_lb_listener.front_end
}

output "target_group_arns" {
  value = aws_lb_target_group.apps[*].arn
}

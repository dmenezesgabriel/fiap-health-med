provider "aws" {
  region = "us-east-1"
}

module "vpc" {
  source = "./vpc"
}

module "load_balancer" {
  source     = "./load-balancer"
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.public_subnet_ids
  apps       = var.apps
}

module "ecs_cluster" {
  source                = "./ecs-cluster"
  cluster_name          = "my-ecs-cluster"
  vpc_id                = module.vpc.vpc_id
  alb_security_group_id = module.load_balancer.alb_security_group_id
}

variable "apps" {
  description = "List of applications to deploy"
  type = list(object({
    name                  = string
    container_image       = string
    container_port        = number
    cpu                   = string
    memory                = string
    desired_count         = number
    path_pattern          = string
    environment_variables = map(string)
  }))
  default = [
    {
      name            = "auth-service"
      container_image = "dmenezesgabriel/fiap-health-auth_service:2ce4869cd457273d975fbf0541235aa08f5931b4"
      container_port  = 8000
      cpu             = "256"
      memory          = "512"
      desired_count   = 2
      path_pattern    = "/auth-service*"
      environment_variables = {
        AWS_DEFAULT_REGION = "us-east-1"
      }
    },
    {
      name            = "availability-service"
      container_image = "dmenezesgabriel/fiap-health-availability_service:2ce4869cd457273d975fbf0541235aa08f5931b4"
      container_port  = 8000
      cpu             = "256"
      memory          = "512"
      desired_count   = 2
      path_pattern    = "/availability-service*"
      environment_variables = {
        AWS_DEFAULT_REGION = "us-east-1"
      }
    },
    {
      name            = "appointment-service"
      container_image = "dmenezesgabriel/fiap-health-appointment_service:2ce4869cd457273d975fbf0541235aa08f5931b4"
      container_port  = 8000
      cpu             = "256"
      memory          = "512"
      desired_count   = 2
      path_pattern    = "/appointment-service*"
      environment_variables = {
        AWS_DEFAULT_REGION       = "us-east-1"
        AVAILABILITY_SERVICE_URL = "http://availability-service.my-ecs-cluster.local:8000"
        SENDER_EMAIL             = ""
        SENDER_PASSWORD          = ""
        SEND_EMAIL_ENABLED       = ""
      }
    }
  ]
}

module "ecs_services" {
  source = "./ecs-service"
  count  = length(var.apps)

  cluster_id                     = module.ecs_cluster.cluster_id
  vpc_id                         = module.vpc.vpc_id
  app_name                       = var.apps[count.index].name
  container_image                = var.apps[count.index].container_image
  container_port                 = var.apps[count.index].container_port
  cpu                            = var.apps[count.index].cpu
  memory                         = var.apps[count.index].memory
  desired_count                  = var.apps[count.index].desired_count
  subnet_ids                     = module.vpc.public_subnet_ids
  task_execution_role_arn        = module.ecs_cluster.task_execution_role_arn
  ecs_tasks_security_group_id    = module.ecs_cluster.ecs_tasks_security_group_id
  alb_security_group_id          = module.load_balancer.alb_security_group_id
  lb_listener                    = module.load_balancer.lb_listener
  target_group_arn               = module.load_balancer.target_group_arns[count.index]
  environment_variables          = var.apps[count.index].environment_variables
  enable_service_discovery       = true
  service_discovery_namespace_id = module.ecs_cluster.service_discovery_namespace_id
}

resource "aws_security_group_rule" "allow_inter_service_communication" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "tcp"
  source_security_group_id = module.ecs_cluster.ecs_tasks_security_group_id
  security_group_id        = module.ecs_cluster.ecs_tasks_security_group_id
  description              = "Allow communication between ECS tasks"
}

resource "aws_iam_role_policy" "auth_service_dynamodb_policy" {
  name = "auth_service-dynamodb-policy"
  role = module.ecs_services[0].task_role_id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = "*"
      }
    ]
  })
}


resource "aws_iam_role_policy" "availability_service_dynamodb_policy" {
  name = "availability_service-dynamodb-policy"
  role = module.ecs_services[1].task_role_id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = "*"
      }
    ]
  })
}
resource "aws_iam_role_policy" "appointment_service_dynamodb_policy" {
  name = "appointment_service-dynamodb-policy"
  role = module.ecs_services[2].task_role_id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = "*"
      }
    ]
  })
}


# Auth table
resource "aws_dynamodb_table" "auth" {
  name           = "auth"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "email"

  attribute {
    name = "email"
    type = "S"
  }

  attribute {
    name = "user_type"
    type = "S"
  }

  global_secondary_index {
    name            = "UserTypeIndex"
    hash_key        = "user_type"
    projection_type = "ALL"
    read_capacity   = 5
    write_capacity  = 5
  }
}

# Appointments table
resource "aws_dynamodb_table" "appointments" {
  name           = "appointments"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "doctor_email"
    type = "S"
  }

  attribute {
    name = "date_time"
    type = "S"
  }

  global_secondary_index {
    name            = "DoctorDateTimeIndex"
    hash_key        = "doctor_email"
    range_key       = "date_time"
    projection_type = "ALL"
    read_capacity   = 5
    write_capacity  = 5
  }
}

# Availability table
resource "aws_dynamodb_table" "availability" {
  name           = "availability"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "doctor_email"
  range_key      = "day_time_slot"

  attribute {
    name = "doctor_email"
    type = "S"
  }

  attribute {
    name = "day_time_slot"
    type = "S"
  }
}

output "alb_dns_name" {
  value = module.load_balancer.alb_dns_name
}

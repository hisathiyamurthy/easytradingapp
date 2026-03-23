terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
  
  backend "s3" {
    bucket = "easytradingapp-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "ap-south-1"
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_availability_zones" "available" {
  state = "available"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"
  
  name = "easytrading-vpc"
  cidr = var.vpc_cidr
  
  azs             = data.aws_availability_zones.available.names
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets
  
  enable_nat_gateway               = true
  single_nat_gateway               = false
  enable_dns_hostnames             = true
  enable_dns_support               = true
  
  tags = {
    Environment = "production"
    Project     = "EasyTradingApp"
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "19.0.0"
  
  cluster_name    = "easytrading-cluster"
  cluster_version = "1.28"
  
  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_public_access = true
  
  eks_managed_node_groups = {
    primary = {
      name = "primary-node-group"
      
      instance_types = ["t3.large"]
      
      capacity_type = "ON_DEMAND"
      
      min_size     = 3
      max_size     = 10
      desired_size = 3
      
      labels = {
        Environment = "production"
        NodeGroup   = "primary"
      }
      
      tags = {
        "k8s.io/cluster-autoscaler/enabled" = "true"
        "k8s.io/cluster-autoscaler/easytrading-cluster" = "owned"
      }
    }
  }
  
  tags = {
    Environment = "production"
    Project     = "EasyTradingApp"
  }
}

module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "6.0.0"
  
  identifier = "easytrading-postgres"
  
  engine               = "postgres"
  engine_version       = "15.4"
  family              = "postgres15"
  instance_class      = var.db_instance_class
  allocated_storage   = 50
  max_allocated_storage = 500
  
  db_name  = "easytradingapp"
  username = var.db_username
  password = var.db_password
  
  vpc_id                 = module.vpc.vpc_id
  subnet_ids            = module.vpc.private_subnets
  db_subnet_group_name  = "easytrading-db-subnet"
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  
  skip_final_snapshot       = false
  final_snapshot_identifier = "easytrading-final-snapshot"
  
  tags = {
    Environment = "production"
    Project     = "EasyTradingApp"
  }
}

module "elasticache" {
  source  = "terraform-aws-modules/elasticache/aws"
  version = "7.0.0"
  
  cluster_id           = "easytrading-redis"
  engine              = "redis"
  engine_version      = "7.0"
  node_type           = "cache.t3.micro"
  num_cache_nodes     = 2
  parameter_group_name = "default.redis7"
  
  port                 = 6379
  at_rest_encryption   = true
  transit_encryption   = true
  auth_token_enabled  = true
  auth_token          = var.redis_auth_token
  
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets
  security_groups = [aws_security_group.redis.id]
  
  tags = {
    Environment = "production"
    Project     = "EasyTradingApp"
  }
}

resource "aws_security_group" "redis" {
  name        = "easytrading-redis-sg"
  description = "Security group for Redis cluster"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
  
  tags = {
    Environment = "production"
    Project     = "EasyTradingApp"
  }
}

resource "aws_security_group" "rabbitmq" {
  name        = "easytrading-rabbitmq-sg"
  description = "Security group for RabbitMQ"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port   = 5672
    to_port     = 5672
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
  
  ingress {
    from_port   = 15672
    to_port     = 15672
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Environment = "production"
    Project     = "EasyTradingApp"
  }
}

module "alb" {
  source  = "terraform-aws-modules/alb/aws"
  version = "8.0.0"
  
  name = "easytrading-alb"
  
  load_balancer_type = "application"
  vpc_id             = module.vpc.vpc_id
  subnets            = module.vpc.public_subnets
  security_groups    = [aws_security_group.alb.id]
  
  enable_deletion_protection = true
  
  http_tcp_listeners = [
    {
      port               = 80
      protocol           = "HTTP"
      target_group_index = 0
    },
    {
      port               = 443
      protocol           = "HTTPS"
      target_group_index = 0
    }
  ]
  
  target_groups = [
    {
      name             = "backend-tg"
      backend_protocol = "HTTP"
      backend_port     = 8000
      health_path      = "/health"
      health_interval  = 30
    }
  ]
  
  tags = {
    Environment = "production"
    Project     = "EasyTradingApp"
  }
}

resource "aws_security_group" "alb" {
  name        = "easytrading-alb-sg"
  description = "Security group for ALB"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Environment = "production"
    Project     = "EasyTradingApp"
  }
}

resource "aws_route53_zone" "main" {
  name = var.domain_name
  
  tags = {
    Environment = "production"
    Project     = "EasyTradingApp"
  }
}

resource "aws_acm_certificate" "main" {
  provider          = aws.us_east_1
  domain_name       = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method = "DNS"
  
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate" "api_cert" {
  provider          = aws.us_east_1
  domain_name       = "api.${var.domain_name}"
  validation_method = "DNS"
  
  lifecycle {
    create_before_destroy = true
  }
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

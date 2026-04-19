variable "aws_region" {
  description = "AWS region to deploy into — eu-west-2 is London"
  type        = string
  default     = "eu-west-2"
}

variable "project_name" {
  description = "Used as a prefix on all resource names so you can identify them"
  type        = string
  default     = "sakura-stack"
}

variable "environment" {
  description = "dev, staging, or prod — helps distinguish resources"
  type        = string
  default     = "dev"
}

variable "db_password" {
  description = "Password for the RDS PostgreSQL instance"
  type        = string
  sensitive   = true # Terraform won't print this in logs
}

variable "db_username" {
  description = "Master username for RDS"
  type        = string
  default     = "sakura_admin"
}

variable "ec2_instance_type" {
  description = "EC2 instance type — t3.micro is free tier"
  type        = string
  default     = "t3.micro"
}

variable "db_instance_class" {
  description = "RDS instance class — db.t3.micro is free tier eligible"
  type        = string
  default     = "db.t3.micro"
}

variable "ec2_public_key" {
  description = "SSH public key content for EC2 access — paste contents of sakura-stack-key.pub"
  type        = string
  default     = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 placeholder-for-ci-validation"
}
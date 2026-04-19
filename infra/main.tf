# ─────────────────────────────────────────────────────────────
# TERRAFORM CONFIGURATION
# ─────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0" # Use AWS provider version 5.x
    }
  }
}

# Tell Terraform which AWS account and region to use
# picks up credentials from AWS CLI config automatically
provider "aws" {
  region = var.aws_region
}

# ─────────────────────────────────────────────────────────────
# DATA SOURCES
# These look up existing AWS info rather than creating new things
# ─────────────────────────────────────────────────────────────

# Get a list of availability zones in your region
# eu-west-2 has eu-west-2a, eu-west-2b, eu-west-2c
data "aws_availability_zones" "available" {
  state = "available"
}

# Get the latest Amazon Linux 2 AMI (operating system image for EC2)
# so that we always get the most recent patched version automatically
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# ─────────────────────────────────────────────────────────────
# S3 BUCKET — stores the raw JLPT PDFs
# ─────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "raw_pdfs" {
  # Bucket names must be globally unique across all AWS accounts
  # Using project name + a suffix makes collisions unlikely
  bucket = "${var.project_name}-raw-pdfs-${var.environment}"

  tags = {
    Name        = "${var.project_name}-raw-pdfs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Block all public access to PDFs (private study materials)
resource "aws_s3_bucket_public_access_block" "raw_pdfs" {
  bucket = aws_s3_bucket.raw_pdfs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning — if uploading a new version of a PDF, 
# the old version is preserved - useful for recovery later
resource "aws_s3_bucket_versioning" "raw_pdfs" {
  bucket = aws_s3_bucket.raw_pdfs.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ─────────────────────────────────────────────────────────────
# VPC — my private network
# Everything else lives inside this
# ─────────────────────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16" # 65,536 private IP addresses
  enable_dns_hostnames = true          # Required for RDS to work properly
  enable_dns_support   = true

  tags = {
    Name    = "${var.project_name}-vpc"
    Project = var.project_name
  }
}

# Internet Gateway — allows VPC to communicate with internet
# or else nothing inside the VPC can reach the outside world
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name    = "${var.project_name}-igw"
    Project = var.project_name
  }
}

# Public subnets — resources here get a public IP and can reach internet
# We create two across two availability zones (required by RDS)
resource "aws_subnet" "public" {
  count  = 2
  vpc_id = aws_vpc.main.id

  # 10.0.0.0/24 and 10.0.1.0/24 — 256 addresses each
  cidr_block = "10.0.${count.index}.0/24"

  # Spread across availability zones for resilience
  availability_zone = data.aws_availability_zones.available.names[count.index]

  # Instances launched here automatically get a public IP
  map_public_ip_on_launch = true

  tags = {
    Name    = "${var.project_name}-public-${count.index + 1}"
    Project = var.project_name
  }
}

# Private subnets — RDS lives here, no direct internet access
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name    = "${var.project_name}-private-${count.index + 1}"
    Project = var.project_name
  }
}

# Route table — tells traffic in the public subnets to go via internet gateway
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0" # All traffic
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name    = "${var.project_name}-public-rt"
    Project = var.project_name
  }
}

# Associate the route table with each public subnet
resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ─────────────────────────────────────────────────────────────
# SECURITY GROUPS — firewall rules
# ─────────────────────────────────────────────────────────────

# Security group for EC2 — controls what traffic can reach your instance
resource "aws_security_group" "ec2" {
  name        = "${var.project_name}-ec2-sg"
  description = "Security group for Sakura Stack EC2 instance"
  vpc_id      = aws_vpc.main.id

  # Allow SSH from anywhere — we need this to connect
  # In production, restrict this to our IP only
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  # Allow Airflow webserver UI (port 8080)
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Airflow UI"
  }

  # Allow Streamlit app (port 8501)
  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Streamlit app"
  }

  # Allow all outbound traffic — EC2 needs to reach internet for packages
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" # All protocols
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "${var.project_name}-ec2-sg"
    Project = var.project_name
  }
}

# Security group for RDS — only allow connections from EC2
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "Security group for Sakura Stack RDS"
  vpc_id      = aws_vpc.main.id

  # Only allow PostgreSQL port (5432) from EC2 security group
  # The database is not directly reachable from the internet
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
    description     = "PostgreSQL from EC2"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "${var.project_name}-rds-sg"
    Project = var.project_name
  }
}

# ─────────────────────────────────────────────────────────────
# EC2 INSTANCE — my virtual machine
# ─────────────────────────────────────────────────────────────

# Key pair — allows you to SSH into the EC2 instance securely
# We generate the key locally; Terraform uploads the public half to AWS
resource "aws_key_pair" "sakura" {
  key_name   = "${var.project_name}-key"
  public_key = var.ec2_public_key
}

resource "aws_instance" "main" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro" #var.ec2_instance_type (t2.miro = free tier)
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  key_name               = aws_key_pair.sakura.key_name

  # Root disk — 20GB should be plenty for this project
  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  # User data script — runs once when the instance first starts
  # Installs Docker in order to run Airflow on the EC2 instance later
  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y docker git
    systemctl start docker
    systemctl enable docker
    usermod -a -G docker ec2-user
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
  EOF

  tags = {
    Name        = "${var.project_name}-ec2"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ─────────────────────────────────────────────────────────────
# RDS POSTGRESQL — managed database
# ─────────────────────────────────────────────────────────────

# Subnet group — tells RDS which subnets it can use
# RDS requires at least two subnets in different availability zones
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name    = "${var.project_name}-db-subnet-group"
    Project = var.project_name
  }
}

resource "aws_db_instance" "postgres" {
  identifier        = "${var.project_name}-postgres"
  engine            = "postgres"
  engine_version    = "15"                  # 15.4 is giving error
  instance_class    = var.db_instance_class # db.t3.micro = free tier
  allocated_storage = 20                    # GB — free tier includes 20GB

  db_name  = "sakura_stack"
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # For portfolio projects, skip multi-AZ (costs money) and backups
  multi_az            = false
  publicly_accessible = false # Only accessible from inside VPC
  skip_final_snapshot = true  # Don't create a snapshot when destroyed
  deletion_protection = false # Allow terraform destroy to delete it

  # Free tier eligible
  storage_type      = "gp2"
  storage_encrypted = false # Encryption costs extra on free tier

  tags = {
    Name        = "${var.project_name}-postgres"
    Environment = var.environment
    Project     = var.project_name
  }
}
output "s3_bucket_name" {
  description = "Name of the S3 bucket for raw PDFs"
  value       = aws_s3_bucket.raw_pdfs.id
}

output "ec2_public_ip" {
  description = "Public IP address of the EC2 instance — use this to SSH in"
  value       = aws_instance.main.public_ip
}

output "ec2_public_dns" {
  description = "Public DNS hostname of EC2"
  value       = aws_instance.main.public_dns
}

output "rds_endpoint" {
  description = "RDS connection endpoint — paste into your .env as DB_HOST"
  value       = aws_db_instance.postgres.endpoint
}

output "rds_port" {
  description = "RDS port number"
  value       = aws_db_instance.postgres.port
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}
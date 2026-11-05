resource "aws_iam_role" "app_ec2" {
  name               = "${var.project_name}-${var.environment}-app-role"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags               = var.tags
}
resource "aws_iam_role_policy" "app_s3_sqs_events" {
  name = "resume-processing-minimum-access"
  role = aws_iam_role.app_ec2.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = "${aws_s3_bucket.resumes.arn}/resumes/*" },
    { Effect = "Allow", Action = ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"], Resource = aws_sqs_queue.resume_processing.arn },
    { Effect = "Allow", Action = ["events:PutEvents"], Resource = "*" }
  ] })
}
resource "aws_iam_instance_profile" "app" {
  name = "${var.project_name}-${var.environment}-app-profile"
  role = aws_iam_role.app_ec2.name
}
resource "aws_vpc" "app" {
  cidr_block           = "10.72.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(var.tags, { Name = "${var.project_name}-${var.environment}-vpc" })
}
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.app.id
  cidr_block              = "10.72.1.0/24"
  map_public_ip_on_launch = true
  tags                    = merge(var.tags, { Name = "${var.project_name}-${var.environment}-public-subnet" })
}
resource "aws_internet_gateway" "app" {
  vpc_id = aws_vpc.app.id
  tags   = var.tags
}
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.app.id
  tags   = var.tags
}
resource "aws_route" "internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.app.id
}
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
resource "aws_security_group" "app" {
  name        = "${var.project_name}-${var.environment}-app-sg"
  description = "No public application port by default; SSH is tightly scoped only for optional EC2 demo"
  vpc_id      = aws_vpc.app.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = var.tags
}
resource "aws_security_group_rule" "ssh_demo" {
  count             = var.create_ec2_demo ? 1 : 0
  type              = "ingress"
  security_group_id = aws_security_group.app.id
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = [var.allowed_ssh_cidr]
  description       = "SSH only from the explicitly configured admin IP"
}
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}
resource "aws_instance" "demo" {
  count                       = var.create_ec2_demo ? 1 : 0
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.ec2_instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.app.id]
  iam_instance_profile        = aws_iam_instance_profile.app.name
  key_name                    = var.ec2_key_name
  associate_public_ip_address = true
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }
  root_block_device {
    encrypted   = true
    volume_type = "gp3"
    volume_size = 8
  }
  user_data = <<-USERDATA
    #!/bin/bash
    set -euo pipefail
    dnf update -y
    dnf install -y docker
    systemctl enable --now docker
    usermod -aG docker ec2-user
    echo "TalentMatch EC2 demo provisioned. Deploy the application separately after reviewing security and costs." > /etc/motd
  USERDATA
  tags      = merge(var.tags, { Name = "${var.project_name}-${var.environment}-demo" })
  lifecycle { ignore_changes = [ami] }
}

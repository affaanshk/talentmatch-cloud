resource "aws_iam_role" "demo_ec2" {
  name = "talentmatch-ec2-demo-local-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "demo_ec2_s3" {
  name = "talentmatch-ec2-resume-read-local"
  role = aws_iam_role.demo_ec2.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:ListBucket"]
      Resource = [aws_s3_bucket.resumes.arn, "${aws_s3_bucket.resumes.arn}/*"]
    }]
  })
}

resource "aws_iam_instance_profile" "demo_ec2" {
  name = "talentmatch-ec2-demo-local-profile"
  role = aws_iam_role.demo_ec2.name
}

resource "aws_vpc" "demo" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "talentmatch-local-vpc" }
}

resource "aws_subnet" "demo" {
  vpc_id                  = aws_vpc.demo.id
  cidr_block              = "10.42.1.0/24"
  map_public_ip_on_launch = false
  tags                    = { Name = "talentmatch-local-subnet" }
}

resource "aws_security_group" "demo" {
  name        = "talentmatch-local-demo-sg"
  description = "Local demo: allow SSH only from the configured local network when supported."
  vpc_id      = aws_vpc.demo.id

  ingress {
    description = "SSH demo rule; do not expose publicly in a real deployment."
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["127.0.0.1/32"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "talentmatch-local-demo-sg" }
}

resource "aws_instance" "demo" {
  count                  = var.ec2_ami_id == "" ? 0 : 1
  ami                    = var.ec2_ami_id
  instance_type          = var.ec2_instance_type
  subnet_id              = aws_subnet.demo.id
  vpc_security_group_ids = [aws_security_group.demo.id]
  iam_instance_profile   = aws_iam_instance_profile.demo_ec2.name
  tags = {
    Name    = "talentmatch-local-ec2-demo"
    Project = "TalentMatch"
  }
}

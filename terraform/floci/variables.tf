variable "aws_region" {
  description = "Local emulator region; no real AWS account is used."
  type        = string
  default     = "us-east-1"
}

variable "floci_endpoint" {
  description = "Floci endpoint reachable from the host running Terraform."
  type        = string
  default     = "http://localhost:4566"
}

variable "ec2_ami_id" {
  description = "Optional AMI identifier known to the local Floci EC2 emulator. Leave empty to skip creating an instance."
  type        = string
  default     = ""
}

variable "ec2_instance_type" {
  type    = string
  default = "t3.micro"
}

variable "aws_region" {
  type        = string
  description = "AWS deployment region"
  default     = "us-east-1"
}
variable "project_name" {
  type    = string
  default = "talentmatch"
}
variable "environment" {
  type    = string
  default = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}
variable "resume_bucket_name" {
  type        = string
  description = "Globally unique bucket name; choose a name you own."
}
variable "create_ec2_demo" {
  type        = bool
  description = "Create a billable EC2 demo instance. Keep false until reviewed."
  default     = false
}
variable "ec2_instance_type" {
  type    = string
  default = "t3.micro"
}
variable "allowed_ssh_cidr" {
  type        = string
  description = "Your public IP in CIDR form, e.g. 203.0.113.10/32. Used only when EC2 demo is enabled."
  default     = "127.0.0.1/32"
}
variable "ec2_key_name" {
  type        = string
  description = "Existing EC2 key pair name; required when create_ec2_demo=true."
  default     = null
  nullable    = true
}
variable "tags" {
  type    = map(string)
  default = { Project = "TalentMatch", ManagedBy = "Terraform" }
}

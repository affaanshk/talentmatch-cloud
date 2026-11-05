
variable "aws_region" {
  description = "AWS region for TalentMatch Cloud"
  type        = string
  default     = "us-east-1"
}

variable "floci_endpoint" {
  description = "Local Floci endpoint; not used for real AWS deployment"
  type        = string
  default     = "http://localhost:4566"
}

variable "project_name" {
  description = "Project name used to label infrastructure"
  type        = string
  default     = "talentmatch"
}

variable "resume_bucket_name" {
  description = "Existing S3 bucket used to store uploaded TalentMatch resumes"
  type        = string
  default     = "talentmatch-resumes-local"
}


variable "environment" {
  description = "Deployment environment used in resource names"
  type        = string
  default     = "local"

  validation {
    condition     = contains(["local", "dev", "staging", "prod"], var.environment)
    error_message = "Environment must be local, dev, staging, or prod."
  }
}

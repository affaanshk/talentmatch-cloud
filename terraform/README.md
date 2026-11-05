# Terraform Infrastructure

This directory contains three separate Terraform configurations.

## 1. Root Configuration

The root configuration contains an earlier local infrastructure setup for S3 and SQS. It uses Floci at localhost:4566 and is retained for reference.

## 2. AWS Configuration

The `aws/` directory contains the configuration intended for deployment to real AWS services.

Before deployment:
- Configure `terraform.tfvars` using `terraform.tfvars.example`.
- Use valid AWS credentials.
- Review resource costs and the Terraform execution plan.
- Keep optional EC2 resources disabled unless required.

## 3. Floci Configuration

The `floci/` directory provisions local cloud resources using Floci.

It is intended for local development and testing without deploying the infrastructure to real AWS.

## Important

Each directory is an independent Terraform root. Run Terraform commands from the relevant directory.

Do not commit Terraform state files, plans, real credentials, or local variable files.

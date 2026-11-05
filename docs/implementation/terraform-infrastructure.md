# Terraform infrastructure

Terraform is used to define cloud infrastructure as code. It does not replace the application code, AI pipeline, or Docker Compose orchestration.

## Terraform roots

- `terraform/floci/`: local Floci resource definitions used by the emulator-based development workflow.
- `terraform/aws/`: separate configuration for a real AWS account.
- `terraform/`: retained earlier/root configuration.

## What Terraform provisions

The AWS root defines infrastructure resources including:
- S3 bucket and configuration
- SQS queue and dead-letter queue/redrive
- Lambda function and EventBridge rule/permission
- DynamoDB audit table
- CloudWatch log group
- IAM roles and policies
- VPC, subnet, internet gateway, route table, and security group
- Optional EC2 resource, disabled by default

## What Terraform does not do in this project

The current AWS root does not deploy the FastAPI and worker containers, configure a production PostgreSQL service, or run database migrations automatically. Those application deployment and data migration steps require additional implementation.

## Safe workflow for a real AWS account

1. Confirm the intended AWS account and region.
2. Review variables and credentials; never commit real secrets or `terraform.tfvars`.
3. Initialize the correct root.
4. Run `terraform validate`.
5. Generate and inspect `terraform plan`.
6. Review IAM permissions, public network exposure, resource naming, and estimated costs.
7. Apply only after explicit approval from the account owner.
8. Record outputs and verify resources in AWS.

The recorded project validation succeeded for both the Floci and AWS configurations. The AWS configuration was not applied to a real account.

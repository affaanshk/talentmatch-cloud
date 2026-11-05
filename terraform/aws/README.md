# TalentMatch real-AWS Terraform stack

This is deliberately isolated from `../` (the existing Floci/local stack). It covers the nine target service areas: S3, SQS/DLQ, EC2 (opt-in), Lambda, EventBridge, CloudWatch Logs, IAM, VPC/security groups, and DynamoDB.

## Safety and costs
- First run only `terraform init`, `terraform fmt -check`, `terraform validate`, and `terraform plan`.
- **Do not apply until you review the plan and AWS billing/account access.** This stack creates AWS resources; S3, EC2, logs, and other services can incur charges.
- EC2 is disabled by default (`create_ec2_demo = false`). If enabling it, use your own public IP `/32` for SSH and an existing key pair. Do not open SSH to `0.0.0.0/0`.
- No NAT gateway is created. The public subnet has an internet route. The EC2 demo is not a production deployment of the API/worker.
- `resume_bucket_name` must be globally unique and must not name a bucket containing data you cannot risk changing. Review the plan carefully.
- Local Floci config and its state remain under `../`; this stack has separate state in this folder.

## Run
1. Copy `terraform.tfvars.example` to `terraform.tfvars` and set a globally unique bucket name.
2. Ensure AWS account access is active and configure credentials through AWS CLI/profile or environment variables. Never hardcode keys in Terraform.
3. From this directory: `terraform init`, `terraform fmt -recursive`, `terraform validate`, `terraform plan`.
4. Inspect the full plan. Apply only after explicit review and confirmation.

## Service mapping
- S3: private, versioned, SSE-S3 encrypted resume bucket.
- SQS: processing queue with three-receive redrive policy and encrypted DLQ.
- EC2: opt-in Amazon Linux 2023 demo instance; not launched by default.
- Lambda: validates/logs completion events and optionally writes event records to DynamoDB when `DYNAMODB_TABLE_NAME` is configured.
- EventBridge: routes `talentmatch.resume` / `Resume Processing Completed` events to Lambda.
- CloudWatch: Lambda log group with 14-day retention.
- IAM: EC2 role scoped to the resume bucket prefix and processing queue; Lambda logging role.
- VPC/security group: VPC, public subnet, internet gateway, route table; no inbound ports unless the EC2 SSH option is enabled.
- DynamoDB: on-demand resume event table with encryption and point-in-time recovery.

Note: this Terraform stack provisions the AWS resources but does not automatically migrate PostgreSQL data, deploy the FastAPI/worker containers, or configure the existing app to use the new AWS resource names. Those runtime values must be wired into the deployment environment after the AWS plan is reviewed.

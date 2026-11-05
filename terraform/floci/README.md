# TalentMatch local cloud stack (Floci)

This Terraform root targets a local Floci endpoint, not a real AWS account. It is intended for learning and local validation.

## Included service areas

1. S3 resume bucket with public access blocked and encryption configuration.
2. SQS processing queue with redrive policy and DLQ.
3. EC2 demo role/profile, network, security group, and optional instance.
4. Lambda completion-event handler.
5. EventBridge rule and Lambda target.
6. CloudWatch log group for the Lambda.
7. IAM roles and a narrowly scoped demo S3-read policy.
8. VPC, subnet, and security group.
9. DynamoDB audit/demo table.

Floci may emulate some APIs only partially. `terraform validate` proves syntax/schema validity, not that every resource can be provisioned by the running emulator. EC2 instance creation is disabled unless a Floci-supported AMI ID is provided.

## Commands (PowerShell)

From the project root:

```powershell
terraform -chdir="terraform/floci" init
terraform -chdir="terraform/floci" fmt -recursive
terraform -chdir="terraform/floci" validate
terraform -chdir="terraform/floci" plan
```

Only after reviewing the plan, provision resources into the local emulator:

```powershell
terraform -chdir="terraform/floci" apply
```

This configuration uses local fake credentials and `http://localhost:4566`. Do not change the endpoint to a public URL or use real credentials here. This local stack is separate from `terraform/aws`.

# AWS-compatible services

The local workflow uses Floci to exercise AWS-style service interactions without claiming that resources were deployed to a live AWS account.

| Service | Project role | Local evidence |
|---|---|---|
| S3 | Store uploaded resume PDFs | Synthetic PDF object was confirmed in the local bucket |
| SQS | Queue upload IDs for background processing | Worker consumed the queued upload |
| SQS DLQ | Hold messages after repeated receive failures | Queue and redrive configuration were present; no deliberate poison-message test is claimed here |
| EventBridge | Route resume-completed events | Completion rule and Lambda target were enabled |
| Lambda | Process completion/audit event | Lambda logs included the tested upload identifier |
| DynamoDB | Store audit records | Audit table existed and scan returned records |
| CloudWatch Logs | Capture Lambda audit logs | Log group contained the tested upload identifier and audit-saved message |
| IAM | Define role/policy/profile | Terraform resources were present in the local emulator |
| VPC / EC2 | Demonstrate network and compute resource definitions | Docker-backed Ubuntu environment and SSH were demonstrated with emulator limitations |

## Real AWS Terraform root

`terraform/aws/` contains a separate intended AWS configuration. It was validated, but no real AWS apply/deployment is claimed. Review the Terraform plan, IAM permissions, networking exposure, region, and costs before applying it.

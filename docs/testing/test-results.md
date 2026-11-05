# Test results and verification

This page records the evidence supplied by the project's local audit and integration-test reports. It distinguishes application/emulator verification from live AWS deployment.

## Automated tests

The recorded Docker-based test run completed with:

- **25 passed**
- **3 warnings**

The warnings were recorded as framework/deprecation warnings. This page does not claim that the tests constitute production load, security, or hiring-outcome validation.

## Local end-to-end upload test

The recorded fresh integration run used a synthetic PDF:

| Check | Recorded result |
|---|---|
| Upload API | HTTP `202 Accepted` |
| Initial state | `queued` |
| Intermediate state | `processing` |
| Final state | `completed` |
| Polling | Completed after 17 status checks (~170 seconds in the recorded run) |
| Overall match score | `50.16` |
| Recommendations | 5 |
| S3 object | Present; 629 bytes; `application/pdf` |
| SQS main queue after processing | No visible/in-flight/delayed messages |
| SQS DLQ after processing | No visible/in-flight/delayed messages |
| EventBridge | Local completion rule enabled and Lambda target configured |
| DynamoDB | Audit table scan returned 12 records |
| CloudWatch | Log entry for the same upload ID included `Resume audit record saved` |
| Worker | Logged completion and event publication |

The recorded upload identifier was `cbcab80a-11c5-488d-9402-7c96857148db`. It is included here only to correlate the evidence in the supplied audit transcript; future runs will use different IDs.

## Infrastructure validation

The supplied audit records successful Terraform validation for the Floci and AWS roots. Validation is not equivalent to provisioning resources in AWS.

## Scope and caveats

- These results describe a local Floci-based integration environment.
- The synthetic test PDF is not a real candidate's resume.
- An empty DLQ after a successful run does not prove that a deliberately failing message was successfully redriven.
- The AWS Terraform configuration was not applied to a live AWS account.
- The EC2 emulator's instance metadata/role credential behaviour was not fully functional.

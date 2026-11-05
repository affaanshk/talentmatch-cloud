# Local integration test walkthrough

This is a concise description of the recorded end-to-end test, not a request to rerun it.

## Expected lifecycle

```text
PDF selected
   |
   v
POST /upload-resume
   |
   +--> validate PDF
   +--> create PostgreSQL upload row
   +--> store object in S3-compatible bucket
   +--> enqueue upload ID in SQS
   |
   v
HTTP 202 Accepted
   |
   v
Worker claims upload
   |
   +--> downloads PDF
   +--> extracts text
   +--> runs hybrid recommendation engine
   +--> stores score + recommendations in PostgreSQL
   +--> publishes completion event
   |
   v
EventBridge -> Lambda -> DynamoDB audit + CloudWatch logs
   |
   v
Frontend retrieves completed report using upload ID
```

## Recorded successful run

The supplied integration report records a 629-byte synthetic PDF accepted with HTTP 202, then progressing through `queued`, `processing`, and `completed`. The final result contained five recommendations and an overall score of 50.16. The S3 object, worker completion log, EventBridge/Lambda path, DynamoDB audit table, and CloudWatch audit log were also checked.

See `docs/testing/test-results.md` for the tabulated evidence and caveats.

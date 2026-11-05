# Resume upload and processing sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as React frontend
    participant API as FastAPI
    participant DB as PostgreSQL
    participant S3 as S3-compatible storage
    participant Q as SQS queue
    participant Worker as Python worker
    participant AI as Matching engine
    participant EB as EventBridge
    participant Lambda
    participant Audit as DynamoDB

    User->>UI: Select PDF and submit
    UI->>API: POST /upload-resume
    API->>API: Validate type, size, signature, readable text
    API->>DB: Create queued upload record
    API->>S3: Store PDF object
    API->>Q: Enqueue upload ID
    API-->>UI: 202 Accepted + upload_id + status_url

    Worker->>Q: Long-poll for message
    Q-->>Worker: Message with upload_id
    Worker->>DB: Atomically claim upload
    Worker->>S3: Download PDF
    Worker->>AI: Extract, vectorize, embed, score, rank
    AI-->>Worker: Top recommendations + score details
    Worker->>DB: Save completed status and JSON result
    Worker->>EB: Publish completion event
    Worker->>Q: Delete message after successful processing

    EB->>Lambda: Invoke configured target
    Lambda->>Audit: Write audit record

    loop Frontend status polling
        UI->>API: GET /uploads/{upload_id}
        API->>DB: Read status/result
        DB-->>API: Current upload record
        API-->>UI: queued / processing / completed + result
    end
```

## Retry behaviour

If worker processing raises an exception, the worker logs the error and does not delete the SQS message. SQS can redeliver it after the visibility timeout. The queue's redrive policy moves a message to the configured dead-letter queue after the configured receive limit. This is queue-managed retry/redrive behaviour, not a custom worker-side DLQ transfer.

## API acceptance versus completion

The upload endpoint returns `202 Accepted` once the upload has been accepted and queued. It does not wait for the matching engine to finish. The client uses the returned upload identifier/status URL to check progress and retrieve the result later.

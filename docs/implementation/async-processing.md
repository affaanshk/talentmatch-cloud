# Asynchronous processing

The upload endpoint deliberately avoids running the full recommendation engine in the request-response cycle.

## Worker responsibilities

The Python worker:
1. Long-polls the configured SQS queue.
2. Reads the upload UUID from the message body.
3. Retrieves the PostgreSQL upload record.
4. Skips messages for missing or terminal records.
5. Atomically claims eligible work using a database update.
6. Downloads the original PDF from object storage.
7. Extracts text and runs the recommendation engine.
8. Saves the completed status, score, and recommendation JSON.
9. Publishes a completion event.
10. Deletes the queue message after successful processing.

## Reliability mechanisms

- **Atomic claim:** prevents two workers from processing the same queued record at the same time.
- **Processing lease:** a processing record older than four minutes can be reclaimed.
- **Visibility timeout:** queue messages become available again if they are not acknowledged within the configured visibility window.
- **DLQ redrive:** the queue moves repeatedly failing messages to the configured DLQ after the receive threshold.

## Known improvement

The event publisher returns a success indicator, but the worker currently does not use that return value to decide whether processing should be retried or whether the event should be republished. A transactional outbox or durable retry strategy would make the completion/audit path more robust.

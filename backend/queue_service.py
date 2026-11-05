import json
import os
from uuid import UUID
import boto3

QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
sqs = boto3.client("sqs", endpoint_url=os.getenv("SQS_ENDPOINT_URL") or os.getenv("AWS_ENDPOINT_URL") or None,
                   region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

def enqueue_resume_processing(upload_id: UUID) -> None:
    if not QUEUE_URL:
        raise RuntimeError("SQS_QUEUE_URL is not configured")
    sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps({"upload_id": str(upload_id)}))

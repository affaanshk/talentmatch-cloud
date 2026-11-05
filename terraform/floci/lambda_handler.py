
import json
import logging
import os
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get(
    "AUDIT_TABLE_NAME",
    "talentmatch-resume-audit-local",
)

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url=(
        os.environ.get("DYNAMODB_ENDPOINT_URL")
        or os.environ.get("AWS_ENDPOINT_URL")
        or None
    ),
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
)

table = dynamodb.Table(TABLE_NAME)


def handler(event, context):
    if not isinstance(event, dict):
        raise ValueError("Event must be a JSON object")

    detail = event.get("detail", {})
    if not isinstance(detail, dict):
        raise ValueError("Event detail must be a JSON object")

    upload_id = detail.get("upload_id")
    if not upload_id:
        raise ValueError("Missing upload_id in event detail")

    status = detail.get("status", "unknown")
    timestamp = datetime.now(timezone.utc).isoformat()

    item = {
        "upload_id": str(upload_id),
        "status": str(status),
        "event_source": str(event.get("source", "unknown")),
        "event_type": str(event.get("detail-type", "unknown")),
        "processed_at": timestamp,
        "event_id": str(event.get("id", getattr(context, "aws_request_id", "unknown"))),
    }

    # Store one audit record per upload. Repeated events for the same
    # upload_id update that record instead of creating duplicate items.
    table.put_item(Item=item)

    logger.info("Resume audit record saved: %s", json.dumps(item))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Resume completion event audited",
            "upload_id": str(upload_id),
            "status": str(status),
        }),
    }

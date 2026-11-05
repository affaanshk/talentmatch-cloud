"""Small idempotent-observable EventBridge completion handler."""
import json
import logging
import os
import time
import boto3

logging.getLogger().setLevel(os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("talentmatch.resume_completed")

def handler(event, context):
    detail = event.get("detail") or {}
    upload_id = detail.get("upload_id")
    status = detail.get("status")
    if not upload_id or status != "completed":
        log.warning("Ignoring malformed or non-completion event: %s", json.dumps(event, default=str))
        return {"accepted": False, "reason": "invalid_event"}
    table_name = os.getenv("DYNAMODB_TABLE_NAME")
    if table_name:
        dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
        table = dynamodb.Table(table_name)
        table.put_item(Item={"upload_id": str(upload_id), "status": "completed", "event_id": event.get("id", "unknown"), "updated_at": int(time.time())})
    log.info("Resume completed: upload_id=%s event_id=%s", upload_id, event.get("id", "unknown"))
    return {"accepted": True, "upload_id": str(upload_id)}

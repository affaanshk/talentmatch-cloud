import json, logging, os, time
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID
import boto3
from backend.database import claim_upload_for_processing, get_upload_record, update_upload_record
from backend.file_handler import extract_text_from_pdf
from backend.storage import download_resume
from core.recommendation.recommender import recommend_jobs
from backend.event_publisher import publish_resume_completed

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("talentmatch.worker")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
sqs = boto3.client("sqs", endpoint_url=os.getenv("SQS_ENDPOINT_URL") or os.getenv("AWS_ENDPOINT_URL") or None, region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

def process_upload(upload_id: UUID) -> bool:
    record = get_upload_record(upload_id)
    if record is None:
        logger.warning("Upload record %s is missing; acknowledging orphaned message", upload_id)
        return True
    if record["status"] in ("completed", "failed"):
        logger.info("Skipping terminal upload %s with status %s", upload_id, record["status"])
        return True
    if not claim_upload_for_processing(upload_id):
        # Leave the message unacknowledged; SQS will redeliver it.
        raise RuntimeError(f"Upload {upload_id} is already claimed; retry after visibility timeout")
    pdf_bytes = download_resume(record["object_key"])
    text = extract_text_from_pdf(SimpleNamespace(file=BytesIO(pdf_bytes)))
    if not text.strip():
        raise ValueError("No readable text found in stored resume")
    result = recommend_jobs(text)
    update_upload_record(
    upload_id,
    "completed",
    overall_score=float(result["overall_score"]),
    result=result,
    error_message=None,
    )
    publish_resume_completed(upload_id)
    logger.info("Upload %s completed", upload_id)
    return True

def run_worker() -> None:
    if not QUEUE_URL:
        raise RuntimeError("SQS_QUEUE_URL is not configured")
    logger.info("Worker started; polling SQS queue")
    while True:
        response = sqs.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=1, WaitTimeSeconds=20, VisibilityTimeout=300, AttributeNames=["ApproximateReceiveCount"])
        for message in response.get("Messages", []):
            upload_id = None
            count = int(message.get("Attributes", {}).get("ApproximateReceiveCount", "1"))
            try:
                upload_id = UUID(json.loads(message["Body"])["upload_id"])
                if process_upload(upload_id):
                    sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=message["ReceiptHandle"])
            except Exception:
                logger.exception("Message processing failed (receive %s)", count)
                if upload_id is not None:
                    try:
                        update_upload_record(upload_id, "queued", error_message="Resume processing failed; SQS will retry and move the message to the DLQ after the configured receive limit")
                    except Exception:
                        logger.exception("Could not update failed upload status")
                time.sleep(1)  # Do not delete; SQS handles retry and DLQ movement.

if __name__ == "__main__":
    run_worker()


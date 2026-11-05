from pathlib import Path
from datetime import datetime
import shutil, sys

ROOT = Path("/app")
if not (ROOT / "backend/database.py").exists():
    sys.exit("Run this script from the project root mounted at /app")

files = ["backend/database.py", "backend/worker.py", "tests/test_worker.py"]
for name in files:
    if not (ROOT / name).exists():
        sys.exit(f"Missing expected file: {name}; no files changed")

backup = ROOT / "backups" / ("pre_worker_reliability_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
for name in files:
    dest = backup / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / name, dest)

db = '''import json
import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]

def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def initialize_database():
    with get_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS resume_uploads (id UUID PRIMARY KEY, filename TEXT NOT NULL, object_key TEXT NOT NULL UNIQUE, file_size_bytes INTEGER NOT NULL, status TEXT NOT NULL, overall_score DOUBLE PRECISION, result JSONB, error_message TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("ALTER TABLE resume_uploads ADD COLUMN IF NOT EXISTS result JSONB")
        conn.execute("ALTER TABLE resume_uploads ADD COLUMN IF NOT EXISTS error_message TEXT")
        conn.execute("ALTER TABLE resume_uploads ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ")

def create_upload_record(upload_id, filename, object_key, file_size_bytes):
    with get_connection() as conn:
        conn.execute("INSERT INTO resume_uploads (id, filename, object_key, file_size_bytes, status) VALUES (%s, %s, %s, %s, %s)", (upload_id, filename, object_key, file_size_bytes, "queued"))

def claim_upload_for_processing(upload_id):
    # Atomic claim; a processing lease older than four minutes can be reclaimed.
    with get_connection() as conn:
        row = conn.execute("UPDATE resume_uploads SET status='processing', processing_started_at=CURRENT_TIMESTAMP, error_message=NULL WHERE id=%s AND (status='queued' OR (status='processing' AND (processing_started_at IS NULL OR processing_started_at < CURRENT_TIMESTAMP - INTERVAL '4 minutes'))) RETURNING id", (upload_id,)).fetchone()
        return row is not None

def update_upload_record(upload_id, status, overall_score=None, result=None, error_message=None):
    serialized = json.dumps(result) if result is not None else None
    with get_connection() as conn:
        conn.execute("UPDATE resume_uploads SET status=%s, overall_score=COALESCE(%s, overall_score), result=COALESCE(%s::jsonb, result), error_message=%s, processing_started_at=CASE WHEN %s='processing' THEN COALESCE(processing_started_at, CURRENT_TIMESTAMP) ELSE NULL END WHERE id=%s", (status, overall_score, serialized, error_message, status, upload_id))

def get_upload_record(upload_id):
    with get_connection() as conn:
        return conn.execute("SELECT id, filename, object_key, file_size_bytes, status, overall_score, result, error_message, created_at, processing_started_at FROM resume_uploads WHERE id=%s", (upload_id,)).fetchone()
'''

worker = '''import json, logging, os, time
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID
import boto3
from backend.database import claim_upload_for_processing, get_upload_record, update_upload_record
from backend.file_handler import extract_text_from_pdf
from backend.storage import download_resume
from core.recommendation.recommender import recommend_jobs

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
    update_upload_record(upload_id, "completed", overall_score=float(result["overall_score"]), result=result, error_message=None)
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
                        update_upload_record(upload_id, "queued" if count < 3 else "failed", error_message="Resume processing failed; retrying" if count < 3 else "Repeated processing failure; inspect the DLQ")
                    except Exception:
                        logger.exception("Could not update failed upload status")
                time.sleep(1)  # Do not delete; SQS handles retry and DLQ movement.

if __name__ == "__main__":
    run_worker()
'''

tests = '''from uuid import uuid4
import pytest
from backend import worker

def test_process_upload_persists_completed_recommendations(monkeypatch):
    upload_id = uuid4()
    monkeypatch.setattr(worker, "get_upload_record", lambda value: {"object_key": "resumes/example.pdf", "status": "queued"})
    monkeypatch.setattr(worker, "claim_upload_for_processing", lambda value: True)
    monkeypatch.setattr(worker, "download_resume", lambda key: b"%PDF-1.4 fake")
    monkeypatch.setattr(worker, "extract_text_from_pdf", lambda file: "Python and SQL developer experience")
    monkeypatch.setattr(worker, "recommend_jobs", lambda text: {"overall_score": 72.5, "recommendations": [{"title": "Python Developer", "score": 72.5}]})
    updates = []
    monkeypatch.setattr(worker, "update_upload_record", lambda *args, **kwargs: updates.append((args, kwargs)))
    assert worker.process_upload(upload_id) is True
    assert updates[0][0][1] == "completed"
    assert updates[0][1]["overall_score"] == 72.5
    assert updates[0][1]["result"]["recommendations"][0]["title"] == "Python Developer"

def test_process_upload_skips_completed_duplicate(monkeypatch):
    monkeypatch.setattr(worker, "get_upload_record", lambda value: {"status": "completed", "object_key": "resumes/example.pdf"})
    monkeypatch.setattr(worker, "claim_upload_for_processing", lambda value: (_ for _ in ()).throw(AssertionError("must not claim completed upload")))
    assert worker.process_upload(uuid4()) is True

def test_process_upload_skips_missing_record(monkeypatch):
    monkeypatch.setattr(worker, "get_upload_record", lambda value: None)
    assert worker.process_upload(uuid4()) is True

def test_process_upload_does_not_acknowledge_when_claim_fails(monkeypatch):
    monkeypatch.setattr(worker, "get_upload_record", lambda value: {"status": "processing", "object_key": "resumes/example.pdf"})
    monkeypatch.setattr(worker, "claim_upload_for_processing", lambda value: False)
    with pytest.raises(RuntimeError, match="already claimed"):
        worker.process_upload(uuid4())

def test_process_upload_rejects_empty_extracted_text(monkeypatch):
    monkeypatch.setattr(worker, "get_upload_record", lambda value: {"status": "queued", "object_key": "resumes/example.pdf"})
    monkeypatch.setattr(worker, "claim_upload_for_processing", lambda value: True)
    monkeypatch.setattr(worker, "download_resume", lambda key: b"%PDF-1.4 fake")
    monkeypatch.setattr(worker, "extract_text_from_pdf", lambda file: "   ")
    monkeypatch.setattr(worker, "recommend_jobs", lambda text: (_ for _ in ()).throw(AssertionError("must not recommend on empty text")))
    with pytest.raises(ValueError, match="No readable text"):
        worker.process_upload(uuid4())
'''

(ROOT / "backend/database.py").write_text(db, encoding="utf-8")
(ROOT / "backend/worker.py").write_text(worker, encoding="utf-8")
(ROOT / "tests/test_worker.py").write_text(tests, encoding="utf-8")
print("Patch applied. Backup:", backup.relative_to(ROOT))
print("Updated database claim logic, worker acknowledgement behavior, and worker tests.")
print("Existing PostgreSQL volume and records are preserved; migration only adds one nullable column.")

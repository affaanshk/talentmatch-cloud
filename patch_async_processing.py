from pathlib import Path
from datetime import datetime
import shutil, re, sys

ROOT = Path.cwd()
required = ["backend/api.py", "backend/database.py", "backend/storage.py", "backend/file_handler.py", "docker-compose.yml", "tests/test_api.py"]
missing = [p for p in required if not (ROOT / p).is_file()]
if missing:
    print("Run from project root; missing: " + ", ".join(missing)); sys.exit(2)
files = {p: (ROOT / p).read_text(encoding="utf-8") for p in required}
checks = [
    "# PDF UPLOAD" in files["backend/api.py"] and "# RESUME UPLOAD HISTORY" in files["backend/api.py"],
    "def create_upload_record(" in files["backend/database.py"],
    "def upload_resume(" in files["backend/storage.py"],
    "  talentmatch:" in files["docker-compose.yml"] and "  db:" in files["docker-compose.yml"],
    "def test_successful_upload(" in files["tests/test_api.py"],
    "def test_marks_upload_failed_when_recommendations_crash(" in files["tests/test_api.py"],
]
if not all(checks):
    print("Expected source markers not found; no files changed. Inspect current files first."); sys.exit(3)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = ROOT / "backups" / f"pre_async_patch_{stamp}"
for rel, content in files.items():
    target = backup / rel; target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / rel, target)

# Existing rows/data are preserved: schema changes are additive.
db = '''import json
import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]

def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS resume_uploads (
                id UUID PRIMARY KEY, filename TEXT NOT NULL,
                object_key TEXT NOT NULL UNIQUE, file_size_bytes INTEGER NOT NULL,
                status TEXT NOT NULL, overall_score DOUBLE PRECISION,
                result JSONB, error_message TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("ALTER TABLE resume_uploads ADD COLUMN IF NOT EXISTS result JSONB")
        conn.execute("ALTER TABLE resume_uploads ADD COLUMN IF NOT EXISTS error_message TEXT")

def create_upload_record(upload_id, filename, object_key, file_size_bytes):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO resume_uploads (id, filename, object_key, file_size_bytes, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (upload_id, filename, object_key, file_size_bytes, "queued"))

def update_upload_record(upload_id, status, overall_score=None, result=None, error_message=None):
    serialized = json.dumps(result) if result is not None else None
    with get_connection() as conn:
        conn.execute("""
            UPDATE resume_uploads SET status = %s,
                overall_score = COALESCE(%s, overall_score),
                result = COALESCE(%s::jsonb, result), error_message = %s
            WHERE id = %s
        """, (status, overall_score, serialized, error_message, upload_id))

def get_upload_record(upload_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT id, filename, object_key, file_size_bytes, status,
                   overall_score, result, error_message, created_at
            FROM resume_uploads WHERE id = %s
        """, (upload_id,)).fetchone()
'''
(ROOT / "backend/database.py").write_text(db, encoding="utf-8")

storage = '''import os
import boto3

s3 = boto3.client("s3", endpoint_url=os.getenv("AWS_ENDPOINT_URL") or None,
                  region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
BUCKET = os.getenv("S3_BUCKET_NAME", "talentmatch-resumes-local")

def upload_resume(pdf_bytes: bytes, object_key: str) -> None:
    s3.put_object(Bucket=BUCKET, Key=object_key, Body=pdf_bytes, ContentType="application/pdf")

def download_resume(object_key: str) -> bytes:
    response = s3.get_object(Bucket=BUCKET, Key=object_key)
    body = response["Body"]
    try:
        return body.read()
    finally:
        body.close()
'''
(ROOT / "backend/storage.py").write_text(storage, encoding="utf-8")

queue_service = '''import json
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
'''
(ROOT / "backend/queue_service.py").write_text(queue_service, encoding="utf-8")

api = files["backend/api.py"]
start, end = api.index("# PDF UPLOAD"), api.index("# RESUME UPLOAD HISTORY")
prefix, suffix = api[:start], api[end:]
prefix = prefix.replace("from fastapi import FastAPI, HTTPException, UploadFile, File", "from fastapi import FastAPI, HTTPException, UploadFile, File, status", 1)
if "from backend.queue_service import enqueue_resume_processing" not in prefix:
    prefix += "\nfrom backend.queue_service import enqueue_resume_processing\n"
route = '''# ------------------------------
# PDF UPLOAD (ASYNC PROCESSING)
# ------------------------------
@app.post("/upload-resume", status_code=status.HTTP_202_ACCEPTED)
async def upload_resume_api(file: UploadFile = File(...)):
    upload_id = uuid.uuid4()
    record_created = False
    try:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Please upload a PDF file")
        pdf_bytes = await file.read(MAX_RESUME_BYTES + 1)
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Empty file")
        if len(pdf_bytes) > MAX_RESUME_BYTES:
            raise HTTPException(status_code=413, detail="Resume must be 5 MB or smaller")
        if not pdf_bytes.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF")
        file.file.seek(0)
        resume_text = extract_text_from_pdf(file)
        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="No readable text found in resume")
        object_key = f"resumes/{upload_id.hex}.pdf"
        create_upload_record(upload_id, file.filename, object_key, len(pdf_bytes))
        record_created = True
        upload_resume(pdf_bytes, object_key)
        enqueue_resume_processing(upload_id)
        return {"upload_id": str(upload_id), "status": "queued",
                "message": "Resume accepted for background processing",
                "status_url": f"/uploads/{upload_id}"}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Resume enqueue failed for upload %s", upload_id)
        if record_created:
            try:
                update_upload_record(upload_id, "failed", error_message="Could not store or queue the resume")
            except Exception:
                logger.exception("Failed to mark upload %s as failed", upload_id)
        raise HTTPException(status_code=500, detail="Resume upload could not be queued")
    finally:
        await file.close()


'''
api = prefix + route + suffix
api = api.replace("SELECT id, filename, status, overall_score, created_at", "SELECT id, filename, status, overall_score, result, error_message, created_at")
api = api.replace("SELECT id, filename, object_key, file_size_bytes,\n                   status, overall_score, created_at", "SELECT id, filename, object_key, file_size_bytes,\n                   status, overall_score, result, error_message, created_at")
(ROOT / "backend/api.py").write_text(api, encoding="utf-8")

worker = '''import json, logging, os, time
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID
import boto3
from backend.database import get_upload_record, update_upload_record
from backend.file_handler import extract_text_from_pdf
from backend.storage import download_resume
from core.recommendation.recommender import recommend_jobs

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("talentmatch.worker")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
sqs = boto3.client("sqs", endpoint_url=os.getenv("SQS_ENDPOINT_URL") or os.getenv("AWS_ENDPOINT_URL") or None,
                   region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

def process_upload(upload_id: UUID) -> None:
    record = get_upload_record(upload_id)
    if record is None or record["status"] in ("completed", "failed"):
        logger.info("Skipping missing or terminal upload %s", upload_id); return
    update_upload_record(upload_id, "processing", error_message=None)
    pdf_bytes = download_resume(record["object_key"])
    text = extract_text_from_pdf(SimpleNamespace(file=BytesIO(pdf_bytes)))
    if not text.strip(): raise ValueError("No readable text found in stored resume")
    result = recommend_jobs(text)
    update_upload_record(upload_id, "completed", overall_score=float(result["overall_score"]), result=result, error_message=None)
    logger.info("Upload %s completed", upload_id)

def run_worker() -> None:
    if not QUEUE_URL: raise RuntimeError("SQS_QUEUE_URL is not configured")
    logger.info("Worker started; polling SQS queue")
    while True:
        response = sqs.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=1,
            WaitTimeSeconds=20, VisibilityTimeout=300, AttributeNames=["ApproximateReceiveCount"])
        for message in response.get("Messages", []):
            upload_id = None
            count = int(message.get("Attributes", {}).get("ApproximateReceiveCount", "1"))
            try:
                upload_id = UUID(json.loads(message["Body"])["upload_id"])
                process_upload(upload_id)
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=message["ReceiptHandle"])
            except Exception:
                logger.exception("Message processing failed (receive %s)", count)
                if upload_id is not None:
                    try:
                        update_upload_record(upload_id, "queued" if count < 3 else "failed",
                            error_message="Resume processing failed; retrying" if count < 3 else "Repeated processing failure; inspect the DLQ")
                    except Exception: logger.exception("Could not update failed upload status")
                time.sleep(1)  # Do not delete; SQS redelivery/DLQ policy handles retrying.

if __name__ == "__main__": run_worker()
'''
(ROOT / "backend/worker.py").write_text(worker, encoding="utf-8")

compose = re.sub(r'^\s*GEMINI_API_KEY:.*$', '      GEMINI_API_KEY: ${GEMINI_API_KEY:-}', files["docker-compose.yml"], count=1, flags=re.M)
if "SQS_QUEUE_URL:" not in compose:
    compose = compose.replace("      S3_BUCKET_NAME: talentmatch-resumes-local\n", "      S3_BUCKET_NAME: talentmatch-resumes-local\n      SQS_ENDPOINT_URL: http://host.docker.internal:4566\n      SQS_QUEUE_URL: http://host.docker.internal:4566/000000000000/talentmatch-local-resume-processing\n", 1)
if "  worker:" not in compose:
    service = '''
  worker:
    build: .
    container_name: talentmatch_worker
    command: ["python", "-m", "backend.worker"]
    environment:
      AWS_ACCESS_KEY_ID: floci
      AWS_SECRET_ACCESS_KEY: floci
      AWS_DEFAULT_REGION: us-east-1
      AWS_ENDPOINT_URL: http://host.docker.internal:4566
      SQS_ENDPOINT_URL: http://host.docker.internal:4566
      SQS_QUEUE_URL: http://host.docker.internal:4566/000000000000/talentmatch-local-resume-processing
      S3_BUCKET_NAME: talentmatch-resumes-local
      DATABASE_URL: postgresql://talentmatch:local_dev_password@db:5432/talentmatch
      GEMINI_API_KEY: ${GEMINI_API_KEY:-}
      GEMINI_MODEL: ${GEMINI_MODEL:-gemini-3.5-flash-lite}
    volumes:
      - .:/app
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
'''
    if "\n  db:\n" not in compose: raise RuntimeError("db service marker missing; backup exists")
    compose = compose.replace("\n  db:\n", "\n" + service + "\n  db:\n", 1)
(ROOT / "docker-compose.yml").write_text(compose, encoding="utf-8")

tests = files["tests/test_api.py"]
a, b = tests.index("def test_successful_upload("), tests.find("\ndef ", tests.index("def test_successful_upload(") + 5)
if b < 0: b = len(tests)
block = tests[a:b]
block = block.replace('    monkeypatch.setattr(\n        api,\n        "upload_resume",\n        lambda pdf_bytes, object_key: None,\n    )\n', '    monkeypatch.setattr(\n        api,\n        "upload_resume",\n        lambda pdf_bytes, object_key: None,\n    )\n    monkeypatch.setattr(api, "enqueue_resume_processing", lambda upload_id: None)\n')
block = re.sub(r'    monkeypatch\.setattr\(\n        api,\n        "recommend_jobs",\n        lambda text: \{"overall_score": 44\.5, "recommendations": \[\]\},\n    \)\n', '', block)
block = block.replace("assert response.status_code == 200", "assert response.status_code == 202").replace('assert data["status"] == "completed"', 'assert data["status"] == "queued"')
block = re.sub(r'    assert data\["overall_score"\] == 44\.5\n', '', block)
tests = tests[:a] + block + tests[b:]
a = tests.index("def test_marks_upload_failed_when_recommendations_crash(")
b = tests.find("\ndef test_career_advice_success(", a)
if b < 0: print("Test boundary missing; restore from backup and inspect."); sys.exit(4)
new_test = '''def test_marks_upload_failed_when_queue_publish_fails(monkeypatch):
    import backend.api as api
    saved, updated = [], []
    monkeypatch.setattr(api, "extract_text_from_pdf", lambda file: "Python and SQL experience")
    monkeypatch.setattr(api, "upload_resume", lambda pdf_bytes, object_key: None)
    monkeypatch.setattr(api, "create_upload_record", lambda **kwargs: saved.append(kwargs))
    monkeypatch.setattr(api, "update_upload_record", lambda *args, **kwargs: updated.append((args, kwargs)))
    def fail_queue(upload_id): raise RuntimeError("Simulated SQS failure")
    monkeypatch.setattr(api, "enqueue_resume_processing", fail_queue)
    response = client.post("/upload-resume", files={"file": ("resume.pdf", b"%PDF-1.4 test content", "application/pdf")})
    assert response.status_code == 500
    assert response.json()["detail"] == "Resume upload could not be queued"
    assert len(saved) == 1 and updated[0][0][1] == "failed"


'''
tests = tests[:a] + new_test + tests[b:]
(ROOT / "tests/test_api.py").write_text(tests, encoding="utf-8")

worker_tests = '''from uuid import uuid4
from backend import worker

def test_process_upload_persists_completed_recommendations(monkeypatch):
    upload_id = uuid4()
    monkeypatch.setattr(worker, "get_upload_record", lambda value: {"object_key": "resumes/example.pdf", "status": "queued"})
    monkeypatch.setattr(worker, "download_resume", lambda key: b"%PDF-1.4 fake")
    monkeypatch.setattr(worker, "extract_text_from_pdf", lambda file: "Python and SQL developer experience")
    monkeypatch.setattr(worker, "recommend_jobs", lambda text: {"overall_score": 72.5, "recommendations": [{"title": "Python Developer", "score": 72.5}]})
    updates = []
    monkeypatch.setattr(worker, "update_upload_record", lambda *args, **kwargs: updates.append((args, kwargs)))
    worker.process_upload(upload_id)
    assert updates[0][0][1] == "processing" and updates[1][0][1] == "completed"
    assert updates[1][1]["overall_score"] == 72.5
    assert updates[1][1]["result"]["recommendations"][0]["title"] == "Python Developer"

def test_process_upload_skips_completed_duplicate(monkeypatch):
    monkeypatch.setattr(worker, "get_upload_record", lambda value: {"status": "completed", "object_key": "resumes/example.pdf"})
    monkeypatch.setattr(worker, "download_resume", lambda key: (_ for _ in ()).throw(AssertionError("must not redownload")))
    worker.process_upload(uuid4())

def test_process_upload_skips_missing_record(monkeypatch):
    monkeypatch.setattr(worker, "get_upload_record", lambda value: None)
    worker.process_upload(uuid4())
'''
(ROOT / "tests/test_worker.py").write_text(worker_tests, encoding="utf-8")

print("Patch applied. Backup folder:", backup.relative_to(ROOT))
print("Changed backend API/database/storage, added queue_service.py and worker.py,")
print("updated Docker Compose and API tests, and added tests/test_worker.py.")
print("No .env file was read or printed.")

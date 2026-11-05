import json
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

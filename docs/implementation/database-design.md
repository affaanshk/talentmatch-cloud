# Database design

The local application uses PostgreSQL 16. The main `resume_uploads` table stores the lifecycle and result of each submitted resume.

| Column | Purpose |
|---|---|
| `id` | UUID primary key for an upload |
| `filename` | Original uploaded filename |
| `object_key` | Unique object-storage key |
| `file_size_bytes` | Uploaded file size |
| `status` | Processing state such as queued, processing, completed, or failed |
| `overall_score` | Overall recommendation score |
| `result` | Full recommendation payload stored as JSONB |
| `error_message` | Most recent processing error, if any |
| `created_at` | Record creation timestamp |
| `processing_started_at` | Processing lease timestamp |

The schema is initialized/extended by SQL statements in `backend/database.py` at application startup. A versioned migration tool such as Alembic is not currently used.

The worker uses a conditional `UPDATE ... RETURNING` operation to claim a queued record or reclaim a stale processing record. This makes the claim atomic at the database level.

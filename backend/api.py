from fastapi import FastAPI, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.skills.skill_engine import extract_skills, compare_skills
from core.recommendation.recommender import recommend_jobs
from backend.file_handler import extract_text_from_pdf

import uuid
from backend.storage import upload_resume
MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5 MB

from backend.database import (
    initialize_database,
    create_upload_record,
    update_upload_record,
    get_connection,
)

import logging
logger = logging.getLogger(__name__)

from backend.genai_service import generate_career_advice
from pydantic import BaseModel, Field

app = FastAPI()
@app.on_event("startup")
def startup():
    initialize_database()


# ------------------------------
# 🔥 CORS
# ------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------
# ROOT
# ------------------------------
@app.get("/")
def home():
    return {"message": "TalentMatch API running successfully"}


# ------------------------------
# MODELS
# ------------------------------
class TextInput(BaseModel):
    text: str


class SkillCompareInput(BaseModel):
    resume_skills: list[str]
    job_skills: list[str]


class RecommendationInput(BaseModel):
    resume_text: str


class CareerAdviceInput(BaseModel):
    job_title: str
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


# ------------------------------
# SKILL EXTRACTION
# ------------------------------
@app.post("/extract-skills")
def extract_skills_api(data: TextInput):

    if not data.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    return {"skills": extract_skills(data.text)}


# ------------------------------
# SKILL COMPARISON
# ------------------------------
@app.post("/compare-skills")
def compare_skills_api(data: SkillCompareInput):

    if not data.resume_skills or not data.job_skills:
        raise HTTPException(status_code=400, detail="Invalid input")

    return compare_skills(data.resume_skills, data.job_skills)


# ------------------------------
# TEXT RECOMMENDATION
# ------------------------------
@app.post("/recommend")
def recommend_api(data: RecommendationInput):

    if not data.resume_text:
        raise HTTPException(status_code=400, detail="Invalid input")

    result = recommend_jobs(data.resume_text)

    return {
        "overall_score": result["overall_score"],
        "recommendations": result["recommendations"]
    }


# ------------------------------
# GEMINI CAREER ADVICE
# ------------------------------
@app.post("/career-advice")
def career_advice(data: CareerAdviceInput):
    if not data.job_title.strip():
        raise HTTPException(
            status_code=400,
            detail="Job title cannot be empty",
        )

    try:
        advice = generate_career_advice(
            job_title=data.job_title.strip(),
            matched_skills=data.matched_skills,
            missing_skills=data.missing_skills,
        )

        return {
            "job_title": data.job_title.strip(),
            "career_advice": advice,
        }

    except RuntimeError as exc:
        # Missing API configuration or an empty model response
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception:
        logger.exception("Gemini career advice generation failed")
        raise HTTPException(
            status_code=502,
            detail="Career advice service is temporarily unavailable",
        )



# ------------------------------

from backend.queue_service import enqueue_resume_processing
# ------------------------------
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


# RESUME UPLOAD HISTORY
# ------------------------------
@app.get("/uploads")
def list_uploads(limit: int = 20):
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100",
        )

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, filename, status, overall_score, result, error_message, created_at
            FROM resume_uploads
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()

    return {"uploads": rows}


@app.get("/uploads/{upload_id}")
def get_upload(upload_id: uuid.UUID):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, filename, object_key, file_size_bytes,
                   status, overall_score, result, error_message, created_at
            FROM resume_uploads
            WHERE id = %s
            """,
            (upload_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Upload not found",
        )

    return row

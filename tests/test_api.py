"""#We'll test the real API endpoint while mocking the expensive or external parts: PDF extraction,
 S3, PostgreSQL writes, and the recommendation engine. 
 That makes the tests fast and prevents them from changing your real database or storage.
"""


from fastapi.testclient import TestClient

from backend.api import app


client = TestClient(app)


def test_rejects_non_pdf():
    response = client.post(
        "/upload-resume",
        files={"file": ("resume.txt", b"not a PDF", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Please upload a PDF file"


def test_rejects_invalid_pdf_signature():
    response = client.post(
        "/upload-resume",
        files={"file": ("resume.pdf", b"not a PDF", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded file is not a valid PDF"


def test_successful_upload(monkeypatch):
    import backend.api as api

    monkeypatch.setattr(
        api,
        "extract_text_from_pdf",
        lambda file: "Python, SQL, FastAPI and machine learning experience",
    )
    monkeypatch.setattr(
        api,
        "upload_resume",
        lambda pdf_bytes, object_key: None,
    )
    monkeypatch.setattr(api, "enqueue_resume_processing", lambda upload_id: None)
    monkeypatch.setattr(api, "create_upload_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        api,
        "update_upload_record",
        lambda *args, **kwargs: None,
    )

    response = client.post(
        "/upload-resume",
        files={
            "file": (
                "resume.pdf",
                b"%PDF-1.4 test content",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 202

    data = response.json()
    assert data["status"] == "queued"
    assert data["upload_id"]


def test_rejects_oversized_resume():
    response = client.post(
        "/upload-resume",
        files={
            "file": (
                "large.pdf",
                b"%PDF-" + b"x" * (5 * 1024 * 1024),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Resume must be 5 MB or smaller"


def test_rejects_pdf_without_readable_text(monkeypatch):
    import backend.api as api

    monkeypatch.setattr(
        api,
        "extract_text_from_pdf",
        lambda file: "   \n  ",
    )

    response = client.post(
        "/upload-resume",
        files={
            "file": (
                "empty_resume.pdf",
                b"%PDF-1.4 test content",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No readable text found in resume"


def test_marks_upload_failed_when_queue_publish_fails(monkeypatch):
    import backend.api as api
    saved, updated = [], []
    monkeypatch.setattr(api, "extract_text_from_pdf", lambda file: "Python and SQL experience")
    monkeypatch.setattr(api, "upload_resume", lambda pdf_bytes, object_key: None)
    monkeypatch.setattr(
    api,
    "create_upload_record",
    lambda *args, **kwargs: saved.append((args, kwargs)),
    )
    monkeypatch.setattr(api, "update_upload_record", lambda *args, **kwargs: updated.append((args, kwargs)))
    def fail_queue(upload_id): raise RuntimeError("Simulated SQS failure")
    monkeypatch.setattr(api, "enqueue_resume_processing", fail_queue)
    response = client.post("/upload-resume", files={"file": ("resume.pdf", b"%PDF-1.4 test content", "application/pdf")})
    assert response.status_code == 500
    assert response.json()["detail"] == "Resume upload could not be queued"
    assert len(saved) == 1 and updated[0][0][1] == "failed"



def test_career_advice_success(monkeypatch):
    import backend.api as api

    monkeypatch.setattr(
        api,
        "generate_career_advice",
        lambda job_title, matched_skills, missing_skills:
            "Build a FastAPI project and practise Docker.",
    )

    response = client.post(
        "/career-advice",
        json={
            "job_title": "Python Developer",
            "matched_skills": ["Python", "SQL"],
            "missing_skills": ["FastAPI", "Docker"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_title"] == "Python Developer"
    assert "FastAPI" in data["career_advice"]


def test_career_advice_missing_api_key(monkeypatch):
    import backend.api as api

    def fail_without_key(job_title, matched_skills, missing_skills):
        raise RuntimeError("Gemini API key is not configured.")

    monkeypatch.setattr(
        api, "generate_career_advice", fail_without_key
    )

    response = client.post(
        "/career-advice",
        json={"job_title": "Python Developer"},
    )

    assert response.status_code == 503
    assert "API key is not configured" in response.json()["detail"]


def test_career_advice_provider_failure(monkeypatch):
    import backend.api as api

    def fail_provider(job_title, matched_skills, missing_skills):
        raise ValueError("Simulated provider failure")

    monkeypatch.setattr(
        api, "generate_career_advice", fail_provider
    )

    response = client.post(
        "/career-advice",
        json={"job_title": "Python Developer"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Career advice service is temporarily unavailable"
    )

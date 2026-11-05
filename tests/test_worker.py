from uuid import uuid4
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

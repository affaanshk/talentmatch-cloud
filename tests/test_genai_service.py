
import pytest

from backend import genai_service


def test_generate_career_advice_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")

    captured = {}

    class FakeModels:
        def generate_content(self, model, contents):
            captured["model"] = model
            captured["prompt"] = contents
            return type(
                "FakeResponse",
                (),
                {"text": "Build a FastAPI project and practise Docker."},
            )()

    class FakeClient:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.models = FakeModels()

    monkeypatch.setattr(
        genai_service.genai, "Client", FakeClient
    )

    result = genai_service.generate_career_advice(
        job_title="Python Developer",
        matched_skills=["Python", "SQL"],
        missing_skills=["FastAPI", "Docker"],
    )

    assert result == "Build a FastAPI project and practise Docker."
    assert captured["api_key"] == "test-api-key"
    assert captured["model"] == "test-model"
    assert "Python Developer" in captured["prompt"]
    assert "FastAPI" in captured["prompt"]


def test_generate_career_advice_missing_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(
        RuntimeError, match="API key is not configured"
    ):
        genai_service.generate_career_advice(
            "Python Developer", ["Python"], ["Docker"]
        )


def test_generate_career_advice_empty_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")

    class FakeModels:
        def generate_content(self, model, contents):
            return type("FakeResponse", (), {"text": "  "})()

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr(
        genai_service.genai, "Client", FakeClient
    )

    with pytest.raises(
        RuntimeError, match="empty response"
    ):
        genai_service.generate_career_advice(
            "Python Developer", ["Python"], ["Docker"]
        )


def test_generate_career_advice_api_error_propagates(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")

    class FakeModels:
        def generate_content(self, model, contents):
            raise RuntimeError("Simulated Gemini failure")

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr(
        genai_service.genai, "Client", FakeClient
    )

    with pytest.raises(
        RuntimeError, match="Simulated Gemini failure"
    ):
        genai_service.generate_career_advice(
            "Python Developer", ["Python"], ["Docker"]
        )


from core.skills.skill_engine import extract_skills, compare_skills


def test_extracts_technical_skills():
    text = "Experienced in Python, PostgreSQL, AWS and Terraform"

    skills = extract_skills(text)

    assert "python" in skills
    assert "postgresql" in skills
    assert "aws" in skills
    assert "terraform" in skills


def test_skill_comparison():
    result = compare_skills(
        ["python", "sql", "aws"],
        ["python", "sql", "docker", "terraform"],
    )

    assert result["matched"] == ["python", "sql"]
    assert result["missing"] == ["docker", "terraform"]
    assert result["score"] == 0.5


def test_empty_job_skills():
    result = compare_skills(["python"], [])

    assert result["matched"] == []
    assert result["missing"] == []
    assert result["score"] == 0.0


import re

COMMON_SKILLS = [
    "python", "java", "c++",
    "machine learning", "deep learning",
    "sql", "mongodb", "docker", "kubernetes",
    "react", "node", "aws", "git",
    "data analysis", "pandas", "numpy",
    "tensorflow", "pytorch", "fastapi", "flask",
    "nlp", "computer vision", "azure", "gcp",
    "postgresql", "mysql", "javascript", "typescript",
    "html", "css", "rest api", "linux",
    "terraform", "jenkins", "github actions",
    "scikit-learn", "natural language processing",
    "generative ai", "large language models",
    "llm", "langchain", "kafka", "redis",
    "aws lambda", "amazon s3", "amazon ec2",
    "amazon rds", "cloudwatch", "iam",
]


def extract_skills(text: str) -> list[str]:
    """Extract known skills in a consistent order."""
    text = text.lower()
    found = []

    for skill in COMMON_SKILLS:
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
        if re.search(pattern, text):
            found.append(skill)

    return found


def compare_skills(
    resume_skills: list[str],
    job_skills: list[str],
) -> dict:
    """Compare resume skills against skills identified in a job."""

    resume_set = {skill.lower() for skill in resume_skills}
    job_set = {skill.lower() for skill in job_skills}

    matched = sorted(resume_set & job_set)
    missing = sorted(job_set - resume_set)

    score = len(matched) / len(job_set) if job_set else 0.0

    return {
        "matched": matched,
        "missing": missing,
        "score": round(score, 3),
    }


import os

from google import genai


def generate_career_advice(
    job_title: str,
    matched_skills: list[str],
    missing_skills: list[str],
) -> str:
    """Generate career advice using Gemini."""

    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    if not api_key:
        raise RuntimeError("Gemini API key is not configured.")

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are a practical career coach.

Target job: {job_title}
Skills the candidate already matches: {", ".join(matched_skills) or "None listed"}
Skills to develop: {", ".join(missing_skills) or "None listed"}

Provide:
1. A brief assessment of the candidate's fit for this job.
2. Three prioritized actions to improve their skills.
3. A realistic learning roadmap with milestones.
4. Two resume-improvement suggestions.
5. Three interview topics to prepare for.

Be specific, encouraging, honest, and concise.
Do not invent qualifications or claim the candidate has skills
that are not listed.
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )

    advice = getattr(response, "text", None)

    if not advice or not advice.strip():
        raise RuntimeError("Gemini returned an empty response.")

    return advice.strip()

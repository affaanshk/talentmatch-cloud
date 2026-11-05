
from unittest.mock import patch

from core.recommendation.recommender import recommend_jobs


def test_overall_score_uses_actual_recommendation_count():
    fake_jobs = [
        {
            "Job Description": "Python developer",
            "Job Title": "Python Developer",
        },
        {
            "Job Description": "Data analyst",
            "Job Title": "Data Analyst",
        },
        {
            "Job Description": "Backend engineer",
            "Job Title": "Backend Engineer",
        },
    ]

    fake_recommendations = {
        "overall_score": 0,
        "recommendations": [],
    }

    with (
        patch(
            "core.recommendation.recommender.load_jobs",
            return_value=__import__("pandas").DataFrame(fake_jobs),
        ),
        patch(
            "core.recommendation.recommender.TFIDFVectorizer"
        ) as mock_tfidf,
        patch(
            "core.recommendation.recommender.Embedder"
        ) as mock_embedder,
        patch(
            "core.recommendation.recommender.extract_skills",
            return_value=["python"],
        ),
        patch(
            "core.recommendation.recommender.compare_skills",
            return_value={
                "score": 1.0,
                "matched": ["python"],
                "missing": [],
            },
        ),
        patch(
            "core.recommendation.recommender.Similarity.compute",
            return_value=0.8,
        ),
    ):
        mock_tfidf.return_value.fit_transform.return_value = [
            [1.0],
            [1.0],
            [1.0],
            [1.0],
        ]
        mock_embedder.return_value.encode.return_value = [
            [0.0] * 384,
            [0.0] * 384,
            [0.0] * 384,
            [0.0] * 384,
        ]

        result = recommend_jobs("Python developer", top_k=5)

    assert len(result["recommendations"]) == 3
    assert result["overall_score"] == 84.0

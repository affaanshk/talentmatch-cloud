# AI matching engine

## Inputs and outputs

The engine receives extracted resume text and compares it with job descriptions loaded by the project data loader. By default, it returns the five highest-ranked recommendations.

Each recommendation contains:
- Job title and a shortened job-description excerpt
- TF-IDF similarity score
- Sentence Transformer semantic similarity score
- Skill overlap score
- Final weighted score
- Matched skills and missing skills
- A skill-improvement suggestion
- A short explanation showing the component scores

## Processing stages

1. Load job titles and descriptions.
2. Build TF-IDF representations using the project vectorizer.
3. Generate semantic embeddings with `all-MiniLM-L6-v2`.
4. Extract skills from the resume and each job description.
5. Compare skill sets to calculate a skill score and missing-skill list.
6. Calculate cosine similarity for TF-IDF vectors and semantic embeddings.
7. Combine component scores and sort recommendations in descending order.
8. Return the top results and average their scores for the overall match percentage.

## Active scoring formula

The implementation in `core/recommendation/recommender.py` uses:

`final_score = 0.30 * tfidf_score + 0.50 * bert_score + 0.20 * skill_score`

The overall score is the mean of the returned top recommendations multiplied by 100.

**Code consistency issue:** `backend/config.py` defines 0.40/0.40/0.20 weights, but the recommender function currently hardcodes 0.30/0.50/0.20. The active behaviour is the hardcoded expression. The documentation intentionally reports the active code path rather than silently treating the config values as effective.

## Important interpretation

The match score is a heuristic ranking signal based on the available dataset and feature combination. It is not a probability of being hired, a validated measure of job performance, or a guarantee that a role is suitable.

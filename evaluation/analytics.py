
def analyze_results(results):
    if not results:
        return {
            "avg_tfidf": 0.0,
            "avg_bert": 0.0,
            "better_model": "Insufficient data",
        }

    avg_tfidf = sum(
        result["TF-IDF"] for result in results
    ) / len(results)

    avg_bert = sum(
        result["BERT"] for result in results
    ) / len(results)

    if avg_bert > avg_tfidf:
        better_model = "BERT"
    elif avg_tfidf > avg_bert:
        better_model = "TF-IDF"
    else:
        better_model = "Tie"

    return {
        "avg_tfidf": round(avg_tfidf, 3),
        "avg_bert": round(avg_bert, 3),
        "better_model": better_model,
    }

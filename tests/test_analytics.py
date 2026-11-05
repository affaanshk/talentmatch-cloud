
from evaluation.analytics import analyze_results


def test_analyze_results_calculates_averages():
    results = [
        {"TF-IDF": 0.4, "BERT": 0.8},
        {"TF-IDF": 0.6, "BERT": 0.6},
    ]

    analysis = analyze_results(results)

    assert analysis["avg_tfidf"] == 0.5
    assert analysis["avg_bert"] == 0.7
    assert analysis["better_model"] == "BERT"


def test_analyze_results_returns_tie():
    results = [{"TF-IDF": 0.7, "BERT": 0.7}]

    analysis = analyze_results(results)

    assert analysis["better_model"] == "Tie"


def test_analyze_results_handles_empty_input():
    analysis = analyze_results([])

    assert analysis["avg_tfidf"] == 0.0
    assert analysis["avg_bert"] == 0.0
    assert analysis["better_model"] == "Insufficient data"

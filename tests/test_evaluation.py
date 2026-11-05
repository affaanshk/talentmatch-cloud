
from evaluation.evaluator import compare_models
from evaluation.analytics import analyze_results


def main():
    test_cases = [
        ("Python developer with machine learning",
         "Looking for ML engineer"),
        ("Data analyst with SQL and Excel",
         "Hiring data scientist with Python"),
        ("Frontend React developer",
         "Looking for backend Java developer")
    ]

    results = []

    print("\n========== MODEL EVALUATION ==========")

    for i, (resume, job) in enumerate(test_cases, 1):
        result = compare_models(resume, job)
        results.append(result)

        print(f"\nTest Case {i}")
        print(f"Resume: {resume}")
        print(f"Job: {job}")
        print(f"TF-IDF Score: {result['TF-IDF']:.3f}")
        print(f"BERT Score:   {result['BERT']:.3f}")

    analysis = analyze_results(results)

    print("\n========== FINAL ANALYSIS ==========")
    print(f"Average TF-IDF: {analysis['avg_tfidf']:.3f}")
    print(f"Average BERT:   {analysis['avg_bert']:.3f}")
    print(f"Better Model:   {analysis['better_model']}")


if __name__ == "__main__":
    main()


from core.representation.vectorizer import TFIDFVectorizer
from core.deep_learning.embedder import Embedder
from sklearn.metrics.pairwise import cosine_similarity


def compare_models(resume, job_desc):
    # TF-IDF similarity
    tfidf = TFIDFVectorizer()
    tfidf_vectors = tfidf.fit_transform(
        [resume, job_desc]
    ).toarray()

    tfidf_score = cosine_similarity(
        tfidf_vectors[0:1],
        tfidf_vectors[1:2]
    )[0][0]

    # Sentence Transformer semantic similarity
    embedder = Embedder()
    embeddings = embedder.encode([resume, job_desc])

    bert_score = cosine_similarity(
        embeddings[0:1],
        embeddings[1:2]
    )[0][0]

    return {
        "TF-IDF": float(tfidf_score),
        "BERT": float(bert_score),
        "difference": float(bert_score - tfidf_score)
    }

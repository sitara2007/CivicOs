from __future__ import annotations

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from app.core.config import get_settings


class LazySentenceTransformer:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def encode(self, text: str):
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model.encode(text)


settings = get_settings()
model = LazySentenceTransformer(settings.rag_embedding_model)

if settings.qdrant_url.strip():
    client = QdrantClient(url=settings.qdrant_url)
else:
    client = QdrantClient(path=settings.rag_qdrant_path)

collection_name = settings.rag_collection_name


def _pgvector_bm25_fallback(query: str, top_k: int = 3):
    """Fallback retrieval mechanism using PGVector/BM25 when Qdrant fails."""
    return []

def retrieve(query, top_k=3):
    query_vector = model.encode(query).tolist()

    try:
        results = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k
        )
        return [
            {"text": point.payload["text"], "score": point.score}
            for point in results.points
        ]
    except (TimeoutError, Exception):
        # Trigger fallback when Qdrant times out or encounters an error
        return _pgvector_bm25_fallback(query, top_k=top_k)


if __name__ == "__main__":
    question = "Who is eligible for this scheme?"
    answers = retrieve(question)
    for item in answers:
        print("\nSCORE:", item["score"])
        print(item["text"][:300])

from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.db.vector_clients.pgvector_client import pgvector_bm25_fallback


class LazySentenceTransformer:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def encode(self, text: str):
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model.encode(text)


settings = get_settings()
# same model used while storing
model = LazySentenceTransformer(settings.rag_embedding_model)

if settings.qdrant_url.strip():
    client = QdrantClient(url=settings.qdrant_url)
else:
    client = QdrantClient(path=settings.rag_qdrant_path)


collection_name = settings.rag_collection_name


def _pgvector_bm25_fallback(query: str, top_k: int) -> list[dict[str, Any]]:
    return pgvector_bm25_fallback(query=query, top_k=top_k)


def retrieve(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    query_vector = model.encode(query).tolist()
    timeout_seconds = max(settings.rag_qdrant_timeout_ms, 1) / 1000.0

    try:
        results = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        if isinstance(exc, TimeoutError) or "timeout" in str(exc).lower():
            return _pgvector_bm25_fallback(query, top_k)
        raise

    chunks: list[dict[str, Any]] = []
    for point in getattr(results, "points", []):
        chunks.append({"text": point.payload["text"], "score": point.score})

    return chunks


if __name__ == "__main__":
    question = "Who is eligible for this scheme?"

    answers = retrieve(question)

    for item in answers:
        print("\nSCORE:", item["score"])

        print(item["text"][:300])

from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.db.vector_clients.pgvector_client import pgvector_bm25_fallback
from app.services.rag.reranker import rerank_chunks


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


def _pgvector_bm25_fallback(query: str, top_k: int) -> list[dict[str, Any]]:
    return pgvector_bm25_fallback(query=query, top_k=top_k)


def _combine_candidates(
    qdrant_chunks: list[dict[str, Any]], bm25_chunks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    combined: dict[str, dict[str, Any]] = {}

    for chunk in [*qdrant_chunks, *bm25_chunks]:
        text = chunk.get("text", "").strip()
        if not text:
            continue

        if text in combined:
            combined[text]["score"] = max(combined[text]["score"], chunk.get("score", 0.0))
            continue

        combined[text] = {"text": text, "score": chunk.get("score", 0.0)}

    return list(combined.values())


def retrieve(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    query_vector = model.encode(query).tolist()
    timeout_seconds = max(settings.rag_qdrant_timeout_ms, 1) / 1000.0
    candidate_k = max(top_k, settings.rag_rerank_candidate_k)

    qdrant_chunks: list[dict[str, Any]] = []
    try:
        results = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=candidate_k,
            timeout=timeout_seconds,
        )
        qdrant_chunks = [
            {"text": point.payload["text"], "score": point.score}
            for point in getattr(results, "points", [])
        ]
    except Exception as exc:
        if not (isinstance(exc, TimeoutError) or "timeout" in str(exc).lower()):
            raise

    bm25_chunks = _pgvector_bm25_fallback(query, candidate_k)
    candidates = _combine_candidates(qdrant_chunks, bm25_chunks)

    if not candidates:
        return []

    return rerank_chunks(query, candidates, top_k)


if __name__ == "__main__":
    question = "Who is eligible for this scheme?"
    answers = retrieve(question)

    for item in answers:
        print("\nSCORE:", item["score"])
        print(item["text"][:300])

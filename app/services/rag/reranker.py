from __future__ import annotations

from typing import Any

from sentence_transformers import CrossEncoder

from app.core.config import get_settings

settings = get_settings()


class LazyCrossEncoder:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: CrossEncoder | None = None

    def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        if self._model is None:
            self._model = CrossEncoder(self._model_name)
        return self._model.predict(pairs).tolist()


reranker = LazyCrossEncoder(settings.rag_reranker_model)


def rerank_chunks(query: str, chunks: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    if not chunks:
        return []

    pairs = [(query, chunk["text"]) for chunk in chunks]
    scores = reranker.score(pairs)

    ranked = [
        {"text": chunk["text"], "score": float(score)}
        for chunk, score in sorted(
            zip(chunks, scores, strict=True), key=lambda pair: pair[1], reverse=True
        )
    ]

    return ranked[:top_k]

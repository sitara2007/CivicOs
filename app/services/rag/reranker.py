"""Robust cross-encoder reranker with fallback handling."""

from __future__ import annotations

import logging
from typing import Any

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class SafeReranker:
    def __init__(self, model_name: str = "cross-encoder/bge-reranker-large"):
        self._model_name = model_name
        self._model = None

    def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        if not self._model:
            try:
                self._model = CrossEncoder(self._model_name)
            except Exception as e:
                logger.warning(
                    f"Could not load Hugging Face model {self._model_name}: {e}. Falling back to default scoring."  # noqa: E501
                )
                return [0.0] * len(pairs)

        return self._model.predict(pairs)


_global_reranker: SafeReranker | None = None


def get_reranker() -> SafeReranker:
    global _global_reranker
    if _global_reranker is None:
        _global_reranker = SafeReranker()
    return _global_reranker


def rerank_chunks(query: str, chunks: list[dict[str, Any]], top_k: int = 3) -> list[dict[str, Any]]:
    """Rerank retrieved document chunks using a cross-encoder model."""
    if not chunks:
        return []

    reranker = get_reranker()
    pairs = [(query, chunk.get("content", "")) for chunk in chunks]

    try:
        scores = reranker.score(pairs)
    except Exception as e:
        logger.error(f"Reranking failed: {e}. Returning original chunk order.")
        return chunks[:top_k]

    # Attach scores to chunks and sort descending with strict zip
    scored_chunks = []
    for chunk, score in zip(chunks, scores, strict=True):
        chunk_copy = chunk.copy()
        chunk_copy["rerank_score"] = float(score)
        scored_chunks.append(chunk_copy)

    scored_chunks.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
    return scored_chunks[:top_k]

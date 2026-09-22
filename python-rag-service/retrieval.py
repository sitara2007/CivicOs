from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


@dataclass
class RetrievalCandidate:
    text: str
    score: float
    source: str = "hybrid"
    metadata: dict[str, Any] = field(default_factory=dict)


class HybridRetriever:
    def __init__(
        self,
        *,
        collection_name: str | None = None,
        qdrant_url: str | None = None,
        qdrant_path: str | None = None,
        dense_model: str | None = None,
        rerank_model: str | None = None,
    ) -> None:
        self.collection_name = collection_name or os.getenv(
            "QDRANT_COLLECTION", "gov_docs"
        )
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL")
        self.qdrant_path = qdrant_path or os.getenv("QDRANT_PATH", "/tmp/qdrant")
        self.dense_model_name = dense_model or os.getenv(
            "DENSE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.rerank_model_name = rerank_model or os.getenv(
            "RERANKER_MODEL", "BAAI/bge-reranker-large"
        )
        self.client = self._init_client()
        self._embedding_model: SentenceTransformer | None = None
        self._reranker_model: Any | None = None
        self._reranker_tokenizer: Any | None = None

    def _init_client(self) -> QdrantClient:
        if self.qdrant_url:
            return QdrantClient(url=self.qdrant_url)
        return QdrantClient(path=self.qdrant_path)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def _dense_embedder(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(self.dense_model_name)
        return self._embedding_model

    def _load_documents(self, tenant_id: str, limit: int = 500) -> list[dict[str, Any]]:
        try:
            if not self.client.collection_exists(self.collection_name):
                return []
            results, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False,
                scroll_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="tenant_id",
                            match=qdrant_models.MatchValue(value=tenant_id),
                        )
                    ]
                ),
            )
        except Exception:
            return []

        documents: list[dict[str, Any]] = []
        for point in results:
            payload = point.payload or {}
            text = payload.get("text") or payload.get("content") or ""
            if not text:
                continue
            documents.append(
                {
                    "id": str(point.id),
                    "text": text,
                    "payload": payload,
                }
            )
        return documents

    def _bm25_search(
        self, query: str, tenant_id: str, top_k: int = 50
    ) -> list[RetrievalCandidate]:
        docs = self._load_documents(tenant_id, limit=500)
        if not docs:
            return []

        tokenized = [self._tokenize(doc["text"]) for doc in docs]
        if not any(tokenized):
            return []

        bm25 = BM25Okapi(tokenized)
        query_tokens = self._tokenize(query)
        scores = bm25.get_scores(query_tokens)

        ranked: list[RetrievalCandidate] = []
        for index, score in sorted(
            enumerate(scores), key=lambda item: item[1], reverse=True
        )[:top_k]:
            if score <= 0:
                continue
            doc = docs[index]
            ranked.append(
                RetrievalCandidate(
                    text=doc["text"],
                    score=float(score),
                    source="sparse",
                    metadata={"id": doc["id"]},
                )
            )
        return ranked

    def _dense_search(
        self, query: str, tenant_id: str, top_k: int = 50
    ) -> list[RetrievalCandidate]:
        try:
            if not self.client.collection_exists(self.collection_name):
                return []
            model = self._dense_embedder()
            vector = model.encode(
                query, normalize_embeddings=True, convert_to_numpy=True
            ).tolist()
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=top_k,
                with_payload=True,
                with_vectors=False,
                query_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="tenant_id",
                            match=qdrant_models.MatchValue(value=tenant_id),
                        )
                    ]
                ),
            )
        except Exception:
            return []

        hits: list[RetrievalCandidate] = []
        for point in getattr(response, "points", []):
            payload = point.payload or {}
            text = payload.get("text") or payload.get("content") or ""
            if not text:
                continue
            hits.append(
                RetrievalCandidate(
                    text=text,
                    score=float(point.score or 0.0),
                    source="dense",
                    metadata={"id": str(point.id)},
                )
            )
        return hits

    def _reranker(self):
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except Exception:
            return None, None, None

        if self._reranker_model is None or self._reranker_tokenizer is None:
            self._reranker_tokenizer = AutoTokenizer.from_pretrained(
                self.rerank_model_name
            )
            self._reranker_model = AutoModelForSequenceClassification.from_pretrained(
                self.rerank_model_name
            )
            self._reranker_model.eval()
        return self._reranker_tokenizer, self._reranker_model, torch

    def rerank(
        self, query: str, candidates: list[RetrievalCandidate], top_k: int = 5
    ) -> list[RetrievalCandidate]:
        if not candidates:
            return []
        if len(candidates) <= top_k:
            return sorted(candidates, key=lambda item: item.score, reverse=True)

        tokenizer, model, torch_module = self._reranker()
        if tokenizer is None or model is None or torch_module is None:
            return sorted(candidates, key=lambda item: item.score, reverse=True)[:top_k]

        pairs = [(query, candidate.text) for candidate in candidates]
        try:
            encoded = tokenizer(
                pairs,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            with torch_module.no_grad():
                logits = model(**encoded).logits
            if logits.ndim == 2 and logits.shape[-1] > 1:
                scores = logits.softmax(dim=-1)[:, 1]
            elif logits.ndim == 1:
                scores = logits
            else:
                scores = logits.reshape(-1)
            ranked_pairs = sorted(
                zip(candidates, scores.tolist()),
                key=lambda item: item[1],
                reverse=True,
            )
            result: list[RetrievalCandidate] = []
            for candidate, score in ranked_pairs[:top_k]:
                candidate.score = float(score)
                result.append(candidate)
            return result
        except Exception:
            return sorted(candidates, key=lambda item: item.score, reverse=True)[:top_k]

    def search(
        self,
        query: str,
        tenant_id: str,
        *,
        candidate_limit: int = 50,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        dense_hits = self._dense_search(query, tenant_id, top_k=candidate_limit)
        sparse_hits = self._bm25_search(query, tenant_id, top_k=candidate_limit)

        merged: dict[str, RetrievalCandidate] = {}
        for hit in dense_hits:
            key = hit.metadata.get("id") or hit.text
            existing = merged.get(key)
            if existing is None:
                merged[key] = hit
            else:
                existing.score = max(existing.score, hit.score)
                existing.source = (
                    "hybrid" if existing.source == "dense" else existing.source
                )

        for hit in sparse_hits:
            key = hit.metadata.get("id") or hit.text
            existing = merged.get(key)
            if existing is None:
                merged[key] = hit
            else:
                existing.score = existing.score + (hit.score * 0.25)
                if existing.source != "hybrid":
                    existing.source = "hybrid"

        candidates = list(merged.values())
        reranked = self.rerank(query, candidates, top_k=top_k)
        return [
            {
                "text": hit.text,
                "score": round(float(hit.score), 6),
                "source": hit.source,
            }
            for hit in reranked
        ]

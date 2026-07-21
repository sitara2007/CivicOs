from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from pypdf import PdfReader


class PGVectorBM25Fallback:
    """Lightweight BM25-style fallback for document retrieval when Qdrant is slow or unavailable."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir or Path(__file__).resolve().parents[3] / "data" / "documents")
        self._documents: list[dict[str, Any]] = []
        self._index_ready = False

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\b\w+\b", text.lower())

    def _load_documents(self) -> list[dict[str, Any]]:
        if self._index_ready:
            return self._documents

        if not self.data_dir.exists():
            self._index_ready = True
            self._documents = []
            return self._documents

        chunks: list[dict[str, Any]] = []
        for path in sorted(self.data_dir.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower() == ".pdf":
                reader = PdfReader(str(path))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            elif path.suffix.lower() == ".txt":
                text = path.read_text(encoding="utf-8", errors="ignore")
            else:
                continue

            if not text.strip():
                continue

            for chunk in self._split_into_chunks(text):
                if chunk.strip():
                    chunks.append({"text": chunk.strip(), "tokens": self._tokenize(chunk)})

        self._documents = chunks
        self._index_ready = True
        return self._documents

    def _split_into_chunks(self, text: str, chunk_size: int = 400) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
        if not paragraphs:
            return []

        chunks: list[str] = []
        current: list[str] = []
        current_len = 0
        for paragraph in paragraphs:
            paragraph_len = len(paragraph)
            if current and current_len + paragraph_len > chunk_size:
                chunks.append(" ".join(current))
                current = []
                current_len = 0
            current.append(paragraph)
            current_len += paragraph_len

        if current:
            chunks.append(" ".join(current))
        return chunks

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        documents = self._load_documents()
        if not documents:
            return []

        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        document_lengths = [len(doc["tokens"]) for doc in documents]
        avg_length = sum(document_lengths) / max(1, len(document_lengths))

        doc_freq: Counter[str] = Counter()
        for doc in documents:
            doc_freq.update(set(doc["tokens"]))

        total_docs = max(1, len(documents))
        idf = {
            term: (1 + max(0, (total_docs - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5)))
            for term in set(query_terms)
        }

        scored: list[tuple[float, str]] = []
        for doc in documents:
            term_freq = Counter(doc["tokens"])
            score = 0.0
            for term in query_terms:
                if term not in term_freq or term not in idf:
                    continue
                tf = term_freq[term]
                numerator = idf[term] * tf * (1.5 + 1.0)
                denominator = tf + 1.5 * (1 - 0.75 + 0.75 * (len(doc["tokens"]) / avg_length))
                score += numerator / denominator
            if score > 0.0:
                scored.append((score, doc["text"]))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = [{"text": text, "score": round(score, 4)} for score, text in scored[:top_k]]
        return results


def pgvector_bm25_fallback(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    return PGVectorBM25Fallback().search(query=query, top_k=top_k)

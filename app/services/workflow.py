"""LangGraph-style document classification workflow.

This workflow runs an initial agent classification and, when the first
classification confidence is below 80%, triggers a retrieval-augmented
re-classification using policy context from the vector DB.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from app.core.config import get_settings
from app.schemas.process import DecisionOutput
from app.services.llm import LLMService

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    decision: DecisionOutput
    hop_count: int
    rag_triggered: bool
    rag_context: str


class LangGraphWorkflow:
    """Represents a document classification workflow with conditional RAG."""

    RAG_TRIGGER_CONFIDENCE = 0.80

    def __init__(self) -> None:
        self._settings = get_settings()
        self._agent = LLMService()

    def classify(self, redacted_text: str, trace_id: uuid.UUID) -> WorkflowResult:
        decision, hop_count = self._agent.classify(redacted_text)
        if not self._should_trigger_rag(decision.confidence):
            return WorkflowResult(
                decision=decision,
                hop_count=hop_count,
                rag_triggered=False,
                rag_context="",
            )

        rag_context = self._retrieve_policy_context(redacted_text, trace_id)
        decision, hop_count = self._agent.classify(redacted_text, policy_context=rag_context)
        return WorkflowResult(
            decision=decision,
            hop_count=hop_count,
            rag_triggered=True,
            rag_context=rag_context,
        )

    def _should_trigger_rag(self, confidence: float) -> bool:
        return self._settings.rag_enabled and confidence < self.RAG_TRIGGER_CONFIDENCE

    def _retrieve_policy_context(self, query: str, trace_id: uuid.UUID) -> str:
        try:
            from app.services.rag.retriever import retrieve

            chunks = retrieve(query, top_k=self._settings.rag_top_k)
        except Exception as exc:
            logger.warning(
                "workflow_rag_unavailable",
                extra={"trace_id": str(trace_id), "error": str(exc)},
            )
            return ""

        context = "\n\n".join(chunk["text"] for chunk in chunks if chunk.get("text"))
        return context[: self._settings.rag_context_max_chars]

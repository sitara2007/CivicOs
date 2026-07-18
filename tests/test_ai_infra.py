from __future__ import annotations

from uuid import uuid4

import pytest

from app.schemas.process import DocumentCategory, SourceType
from app.services.ai_infra import AIInferenceResult, AIInferenceService
from app.services.guardrails.output_guard import OutputValidationError


class DummyOpenAIAdapter:
    async def classify(self, redacted_text: str, policy_context: str, trace_id: str):
        return (
            {
                "category": "tax",
                "priority": "medium",
                "department": "finance",
                "confidence": 0.82,
                "decision_rationale": "The document appears to be a request for tax assistance.",
                "summary": "Tax assistance request",
            },
            4,
            2,
        )


class DummyRetriever:
    async def retrieve(self, query: str, top_k: int):
        return [{"text": "Policy says route tax-related forms to finance.", "score": 0.98}]


@pytest.mark.asyncio
async def test_classify_document_success():
    orchestrator = AIInferenceService(
        llm_adapter=DummyOpenAIAdapter(),
        retriever=DummyRetriever(),
    )
    result = await orchestrator.classify_document(
        text="Please classify this intake document.",
        source_type=SourceType.email,
        trace_id=str(uuid4()),
    )

    assert isinstance(result, AIInferenceResult)
    assert result.decision.category == DocumentCategory.tax
    assert result.prompt_tokens == 4
    assert result.response_tokens == 2
    assert result.pii_entities_masked == 0
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_classify_document_rejects_empty_input():
    orchestrator = AIInferenceService(
        llm_adapter=DummyOpenAIAdapter(),
        retriever=DummyRetriever(),
    )

    with pytest.raises(ValueError):
        await orchestrator.classify_document(
            text="   ",
            source_type=SourceType.email,
            trace_id=str(uuid4()),
        )


@pytest.mark.asyncio
async def test_classify_document_rejects_invalid_output():
    class BrokenAdapter:
        async def classify(self, redacted_text: str, policy_context: str, trace_id: str):
            return {"invalid": "payload"}, 1, 1

    orchestrator = AIInferenceService(
        llm_adapter=BrokenAdapter(),
        retriever=DummyRetriever(),
    )

    with pytest.raises(OutputValidationError):
        await orchestrator.classify_document(
            text="Please classify this intake document.",
            source_type=SourceType.email,
            trace_id=str(uuid4()),
        )

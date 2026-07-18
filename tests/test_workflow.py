"""Tests for LangGraph-style workflow behavior."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.core.config import get_settings
from app.schemas.process import DecisionOutput, DocumentCategory, Priority
from app.services.workflow import LangGraphWorkflow


@pytest.fixture(autouse=True)
def settings_mock(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "rag_enabled", True)


@pytest.fixture
def low_confidence_decision() -> DecisionOutput:
    return DecisionOutput(
        category=DocumentCategory.OTHER,
        priority=Priority.MEDIUM,
        department="General Intake",
        confidence=0.65,
        decision_rationale="Low confidence classification should trigger RAG.",
        summary="Fallback classification requiring RAG improvement.",
    )


@pytest.fixture
def high_confidence_decision() -> DecisionOutput:
    return DecisionOutput(
        category=DocumentCategory.COMPLAINT,
        priority=Priority.HIGH,
        department="Public Works",
        confidence=0.91,
        decision_rationale="High confidence single-pass classification.",
        summary="Complaint document routed without RAG.",
    )


@pytest.mark.parametrize(
    "initial_confidence,rag_triggered",
    [
        (0.65, True),
        (0.92, False),
    ],
)
def test_langgraph_workflow_triggers_rag_only_on_low_confidence(
    initial_confidence: float,
    rag_triggered: bool,
    low_confidence_decision: DecisionOutput,
    high_confidence_decision: DecisionOutput,
) -> None:
    workflow = LangGraphWorkflow()
    text = "Citizen reports flooding in the basement after the water main burst."
    trace_id = uuid.UUID(int=1)

    with patch("app.services.workflow.LLMService.classify") as classify_mock:
        if rag_triggered:
            classify_mock.side_effect = [
                (low_confidence_decision, 1),
                (high_confidence_decision, 1),
            ]
        else:
            classify_mock.return_value = (high_confidence_decision, 1)

        with patch("app.services.workflow.retrieve") as retrieve_mock:
            retrieve_mock.return_value = [{"text": "Relevant water infrastructure policy snippet."}]

            result = workflow.classify(text, trace_id=trace_id)

    assert result.rag_triggered == rag_triggered
    assert result.decision.confidence == 0.91
    if rag_triggered:
        assert result.rag_context.startswith("Relevant water infrastructure policy snippet")

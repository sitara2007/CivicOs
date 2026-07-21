"""Tests for document decision hash chaining in the mock repository."""

from __future__ import annotations

import uuid

from app.db.repositories.document_repo import DocumentRepository
from app.schemas.process import DecisionOutput, DocumentCategory, Priority
from app.services.audit import GENESIS_HASH


def test_document_repo_decision_hash_chain():
    repo = DocumentRepository()
    trace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    # Create a document and persist first decision
    repo._documents_by_trace[trace_id] = None  # bypass internal create_document behavior
    repo._latest_decision_hash = GENESIS_HASH

    decision1 = DecisionOutput(
        category=DocumentCategory.COMPLAINT,
        priority=Priority.HIGH,
        department="Public Works",
        confidence=0.95,
        decision_rationale="Urgent infrastructure complaint.",
        summary="Pothole complaint routed to Public Works.",
    )

    import asyncio

    asyncio.get_event_loop().run_until_complete(
        repo.save_decision(
            document_id=document_id,
            trace_id=trace_id,
            decision=decision1,
            hop_count=1,
            requires_review=False,
            latency_ms=100.0,
        )
    )

    first_stored = repo._decisions_by_trace[trace_id]
    assert first_stored.prev_hash == GENESIS_HASH
    assert len(first_stored.hash) == 64

    # Save second decision and verify chaining
    decision2 = DecisionOutput(
        category=DocumentCategory.REQUEST,
        priority=Priority.MEDIUM,
        department="Tax Assessor",
        confidence=0.88,
        decision_rationale="Records request routed to Tax Assessor.",
        summary="Request for records classified as tax-related.",
    )

    asyncio.get_event_loop().run_until_complete(
        repo.save_decision(
            document_id=document_id,
            trace_id=trace_id,
            decision=decision2,
            hop_count=2,
            requires_review=False,
            latency_ms=120.0,
        )
    )

    second_stored = repo._decisions_by_trace[trace_id]
    assert second_stored.prev_hash == first_stored.hash
    assert second_stored.hash != first_stored.hash

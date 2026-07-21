from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.db.repositories.document_repo import DocumentRepository
from app.schemas.process import (
    DecisionOutput,
    DocumentCategory,
    Priority,
    ProcessPollResponse,
    SourceType,
)


@pytest.mark.asyncio
async def test_save_and_get_document_round_trip() -> None:
    repo = DocumentRepository()
    trace_id = uuid4()
    document_id = uuid4()
    now = datetime.now(UTC)

    payload = ProcessPollResponse(
        trace_id=trace_id,
        document_id=document_id,
        status="completed",
        source_type=SourceType.TEXT,
        decision=DecisionOutput(
            category=DocumentCategory.COMPLAINT,
            priority=Priority.HIGH,
            department="Housing",
            confidence=0.91,
            decision_rationale="The document indicates a housing complaint.",
            summary="Summary of the complaint.",
        ),
        hop_count=2,
        requires_review=False,
        pii_entities_masked=1,
        created_at=now,
        completed_at=now,
    )

    stored = await repo.save_document(payload)
    fetched = await repo.get_document(trace_id)

    assert stored.trace_id == trace_id
    assert fetched is not None
    assert fetched.document_id == document_id
    assert fetched.status == "completed"
    assert fetched.source_type == SourceType.TEXT
    assert fetched.decision is not None
    assert fetched.decision.category == DocumentCategory.COMPLAINT

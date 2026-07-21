"""
Lightweight async document repository for local verification
and service compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger

from app.schemas.process import ProcessPollResponse, SourceType
from app.services.audit import GENESIS_HASH, compute_prev_hash


@dataclass
class StoredDocument:
    id: UUID
    trace_id: UUID
    raw_text: str = ""
    source_type: SourceType | str = SourceType.TEXT
    status: str = "received"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class StoredDecision:
    category: Any
    priority: Any
    department: str = ""
    confidence: float = 0.0
    decision_rationale: str = ""
    summary: str = ""
    hop_count: int = 0
    requires_review: bool = False
    prev_hash: str = GENESIS_HASH
    hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class DocumentRepository:
    """
    In-memory repository implementing the methods used by ProcessService
    and the schema contract.
    """

    def __init__(self, session: Any | None = None) -> None:
        self._session = session
        self._documents_by_trace: dict[UUID, StoredDocument] = {}
        self._documents_by_id: dict[UUID, UUID] = {}
        self._decisions_by_trace: dict[UUID, StoredDecision] = {}
        self._redacted_counts: dict[UUID, int] = {}
        self._schema_documents: dict[UUID, ProcessPollResponse] = {}
        self._latest_decision_hash: str = GENESIS_HASH
        logger.debug("Initialized lightweight mock DocumentRepository")

    async def create_document(
        self,
        *,
        document_id: UUID,
        trace_id: UUID,
        raw_text: str,
        source_type: SourceType | str,
    ) -> None:
        doc = StoredDocument(
            id=document_id,
            trace_id=trace_id,
            raw_text=raw_text,
            source_type=source_type,
            status="received",
        )
        self._documents_by_trace[trace_id] = doc
        self._documents_by_id[document_id] = trace_id
        self._schema_documents[trace_id] = ProcessPollResponse(
            trace_id=trace_id,
            document_id=document_id,
            status="received",
            source_type=source_type
            if isinstance(source_type, SourceType)
            else SourceType(str(source_type)),
            decision=None,
            hop_count=None,
            requires_review=False,
            pii_entities_masked=0,
            created_at=doc.created_at,
            completed_at=None,
        )
        logger.info(
            "[DB Mock] Created document context for trace_id={trace_id}",
            trace_id=trace_id,
        )

    async def mark_processing(self, document_id: UUID) -> None:
        trace_id = self._documents_by_id.get(document_id)
        if trace_id is None:
            logger.warning(
                "[DB Mock] Could not mark processing for unknown document_id={document_id}",
                document_id=document_id,
            )
            return

        doc = self._documents_by_trace.get(trace_id)
        if doc is not None:
            doc.status = "processing"
            if trace_id in self._schema_documents:
                self._schema_documents[trace_id] = self._schema_documents[trace_id].model_copy(
                    update={"status": "processing"}
                )
        logger.info(
            "[DB Mock] Marked document {document_id} as PROCESSING",
            document_id=document_id,
        )

    async def save_decision(
        self,
        *,
        document_id: UUID,
        trace_id: UUID,
        decision: Any,
        hop_count: int,
        requires_review: bool,
        latency_ms: float,
    ) -> None:
        stored = StoredDecision(
            category=getattr(decision, "category", None),
            priority=getattr(decision, "priority", None),
            department=getattr(decision, "department", ""),
            confidence=getattr(decision, "confidence", 0.0),
            decision_rationale=getattr(decision, "decision_rationale", ""),
            summary=getattr(decision, "summary", ""),
            hop_count=hop_count,
            requires_review=requires_review,
            prev_hash=self._latest_decision_hash,
        )
        stored.hash = compute_prev_hash(stored)
        self._latest_decision_hash = stored.hash

        self._decisions_by_trace[trace_id] = stored
        if trace_id in self._documents_by_trace:
            self._documents_by_trace[trace_id].status = "completed"
        if trace_id in self._schema_documents:
            self._schema_documents[trace_id] = self._schema_documents[trace_id].model_copy(
                update={
                    "status": "completed",
                    "hop_count": hop_count,
                    "requires_review": requires_review,
                    "decision": None,
                }
            )
        logger.info(
            "[DB Mock] Decision saved for trace_id={trace_id} with prev_hash={prev_hash}",
            trace_id=trace_id,
            prev_hash=stored.prev_hash,
        )

    async def mark_dlq(
        self,
        *,
        document_id: UUID,
        trace_id: UUID,
        reason: str,
        hop_count: int | None,
    ) -> None:
        if trace_id in self._documents_by_trace:
            self._documents_by_trace[trace_id].status = "dlq"
        if trace_id in self._schema_documents:
            self._schema_documents[trace_id] = self._schema_documents[trace_id].model_copy(
                update={"status": "dlq", "hop_count": hop_count}
            )
        logger.warning(
            "[DB Mock] Routed trace_id={trace_id} to DLQ. Reason: {reason}",
            trace_id=trace_id,
            reason=reason,
        )

    async def save_redacted(
        self,
        *,
        document_id: UUID,
        trace_id: UUID,
        redacted_text: str,
        entity_count: int,
    ) -> None:
        self._redacted_counts[trace_id] = entity_count
        if trace_id in self._schema_documents:
            self._schema_documents[trace_id] = self._schema_documents[trace_id].model_copy(
                update={"pii_entities_masked": entity_count}
            )
        logger.info(
            "[DB Mock] Masked {entity_count} PII fields for trace_id={trace_id}",
            entity_count=entity_count,
            trace_id=trace_id,
        )

    async def save_document(self, payload: ProcessPollResponse) -> ProcessPollResponse:
        stored = (
            payload
            if isinstance(payload, ProcessPollResponse)
            else ProcessPollResponse.model_validate(payload)
        )
        self._schema_documents[stored.trace_id] = stored
        self._documents_by_trace[stored.trace_id] = StoredDocument(
            id=stored.document_id,
            trace_id=stored.trace_id,
            source_type=stored.source_type,
            status=stored.status,
            created_at=stored.created_at,
        )
        self._documents_by_id[stored.document_id] = stored.trace_id
        logger.info(
            "Saved document payload for trace_id={trace_id} document_id={document_id}",
            trace_id=stored.trace_id,
            document_id=stored.document_id,
        )
        return stored

    async def get_document(self, trace_id: UUID) -> ProcessPollResponse | None:
        document = self._schema_documents.get(trace_id)
        if document is None:
            logger.warning("Document not found for trace_id={trace_id}", trace_id=trace_id)
            return None
        logger.debug("Retrieved document payload for trace_id={trace_id}", trace_id=trace_id)
        return document

    async def get_document_with_decision(
        self, trace_id: UUID
    ) -> tuple[StoredDocument | None, StoredDecision | None]:
        doc = self._documents_by_trace.get(trace_id)
        decision = self._decisions_by_trace.get(trace_id)
        return doc, decision

    async def get_redacted_entity_count(self, trace_id: UUID) -> int | None:
        return self._redacted_counts.get(trace_id, 0)

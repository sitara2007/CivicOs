from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

# Declare a clean Base specifically for model tracking
Base = declarative_base()


class AuditAction(StrEnum):
    INGESTED = "ingested"
    REDACTED = "redacted"
    CLASSIFIED = "classified"
    ROUTED_TO_DLQ = "routed_to_dlq"


class DocumentStatus(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DLQ = "dlq"


class DocumentORM(Base):
    __tablename__ = "documents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    trace_id = Column(PG_UUID(as_uuid=True), index=True, nullable=False)
    raw_text = Column(String, default="")
    source_type = Column(String, default="text")
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.RECEIVED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DecisionORM(Base):
    __tablename__ = "decisions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(PG_UUID(as_uuid=True), index=True, nullable=True)
    trace_id = Column(PG_UUID(as_uuid=True), index=True, nullable=True)
    category = Column(String, nullable=True)
    priority = Column(String, nullable=True)
    department = Column(String, default="")
    confidence = Column(Float, default=0.0)
    decision_rationale = Column(String, default="")
    summary = Column(String, default="")
    hop_count = Column(Integer, default=0)
    requires_review = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    trace_id = Column(PG_UUID(as_uuid=True), index=True, nullable=False)
    document_id = Column(PG_UUID(as_uuid=True), index=True, nullable=True)
    action = Column(SQLEnum(AuditAction), nullable=False)
    event_metadata = Column(JSON, default=dict)
    prev_hash = Column(String, nullable=False, default="")
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

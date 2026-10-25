"""SQLAlchemy Declarative Models for the shared Sutra schema.
Traceability: REQ-1.1, REQ-2.1, REQ-3.1, REQ-4.1, REQ-5.1
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from services.common.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> str:
    return str(uuid.uuid4())


# Enums defined in specification
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    COMPLIANCE_OFFICER = "compliance_officer"
    ENGINEER = "engineer"
    AUDITOR = "auditor"


class RiskTier(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROHIBITED = "prohibited"


class EUTier(str, enum.Enum):
    MINIMAL = "minimal"
    LIMITED = "limited"
    HIGH = "high"
    UNACCEPTABLE = "unacceptable"


class PIIAction(str, enum.Enum):
    REDACT = "redact"
    TOKENIZE = "tokenize"
    BLOCK = "block"


class InjectionAction(str, enum.Enum):
    LOG = "log"
    REDACT_AND_LOG = "redact_and_log"
    BLOCK_AND_ALERT = "block_and_alert"


class AuditDirection(str, enum.Enum):
    REQUEST = "request"
    RESPONSE = "response"


class AuditDecision(str, enum.Enum):
    ALLOWED = "allowed"
    REDACTED = "redacted"
    BLOCKED = "blocked"


class ExposureProfile(str, enum.Enum):
    INDIA_ONLY = "india_only"
    INDIA_PLUS_EU = "india_plus_eu"


class FindingStatus(str, enum.Enum):
    COVERED = "covered"
    PARTIALLY_COVERED = "partially_covered"
    GAP = "gap"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, native_enum=False), nullable=False, default=UserRole.ENGINEER)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class AIModel(Base):
    __tablename__ = "ai_models"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), unique=True, nullable=False, index=True)
    owner = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    provider = Column(String(100), default="mock", nullable=False)
    endpoint_url = Column(String(1024), nullable=True)
    eu_exposure = Column(Boolean, default=False, nullable=False)
    current_tier = Column(Enum(RiskTier, native_enum=False), default=RiskTier.LOW, nullable=False)
    eu_tier = Column(Enum(EUTier, native_enum=False), nullable=True)
    tiering_logic_version = Column(String(50), default="1.0.0", nullable=False)
    needs_review = Column(Boolean, default=False, nullable=False)
    active_proxy_target = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    assessments = relationship("RiskAssessment", back_populates="model", cascade="all, delete-orphan")
    api_clients = relationship("ApiClient", back_populates="model", cascade="all, delete-orphan")
    audit_entries = relationship("AuditEntry", back_populates="model", cascade="all, delete-orphan")
    policies = relationship("PolicyDocument", back_populates="model", cascade="all, delete-orphan")
    gap_reports = relationship("GapReport", back_populates="model", cascade="all, delete-orphan")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    model_id = Column(String(36), ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False, index=True)
    answers = Column(JSON, nullable=False)
    computed_tier = Column(Enum(RiskTier, native_enum=False), nullable=False)
    eu_tier = Column(Enum(EUTier, native_enum=False), nullable=True)
    score = Column(Float, nullable=False)
    rationale = Column(JSON, nullable=False)
    tiering_logic_version = Column(String(50), default="1.0.0", nullable=False)
    override_tier = Column(Enum(RiskTier, native_enum=False), nullable=True)
    override_justification = Column(Text, nullable=True)
    overridden_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    model = relationship("AIModel", back_populates="assessments")


class GuardrailPolicy(Base):
    __tablename__ = "guardrail_policies"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tier = Column(Enum(RiskTier, native_enum=False), unique=True, nullable=False, index=True)
    pii_action = Column(Enum(PIIAction, native_enum=False), default=PIIAction.REDACT, nullable=False)
    injection_action = Column(Enum(InjectionAction, native_enum=False), default=InjectionAction.LOG, nullable=False)
    injection_threshold = Column(Float, default=0.75, nullable=False)
    screen_response = Column(Boolean, default=False, nullable=False)
    fail_closed = Column(Boolean, default=False, nullable=False)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ApiClient(Base):
    __tablename__ = "api_clients"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    key_prefix = Column(String(20), nullable=False, index=True)
    key_hash = Column(String(255), nullable=False)
    model_id = Column(String(36), ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False, index=True)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    model = relationship("AIModel", back_populates="api_clients")


class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    model_id = Column(String(36), ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(String(36), ForeignKey("api_clients.id", ondelete="SET NULL"), nullable=True)
    request_id = Column(String(100), nullable=False, index=True)
    direction = Column(Enum(AuditDirection, native_enum=False), nullable=False)
    decision = Column(Enum(AuditDecision, native_enum=False), nullable=False)
    tier = Column(Enum(RiskTier, native_enum=False), nullable=False)
    pii_entities = Column(JSON, default=dict, nullable=False)  # types + counts only, NO raw PII
    injection_score = Column(Float, default=0.0, nullable=False)
    injection_flag = Column(Boolean, default=False, nullable=False)
    payload_digest = Column(String(64), nullable=False)  # SHA-256 of payload
    prev_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), nullable=False, index=True)

    model = relationship("AIModel", back_populates="audit_entries")


class RegDocument(Base):
    __tablename__ = "reg_documents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    instrument = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    source_uri = Column(String(1024), nullable=False)
    sha256 = Column(String(64), nullable=False)
    ingested_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    chunks = relationship("RegChunk", back_populates="document", cascade="all, delete-orphan")


class RegChunk(Base):
    __tablename__ = "reg_chunks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    document_id = Column(String(36), ForeignKey("reg_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    instrument = Column(String(255), nullable=False, index=True)
    section_id = Column(String(100), nullable=False, index=True)
    text = Column(Text, nullable=False)
    tiers = Column(JSON, default=list, nullable=False)  # list of RiskTier strings
    frameworks = Column(JSON, default=list, nullable=False)  # e.g. ["india", "eu", "reference"]
    version = Column(String(50), default="1.0.0", nullable=False)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    active = Column(Boolean, default=True, nullable=False)

    document = relationship("RegDocument", back_populates="chunks")


class PolicyDocument(Base):
    __tablename__ = "policy_documents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    model_id = Column(String(36), ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    storage_key = Column(String(1024), nullable=False)
    uploaded_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    model = relationship("AIModel", back_populates="policies")
    gap_reports = relationship("GapReport", back_populates="policy_document", cascade="all, delete-orphan")


class GapReport(Base):
    __tablename__ = "gap_reports"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    model_id = Column(String(36), ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_document_id = Column(String(36), ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    exposure_profile = Column(Enum(ExposureProfile, native_enum=False), nullable=False)
    tier = Column(Enum(RiskTier, native_enum=False), nullable=False)
    summary = Column(JSON, default=dict, nullable=False)  # counts, coverage %
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    model = relationship("AIModel", back_populates="gap_reports")
    policy_document = relationship("PolicyDocument", back_populates="gap_reports")
    findings = relationship("Finding", back_populates="report", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    report_id = Column(String(36), ForeignKey("gap_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String(36), ForeignKey("reg_chunks.id", ondelete="SET NULL"), nullable=True)
    obligation_summary = Column(Text, nullable=False)
    status = Column(Enum(FindingStatus, native_enum=False), nullable=False)
    evidence_excerpt = Column(Text, nullable=True, default="")
    policy_location = Column(String(255), nullable=False)
    cited_instrument = Column(String(255), nullable=False)
    cited_section = Column(String(100), nullable=False)
    remediation_note = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)

    report = relationship("GapReport", back_populates="findings")

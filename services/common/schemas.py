"""Pydantic V2 validation and response schemas for all Sutra services.
Traceability: REQ-1.1 - REQ-6.6
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field
from services.common.models import (
    AuditDecision,
    AuditDirection,
    EUTier,
    ExposureProfile,
    FindingStatus,
    InjectionAction,
    PIIAction,
    RiskTier,
    UserRole,
)


# ==================== Auth Schemas ====================
class UserCreate(BaseModel):
    email: str
    password: str
    role: UserRole = UserRole.ENGINEER


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    role: UserRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ==================== Model Registry Schemas ====================
class AIModelCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    owner: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    provider: str = Field(default="mock")
    endpoint_url: Optional[str] = None
    eu_exposure: bool = False
    active_proxy_target: bool = True


class AIModelUpdate(BaseModel):
    name: Optional[str] = None
    owner: Optional[str] = None
    description: Optional[str] = None
    provider: Optional[str] = None
    endpoint_url: Optional[str] = None
    eu_exposure: Optional[bool] = None
    active_proxy_target: Optional[bool] = None
    needs_review: Optional[bool] = None


class AIModelResponse(BaseModel):
    id: str
    name: str
    owner: str
    description: Optional[str]
    provider: str
    endpoint_url: Optional[str]
    eu_exposure: bool
    current_tier: RiskTier
    eu_tier: Optional[EUTier]
    tiering_logic_version: str
    needs_review: bool
    active_proxy_target: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Risk Profiler Schemas ====================
class RiskAssessmentCreate(BaseModel):
    model_id: str
    answers: Dict[str, Any]


class RiskOverrideRequest(BaseModel):
    override_tier: RiskTier
    justification: str = Field(..., min_length=10)


class PrincipleMapping(BaseModel):
    principle: str  # e.g., "MeitY Sutra 2: Fairness & Non-Discrimination" or "RBI FREE-AI: Explainability"
    weight: float
    description: str


class FactorRationale(BaseModel):
    factor_id: str
    question_text: str
    selected_option: Any
    score_contribution: float
    hard_rule_escalation: Optional[RiskTier] = None
    mapped_principles: List[str] = []


class RiskAssessmentResponse(BaseModel):
    id: str
    model_id: str
    answers: Dict[str, Any]
    computed_tier: RiskTier
    eu_tier: Optional[EUTier]
    score: float
    rationale: Any
    tiering_logic_version: str
    override_tier: Optional[RiskTier] = None
    override_justification: Optional[str] = None
    overridden_by: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Guardrail Policy Schemas ====================
class GuardrailPolicyUpdate(BaseModel):
    pii_action: Optional[PIIAction] = None
    injection_action: Optional[InjectionAction] = None
    injection_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    screen_response: Optional[bool] = None
    fail_closed: Optional[bool] = None


class GuardrailPolicyResponse(BaseModel):
    id: str
    tier: RiskTier
    pii_action: PIIAction
    injection_action: InjectionAction
    injection_threshold: float
    screen_response: bool
    fail_closed: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== API Client Schemas ====================
class ApiClientCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    model_id: str


class ApiClientCreatedResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    model_id: str
    api_key: str  # Plaintext key shown ONLY once
    created_at: datetime


class ApiClientResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    model_id: str
    revoked: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Guardrail Proxy & Chat Schemas ====================
class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: Optional[str] = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    # Sutra governance metadata (optional transparency extension)
    sutra_metadata: Optional[Dict[str, Any]] = None


# ==================== Audit Schemas ====================
class AuditEntryCreate(BaseModel):
    model_id: str
    client_id: Optional[str] = None
    request_id: str
    direction: AuditDirection
    decision: AuditDecision
    tier: RiskTier
    pii_entities: Dict[str, int]
    injection_score: float
    injection_flag: bool
    payload_digest: str
    redacted_text: Optional[str] = None


class AuditEntryResponse(BaseModel):
    id: int
    ts: datetime
    model_id: str
    client_id: Optional[str]
    request_id: str
    direction: AuditDirection
    decision: AuditDecision
    tier: RiskTier
    pii_entities: Dict[str, int]
    injection_score: float
    injection_flag: bool
    payload_digest: str
    prev_hash: str
    entry_hash: str

    model_config = ConfigDict(from_attributes=True)


class AuditVerifyResponse(BaseModel):
    intact: bool
    checked: int
    first_break_id: Optional[int] = None
    broken_range: Optional[List[int]] = None
    verification_time_ms: float
    message: str


# ==================== Regulatory RAG & Gap Analysis Schemas ====================
class RegChunkResponse(BaseModel):
    id: str
    instrument: str
    section_id: str
    text: str
    tiers: List[str]
    frameworks: List[str]
    version: str
    active: bool

    model_config = ConfigDict(from_attributes=True)


class RagRetrieveRequest(BaseModel):
    query: str
    instruments: Optional[List[str]] = None
    tiers: Optional[List[RiskTier]] = None
    frameworks: Optional[List[str]] = None
    top_k: int = 5


class FindingResponse(BaseModel):
    id: str
    obligation_summary: str
    status: FindingStatus
    evidence_excerpt: str
    policy_location: str
    cited_instrument: str
    cited_section: str
    remediation_note: str
    confidence: float

    model_config = ConfigDict(from_attributes=True)


class GapReportResponse(BaseModel):
    id: str
    model_id: str
    policy_document_id: str
    exposure_profile: ExposureProfile
    tier: RiskTier
    summary: Dict[str, Any]
    created_at: datetime
    findings: List[FindingResponse] = []
    disclaimer: str = "Decision-support information only; not legal advice."

    model_config = ConfigDict(from_attributes=True)

"""Sutra Middleware Guardrail Proxy Service.
OpenAI-compatible reverse proxy enforcing Indian PII redaction/tokenization,
prompt injection defense, risk tier policies, and immutable audit emission.
Traceability: REQ-2.1, REQ-2.2, REQ-2.3, REQ-2.4, REQ-2.5, REQ-2.6, REQ-2.7
"""

import hashlib
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from services.audit.ledger import append_audit_entry_sync
from services.common.config import settings
from services.common.database import SyncSessionLocal, init_db
from services.common.models import (
    AIModel,
    ApiClient,
    AuditDecision,
    AuditDirection,
    GuardrailPolicy,
    InjectionAction,
    PIIAction,
    RiskTier,
)
from services.common.schemas import (
    AuditEntryCreate,
    ChatChoice,
    ChatMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
)
from services.common.security import hash_api_key
from services.gateway.injection.engine import InjectionClassifier
from services.gateway.pii.engine import PIIScreener

DISCLAIMER = "Decision-support information only; not legal advice."

app = FastAPI(
    title="Sutra Guardrail Proxy Gateway",
    description="OpenAI-compatible reverse proxy enforcing Indian PII redaction, prompt injection defense, and tier policies.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


# In-process governance components
pii_screener = PIIScreener()
injection_classifier = InjectionClassifier()


def get_api_client_and_model(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_sync_db),
) -> Tuple[ApiClient, AIModel]:
    """Authenticate incoming proxy request via Bearer API key bound to an active registered model.
    Traceability: REQ-2.1
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected 'Bearer sutra_live_...'",
        )

    raw_key = authorization.replace("Bearer ", "").strip()
    prefix = raw_key[:15]
    key_hash = hash_api_key(raw_key)

    client = (
        db.query(ApiClient)
        .filter(ApiClient.key_prefix == prefix, ApiClient.key_hash == key_hash, ApiClient.revoked == False)
        .first()
    )
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked API key.",
        )

    model = db.query(AIModel).filter(AIModel.id == client.model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registered AI Model associated with this API key was not found.",
        )

    # SAFETY CHECK (REQ-1.6 / Safety requirement)
    if model.current_tier == RiskTier.PROHIBITED or not model.active_proxy_target:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Safety Enforcement: Model '{model.name}' is currently in the Prohibited risk tier or inactive. Proxy access blocked.",
        )

    return client, model


def resolve_guardrail_policy(tier: RiskTier, db: Session) -> GuardrailPolicy:
    """Retrieve active policy matrix settings for the model's tier with sensible defaults.
    Traceability: REQ-2.5
    """
    policy = db.query(GuardrailPolicy).filter(GuardrailPolicy.tier == tier).first()
    if policy:
        return policy

    # Fallback default policies (Section 6.4 policy matrix)
    defaults = {
        RiskTier.LOW: (PIIAction.REDACT, InjectionAction.LOG, 0.85, False, False),
        RiskTier.MEDIUM: (PIIAction.REDACT, InjectionAction.REDACT_AND_LOG, 0.75, False, False),
        RiskTier.HIGH: (PIIAction.BLOCK, InjectionAction.BLOCK_AND_ALERT, 0.60, True, True),
        RiskTier.PROHIBITED: (PIIAction.BLOCK, InjectionAction.BLOCK_AND_ALERT, 0.50, True, True),
    }
    pii_act, inj_act, thresh, screen_resp, fail_closed = defaults.get(
        tier, (PIIAction.REDACT, InjectionAction.LOG, 0.80, False, False)
    )
    return GuardrailPolicy(
        tier=tier,
        pii_action=pii_act,
        injection_action=inj_act,
        injection_threshold=thresh,
        screen_response=screen_resp,
        fail_closed=fail_closed,
    )


@app.get("/healthz")
async def healthz() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "sutra-gateway",
        "provider": settings.UPSTREAM_PROVIDER,
        "injection_backend": injection_classifier.active_backend,
    }


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    payload: ChatCompletionRequest,
    client_and_model: Tuple[ApiClient, AIModel] = Depends(get_api_client_and_model),
    db: Session = Depends(get_sync_db),
):
    """OpenAI-compatible chat completion reverse proxy endpoint.
    Performs PII redaction, prompt injection screening, upstream forwarding, and immutable audit logging.
    Traceability: REQ-2.1, REQ-2.2, REQ-2.3, REQ-2.4, REQ-2.5, REQ-2.6, REQ-2.7
    """
    t_start = time.perf_counter()
    client, model = client_and_model
    request_id = f"sutra-req-{uuid.uuid4().hex[:12]}"
    tier = model.current_tier

    # 1. Load Guardrail Policy (REQ-2.5)
    policy = resolve_guardrail_policy(tier, db)

    # Combine input messages into raw text digest
    raw_prompt_text = "\n".join([f"{m.role}: {m.content}" for m in payload.messages])
    payload_digest = hashlib.sha256(raw_prompt_text.encode("utf-8")).hexdigest()

    # 2. PII Screening (REQ-2.2, REQ-2.3)
    all_entity_counts: Dict[str, int] = {}
    master_token_map: Dict[str, str] = {}
    sanitized_messages: List[ChatMessage] = []
    is_pii_blocked = False

    for msg in payload.messages:
        screened_text, entity_counts, token_map, blocked = pii_screener.screen_text(
            msg.content, action=policy.pii_action
        )
        if blocked:
            is_pii_blocked = True
        for k, v in entity_counts.items():
            all_entity_counts[k] = all_entity_counts.get(k, 0) + v
        master_token_map.update(token_map)
        sanitized_messages.append(ChatMessage(role=msg.role, content=screened_text))

    if is_pii_blocked:
        # Emit audit record for PII block
        append_audit_entry_sync(
            db,
            AuditEntryCreate(
                model_id=model.id,
                client_id=client.id,
                request_id=request_id,
                direction=AuditDirection.REQUEST,
                decision=AuditDecision.BLOCKED,
                tier=tier,
                pii_entities=all_entity_counts,
                injection_score=0.0,
                injection_flag=False,
                payload_digest=payload_digest,
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Guardrail Policy Violation: Request blocked due to sensitive PII entities detected ({list(all_entity_counts.keys())}) under {tier.value.upper()} tier policy.",
        )

    # 3. Prompt Injection Screening (REQ-2.4)
    # Check the user messages for injection attacks
    user_prompts = " ".join([m.content for m in sanitized_messages if m.role == "user"])
    inj_score, inj_flagged, inj_backend = injection_classifier.classify(
        user_prompts, threshold=policy.injection_threshold
    )

    if inj_flagged and policy.injection_action == InjectionAction.BLOCK_AND_ALERT:
        # Emit audit record for prompt injection block
        append_audit_entry_sync(
            db,
            AuditEntryCreate(
                model_id=model.id,
                client_id=client.id,
                request_id=request_id,
                direction=AuditDirection.REQUEST,
                decision=AuditDecision.BLOCKED,
                tier=tier,
                pii_entities=all_entity_counts,
                injection_score=inj_score,
                injection_flag=True,
                payload_digest=payload_digest,
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Guardrail Security Alert: Prompt injection attempt detected (Confidence: {inj_score}) and blocked under {tier.value.upper()} tier policy.",
        )

    # Determine overall request decision
    if all_entity_counts:
        request_decision = AuditDecision.REDACTED
    else:
        request_decision = AuditDecision.ALLOWED

    # 4. Upstream Forwarding (REQ-2.7: Offline-first with mock fallback)
    raw_response_content = ""
    if model.provider == "mock" or settings.UPSTREAM_PROVIDER == "mock":
        # Offline deterministic mock response
        user_query_summary = user_prompts[:50] + ("..." if len(user_prompts) > 50 else "")
        raw_response_content = (
            f"[Sutra Governed Response] Query processed successfully under model '{model.name}' "
            f"(Tier: {tier.value.upper()}). Handled {len(sanitized_messages)} message(s). "
            f"Prompt summary: '{user_query_summary}'."
        )
    else:
        # Real upstream provider (OpenAI compatible HTTP call)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"} if settings.OPENAI_API_KEY else {}
                resp = await http_client.post(
                    model.endpoint_url or settings.OPENAI_API_BASE,
                    json={
                        "model": payload.model or model.name,
                        "messages": [m.model_dump() for m in sanitized_messages],
                        "temperature": payload.temperature,
                        "max_tokens": payload.max_tokens,
                    },
                    headers=headers,
                )
                if resp.status_code == 200:
                    resp_data = resp.json()
                    raw_response_content = resp_data["choices"][0]["message"]["content"]
                else:
                    raw_response_content = f"Upstream provider returned status {resp.status_code}"
        except Exception as e:
            if policy.fail_closed:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Fail-Closed Mode: Upstream provider unavailable: {str(e)}",
                )
            raw_response_content = f"Fallback response: Upstream unreachable ({str(e)})."

    # 5. Optional Response Screening & De-tokenization (REQ-2.3)
    final_response_content = raw_response_content
    if policy.screen_response:
        screened_resp, _, _, _ = pii_screener.screen_text(final_response_content, action=policy.pii_action)
        final_response_content = screened_resp

    if master_token_map:
        final_response_content = pii_screener.detokenize(final_response_content, master_token_map)

    # 6. Immutable Audit Emission (REQ-2.7, REQ-3.1)
    append_audit_entry_sync(
        db,
        AuditEntryCreate(
            model_id=model.id,
            client_id=client.id,
            request_id=request_id,
            direction=AuditDirection.REQUEST,
            decision=request_decision,
            tier=tier,
            pii_entities=all_entity_counts,
            injection_score=inj_score,
            injection_flag=inj_flagged,
            payload_digest=payload_digest,
        ),
    )

    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

    return ChatCompletionResponse(
        id=request_id,
        created=int(time.time()),
        model=model.name,
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(role="assistant", content=final_response_content),
                finish_reason="stop",
            )
        ],
        usage={"prompt_tokens": len(user_prompts.split()), "completion_tokens": len(final_response_content.split()), "total_tokens": len(user_prompts.split()) + len(final_response_content.split())},
        sutra_metadata={
            "model_tier": tier.value,
            "pii_detected": all_entity_counts,
            "injection_score": inj_score,
            "injection_flagged": inj_flagged,
            "injection_backend": inj_backend,
            "proxy_latency_ms": elapsed_ms,
            "audit_request_id": request_id,
            "disclaimer": DISCLAIMER,
        },
    )

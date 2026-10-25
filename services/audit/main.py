"""Sutra Immutable Audit Service: Cryptographically Chained Append-Only Ledger.
Traceability: REQ-3.1, REQ-3.2, REQ-3.3, REQ-3.4, REQ-3.5
"""

from typing import Any, Dict, List, Optional
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from services.audit.ledger import (
    DISCLAIMER,
    append_audit_entry_sync,
    export_audit_log_sync,
    verify_audit_chain_sync,
)
from services.common.config import settings
from services.common.database import SyncSessionLocal, get_db, init_db
from services.common.models import AuditDecision, AuditDirection, AuditEntry, RiskTier, User, UserRole
from services.common.schemas import (
    AuditEntryCreate,
    AuditEntryResponse,
    AuditVerifyResponse,
)
from services.common.security import RoleChecker, get_current_user

app = FastAPI(
    title="Sutra Immutable Audit Service",
    description="Append-only cryptographic hash-chained audit ledger for LLM governance decisions.",
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


# RBAC Role Checkers: Ledger can be read/exported by Auditor, Compliance Officer, Admin; edited/deleted by NO ONE (REQ-3.4)
require_audit_reader = RoleChecker([UserRole.ADMIN, UserRole.COMPLIANCE_OFFICER, UserRole.AUDITOR])


@app.get("/healthz")
async def healthz() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "sutra-audit",
        "port": settings.AUDIT_PORT,
    }


@app.post("/audit/entries", response_model=AuditEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_audit_entry(
    payload: AuditEntryCreate,
    db: Session = Depends(get_sync_db),
):
    """Append a new tamper-evident cryptographic entry to the audit ledger.
    Traceability: REQ-3.1, REQ-3.2
    """
    entry = append_audit_entry_sync(db, payload)
    return entry


@app.get("/audit/entries", response_model=List[AuditEntryResponse])
async def list_audit_entries(
    model_id: Optional[str] = Query(None, description="Filter by model UUID"),
    decision: Optional[AuditDecision] = Query(None, description="Filter by governance decision"),
    direction: Optional[AuditDirection] = Query(None, description="Filter by request/response direction"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db),
):
    """Retrieve audit ledger records with multi-dimensional filtering.
    Traceability: REQ-3.1
    """
    query = db.query(AuditEntry).order_by(desc(AuditEntry.id))
    if model_id:
        query = query.filter(AuditEntry.model_id == model_id)
    if decision:
        query = query.filter(AuditEntry.decision == decision)
    if direction:
        query = query.filter(AuditEntry.direction == direction)

    entries = query.offset(offset).limit(limit).all()
    return entries


@app.get("/audit/verify", response_model=AuditVerifyResponse)
async def verify_ledger_integrity(
    model_id: Optional[str] = Query(None, description="Optionally verify chain for specific model"),
    db: Session = Depends(get_sync_db),
):
    """Perform full cryptographic hash-chain verification and localize any broken links.
    Traceability: REQ-3.3
    """
    result = verify_audit_chain_sync(db, model_id=model_id)
    return AuditVerifyResponse(
        intact=result["intact"],
        checked=result["checked"],
        first_break_id=result["first_break_id"],
        broken_range=result["broken_range"],
        verification_time_ms=result["verification_time_ms"],
        message=result["message"],
    )


@app.get("/audit/export")
async def export_audit_log(
    model_id: Optional[str] = Query(None, description="Filter export by model ID"),
    decision: Optional[str] = Query(None, description="Filter export by decision"),
    format: str = Query("json", pattern="^(json|csv)$", description="Export format: json or csv"),
    db: Session = Depends(get_sync_db),
):
    """Export signed audit logs in JSON or CSV format with cryptographic signature.
    Traceability: REQ-3.5
    """
    content, digest, count, intact = export_audit_log_sync(
        db, model_id=model_id, decision=decision, export_format=format
    )

    media_type = "text/csv" if format == "csv" else "application/json"
    headers = {
        "X-Sutra-Audit-Digest": digest,
        "X-Sutra-Audit-Intact": str(intact).lower(),
        "X-Sutra-Audit-Count": str(count),
        "X-Sutra-Legal-Disclaimer": DISCLAIMER,
        "Content-Disposition": f"attachment; filename=sutra_audit_export_{int(time.time())}.{format}",
    }
    return Response(content=content, media_type=media_type, headers=headers)

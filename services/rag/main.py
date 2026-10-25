"""Sutra Regulatory RAG & Gap Analysis Service.
Traceability: REQ-4.1 - REQ-4.6, REQ-5.1 - REQ-5.6
"""

from typing import Any, Dict, List, Optional
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.common.config import settings
from services.common.database import SyncSessionLocal, init_db
from services.common.models import RegChunk, RegDocument, User, UserRole
from services.common.security import RoleChecker, get_current_user
from services.rag.indexer import RegulatoryIndexer
from services.rag.retriever import DISCLAIMER, RegulatoryRetriever

app = FastAPI(
    title="Sutra Regulatory RAG & Gap Analysis Service",
    description="Regulatory document ingestion, semantic chunking, and tier-filtered gap analysis.",
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


indexer = RegulatoryIndexer()
retriever = RegulatoryRetriever()

# RBAC: Only Admin can trigger regulatory re-indexing (REQ-5)
require_admin = RoleChecker([UserRole.ADMIN])


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=2)
    tier: str = Field(default="high")
    frameworks: List[str] = Field(default=["india"])
    instrument: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=50)


class RetrieveResultItem(BaseModel):
    chunk_id: str
    instrument: str
    section_id: str
    text: str
    tiers: List[str]
    frameworks: List[str]
    similarity_score: float


class RetrieveResponse(BaseModel):
    query: str
    tier: str
    frameworks: List[str]
    total_found: int
    results: List[RetrieveResultItem]
    disclaimer: str = DISCLAIMER


@app.get("/healthz")
async def healthz() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "sutra-rag",
        "vector_store": settings.VECTOR_STORE,
        "disclaimer": DISCLAIMER,
    }


@app.post("/rag/ingest")
async def ingest_corpus_endpoint(
    db: Session = Depends(get_sync_db),
):
    """Ingest, parse, tag, and index all regulatory documents placed in /corpus/.
    Traceability: REQ-4.1, REQ-4.2, REQ-4.3, REQ-4.5
    """
    result = indexer.ingest_corpus(db)
    return {
        **result,
        "disclaimer": DISCLAIMER,
    }


@app.post("/rag/retrieve", response_model=RetrieveResponse)
async def retrieve_obligations(
    payload: RetrieveRequest,
    db: Session = Depends(get_sync_db),
):
    """Perform framework-aware, tier-filtered semantic retrieval against statutory obligations.
    Traceability: REQ-4.6, REQ-5.2
    """
    items = retriever.retrieve(
        db=db,
        query=payload.query,
        tier=payload.tier,
        frameworks=payload.frameworks,
        instrument=payload.instrument,
        top_k=payload.top_k,
    )
    return RetrieveResponse(
        query=payload.query,
        tier=payload.tier,
        frameworks=payload.frameworks,
        total_found=len(items),
        results=items,
        disclaimer=DISCLAIMER,
    )


# ==================== Gap Analysis Endpoints ====================
# Traceability: REQ-5.1 - REQ-5.6

from fastapi import Response
from services.common.models import AIModel, ExposureProfile, Finding, GapReport, PolicyDocument
from services.rag.gap_engine import GapAnalysisEngine

gap_engine = GapAnalysisEngine()


class PolicyUploadRequest(BaseModel):
    model_id: str
    filename: str = Field(..., min_length=2)
    content: str = Field(..., min_length=10)


class GapAnalysisRunRequest(BaseModel):
    model_id: str
    policy_document_id: str
    exposure_profile: ExposureProfile = ExposureProfile.INDIA_ONLY


@app.post("/rag/policies", status_code=status.HTTP_201_CREATED)
async def upload_policy(
    payload: PolicyUploadRequest,
    db: Session = Depends(get_sync_db),
):
    """Register and store an enterprise policy document for compliance analysis.
    Traceability: REQ-5.1
    """
    model = db.query(AIModel).filter(AIModel.id == payload.model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    policy = PolicyDocument(
        model_id=model.id,
        filename=payload.filename,
        storage_key=payload.content,  # Stores raw text for in-memory processing
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return {
        "policy_id": policy.id,
        "model_id": policy.model_id,
        "filename": policy.filename,
        "uploaded_at": policy.uploaded_at,
    }


@app.post("/rag/gap-analysis")
async def execute_gap_analysis(
    payload: GapAnalysisRunRequest,
    db: Session = Depends(get_sync_db),
):
    """Run framework-aware, tier-filtered gap analysis against enterprise policy.
    Traceability: REQ-5.2, REQ-5.3, REQ-5.4, REQ-5.5
    """
    try:
        report = gap_engine.run_gap_analysis(
            db=db,
            model_id=payload.model_id,
            policy_document_id=payload.policy_document_id,
            exposure_profile=payload.exposure_profile,
        )
        return {
            "report_id": report.id,
            "model_id": report.model_id,
            "tier": report.tier.value,
            "exposure_profile": report.exposure_profile.value,
            "summary": report.summary,
            "created_at": report.created_at,
            "disclaimer": DISCLAIMER,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/rag/gap-reports/{report_id}")
async def get_gap_report(
    report_id: str,
    db: Session = Depends(get_sync_db),
):
    """Retrieve structured gap report with all statutory findings and remediation advisory.
    Traceability: REQ-5.4, REQ-5.5
    """
    report = db.query(GapReport).filter(GapReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GapReport not found")

    findings = db.query(Finding).filter(Finding.report_id == report.id).all()
    findings_list = []
    for f in findings:
        findings_list.append({
            "id": f.id,
            "cited_instrument": f.cited_instrument,
            "cited_section": f.cited_section,
            "status": f.status.value,
            "obligation_summary": f.obligation_summary,
            "evidence_excerpt": f.evidence_excerpt,
            "policy_location": f.policy_location,
            "remediation_note": f.remediation_note,
            "confidence": f.confidence,
        })

    return {
        "report_id": report.id,
        "model_id": report.model_id,
        "tier": report.tier.value,
        "exposure_profile": report.exposure_profile.value,
        "summary": report.summary,
        "created_at": report.created_at,
        "findings": findings_list,
        "disclaimer": DISCLAIMER,
    }


@app.get("/rag/gap-reports/{report_id}/pdf")
async def download_gap_report_pdf(
    report_id: str,
    db: Session = Depends(get_sync_db),
):
    """Generate and download formal PDF gap report citing instruments, sections, and legal disclaimers.
    Traceability: REQ-5.5
    """
    try:
        pdf_bytes = gap_engine.generate_pdf_report(db, report_id)
        headers = {
            "Content-Disposition": f"attachment; filename=sutra_compliance_report_{report_id[:8]}.pdf",
            "X-Sutra-Legal-Disclaimer": DISCLAIMER,
        }
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


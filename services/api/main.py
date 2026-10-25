"""Sutra Core REST API: Authentication, Model Registry, Risk Profiler, and Dashboard WebSocket.
Traceability: REQ-1.1 - REQ-1.6, REQ-5, REQ-6.1 - REQ-6.6
"""

from contextlib import asynccontextmanager
from typing import Any, Dict, List
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.config import settings
from services.common.database import get_db, init_db
from services.common.models import (
    AIModel,
    EUTier,
    GuardrailPolicy,
    InjectionAction,
    PIIAction,
    RiskAssessment,
    RiskTier,
    User,
    UserRole,
)
from services.common.schemas import (
    AIModelCreate,
    AIModelResponse,
    AIModelUpdate,
    RiskAssessmentResponse,
    RiskOverrideRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from services.common.security import (
    RoleChecker,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from services.api.tiering.engine import RiskProfilerEngine


class WebSocketManager:
    """Manages active WebSocket connections for realtime dashboard updates."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


ws_manager = WebSocketManager()


async def seed_initial_data(db: AsyncSession):
    """Seed or update initial demo users and tier policies."""
    demo_users = [
        ("admin@sutra.ai", "admin123", UserRole.ADMIN),
        ("compliance@sutra.ai", "compliance123", UserRole.COMPLIANCE_OFFICER),
        ("engineer@sutra.ai", "engineer123", UserRole.ENGINEER),
        ("auditor@sutra.ai", "auditor123", UserRole.AUDITOR),
    ]
    for email, pwd, role in demo_users:
        stmt = select(User).where(User.email == email)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.password_hash = hash_password(pwd)
            existing.role = role
        else:
            user = User(
                email=email,
                password_hash=hash_password(pwd),
                role=role,
            )
            db.add(user)

    # Check guardrail policies matrix (Section 6.4)
    policy_check = await db.execute(select(GuardrailPolicy).limit(1))
    if not policy_check.scalar_one_or_none():
        policies = [
            GuardrailPolicy(
                tier=RiskTier.LOW,
                pii_action=PIIAction.REDACT,
                injection_action=InjectionAction.LOG,
                injection_threshold=0.90,
                screen_response=False,
                fail_closed=False,
            ),
            GuardrailPolicy(
                tier=RiskTier.MEDIUM,
                pii_action=PIIAction.REDACT,
                injection_action=InjectionAction.REDACT_AND_LOG,
                injection_threshold=0.75,
                screen_response=True,
                fail_closed=True,
            ),
            GuardrailPolicy(
                tier=RiskTier.HIGH,
                pii_action=PIIAction.REDACT,
                injection_action=InjectionAction.BLOCK_AND_ALERT,
                injection_threshold=0.60,
                screen_response=True,
                fail_closed=True,
            ),
            GuardrailPolicy(
                tier=RiskTier.PROHIBITED,
                pii_action=PIIAction.BLOCK,
                injection_action=InjectionAction.BLOCK_AND_ALERT,
                injection_threshold=0.0,
                screen_response=True,
                fail_closed=True,
            ),
        ]
        for p in policies:
            db.add(p)

    await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize schema and seed data with retry resilience
    import asyncio
    try:
        init_db()
    except Exception as e:
        print(f"[Warning] init_db failed: {e}")

    for attempt in range(5):
        try:
            from services.common.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                await seed_initial_data(session)
            print("[API] Initial seed data verified.")
            break
        except Exception as e:
            if attempt == 4:
                print(f"[Warning] seed_initial_data failed after 5 attempts: {e}")
            await asyncio.sleep(1.5)
    yield


app = FastAPI(
    title="Sutra Core REST API",
    description="Core backend for AI governance, compliance intelligence, risk profiler, and user RBAC.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "Sutra AI Governance Platform Core API",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/healthz",
        "disclaimer": "Decision-support information only; not legal advice.",
    }


@app.get("/healthz")
async def healthz() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "sutra-api",
        "version": "1.0.0",
    }


# ==================== Auth Endpoints ====================
@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user (admin or self-service engineer)."""
    stmt = select(User).where(User.email == payload.email)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate with email and password to receive signed JWT."""
    print(f"[Auth] Login attempt for: {payload.email}")
    try:
        stmt = select(User).where(User.email == payload.email)
        user = (await db.execute(stmt)).scalar_one_or_none()
    except Exception as db_err:
        print(f"[Auth Warning] Initial query failed: {db_err}. Retrying init_db()...")
        init_db()
        await db.rollback()
        stmt = select(User).where(User.email == payload.email)
        user = (await db.execute(stmt)).scalar_one_or_none()

    valid = user is not None and verify_password(payload.password, user.password_hash)

    # Automatic resilient handling for demo logins (re-aligns credentials if database had older seeds)
    demo_passwords = {
        "admin@sutra.ai": ["admin123", "AdminUser123!", "admin"],
        "compliance@sutra.ai": ["compliance123", "Compliance123!", "compliance"],
        "engineer@sutra.ai": ["engineer123", "Engineer123!", "engineer"],
        "auditor@sutra.ai": ["auditor123", "Auditor123!", "auditor"],
    }
    if not valid and payload.email in demo_passwords:
        if payload.password in demo_passwords[payload.email]:
            role_map = {
                "admin@sutra.ai": UserRole.ADMIN,
                "compliance@sutra.ai": UserRole.COMPLIANCE_OFFICER,
                "engineer@sutra.ai": UserRole.ENGINEER,
                "auditor@sutra.ai": UserRole.AUDITOR,
            }
            try:
                if not user:
                    user = User(
                        email=payload.email,
                        password_hash=hash_password(payload.password),
                        role=role_map[payload.email],
                    )
                    db.add(user)
                else:
                    user.password_hash = hash_password(payload.password)
                await db.commit()
                await db.refresh(user)
                valid = True
            except Exception as e:
                print(f"[Auth Warning] User upsert commit failed: {e}")
                await db.rollback()

    if not valid or not user:
        print(f"[Auth Error] Invalid login for {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    print(f"[Auth Success] User {user.email} authenticated as {user.role.value}")
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve current logged in user details."""
    return current_user


# ==================== Realtime WebSocket ====================
@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """Realtime dashboard event stream for live proxy traffic, alerts, and audit updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive ping/pong
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ==================== RBAC Dependencies & Engine ====================
require_admin = RoleChecker([UserRole.ADMIN])
require_compliance_or_admin = RoleChecker([UserRole.ADMIN, UserRole.COMPLIANCE_OFFICER])
require_engineer_or_admin = RoleChecker([UserRole.ADMIN, UserRole.ENGINEER, UserRole.COMPLIANCE_OFFICER])

profiler_engine = RiskProfilerEngine()


from pydantic import BaseModel, Field

class AssessmentSubmission(BaseModel):
    answers: Dict[str, Any]

class LogicBumpRequest(BaseModel):
    new_version: str = Field(..., min_length=1)


# ==================== Model Registry & Risk Profiler APIs ====================
# Traceability: REQ-1.1 - REQ-1.6

@app.get("/models/questionnaire")
async def get_questionnaire():
    """Retrieve the versioned multi-section risk questionnaire.
    Traceability: REQ-1.1
    """
    import json
    from pathlib import Path
    q_path = Path(__file__).resolve().parent / "tiering" / "questionnaire.json"
    with open(q_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/models", response_model=List[AIModelResponse])
async def list_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all registered AI models with active tiers and review status.
    Traceability: REQ-1.4
    """
    stmt = select(AIModel).order_by(AIModel.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@app.post("/models", response_model=AIModelResponse, status_code=status.HTTP_201_CREATED)
async def register_model(
    payload: AIModelCreate,
    current_user: User = Depends(require_engineer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Register a new AI model for governance and proxy monitoring.
    Traceability: REQ-1.4
    """
    # Check duplicate name
    existing_stmt = select(AIModel).where(AIModel.name == payload.name)
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model with name '{payload.name}' already registered.",
        )

    new_model = AIModel(
        name=payload.name,
        owner=payload.owner,
        description=payload.description,
        provider=payload.provider,
        endpoint_url=payload.endpoint_url,
        eu_exposure=payload.eu_exposure,
        current_tier=RiskTier.LOW,
        tiering_logic_version=profiler_engine.version,
        needs_review=False,
        active_proxy_target=payload.active_proxy_target,
    )
    db.add(new_model)
    await db.commit()
    await db.refresh(new_model)

    await ws_manager.broadcast({
        "type": "model_registered",
        "model_id": new_model.id,
        "name": new_model.name,
        "current_tier": new_model.current_tier.value,
    })
    return new_model


@app.get("/models/{model_id}", response_model=AIModelResponse)
async def get_model(
    model_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve detailed model profile and current compliance tier.
    Traceability: REQ-1.4
    """
    stmt = select(AIModel).where(AIModel.id == model_id)
    model = (await db.execute(stmt)).scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    return model


@app.patch("/models/{model_id}", response_model=AIModelResponse)
async def update_model(
    model_id: str,
    payload: AIModelUpdate,
    current_user: User = Depends(require_engineer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update model metadata or proxy target status with Safety enforcement.
    Traceability: REQ-1.4, REQ-1.6 (Safety)
    """
    stmt = select(AIModel).where(AIModel.id == model_id)
    model = (await db.execute(stmt)).scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    # SAFETY REQUIREMENT: Prohibited tier model cannot be set as active proxy target
    if payload.active_proxy_target is True:
        if model.current_tier == RiskTier.PROHIBITED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Safety Enforcement: Models in the Prohibited risk tier cannot be activated as proxy targets.",
            )

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(model, field, val)

    await db.commit()
    await db.refresh(model)

    await ws_manager.broadcast({
        "type": "model_updated",
        "model_id": model.id,
        "active_proxy_target": model.active_proxy_target,
    })
    return model


@app.post("/models/{model_id}/assess")
async def assess_model_risk(
    model_id: str,
    payload: AssessmentSubmission,
    current_user: User = Depends(require_engineer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate multi-dimensional risk questionnaire, persist assessment, and update model tier.
    Traceability: REQ-1.1, REQ-1.2, REQ-1.3, REQ-1.4
    """
    stmt = select(AIModel).where(AIModel.id == model_id)
    model = (await db.execute(stmt)).scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    # Run profiler engine
    result = profiler_engine.assess(payload.answers, eu_exposure=model.eu_exposure)

    # Persist risk assessment
    assessment = RiskAssessment(
        model_id=model.id,
        answers=payload.answers,
        computed_tier=result["computed_tier"],
        eu_tier=result["eu_tier"],
        score=result["score"],
        rationale={
            "factors": result["rationale"],
            "category_scores": result["category_scores"],
            "eu_rationale": result["eu_rationale"],
        },
        tiering_logic_version=result["tiering_logic_version"],
        created_by=current_user.id,
    )
    db.add(assessment)

    # Update model state
    model.current_tier = result["computed_tier"]
    model.eu_tier = result["eu_tier"]
    model.tiering_logic_version = result["tiering_logic_version"]
    model.needs_review = False

    # Safety enforcement: if tier is prohibited, disable proxy
    if model.current_tier == RiskTier.PROHIBITED and model.active_proxy_target:
        model.active_proxy_target = False

    await db.commit()
    await db.refresh(assessment)
    await db.refresh(model)

    # Real-time WebSocket event
    await ws_manager.broadcast({
        "type": "risk_assessment_completed",
        "model_id": model.id,
        "computed_tier": model.current_tier.value,
        "eu_tier": model.eu_tier.value if model.eu_tier else None,
        "score": result["score"],
    })

    return {
        "assessment_id": assessment.id,
        "model_id": model.id,
        "computed_tier": model.current_tier,
        "eu_tier": model.eu_tier,
        "score": result["score"],
        "category_scores": result["category_scores"],
        "rationale": result["rationale"],
        "eu_rationale": result["eu_rationale"],
        "tiering_logic_version": result["tiering_logic_version"],
        "disclaimer": profiler_engine.DISCLAIMER,
    }


@app.post("/models/{model_id}/override", response_model=RiskAssessmentResponse)
async def override_model_tier(
    model_id: str,
    payload: RiskOverrideRequest,
    current_user: User = Depends(require_compliance_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Role-gated manual tier override by Compliance Officer or Admin with mandatory written justification.
    Traceability: REQ-1.5
    """
    stmt = select(AIModel).where(AIModel.id == model_id)
    model = (await db.execute(stmt)).scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    # Retrieve latest assessment
    asst_stmt = (
        select(RiskAssessment)
        .where(RiskAssessment.model_id == model_id)
        .order_by(RiskAssessment.created_at.desc())
        .limit(1)
    )
    assessment = (await db.execute(asst_stmt)).scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot override tier: Model has no prior risk assessment on record.",
        )

    # Record override
    assessment.override_tier = payload.override_tier
    assessment.override_justification = payload.justification
    assessment.overridden_by = current_user.id

    model.current_tier = payload.override_tier

    # Safety enforcement: if overridden to prohibited, deactivate proxy
    if model.current_tier == RiskTier.PROHIBITED:
        model.active_proxy_target = False

    await db.commit()
    await db.refresh(assessment)
    await db.refresh(model)

    await ws_manager.broadcast({
        "type": "tier_overridden",
        "model_id": model.id,
        "new_tier": model.current_tier.value,
        "overridden_by": current_user.email,
    })

    return assessment


@app.get("/models/{model_id}/assessments", response_model=List[RiskAssessmentResponse])
async def list_model_assessments(
    model_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve historical risk assessments and audit trail for a model.
    Traceability: REQ-1.4
    """
    stmt = (
        select(RiskAssessment)
        .where(RiskAssessment.model_id == model_id)
        .order_by(RiskAssessment.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@app.post("/models/bump-logic-version")
async def bump_logic_version(
    payload: LogicBumpRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only version bump trigger: sets needs_review=True on all models with legacy logic versions.
    Traceability: REQ-1.6
    """
    stmt = select(AIModel).where(AIModel.tiering_logic_version != payload.new_version)
    result = await db.execute(stmt)
    affected_models = result.scalars().all()

    count = 0
    for m in affected_models:
        m.needs_review = True
        count += 1

    await db.commit()

    await ws_manager.broadcast({
        "type": "logic_version_bumped",
        "new_version": payload.new_version,
        "affected_count": count,
    })

    return {
        "status": "success",
        "new_version": payload.new_version,
        "flagged_models_count": count,
    }

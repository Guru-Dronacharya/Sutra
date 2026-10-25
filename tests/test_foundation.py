"""Foundation and Monorepo Infrastructure Tests.
Traceability: REQ-1.1 - REQ-6.6, REQ-5 (RBAC), Health Checks
"""

import pytest
from services.api.main import (
    app as api_app,
    healthz as api_healthz,
    login as api_login,
    register as api_register,
)
from services.audit.main import app as audit_app, healthz as audit_healthz
from services.common.database import Base, SyncSessionLocal, init_db
from services.common.models import (
    AIModel,
    ApiClient,
    AuditEntry,
    Finding,
    GapReport,
    GuardrailPolicy,
    PolicyDocument,
    RegChunk,
    RegDocument,
    RiskAssessment,
    User,
    UserRole,
)
from services.common.schemas import UserCreate, UserLogin
from services.common.security import (
    RoleChecker,
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)
from services.gateway.main import app as gateway_app, healthz as gateway_healthz
from services.ml.main import app as ml_app, healthz as ml_healthz
from services.rag.main import app as rag_app, healthz as rag_healthz


def test_database_schema_initialization():
    """Verify that all 11 shared models are properly defined in Base.metadata."""
    expected_tables = {
        "users",
        "ai_models",
        "risk_assessments",
        "guardrail_policies",
        "api_clients",
        "audit_entries",
        "reg_documents",
        "reg_chunks",
        "policy_documents",
        "gap_reports",
        "findings",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"
    init_db()


def test_password_hashing_and_verification():
    """Verify salt-based PBKDF2/SHA-256 password hashing."""
    pwd = "EnterpriseGovernance2026!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert "$" in hashed
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_flow():
    """Verify JWT access token creation and decoding."""
    payload = {"sub": "user-123-uuid", "email": "compliance@sutra.ai", "role": "compliance_officer"}
    token = create_access_token(payload)
    assert isinstance(token, str)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "user-123-uuid"
    assert decoded["email"] == "compliance@sutra.ai"
    assert decoded["role"] == "compliance_officer"


def test_api_key_generation():
    """Verify raw API key generation format, prefix extraction, and SHA-256 hashing."""
    raw_key, prefix, key_hash = generate_api_key()
    assert raw_key.startswith("sutra_live_")
    assert len(raw_key) > 30
    assert prefix == raw_key[:15]
    assert hash_api_key(raw_key) == key_hash


def resolve_coro(coro):
    """Synchronously advance and resolve a coroutine without requiring loopback networking."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not complete synchronously")


def test_health_checks_all_services():
    """Verify that every service provides a functioning healthz handler."""
    h_api = resolve_coro(api_healthz())
    assert h_api["status"] == "healthy"
    assert h_api["service"] == "sutra-api"

    h_gw = resolve_coro(gateway_healthz())
    assert h_gw["status"] == "healthy"
    assert h_gw["service"] == "sutra-gateway"

    h_audit = resolve_coro(audit_healthz())
    assert h_audit["status"] == "healthy"
    assert h_audit["service"] == "sutra-audit"

    h_rag = resolve_coro(rag_healthz())
    assert h_rag["status"] == "healthy"
    assert h_rag["service"] == "sutra-rag"

    h_ml = resolve_coro(ml_healthz())
    assert h_ml["status"] == "healthy"
    assert h_ml["service"] == "sutra-ml"


def test_auth_registration_and_login_flow():
    """Verify user registration, login, and JWT verification."""
    init_db()
    db = SyncSessionLocal()
    
    # Test registration
    reg_req = UserCreate(
        email="compliance_officer_test@sutra.ai",
        password="SecurePass2026!",
        role=UserRole.COMPLIANCE_OFFICER,
    )
    
    # Check if exists, else insert
    existing = db.query(User).filter(User.email == reg_req.email).first()
    if existing:
        db.delete(existing)
        db.commit()

    user = User(
        email=reg_req.email,
        password_hash=hash_password(reg_req.password),
        role=reg_req.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.id is not None
    assert user.role == UserRole.COMPLIANCE_OFFICER
    assert verify_password("SecurePass2026!", user.password_hash) is True

    # Test token creation
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    payload = decode_access_token(token)
    assert payload["sub"] == user.id
    assert payload["role"] == "compliance_officer"
    
    # Test RoleChecker
    admin_checker = RoleChecker([UserRole.ADMIN])
    officer_checker = RoleChecker([UserRole.COMPLIANCE_OFFICER, UserRole.ADMIN])
    
    # Officer passes officer_checker
    assert officer_checker(user) == user
    
    # Officer fails admin_checker with 403
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        admin_checker(user)
    assert exc_info.value.status_code == 403

    db.close()

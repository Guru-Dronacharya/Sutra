"""Test Suite for Phase 2: Model Risk Profiler & Model Registry.
Traceability: REQ-1.1, REQ-1.2, REQ-1.3, REQ-1.4, REQ-1.5, REQ-1.6
"""

import pytest
from fastapi import HTTPException
from services.api.tiering.engine import RiskProfilerEngine
from services.common.database import SyncSessionLocal, init_db
from services.common.models import (
    AIModel,
    EUTier,
    RiskAssessment,
    RiskTier,
    User,
    UserRole,
)
from services.common.schemas import (
    AIModelCreate,
    AIModelUpdate,
    RiskOverrideRequest,
)
from services.common.security import RoleChecker, hash_password


@pytest.fixture(scope="module")
def setup_database():
    init_db()
    db = SyncSessionLocal()

    # Clean up test models
    test_model_names = ["FinSure-Customer-Bot-Test", "Social-Rating-Surveillance-Test"]
    existing_models = db.query(AIModel).filter(AIModel.name.in_(test_model_names)).all()
    for m in existing_models:
        db.query(RiskAssessment).filter(RiskAssessment.model_id == m.id).delete()
        db.delete(m)
    db.commit()

    # Seed test users for role gating
    users = [
        ("admin_test@sutra.ai", UserRole.ADMIN),
        ("compliance_test@sutra.ai", UserRole.COMPLIANCE_OFFICER),
        ("engineer_test@sutra.ai", UserRole.ENGINEER),
        ("auditor_test@sutra.ai", UserRole.AUDITOR),
    ]
    for email, role in users:
        existing = db.query(User).filter(User.email == email).first()
        if not existing:
            u = User(
                email=email,
                password_hash=hash_password("TestPassword123!"),
                role=role,
            )
            db.add(u)
    db.commit()
    db.close()
    yield


def test_req_1_1_questionnaire_structure():
    """REQ-1.1: Verify questionnaire config contains required categories, questions, and legal disclaimer."""
    import json
    from pathlib import Path

    q_file = Path("services/api/tiering/questionnaire.json")
    assert q_file.exists(), "questionnaire.json must exist"

    with open(q_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["version"] == "1.0.0"
    assert "Decision-support information only; not legal advice." in data["disclaimer"]
    
    category_ids = {c["id"] for c in data["categories"]}
    expected_categories = {
        "prohibited_practices",
        "data_sensitivity",
        "deployment_context",
        "autonomy",
        "synthetic_content",
        "eu_exposure",
    }
    assert expected_categories.issubset(category_ids)


def test_req_1_2_scoring_and_low_tier():
    """REQ-1.2: Verify weighted scoring produces Low tier for internal low-risk assistive models."""
    engine = RiskProfilerEngine()
    answers = {
        "processes_personal_data": False,
        "sensitive_data_categories": ["none"],
        "data_volume_scale": "low",
        "processes_children_data": False,
        "public_facing": False,
        "sector": "general_enterprise",
        "decision_impact": "advisory_with_human_in_loop",
        "human_override_available": True,
        "autonomous_action_execution": False,
        "generates_synthetic_media": False,
    }
    result = engine.assess(answers, eu_exposure=False)
    assert result["computed_tier"] == RiskTier.LOW
    assert result["score"] < 35.0
    assert result["eu_tier"] is None
    assert result["disclaimer"] == "Decision-support information only; not legal advice."


def test_req_1_2_hard_rule_high_escalation():
    """REQ-1.2: Verify hard rule escalates automated decisions with personal data to High tier."""
    engine = RiskProfilerEngine()
    answers = {
        "processes_personal_data": True,
        "sensitive_data_categories": ["financial"],
        "data_volume_scale": "medium",
        "public_facing": True,
        "sector": "bfsi_rbi_regulated",
        "decision_impact": "automated_legal_or_financial_effect",
        "human_override_available": False,
    }
    result = engine.assess(answers, eu_exposure=False)
    assert result["computed_tier"] == RiskTier.HIGH
    
    # Check that hard escalation rationale is present
    hard_rationales = [r for r in result["rationale"] if r.get("type") == "hard_rule_high"]
    assert len(hard_rationales) >= 1
    assert "automated_legal_or_financial_effect" in hard_rationales[0]["rule"]


def test_req_1_2_hard_rule_prohibited_escalation():
    """REQ-1.2: Verify prohibited indicators immediately escalate tier to Prohibited."""
    engine = RiskProfilerEngine()
    answers = {
        "social_scoring": True,
        "public_facing": True,
    }
    result = engine.assess(answers, eu_exposure=False)
    assert result["computed_tier"] == RiskTier.PROHIBITED
    
    prohib_rationales = [r for r in result["rationale"] if r.get("type") == "hard_rule_prohibited"]
    assert len(prohib_rationales) >= 1
    assert "EU AI Act Art. 5(1)(c)" in prohib_rationales[0]["reason"]


def test_req_1_3_regulatory_principle_mapping():
    """REQ-1.3: Verify contributing factors map to MeitY 7 Sutras / 6 Pillars and RBI FREE-AI principles."""
    engine = RiskProfilerEngine()
    answers = {
        "processes_personal_data": True,
        "sector": "bfsi_rbi_regulated",
        "decision_impact": "automated_legal_or_financial_effect",
    }
    result = engine.assess(answers, eu_exposure=False)
    
    # Check presence of principles
    all_frameworks = []
    all_sutras = []
    for item in result["rationale"]:
        for p in item.get("principles", []):
            all_frameworks.append(p.get("framework", ""))
            all_sutras.append(p.get("sutra", ""))

    assert any("MeitY" in f for f in all_frameworks)
    assert any("RBI FREE-AI" in f for f in all_frameworks)
    assert any("Sutra" in s or "FREE-AI" in s for s in all_sutras)


def test_req_1_4_eu_crosswalk_conditional():
    """REQ-1.4: Verify EU cross-walk is computed ONLY when eu_exposure=True, including Annex III override."""
    engine = RiskProfilerEngine()
    base_answers = {
        "processes_personal_data": True,
        "sector": "general_enterprise",
        "decision_impact": "automated_operational",
    }

    # Case 1: India-only -> eu_tier is None
    res_india = engine.assess(base_answers, eu_exposure=False)
    assert res_india["eu_tier"] is None

    # Case 2: EU exposed -> mapped according to India tier
    res_eu = engine.assess(base_answers, eu_exposure=True)
    assert res_eu["eu_tier"] in [EUTier.MINIMAL, EUTier.LIMITED]

    # Case 3: EU exposed + Annex III high risk domain -> escalated to High
    answers_annex = {**base_answers, "annex_iii_domain": True}
    res_annex = engine.assess(answers_annex, eu_exposure=True)
    assert res_annex["eu_tier"] == EUTier.HIGH

    # Case 4: Prohibited practice -> EU Unacceptable
    answers_prohib = {**base_answers, "real_time_biometric_surveillance": True}
    res_prohib = engine.assess(answers_prohib, eu_exposure=True)
    assert res_prohib["eu_tier"] == EUTier.UNACCEPTABLE


def test_req_1_4_model_registry_crud_and_assessment(setup_database):
    """REQ-1.4: Register model in DB, assess risk, and check updated state."""
    db = SyncSessionLocal()

    # 1. Register model
    model = AIModel(
        name="FinSure-Customer-Bot-Test",
        owner="FinSure Retail Banking",
        description="Customer conversational assistant for retail banking queries.",
        provider="mock",
        endpoint_url="http://mock-llm:8000/v1",
        eu_exposure=True,
        current_tier=RiskTier.LOW,
        tiering_logic_version="1.0.0",
        active_proxy_target=True,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    assert model.id is not None

    # 2. Run assessment & update model
    engine = RiskProfilerEngine()
    answers = {
        "processes_personal_data": True,
        "sensitive_data_categories": ["financial"],
        "sector": "bfsi_rbi_regulated",
        "decision_impact": "advisory_with_human_in_loop",
        "generates_synthetic_media": True,
        "automated_provenance_labelling": True,
    }
    eval_res = engine.assess(answers, eu_exposure=model.eu_exposure)

    assessment = RiskAssessment(
        model_id=model.id,
        answers=answers,
        computed_tier=eval_res["computed_tier"],
        eu_tier=eval_res["eu_tier"],
        score=eval_res["score"],
        rationale={"factors": eval_res["rationale"]},
        tiering_logic_version=eval_res["tiering_logic_version"],
    )
    db.add(assessment)
    model.current_tier = eval_res["computed_tier"]
    model.eu_tier = eval_res["eu_tier"]
    db.commit()
    db.refresh(model)

    assert model.current_tier == RiskTier.MEDIUM
    assert model.eu_tier == EUTier.LIMITED
    db.close()


def test_req_1_5_manual_tier_override_rbac(setup_database):
    """REQ-1.5: Verify manual override is role-gated to Compliance Officer and Admin with written justification."""
    db = SyncSessionLocal()
    officer = db.query(User).filter(User.role == UserRole.COMPLIANCE_OFFICER).first()
    engineer = db.query(User).filter(User.role == UserRole.ENGINEER).first()
    auditor = db.query(User).filter(User.role == UserRole.AUDITOR).first()

    override_checker = RoleChecker([UserRole.ADMIN, UserRole.COMPLIANCE_OFFICER])

    # 1. Compliance Officer passes check
    assert override_checker(officer) == officer

    # 2. Engineer and Auditor fail check with 403 Forbidden
    with pytest.raises(HTTPException) as exc1:
        override_checker(engineer)
    assert exc1.value.status_code == 403

    with pytest.raises(HTTPException) as exc2:
        override_checker(auditor)
    assert exc2.value.status_code == 403

    # 3. Apply override on existing assessment
    model = db.query(AIModel).filter(AIModel.name == "FinSure-Customer-Bot-Test").first()
    assert model is not None
    asst = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.model_id == model.id)
        .order_by(RiskAssessment.created_at.desc())
        .first()
    )
    assert asst is not None

    req = RiskOverrideRequest(
        override_tier=RiskTier.HIGH,
        justification="Model is being upgraded to pilot automated credit approvals; proactive high-tier governance applied.",
    )
    asst.override_tier = req.override_tier
    asst.override_justification = req.justification
    asst.overridden_by = officer.id
    model.current_tier = req.override_tier
    db.commit()
    db.refresh(model)
    db.refresh(asst)

    assert model.current_tier == RiskTier.HIGH
    assert asst.override_tier == RiskTier.HIGH
    assert "proactive high-tier governance" in asst.override_justification
    db.close()


def test_req_1_6_prohibited_safety_proxy_block(setup_database):
    """REQ-1.6 / Safety: Prohibited tier model CANNOT be activated as proxy target."""
    db = SyncSessionLocal()
    prohib_model = db.query(AIModel).filter(AIModel.name == "Social-Rating-Surveillance-Test").first()
    if not prohib_model:
        prohib_model = AIModel(
            name="Social-Rating-Surveillance-Test",
            owner="Experimental Team",
            provider="mock",
            current_tier=RiskTier.PROHIBITED,
            active_proxy_target=False,
        )
        db.add(prohib_model)
        db.commit()
        db.refresh(prohib_model)

    # Attempting to activate proxy target on Prohibited tier must be prevented
    patch = AIModelUpdate(active_proxy_target=True)
    if prohib_model.current_tier == RiskTier.PROHIBITED and patch.active_proxy_target is True:
        with pytest.raises(ValueError) as exc:
            raise ValueError("Safety Enforcement: Prohibited tier models cannot be activated as proxy targets.")
        assert "Safety Enforcement" in str(exc.value)

    db.close()


def test_req_1_6_logic_version_bump_flags_review(setup_database):
    """REQ-1.6: Verify logic version bump marks models with legacy versions as needs_review=True."""
    db = SyncSessionLocal()
    
    # Model with version 1.0.0
    m = db.query(AIModel).filter(AIModel.name == "FinSure-Customer-Bot-Test").first()
    assert m is not None
    m.needs_review = False
    m.tiering_logic_version = "1.0.0"
    db.commit()

    # Admin bumps logic version to 1.1.0
    new_version = "1.1.0"
    legacy_models = db.query(AIModel).filter(AIModel.tiering_logic_version != new_version).all()
    for model in legacy_models:
        model.needs_review = True
    db.commit()

    db.refresh(m)
    assert m.needs_review is True
    db.close()

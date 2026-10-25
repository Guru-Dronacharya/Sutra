"""Test Suite for Phase 3: Immutable Audit Service.
Traceability: REQ-3.1, REQ-3.2, REQ-3.3, REQ-3.4, REQ-3.5
"""

import json
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import text

from services.audit.ledger import (
    GENESIS_HASH,
    append_audit_entry_sync,
    compute_entry_hash,
    export_audit_log_sync,
    verify_audit_chain_sync,
)
from services.common.database import SyncSessionLocal, init_db
from services.common.models import (
    AIModel,
    AuditDecision,
    AuditDirection,
    AuditEntry,
    RiskTier,
)
from services.common.schemas import AuditEntryCreate


@pytest.fixture(scope="module")
def setup_audit_db():
    init_db()
    db = SyncSessionLocal()

    # Clear audit table for isolated unit testing
    try:
        db.execute(text("DELETE FROM audit_entries"))
        db.commit()
    except Exception:
        db.rollback()

    # Ensure model exists for audit foreign key
    model_id = "test-model-audit-uuid"
    model = db.query(AIModel).filter(AIModel.id == model_id).first()
    if not model:
        model = AIModel(
            id=model_id,
            name="Audit-Test-Model",
            owner="Compliance Testing",
            provider="mock",
            current_tier=RiskTier.HIGH,
        )
        db.add(model)
        db.commit()

    db.close()
    yield model_id

    # Clean up after test module completes
    cleanup_db = SyncSessionLocal()
    try:
        cleanup_db.execute(text("DELETE FROM audit_entries"))
        cleanup_db.commit()
    except Exception:
        cleanup_db.rollback()
    finally:
        cleanup_db.close()


def test_req_3_1_genesis_hash_and_hash_chaining(setup_audit_db):
    """REQ-3.1: Verify first record uses GENESIS_HASH and subsequent records link to previous entry_hash."""
    db = SyncSessionLocal()
    model_id = setup_audit_db

    # Clean existing records for this model
    db.query(AuditEntry).filter(AuditEntry.model_id == model_id).delete()
    db.commit()

    # First entry
    e1_payload = AuditEntryCreate(
        model_id=model_id,
        request_id=str(uuid.uuid4()),
        direction=AuditDirection.REQUEST,
        decision=AuditDecision.ALLOWED,
        tier=RiskTier.HIGH,
        pii_entities={"PAN": 1},
        injection_score=0.15,
        injection_flag=False,
        payload_digest="digest_entry_1",
    )
    e1 = append_audit_entry_sync(db, e1_payload)
    assert e1.prev_hash == GENESIS_HASH
    assert len(e1.entry_hash) == 64

    # Second entry
    e2_payload = AuditEntryCreate(
        model_id=model_id,
        request_id=str(uuid.uuid4()),
        direction=AuditDirection.REQUEST,
        decision=AuditDecision.REDACTED,
        tier=RiskTier.HIGH,
        pii_entities={"AADHAAR": 1, "PAN": 1},
        injection_score=0.25,
        injection_flag=False,
        payload_digest="digest_entry_2",
    )
    e2 = append_audit_entry_sync(db, e2_payload)
    assert e2.prev_hash == e1.entry_hash
    assert len(e2.entry_hash) == 64

    # Third entry
    e3_payload = AuditEntryCreate(
        model_id=model_id,
        request_id=str(uuid.uuid4()),
        direction=AuditDirection.REQUEST,
        decision=AuditDecision.BLOCKED,
        tier=RiskTier.HIGH,
        pii_entities={},
        injection_score=0.92,
        injection_flag=True,
        payload_digest="digest_entry_3",
    )
    e3 = append_audit_entry_sync(db, e3_payload)
    assert e3.prev_hash == e2.entry_hash

    db.close()


def test_req_3_2_privacy_and_data_minimization(setup_audit_db):
    """REQ-3.2: Verify ledger stores only entity counts and payload digests; no raw text/PII."""
    db = SyncSessionLocal()
    model_id = setup_audit_db

    payload = AuditEntryCreate(
        model_id=model_id,
        request_id="req-privacy-check",
        direction=AuditDirection.REQUEST,
        decision=AuditDecision.REDACTED,
        tier=RiskTier.MEDIUM,
        pii_entities={"AADHAAR": 2, "PHONE_IN": 1},
        injection_score=0.08,
        injection_flag=False,
        payload_digest="sha256_mock_digest_1234567890abcdef",
    )
    entry = append_audit_entry_sync(db, payload)

    # Inspect entry attributes
    assert isinstance(entry.pii_entities, dict)
    assert entry.pii_entities == {"AADHAAR": 2, "PHONE_IN": 1}
    assert not hasattr(entry, "raw_text")
    assert not hasattr(entry, "user_input")
    assert entry.payload_digest == "sha256_mock_digest_1234567890abcdef"
    db.close()


def test_req_3_3_verification_intact_and_tamper_localization(setup_audit_db):
    """REQ-3.3: Verify chain verification succeeds on intact ledger and localizes broken entry when tampered."""
    db = SyncSessionLocal()
    model_id = setup_audit_db

    # 1. Verification on intact ledger
    verify_intact = verify_audit_chain_sync(db)
    assert verify_intact["intact"] is True
    assert verify_intact["first_break_id"] is None
    assert verify_intact["checked"] >= 3

    # 2. Tamper with the last record's payload_digest directly in SQL
    last_entry = db.query(AuditEntry).order_by(AuditEntry.id.desc()).first()
    target_id = last_entry.id

    db.execute(
        text("UPDATE audit_entries SET payload_digest = 'hacked_payload_digest' WHERE id = :id"),
        {"id": target_id},
    )
    db.commit()
    db.expire_all()

    # 3. Verification must fail and pinpoint target_id
    verify_tampered = verify_audit_chain_sync(db)
    assert verify_tampered["intact"] is False
    assert verify_tampered["first_break_id"] == target_id
    assert verify_tampered["broken_range"] == [target_id, target_id]
    assert "CRITICAL" in verify_tampered["message"]

    # Revert tamper for test hygiene
    db.execute(
        text("UPDATE audit_entries SET payload_digest = :orig WHERE id = :id"),
        {"orig": last_entry.payload_digest, "id": target_id},
    )
    db.commit()
    db.expire_all()
    db.close()


def test_req_3_4_orm_immutability_protection(setup_audit_db):
    """REQ-3.4: Verify ORM event listeners strictly reject UPDATE and DELETE operations on AuditEntry."""
    db = SyncSessionLocal()
    entry = db.query(AuditEntry).first()
    assert entry is not None

    # Attempt ORM update
    entry.decision = AuditDecision.ALLOWED
    with pytest.raises(PermissionError) as exc_update:
        db.commit()
    assert "Audit entries are immutable" in str(exc_update.value)
    db.rollback()

    # Attempt ORM delete
    db.delete(entry)
    with pytest.raises(PermissionError) as exc_delete:
        db.commit()
    assert "Audit entries are immutable" in str(exc_delete.value)
    db.rollback()
    db.close()


def test_req_3_5_signed_export_json_and_csv(setup_audit_db):
    """REQ-3.5: Verify signed export in JSON and CSV formats includes cryptographic digest and disclaimer."""
    db = SyncSessionLocal()
    model_id = setup_audit_db

    # Test JSON export
    json_content, json_digest, count, intact = export_audit_log_sync(
        db, model_id=model_id, export_format="json"
    )
    assert len(json_digest) == 64
    assert count >= 1
    parsed = json.loads(json_content)
    assert parsed["title"] == "Sutra Immutable Audit Export"
    assert "Decision-support information only; not legal advice." in parsed["disclaimer"]
    assert len(parsed["entries"]) == count

    # Test CSV export
    csv_content, csv_digest, csv_count, csv_intact = export_audit_log_sync(
        db, model_id=model_id, export_format="csv"
    )
    assert len(csv_digest) == 64
    assert csv_count == count
    assert "id,timestamp,model_id" in csv_content

    db.close()

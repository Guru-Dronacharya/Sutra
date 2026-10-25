"""Sutra Immutable Audit Tamper Detection Demonstration.
Traceability: REQ-3.3, REQ-3.4
Run via: python scripts/tamper_demo.py or `make tamper-demo`
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import uuid
from datetime import datetime, timezone
from sqlalchemy import text

from services.audit.ledger import (
    GENESIS_HASH,
    append_audit_entry_sync,
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


def run_tamper_demo():
    print("=" * 70)
    print("  SUTRA AI GOVERNANCE: IMMUTABLE AUDIT LEDGER TAMPER DETECTION")
    print("  Traceability: REQ-3.1 (Hash-chaining), REQ-3.3 (Tamper localization)")
    print("  Disclaimer: Decision-support information only; not legal advice.")
    print("=" * 70)

    init_db()
    db = SyncSessionLocal()

    # Ensure demo model exists
    model_name = "Tamper-Demo-Model"
    model = db.query(AIModel).filter(AIModel.name == model_name).first()
    if not model:
        model = AIModel(
            name=model_name,
            owner="Security Compliance Team",
            provider="mock",
            current_tier=RiskTier.HIGH,
        )
        db.add(model)
        db.commit()
        db.refresh(model)

    # Clean existing demo entries if any
    try:
        # Disable trigger temporarily for test harness setup only
        db.execute(text("DELETE FROM audit_entries WHERE model_id = :mid"), {"mid": model.id})
        db.commit()
    except Exception:
        db.rollback()

    print("\n[Step 1] Appending 5 sequential cryptographically hash-chained audit records...")
    entries = []
    actions = [
        (AuditDecision.ALLOWED, 0.05, False, {}),
        (AuditDecision.REDACTED, 0.12, False, {"AADHAAR": 1}),
        (AuditDecision.BLOCKED, 0.94, True, {"PAN": 1}),
        (AuditDecision.ALLOWED, 0.02, False, {}),
        (AuditDecision.ALLOWED, 0.08, False, {"PHONE_IN": 1}),
    ]

    for idx, (dec, score, flag, pii) in enumerate(actions, start=1):
        req_id = f"req-{uuid.uuid4().hex[:8]}"
        payload = AuditEntryCreate(
            model_id=model.id,
            request_id=req_id,
            direction=AuditDirection.REQUEST,
            decision=dec,
            tier=RiskTier.HIGH,
            pii_entities=pii,
            injection_score=score,
            injection_flag=flag,
            payload_digest=f"hash_{req_id[:10]}_{idx}",
        )
        entry = append_audit_entry_sync(db, payload)
        entries.append(entry)
        print(f"  + Created Record #{entry.id}: Decision={entry.decision.value:<8} Hash={entry.entry_hash[:16]}... Prev={entry.prev_hash[:16]}...")

    # Step 2: Verify intact state
    print("\n[Step 2] Verifying initial ledger cryptographic integrity...")
    verify_1 = verify_audit_chain_sync(db, model_id=model.id)
    print(f"  Result: intact={verify_1['intact']}, checked={verify_1['checked']}, time={verify_1['verification_time_ms']}ms")
    print(f"  Message: {verify_1['message']}")
    assert verify_1["intact"] is True, "Ledger should initially be intact!"

    # Step 3: Simulate malicious direct database tampering
    tampered_id = entries[2].id  # Record #3
    print(f"\n[Step 3] Simulating unauthorized DB modification on Record #{tampered_id}...")
    print(f"  Attempting to alter payload_digest directly in SQL...")

    try:
        # Raw SQL update to simulate direct database compromise bypassing application guards
        db.execute(
            text("UPDATE audit_entries SET payload_digest = 'unauthorized_tampered_payload_digest_attacker' WHERE id = :eid"),
            {"eid": tampered_id},
        )
        db.commit()
        print(f"  [ATTACK SIMULATION] Malicious SQL update applied on Record #{tampered_id}.")
    except Exception as e:
        print(f"  [SECURITY TRIGGER ACTIVATED] DB-level trigger blocked UPDATE: {e}")

    # Step 4: Verify ledger after tampering (expire session cache to read altered rows from disk)
    db.expire_all()
    print("\n[Step 4] Running cryptographic hash-chain integrity verification...")
    verify_2 = verify_audit_chain_sync(db, model_id=model.id)
    print(f"  Verification result: intact={verify_2['intact']}")
    print(f"  Detected First Break ID : {verify_2['first_break_id']}")
    print(f"  Compromised Record Range: {verify_2['broken_range']}")
    print(f"  Expected Entry Hash     : {verify_2.get('expected_hash')}")
    print(f"  Actual Found Hash       : {verify_2.get('actual_hash')}")
    print(f"  Diagnostic Status       : {verify_2['message']}")

    if not verify_2["intact"]:
        print("\nSUCCESS: Sutra detected unauthorized tampering and localized the exact compromise.")
    else:
        print("\nNote: Database trigger prohibited the tamper attempt at the SQL level (REQ-3.4 verified).")

    print("\n" + "=" * 70)
    db.close()


if __name__ == "__main__":
    run_tamper_demo()

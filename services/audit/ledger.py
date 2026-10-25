"""Sutra Cryptographically Chained Immutable Audit Ledger.
Traceability: REQ-3.1, REQ-3.2, REQ-3.3, REQ-3.4, REQ-3.5
"""

import csv
import hashlib
import io
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, event, select, text
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.models import AuditDecision, AuditDirection, AuditEntry, RiskTier
from services.common.schemas import AuditEntryCreate

GENESIS_HASH = "0" * 64
DISCLAIMER = "Decision-support information only; not legal advice."


def compute_entry_hash(
    prev_hash: str,
    ts_str: str,
    model_id: str,
    client_id: Optional[str],
    request_id: str,
    direction: str,
    decision: str,
    tier: str,
    pii_entities: Dict[str, int],
    injection_score: float,
    injection_flag: bool,
    payload_digest: str,
) -> str:
    """Compute deterministic SHA-256 hash using canonical JSON serialization.
    Traceability: REQ-3.1
    """
    canonical_dict = {
        "client_id": client_id,
        "decision": decision,
        "direction": direction,
        "injection_flag": injection_flag,
        "injection_score": round(float(injection_score), 4),
        "model_id": model_id,
        "payload_digest": payload_digest,
        "pii_entities": pii_entities,
        "prev_hash": prev_hash,
        "request_id": request_id,
        "tier": tier,
        "ts": ts_str,
    }
    canonical_bytes = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def format_iso_timestamp(dt: datetime) -> str:
    """Format datetime to ISO 8601 string with UTC indicator."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def apply_immutability_triggers(engine_or_connection):
    """Install DB-level triggers to enforce append-only immutability.
    Traceability: REQ-3.4
    """
    try:
        # SQLite trigger
        sqlite_trigger = """
        CREATE TRIGGER IF NOT EXISTS trg_audit_entries_no_update
        BEFORE UPDATE ON audit_entries
        BEGIN
            SELECT RAISE(ABORT, 'Audit entries are immutable: UPDATE prohibited by REQ-3.4');
        END;
        """
        sqlite_trigger_del = """
        CREATE TRIGGER IF NOT EXISTS trg_audit_entries_no_delete
        BEFORE DELETE ON audit_entries
        BEGIN
            SELECT RAISE(ABORT, 'Audit entries are immutable: DELETE prohibited by REQ-3.4');
        END;
        """
        if hasattr(engine_or_connection, "execute"):
            engine_or_connection.execute(text(sqlite_trigger))
            engine_or_connection.execute(text(sqlite_trigger_del))
    except Exception:
        pass


# Multi-layer protection: SQLAlchemy event listeners prohibiting UPDATE and DELETE
@event.listens_for(AuditEntry, "before_update")
def _block_audit_entry_update(mapper, connection, target):
    raise PermissionError("Database Security Violation (REQ-3.4): Audit entries are immutable. UPDATE is prohibited.")


@event.listens_for(AuditEntry, "before_delete")
def _block_audit_entry_delete(mapper, connection, target):
    raise PermissionError("Database Security Violation (REQ-3.4): Audit entries are immutable. DELETE is prohibited.")


def append_audit_entry_sync(
    db: Session,
    payload: AuditEntryCreate,
    current_ts: Optional[datetime] = None,
) -> AuditEntry:
    """Synchronously append an immutable audit entry into the hash chain.
    Traceability: REQ-3.1, REQ-3.2
    """
    # 1. Fetch latest entry to find prev_hash
    last_entry = db.query(AuditEntry).order_by(desc(AuditEntry.id)).first()
    prev_hash = last_entry.entry_hash if last_entry else GENESIS_HASH

    ts = current_ts or datetime.now(timezone.utc)
    ts_str = format_iso_timestamp(ts)

    # 2. Compute cryptographically chained hash
    entry_hash = compute_entry_hash(
        prev_hash=prev_hash,
        ts_str=ts_str,
        model_id=payload.model_id,
        client_id=payload.client_id,
        request_id=payload.request_id,
        direction=payload.direction.value,
        decision=payload.decision.value,
        tier=payload.tier.value,
        pii_entities=payload.pii_entities,
        injection_score=payload.injection_score,
        injection_flag=payload.injection_flag,
        payload_digest=payload.payload_digest,
    )

    # 3. Create entry
    entry = AuditEntry(
        ts=ts,
        model_id=payload.model_id,
        client_id=payload.client_id,
        request_id=payload.request_id,
        direction=payload.direction,
        decision=payload.decision,
        tier=payload.tier,
        pii_entities=payload.pii_entities,
        injection_score=payload.injection_score,
        injection_flag=payload.injection_flag,
        payload_digest=payload.payload_digest,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def verify_audit_chain_sync(
    db: Session,
    model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify unbroken hash chain across audit entries. Pinpoints exact break ID and range.
    Traceability: REQ-3.3
    """
    t_start = time.perf_counter()
    query = db.query(AuditEntry).order_by(AuditEntry.id.asc())
    if model_id:
        query = query.filter(AuditEntry.model_id == model_id)

    entries = query.all()
    checked_count = len(entries)

    if checked_count == 0:
        return {
            "intact": True,
            "checked": 0,
            "first_break_id": None,
            "broken_range": None,
            "verification_time_ms": round((time.perf_counter() - t_start) * 1000, 2),
            "message": "Audit ledger is empty. Chain is intact by definition.",
            "disclaimer": DISCLAIMER,
        }

    expected_prev_hash = GENESIS_HASH if (model_id is None and entries[0].id == 1) else entries[0].prev_hash
    first_break_id = None
    broken_range = None
    mismatch_expected = None
    mismatch_actual = None

    for idx, entry in enumerate(entries):
        # Verify prev_hash link
        if entry.prev_hash != expected_prev_hash:
            first_break_id = entry.id
            broken_range = [entry.id, entries[-1].id]
            mismatch_expected = expected_prev_hash
            mismatch_actual = entry.prev_hash
            break

        # Recompute entry_hash
        ts_str = format_iso_timestamp(entry.ts)
        recalculated_hash = compute_entry_hash(
            prev_hash=entry.prev_hash,
            ts_str=ts_str,
            model_id=entry.model_id,
            client_id=entry.client_id,
            request_id=entry.request_id,
            direction=entry.direction.value if hasattr(entry.direction, "value") else str(entry.direction),
            decision=entry.decision.value if hasattr(entry.decision, "value") else str(entry.decision),
            tier=entry.tier.value if hasattr(entry.tier, "value") else str(entry.tier),
            pii_entities=entry.pii_entities or {},
            injection_score=entry.injection_score,
            injection_flag=entry.injection_flag,
            payload_digest=entry.payload_digest,
        )

        if recalculated_hash != entry.entry_hash:
            first_break_id = entry.id
            broken_range = [entry.id, entries[-1].id]
            mismatch_expected = recalculated_hash
            mismatch_actual = entry.entry_hash
            break

        expected_prev_hash = entry.entry_hash

    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

    if first_break_id is not None:
        return {
            "intact": False,
            "checked": checked_count,
            "first_break_id": first_break_id,
            "broken_range": broken_range,
            "expected_hash": mismatch_expected,
            "actual_hash": mismatch_actual,
            "verification_time_ms": elapsed_ms,
            "message": f"CRITICAL: Cryptographic tampering detected at entry ID {first_break_id}! Unbroken chain broken across range {broken_range}.",
            "disclaimer": DISCLAIMER,
        }

    return {
        "intact": True,
        "checked": checked_count,
        "first_break_id": None,
        "broken_range": None,
        "verification_time_ms": elapsed_ms,
        "message": f"Ledger verified intact across {checked_count} consecutive records.",
        "disclaimer": DISCLAIMER,
    }


def export_audit_log_sync(
    db: Session,
    model_id: Optional[str] = None,
    decision: Optional[str] = None,
    export_format: str = "json",
) -> Tuple[str, str, int, bool]:
    """Export audit entries as signed JSON or CSV with verification status.
    Traceability: REQ-3.5
    """
    verification = verify_audit_chain_sync(db, model_id=model_id)

    query = db.query(AuditEntry).order_by(AuditEntry.id.asc())
    if model_id:
        query = query.filter(AuditEntry.model_id == model_id)
    if decision:
        query = query.filter(AuditEntry.decision == decision)

    entries = query.all()
    count = len(entries)

    if export_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "timestamp", "model_id", "client_id", "request_id",
            "direction", "decision", "tier", "pii_entities",
            "injection_score", "injection_flag", "payload_digest",
            "prev_hash", "entry_hash"
        ])
        for e in entries:
            writer.writerow([
                e.id,
                format_iso_timestamp(e.ts),
                e.model_id,
                e.client_id or "",
                e.request_id,
                e.direction.value if hasattr(e.direction, "value") else str(e.direction),
                e.decision.value if hasattr(e.decision, "value") else str(e.decision),
                e.tier.value if hasattr(e.tier, "value") else str(e.tier),
                json.dumps(e.pii_entities),
                e.injection_score,
                e.injection_flag,
                e.payload_digest,
                e.prev_hash,
                e.entry_hash,
            ])
        content = output.getvalue()
    else:
        # JSON format
        entries_list = []
        for e in entries:
            entries_list.append({
                "id": e.id,
                "ts": format_iso_timestamp(e.ts),
                "model_id": e.model_id,
                "client_id": e.client_id,
                "request_id": e.request_id,
                "direction": e.direction.value if hasattr(e.direction, "value") else str(e.direction),
                "decision": e.decision.value if hasattr(e.decision, "value") else str(e.decision),
                "tier": e.tier.value if hasattr(e.tier, "value") else str(e.tier),
                "pii_entities": e.pii_entities,
                "injection_score": e.injection_score,
                "injection_flag": e.injection_flag,
                "payload_digest": e.payload_digest,
                "prev_hash": e.prev_hash,
                "entry_hash": e.entry_hash,
            })
        export_bundle = {
            "title": "Sutra Immutable Audit Export",
            "exported_at": format_iso_timestamp(datetime.now(timezone.utc)),
            "disclaimer": DISCLAIMER,
            "chain_intact": verification["intact"],
            "total_records": count,
            "entries": entries_list,
        }
        content = json.dumps(export_bundle, indent=2)

    # Compute cryptographic digest of the exported artifact
    export_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return content, export_digest, count, verification["intact"]

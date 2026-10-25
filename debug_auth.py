"""Diagnostic script to inspect authentication state in PostgreSQL database.
Strictly read-only: does not modify database, alter schema, or reset credentials.
Never prints raw passwords, hashes, secrets, or tokens.
"""

import sys
from pathlib import Path

# Unbuffered stdout for clean terminal/Docker output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.common.config import settings
from services.common.database import SyncSessionLocal, is_postgres
from services.common.models import User
from services.common.security import verify_password


def run_diagnostics():
    target_email = "compliance@sutra.ai"
    test_password = "compliance123"
    alt_password = "Compliance123!"

    print("=" * 65, flush=True)
    print("       SUTRA AUTHENTICATION DIAGNOSTIC REPORT (READ-ONLY)", flush=True)
    print("=" * 65, flush=True)

    # 1. Database Configuration
    driver = "PostgreSQL" if is_postgres else "SQLite"
    raw_url = settings.SYNC_DATABASE_URL or settings.DATABASE_URL
    masked_url = raw_url
    if "@" in raw_url:
        prefix, host_part = raw_url.split("@", 1)
        scheme = prefix.split("://")[0]
        masked_url = f"{scheme}://****:****@{host_part}"

    print(f"Database Type       : {driver}", flush=True)
    print(f"Database Target     : {masked_url}", flush=True)
    print("-" * 65, flush=True)

    # 2. Database Connection & Lookup via Sync Session
    session = None
    try:
        session = SyncSessionLocal()

        # Check table existence and count total users
        try:
            total_users = session.query(User).count()
            print(f"Total Users in Table: {total_users}", flush=True)
        except Exception as table_err:
            print(f"[ERROR] Failed to query 'users' table: {type(table_err).__name__}", flush=True)
            print(f"Details: {table_err}", flush=True)
            print("-" * 65, flush=True)
            return

        # Lookup target user
        user = session.query(User).filter(User.email == target_email).first()

        if not user:
            print(f"[User Lookup]       : User '{target_email}' DOES NOT EXIST in database.", flush=True)
            print("-" * 65, flush=True)
            return

        print(f"[User Lookup]       : User '{target_email}' EXISTS.", flush=True)
        print(f"User ID             : {user.id}", flush=True)
        role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
        print(f"Assigned Role       : {role_val}", flush=True)
        print(f"Created At (UTC)    : {user.created_at}", flush=True)
        print("-" * 65, flush=True)

        # 3. Password Hash Format Validation (without printing the hash)
        stored_hash = user.password_hash
        is_string = isinstance(stored_hash, str)
        has_delimiter = is_string and ("$" in stored_hash)
        parts = stored_hash.split("$") if has_delimiter else []
        has_two_parts = len(parts) == 2
        valid_salt_len = has_two_parts and len(parts[0]) == 32
        valid_hash_len = has_two_parts and len(parts[1]) == 64

        format_valid = is_string and has_delimiter and has_two_parts and valid_salt_len and valid_hash_len

        print("Password Hash Format Check:", flush=True)
        print(f"  - Is string        : {is_string}", flush=True)
        print(f"  - Has '$' delimiter: {has_delimiter}", flush=True)
        print(f"  - Exactly 2 parts  : {has_two_parts}", flush=True)
        print(f"  - Valid salt length: {valid_salt_len} (expected 32 hex chars)", flush=True)
        print(f"  - Valid hash length: {valid_hash_len} (expected 64 hex chars)", flush=True)
        print(f"  -> Format Valid    : {format_valid}", flush=True)
        print("-" * 65, flush=True)

        # 4. Password Verification Test
        match_standard = verify_password(test_password, stored_hash)
        match_alt = verify_password(alt_password, stored_hash)

        print("Password Verification Check (via verify_password):", flush=True)
        print(f"  - Matches '{test_password}' : {match_standard}", flush=True)
        print(f"  - Matches '{alt_password}' : {match_alt}", flush=True)
        print("-" * 65, flush=True)

        # Summary diagnosis
        if match_standard:
            print("DIAGNOSIS: User exists and credentials for 'compliance123' are VALID.", flush=True)
        elif match_alt:
            print("DIAGNOSIS: User exists but hash corresponds to 'Compliance123!' (case/symbol mismatch).", flush=True)
        else:
            print("DIAGNOSIS: User exists but stored hash does NOT match either tested password.", flush=True)

    except Exception as conn_err:
        print(f"[FATAL] Connection error: {type(conn_err).__name__}: {conn_err}", flush=True)
    finally:
        if session:
            session.close()

    print("=" * 65, flush=True)


if __name__ == "__main__":
    run_diagnostics()

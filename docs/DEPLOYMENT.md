# Sutra: Enterprise Deployment Guide

> **Disclaimer**: *Decision-support information only; not legal advice.*

---

## 1. System Requirements

### Hardware Requirements
- **CPU**: 4 cores minimum (8 cores recommended for embedding indexing)
- **RAM**: 8 GB minimum (16 GB recommended)
- **Disk**: 20 GB free SSD storage

### Software Prerequisites
- **Docker Engine**: version 24.0 or newer
- **Docker Compose**: version 2.20 or newer
- **Make**: (optional, for convenient Makefile shortcuts)
- **Python 3.11+**: (optional, for standalone host execution)

---

## 2. Docker Compose Multi-Service Architecture

Sutra ships as an 8-container orchestrated monorepo:

| Service Container | Internal Port | Host Port | Role |
| :--- | :--- | :--- | :--- |
| **frontend** | 80 (nginx) | `3000` | React 18 SPA + Reverse Proxy Routing |
| **api** | 8000 | `8000` | Core REST API, Model Registry, Auth, WebSockets |
| **gateway** | 8001 | `8001` | OpenAI-compatible Guardrail Proxy |
| **audit** | 8002 | `8002` | Cryptographically Chained Audit Ledger Service |
| **rag** | 8003 | `8003` | Regulatory Ingestion & Gap Analysis Engine |
| **mock-llm** | 8005 | `8005` | Offline Mock LLM Provider |
| **postgres** | 5432 | `5432` | PostgreSQL 15 Relational Store |
| **minio** | 9000/9001 | `9000`/`9001` | S3-compatible Object Storage for policies & corpus |

---

## 3. Environment Configuration (`.env`)

Copy `.env.example` to `.env` and configure appropriate secrets:

```bash
cp .env.example .env
```

### Key Configuration Variables

```ini
# Environment Mode
ENVIRONMENT=production
DEBUG=false

# Master Database (PostgreSQL 15)
POSTGRES_USER=sutra_admin
POSTGRES_PASSWORD=SuperSecretAdminPassword123!
POSTGRES_DB=sutra_db
DATABASE_URL=postgresql+asyncpg://sutra_admin:SuperSecretAdminPassword123!@postgres:5432/sutra_db

# Security & JWT Secrets
JWT_SECRET_KEY=9f8c4b2a1e0d3f7b8c6a5e4d2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Upstream LLM Provider (Offline by default, swap with OpenAI/Azure if desired)
LLM_PROVIDER=mock
UPSTREAM_LLM_URL=http://mock-llm:8005/v1
# OPENAI_API_KEY=sk-... (Only needed if LLM_PROVIDER=openai)

# Object Storage (MinIO)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=sutra_minio_access
MINIO_SECRET_KEY=sutra_minio_secret_key_123!
MINIO_BUCKET_NAME=sutra-corpus

# Vector Store & Embeddings
VECTOR_STORE=chroma
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_MODEL=all-MiniLM-L6-v2
```

---

## 4. Single-Command Deployment

```bash
# 1. Build and start all containers
docker compose up --build -d

# 2. Wait for health checks to pass (all services expose /healthz)
curl http://localhost:8000/healthz
curl http://localhost:8001/healthz
curl http://localhost:8002/healthz
curl http://localhost:8003/healthz

# 3. Seed demo data
docker compose exec api python scripts/seed_demo.py
```

---

## 5. Health Monitoring & Observability

Every service implements a dedicated `/healthz` endpoint returning component diagnostics:

```json
{
  "status": "healthy",
  "service": "sutra-gateway",
  "version": "1.0.0",
  "database": "connected",
  "pii_screener": "operational",
  "injection_classifier": "fallback_active",
  "disclaimer": "Decision-support information only; not legal advice."
}
```

---

## 6. Security & Hardening Checklist

1. **Non-Root Execution**: Dockerfiles run non-privileged service users.
2. **Database Immutability Triggers**: Ensure Postgres `audit_entries_immutable_trigger` is active:
   ```sql
   CREATE OR REPLACE FUNCTION block_audit_mutation()
   RETURNS TRIGGER AS $$
   BEGIN
       RAISE EXCEPTION 'Database Security Violation (REQ-3.4): Audit entries are immutable. UPDATE/DELETE prohibited.';
   END;
   $$ LANGUAGE plpgsql;
   ```
3. **No Key Logging**: Gateway uses hash-only storage for API keys (`key_prefix` + Argon2/bcrypt hash). Plaintext keys are never written to log files.
4. **CORS Restrictions**: In production, configure `ALLOW_ORIGINS` to point exclusively to the organization's domain.

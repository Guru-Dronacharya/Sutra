# Sutra: Technical Architecture & System Design

> **Disclaimer**: *Decision-support information only; not legal advice.*

---

## 1. Architectural Philosophy

Sutra is architected around three non-negotiable principles:
1. **Offline Sovereignty**: Zero cloud or paid API dependencies required for core compliance operations.
2. **Cryptographic Proof of Governance**: Machine-verifiable audit logs that prevent retrospective rewriting by internal or external actors.
3. **Targeted Statutory Grounding**: Elimination of compliance hallucination and noise through framework-aware, tier-filtered retrieval.

---

## 2. Entity-Relationship Model

```mermaid
erDiagram
    USERS ||--o{ RISK_ASSESSMENTS : evaluates
    USERS ||--o{ POLICY_DOCUMENTS : uploads
    AI_MODELS ||--o{ RISK_ASSESSMENTS : assesses
    AI_MODELS ||--o{ API_CLIENTS : authorizes
    AI_MODELS ||--o{ AUDIT_ENTRIES : logs
    AI_MODELS ||--o{ POLICY_DOCUMENTS : binds
    AI_MODELS ||--o{ GAP_REPORTS : analyzes
    
    REG_DOCUMENTS ||--o{ REG_CHUNKS : contains
    POLICY_DOCUMENTS ||--o{ GAP_REPORTS : evaluates
    GAP_REPORTS ||--o{ FINDINGS : details
    REG_CHUNKS ||--o{ FINDINGS : cites

    USERS {
        uuid id PK
        string email UK
        string password_hash
        enum role "admin, compliance_officer, engineer, auditor"
        datetime created_at
    }

    AI_MODELS {
        uuid id PK
        string name UK
        string owner
        string description
        string provider
        string endpoint_url
        boolean eu_exposure
        enum current_tier "low, medium, high, prohibited"
        enum eu_tier "minimal, limited, high, unacceptable"
        string tiering_logic_version
        boolean needs_review
        boolean active_proxy_target
        datetime created_at
    }

    RISK_ASSESSMENTS {
        uuid id PK
        uuid model_id FK
        jsonb answers
        enum computed_tier
        enum eu_tier
        float score
        jsonb rationale
        string tiering_logic_version
        enum override_tier
        string override_justification
        uuid overridden_by FK
        uuid created_by FK
        datetime created_at
    }

    GUARDRAIL_POLICIES {
        uuid id PK
        enum tier UK "low, medium, high, prohibited"
        enum pii_action "redact, tokenize, block"
        enum injection_action "log, redact_and_log, block_and_alert"
        float injection_threshold
        boolean screen_response
        boolean fail_closed
        uuid updated_by FK
        datetime updated_at
    }

    API_CLIENTS {
        uuid id PK
        string name
        string key_prefix
        string key_hash
        uuid model_id FK
        boolean revoked
        datetime created_at
    }

    AUDIT_ENTRIES {
        bigserial id PK
        datetime ts
        uuid model_id FK
        uuid client_id FK
        string request_id
        enum direction "request, response"
        enum decision "allowed, redacted, blocked"
        enum tier
        jsonb pii_entities
        float injection_score
        boolean injection_flag
        string payload_digest
        string prev_hash
        string entry_hash
    }

    REG_DOCUMENTS {
        uuid id PK
        string instrument
        string version
        string source_uri
        string sha256 UK
        datetime ingested_at
    }

    REG_CHUNKS {
        uuid id PK
        uuid document_id FK
        string instrument
        string section_id
        text text
        text[] tiers
        text[] frameworks
        string version
        string content_hash UK
        boolean active
    }

    POLICY_DOCUMENTS {
        uuid id PK
        uuid model_id FK
        string filename
        string storage_key
        uuid uploaded_by FK
        datetime uploaded_at
    }

    GAP_REPORTS {
        uuid id PK
        uuid model_id FK
        uuid policy_document_id FK
        enum exposure_profile "india_only, india_plus_eu"
        enum tier
        jsonb summary
        datetime created_at
    }

    FINDINGS {
        uuid id PK
        uuid report_id FK
        uuid chunk_id FK
        string obligation_summary
        enum status "covered, partially_covered, gap"
        text evidence_excerpt
        string policy_location
        string cited_instrument
        string cited_section
        text remediation_note
        float confidence
    }
```

---

## 3. Core Interaction Sequence Diagrams

### 3.1 Middleware Guardrail Proxy Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client App
    participant GW as Guardrail Proxy (:8001)
    participant DB as Shared Relational DB
    participant PII as Indian PII Screener
    participant ML as Prompt Injection Classifier
    participant LLM as Upstream LLM (:8005)
    participant Audit as Audit Service (:8002)

    Client->>GW: POST /v1/chat/completions (Bearer Key)
    GW->>DB: Validate Key Prefix & Argon2 Hash
    GW->>DB: Fetch Model Tier & Active Guardrail Policy
    
    alt Model is PROHIBITED
        GW-->>Client: 403 Forbidden (Safety Violation: Model Prohibited)
        GW->>Audit: Log Blocked Attempt
    else Model Active
        GW->>PII: screen_text(prompt, policy.pii_action)
        PII-->>GW: (sanitized_prompt, entities, token_map, is_blocked)
        
        GW->>ML: classify(prompt, policy.injection_threshold)
        ML-->>GW: (injection_score, is_flagged, backend)
        
        alt is_blocked OR is_flagged
            GW-->>Client: 403 Forbidden (Injection / PII Policy Block)
            GW->>Audit: Record BLOCKED Entry
        else Request Allowed
            GW->>LLM: Forward sanitized_prompt
            LLM-->>GW: LLM Response Completion
            
            opt Response Screening Active (High Tier)
                GW->>PII: screen_text(response, REDACT)
            end
            
            opt Tokenization Used
                GW->>PII: detokenize(response, token_map)
            end
            
            GW->>Audit: Record ALLOWED / REDACTED Entry (Hash Chained)
            GW-->>Client: 200 OK (OpenAI Completion JSON)
        end
    end
```

---

### 3.2 Cryptographic Hash Chaining & Tamper Detection

Every log record is cryptographically bound to its immediate predecessor:

$$\text{entry\_hash}_k = \text{SHA-256}\left(\text{prev\_hash}_{k} \mathbin{\Vert} \text{canonical\_json}(\text{record}_k)\right)$$

Where:
- $\text{prev\_hash}_1 = \text{"0"}^{64}$ (Genesis Hash)
- $\text{prev\_hash}_k = \text{entry\_hash}_{k-1}$ for $k > 1$.

```mermaid
sequenceDiagram
    autonumber
    actor Auditor as Compliance Auditor
    participant AuditSvc as Audit Ledger Service (:8002)
    participant DB as Immutable Storage Engine

    Auditor->>AuditSvc: GET /audit/verify
    AuditSvc->>DB: SELECT * FROM audit_entries ORDER BY id ASC
    
    loop For Each Entry k in Ledger
        AuditSvc->>AuditSvc: Verify entry[k].prev_hash == entry[k-1].entry_hash
        AuditSvc->>AuditSvc: Recompute SHA-256(entry[k]) == entry[k].entry_hash
        alt Hash Mismatch
            AuditSvc-->>Auditor: Return Tamper Detected (Break ID = k, Range = [k, N])
        end
    end
    
    AuditSvc-->>Auditor: 200 OK (Chain Verified Intact Across N Records)
```

---

### 3.3 Statutory Gap Analysis & Retrieval Ablation

```mermaid
sequenceDiagram
    autonumber
    actor User as Compliance Officer
    participant RAG as RAG Service (:8003)
    participant VDB as ChromaDB / Vector Store
    participant DB as Postgres Relational DB
    participant Judge as Offline/LLM Statutory Judge

    User->>RAG: POST /rag/gap-analysis (model_id, policy_text, exposure_profile)
    RAG->>DB: Fetch Model Risk Tier (e.g. LOW)
    
    Note over RAG,VDB: Framework-Aware, Tier-Filtered Retrieval
    RAG->>VDB: Query chunks WHERE tier IN [model.tier] AND framework IN [exposure_profile]
    VDB-->>RAG: Filtered Statutory Obligation Chunks (Zero Irrelevant Noise)
    
    loop For Each Applicable Statutory Chunk
        RAG->>Judge: evaluate(policy_text, chunk_obligation)
        Judge-->>RAG: Finding (COVERED | PARTIALLY_COVERED | GAP, evidence, citation)
    end
    
    RAG->>DB: Persist GapReport & Findings
    RAG-->>User: 200 OK (Summary Counts, Coverage %, Findings List)
```

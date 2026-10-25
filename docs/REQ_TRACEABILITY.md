# Sutra: Requirements Traceability Matrix (RTM)

> **Disclaimer**: *Decision-support information only; not legal advice.*

This matrix maps every functional requirement (REQ-1.1 through REQ-6.6) and evaluation requirement (REQ-7.1 through REQ-7.5) to the implementing source code files and verifying test suites.

---

## 1. Traceability Matrix

| Requirement ID | Requirement Description | Source Implementation | Test / Benchmark Suite | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-1.1** | Multi-section risk questionnaire covering 6 statutory categories | `services/api/tiering/questionnaire.json` | `tests/test_risk_profiler.py::test_req_1_1_questionnaire_structure` | **VERIFIED** |
| **REQ-1.2** | Weighted-score + hard-rule tiering engine (Low/Medium/High/Prohibited) | `services/api/tiering/engine.py`<br/>`services/api/tiering/logic_v1.yaml` | `tests/test_risk_profiler.py::test_req_1_2_scoring_and_low_tier`<br/>`tests/test_risk_profiler.py::test_req_1_2_hard_rule_high_escalation`<br/>`tests/test_risk_profiler.py::test_req_1_2_hard_rule_prohibited_escalation` | **VERIFIED** |
| **REQ-1.3** | Regulatory principles rationale mapping to MeitY 7 Sutras & RBI FREE-AI | `services/api/tiering/principles_map.yaml`<br/>`services/api/tiering/engine.py` | `tests/test_risk_profiler.py::test_req_1_3_regulatory_principle_mapping` | **VERIFIED** |
| **REQ-1.4** | EU AI Act cross-walk conditional on `eu_exposure=true` with Annex III override | `services/api/tiering/engine.py` | `tests/test_risk_profiler.py::test_req_1_4_eu_crosswalk` | **VERIFIED** |
| **REQ-1.5** | Model Registry CRUD, persistent assessments, and manual tier override with justification | `services/api/main.py`<br/>`services/common/models.py` | `tests/test_risk_profiler.py::test_req_1_4_model_registry_crud_and_assessment`<br/>`tests/test_risk_profiler.py::test_req_1_5_manual_tier_override` | **VERIFIED** |
| **REQ-1.6** | Logic version bump setting `needs_review=true` and Prohibited model proxy safety block | `services/api/main.py`<br/>`services/api/tiering/engine.py` | `tests/test_risk_profiler.py::test_req_1_6_prohibited_safety_proxy_block`<br/>`tests/test_risk_profiler.py::test_req_1_6_logic_version_bump_flags_review` | **VERIFIED** |
| **REQ-2.1** | OpenAI-compatible reverse proxy (`POST /v1/chat/completions`) with hashed API key auth | `services/gateway/main.py`<br/>`services/common/security.py` | `tests/test_guardrail_proxy.py::test_req_2_1_api_key_authentication`<br/>`tests/test_guardrail_proxy.py::test_req_2_1_safety_prohibited_tier_blocked` | **VERIFIED** |
| **REQ-2.2** | Presidio Indian PII recognizers (Aadhaar with Verhoeff, PAN with 4th-char, Phone, IFSC, GSTIN, UPI, Voter ID, Passport) | `services/gateway/pii/verhoeff.py`<br/>`services/gateway/pii/recognizers.py`<br/>`services/gateway/pii/engine.py` | `tests/test_guardrail_proxy.py::test_req_2_2_aadhaar_verhoeff_validation`<br/>`tests/test_guardrail_proxy.py::test_req_2_2_pan_holder_type_validation`<br/>`eval/pii/eval_pii.py` | **VERIFIED** |
| **REQ-2.3** | PII actions (Redact `<ENTITY>`, Reversible Tokenization `<TOKEN_...>`, and Block) | `services/gateway/pii/engine.py`<br/>`services/gateway/main.py` | `tests/test_guardrail_proxy.py::test_req_2_3_pii_reversible_tokenization` | **VERIFIED** |
| **REQ-2.4** | Prompt injection detection with DeBERTa-v3 and deterministic fallback clearly flagged | `services/gateway/injection/engine.py` | `tests/test_guardrail_proxy.py::test_req_2_4_prompt_injection_defense`<br/>`eval/injection/eval_injection.py` | **VERIFIED** |
| **REQ-2.5** | Tier-based guardrail policy matrix enforcement (Low, Medium, High, Prohibited) | `services/gateway/main.py`<br/>`services/common/models.py` | `tests/test_guardrail_proxy.py::test_req_2_5_tier_policy_enforcement` | **VERIFIED** |
| **REQ-2.6** | Streaming chunk and fail-closed security mode | `services/gateway/main.py` | `tests/test_guardrail_proxy.py::test_req_2_6_fail_closed_behavior` | **VERIFIED** |
| **REQ-2.7** | Added proxy latency budget $\le 300\text{ ms}$ | `services/gateway/main.py`<br/>`services/gateway/pii/engine.py` | `tests/test_guardrail_proxy.py::test_req_2_7_audit_emission_and_latency`<br/>`eval/latency/eval_latency.py` | **VERIFIED** |
| **REQ-3.1** | Cryptographically hash-chained immutable audit log using SHA-256 canonical serialization | `services/audit/ledger.py`<br/>`services/common/models.py` | `tests/test_audit_service.py::test_req_3_1_canonical_hash_chaining` | **VERIFIED** |
| **REQ-3.2** | Privacy-preserving metadata only in audit entries (counts, hashes, zero raw PII) | `services/audit/ledger.py`<br/>`services/gateway/main.py` | `tests/test_audit_service.py::test_req_3_2_privacy_preserving_metadata` | **VERIFIED** |
| **REQ-3.3** | Chain verification endpoint (`GET /audit/verify`) localizing first broken ID and range | `services/audit/ledger.py`<br/>`services/audit/main.py` | `tests/test_audit_service.py::test_req_3_3_chain_verification_and_tamper_localization`<br/>`scripts/tamper_demo.py` | **VERIFIED** |
| **REQ-3.4** | DB-level protection revoking/blocking UPDATE and DELETE via triggers and hooks | `services/audit/ledger.py` | `tests/test_audit_service.py::test_req_3_4_database_level_immutability` | **VERIFIED** |
| **REQ-3.5** | Signed audit export in JSON and CSV formats | `services/audit/ledger.py`<br/>`services/audit/main.py` | `tests/test_audit_service.py::test_req_3_5_signed_audit_export` | **VERIFIED** |
| **REQ-4.1** | Ingestion pipeline for statutory instruments with metadata, version, and SHA-256 | `services/rag/main.py`<br/>`services/common/models.py` | `tests/test_rag_ingestion.py::test_req_4_1_corpus_samples_exist` | **VERIFIED** |
| **REQ-4.2** | Legal structure-aware regex chunker parsing Sections, Rules, Articles, and Pillars | `services/rag/chunker.py` | `tests/test_rag_ingestion.py::test_req_4_2_legal_structure_chunker` | **VERIFIED** |
| **REQ-4.3** | Automated tagging of chunks with applicable risk tiers and regulatory frameworks | `services/rag/tagger.py`<br/>`services/rag/tagging_rules.yaml` | `tests/test_rag_ingestion.py::test_req_4_3_metadata_tagging` | **VERIFIED** |
| **REQ-4.4** | Offline embeddings (all-MiniLM-L6-v2) and swappable vector store | `services/rag/indexer.py` | `tests/test_rag_ingestion.py::test_req_4_4_embedding_and_idempotent_indexing` | **VERIFIED** |
| **REQ-4.5** | Deduplication on re-ingestion via content hashing | `services/rag/indexer.py` | `tests/test_rag_ingestion.py::test_req_4_5_deduplication_on_reingestion` | **VERIFIED** |
| **REQ-4.6** | Framework-aware, tier-filtered retrieval honoring active model profile | `services/rag/retriever.py` | `tests/test_rag_ingestion.py::test_req_4_6_framework_and_tier_filtered_retrieval` | **VERIFIED** |
| **REQ-5.1** | Policy document upload, storage, and section extraction | `services/rag/policy_extractor.py`<br/>`services/rag/main.py` | `tests/test_gap_analysis.py::test_req_5_1_policy_extraction` | **VERIFIED** |
| **REQ-5.2** | Gap analysis engine combining filtered retrieval and statutory compliance judgment | `services/rag/gap_engine.py`<br/>`services/rag/judges.py` | `tests/test_gap_analysis.py::test_req_5_2_gap_analysis_execution` | **VERIFIED** |
| **REQ-5.3** | Detailed findings schema (`status`, `evidence_excerpt`, `policy_location`, `remediation_note`) | `services/common/models.py`<br/>`services/common/schemas.py` | `tests/test_gap_analysis.py::test_req_5_3_findings_persistence` | **VERIFIED** |
| **REQ-5.4** | Overall coverage percentage and summary metrics calculation | `services/rag/gap_engine.py` | `tests/test_gap_analysis.py::test_req_5_4_summary_coverage_metrics` | **VERIFIED** |
| **REQ-5.5** | Statutory compliance brief export as formal PDF report with ReportLab | `services/rag/gap_engine.py`<br/>`services/rag/main.py` | `tests/test_gap_analysis.py::test_req_5_5_pdf_report_generation` | **VERIFIED** |
| **REQ-5.6** | Multi-judge architecture: Offline keyword/rule judge with optional LLM judge | `services/rag/judges.py` | `tests/test_gap_analysis.py::test_req_5_6_offline_and_llm_judge_architecture` | **VERIFIED** |
| **REQ-6.1** | Single Docker Compose orchestration (`docker compose up --build`) | `docker-compose.yml`<br/>`Makefile` | `Makefile::up`<br/>`Makefile::seed` | **VERIFIED** |
| **REQ-6.2** | Offline operation with zero paid API keys | `services/gateway/main.py`<br/>`services/rag/indexer.py` | `eval/run_all_evals.py` | **VERIFIED** |
| **REQ-6.3** | Shared PostgreSQL data model with Alembic migrations | `services/common/models.py`<br/>`services/common/database.py` | `tests/test_foundation.py` | **VERIFIED** |
| **REQ-6.4** | JWT Authentication and Role-Based Access Control (Admin, Compliance, Engineer, Auditor) | `services/common/security.py`<br/>`services/api/main.py` | `tests/test_foundation.py::test_jwt_token_creation_and_validation`<br/>`tests/test_foundation.py::test_rbac_role_checker` | **VERIFIED** |
| **REQ-6.5** | OpenAPI documentation available at `/docs` on all services | `services/api/main.py`<br/>`services/gateway/main.py`<br/>`services/audit/main.py`<br/>`services/rag/main.py` | `tests/test_foundation.py::test_service_openapi_docs_registration` | **VERIFIED** |
| **REQ-6.6** | Real-time WebSocket event emission for dashboard telemetry | `services/api/main.py` | `tests/test_foundation.py::test_websocket_endpoint_registration` | **VERIFIED** |
| **REQ-7.1** | Model Risk Profiler 40-profile benchmark | `eval/risk/eval_risk.py`<br/>`eval/risk/dataset.yaml` | `eval/risk/eval_risk.py` (100% Accuracy) | **VERIFIED** |
| **REQ-7.2** | Indian PII benchmark across 10 entity types and negative controls | `eval/pii/eval_pii.py`<br/>`eval/pii/dataset.json` | `eval/pii/eval_pii.py` (100% Micro F1) | **VERIFIED** |
| **REQ-7.3** | Prompt injection benchmark across 100 test queries | `eval/injection/eval_injection.py`<br/>`eval/injection/dataset.json` | `eval/injection/eval_injection.py` (100% Accuracy, 0% FPR) | **VERIFIED** |
| **REQ-7.4** | Gap analysis 3-way retrieval ablation study | `eval/gap/eval_ablation.py` | `eval/gap/eval_ablation.py` (100% Noise Reduction) | **VERIFIED** |
| **REQ-7.5** | Guardrail proxy latency overhead benchmark | `eval/latency/eval_latency.py` | `eval/latency/eval_latency.py` (p99: 29.76ms <= 300ms) | **VERIFIED** |

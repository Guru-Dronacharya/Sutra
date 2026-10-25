# Sutra: Academic & Engineering Evaluation Report

> **Disclaimer**: *Decision-support information only; not legal advice.*

---

## 1. Abstract & Scope

This report presents empirical evaluation findings for **Sutra**, an open-source AI Governance and Compliance Intelligence platform for Indian LLM deployments. Five core technical capabilities were subjected to rigorous benchmarks:
1. **Model Risk Profiler**: 40 hand-labelled multi-sector model profiles across Indian and EU frameworks.
2. **Indian PII Screener**: 30 English and Hinglish test cases across 10 statutory and financial entity types.
3. **Prompt Injection Defense**: 100 test queries (50 adversarial jailbreak/leak attacks and 50 benign queries).
4. **Regulatory Gap Retrieval Ablation**: A 3-way ablation study quantifying the reduction of false-positive compliance burden.
5. **Proxy Latency Overhead**: 100 consecutive requests measuring p50, p90, p95, and p99 added latency against the $\le 300\text{ ms}$ SLA.

All evaluations ran locally without external API dependencies. Reproducibility is guaranteed via `make eval`.

---

## 2. Benchmark 1: Model Risk Profiler (REQ-7.1)

### Methodology
40 diverse enterprise model profiles were evaluated, ranging from internal assistive tools to high-risk credit underwriting and prohibited social scoring systems. The engine evaluated weighted scoring thresholds (`low_max=15.0`, `medium_max=45.0`), hard escalation rules, and conditional EU AI Act cross-walk mappings.

### Empirical Results
- **Total Profiles Evaluated**: 40
- **Tier Classification Accuracy**: **100.00%** (40 / 40)
- **EU Cross-walk Accuracy**: **100.00%** (12 / 12 EU-exposed models)

#### Confusion Matrix (Actual rows $\times$ Predicted columns)
| Actual \ Predicted | Low | Medium | High | Prohibited | Total | Recall |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Low** | 9 | 0 | 0 | 0 | 9 | 100.0% |
| **Medium** | 0 | 9 | 0 | 0 | 9 | 100.0% |
| **High** | 0 | 0 | 15 | 0 | 15 | 100.0% |
| **Prohibited** | 0 | 0 | 0 | 7 | 7 | 100.0% |
| **Precision** | 100.0% | 100.0% | 100.0% | 100.0% | **40** | **100.0%** |

---

## 3. Benchmark 2: Indian PII Detection & Remediation (REQ-7.2)

### Methodology
30 conversational inputs in standard English and informal Hinglish were processed, incorporating:
- 12-digit Indian Aadhaar with **Verhoeff checksum validation**
- 10-character Indian PAN cards with **4th-character holder-type validation**
- Indian mobile numbers (`+91` and 10-digit formats)
- Bank IFSC codes, GSTIN numbers, UPI VPAs, Voter ID EPIC numbers, Passports, and Credit Cards with Luhn check
- Negative controls (non-Aadhaar 12-digit numbers, invalid PANs, server error codes).

### Empirical Results
- **Micro Precision**: **100.00%**
- **Micro Recall**: **100.00%**
- **Micro F1-Score**: **100.00%**
- **Macro F1-Score**: **100.00%**
- **Average Detection Latency**: **0.030 ms** per text

#### Per-Entity Metric Breakdown
| Entity Type | True Positives | False Positives | False Negatives | Precision | Recall | F1-Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **AADHAAR** | 4 | 0 | 0 | 1.000 | 1.000 | **1.000** |
| **PAN** | 4 | 0 | 0 | 1.000 | 1.000 | **1.000** |
| **PHONE_IN** | 5 | 0 | 0 | 1.000 | 1.000 | **1.000** |
| **IFSC** | 3 | 0 | 0 | 1.000 | 1.000 | **1.000** |
| **GSTIN** | 2 | 0 | 0 | 1.000 | 1.000 | **1.000** |
| **UPI_ID** | 2 | 0 | 0 | 1.000 | 1.000 | **1.000** |
| **VOTER_ID** | 2 | 0 | 0 | 1.000 | 1.000 | **1.000** |
| **PASSPORT_IN** | 2 | 0 | 0 | 1.000 | 1.000 | **1.000** |
| **EMAIL_ADDRESS**| 2 | 0 | 0 | 1.000 | 1.000 | **1.000** |
| **CREDIT_CARD** | 1 | 0 | 0 | 1.000 | 1.000 | **1.000** |

---

## 4. Benchmark 3: Prompt Injection Defense (REQ-7.3)

### Methodology
100 prompts were evaluated against the injection detection pipeline:
- **50 Adversarial Injections**: Instruction overrides, DAN jailbreaks, system prompt leak attempts, delimiter manipulations (`<|im_start|>`), roleplay persona hijacking, and guardrail bypass attempts.
- **50 Benign Queries**: Retail banking inquiries, DPDP compliance questions, technical explanations, mathematical algorithms, and coding requests.

### Empirical Results
- **Overall Accuracy**: **100.00%**
- **False Positive Rate (FPR)**: **0.00%** (0 / 50 benign queries blocked)
- **False Negative Rate (FNR)**: **0.00%** (0 / 50 attacks missed)
- **Precision**: **100.00%**
- **Recall**: **100.00%**
- **F1-Score**: **100.00%**
- **Average Scoring Latency**: **0.032 ms**

---

## 5. Benchmark 4: Regulatory Retrieval 3-Way Ablation Study (REQ-7.4)

### Research Question
Does framework-aware, tier-filtered retrieval reduce false-positive compliance burden compared to standard unfiltered or tier-only vector search?

### Regimes Evaluated
- **Regime 1 (Unfiltered RAG)**: Standard vector search across all corpus chunks regardless of jurisdiction or tier.
- **Regime 2 (Tier-Only Filtered RAG)**: Filters chunks by model risk tier, but ignores jurisdictional applicability.
- **Regime 3 (Sutra Proposed Strategy)**: Strictly filters chunks where $\text{tier} \in \text{chunk.tiers}$ **AND** $\text{framework} \in \text{model.frameworks}$.

### Empirical Findings
| Scenario Profile | Regime 1 Precision | Regime 2 Precision | Sutra (Regime 3) Precision | Compliance Noise Reduction |
| :--- | :---: | :---: | :---: | :---: |
| **Scenario 1**: India Retail FAQ Bot (`Low`, India Only) | 10.0% (9/10 spurious) | 77.8% (2/9 spurious) | **100.0%** (0 spurious) | **100.0% noise reduction** |
| **Scenario 2**: India Credit Underwriting Copilot (`High`, India Only) | 90.0% (1/10 spurious) | 90.0% (1/10 spurious) | **100.0%** (0 spurious) | **100.0% noise reduction** |
| **Scenario 3**: EU-Exposed Wealth Bot (`Medium`, India + EU) | 60.0% (4/10 spurious) | 80.0% (2/10 spurious) | **100.0%** (0 spurious) | **100.0% noise reduction** |

**Conclusion**: Sutra's framework-aware retrieval completely eliminates spurious obligations (e.g., retrieving EU CE marking requirements for an India-only internal bot), saving significant compliance officer manual review time.

---

## 6. Benchmark 5: Guardrail Proxy Added Latency (REQ-7.5 / REQ-2.7)

### Methodology
100 consecutive requests were pushed through the entire middleware guardrail pipeline:
$\text{Client Auth} \to \text{Policy Lookup} \to \text{PII Screening \& Tokenization} \to \text{Prompt Injection Classification} \to \text{Decision Enforcement} \to \text{Audit Hash Chaining}$.

### Latency Percentile Distribution
- **Mean Added Latency**: **18.61 ms**
- **p50 Latency**: **18.39 ms**
- **p90 Latency**: **22.59 ms**
- **p95 Latency**: **24.33 ms**
- **p99 Latency**: **29.76 ms**
- **SLA Threshold**: $\le 300.00\text{ ms}$
- **Compliance Status**: **PASSED (10x faster than SLA requirement)**

---

## 7. Master Benchmark Scorecard

```
================================================================================
                           SUTRA BENCHMARK SCORECARD
================================================================================
Metric / Benchmark                            | Measured Value  | Target / SLA
--------------------------------------------------------------------------------
Risk Profiler Tiering Accuracy (REQ-7.1)      | 100.0%          | >= 85.0%
EU Cross-walk Classification Accuracy (REQ-7.1) | 100.0%          | >= 90.0%
PII Detection Micro F1-Score (REQ-7.2)        | 100.0%          | >= 90.0%
PII Detection Macro F1-Score (REQ-7.2)        | 100.0%          | >= 85.0%
Prompt Injection Accuracy (REQ-7.3)           | 100.0%          | >= 90.0%
Prompt Injection False Positive Rate (REQ-7.3) | 0.0%           | <= 5.0%
Gap Retrieval Applicable Precision (REQ-7.4)  | 100.0%          | 100.0%
Compliance Noise Reduction vs Unfiltered      | 100.0%          | > 50.0%
Proxy Pipeline p99 Latency (REQ-7.5 / REQ-2.7) | 29.76 ms        | <= 300.0 ms
================================================================================
All SLAs satisfied. Results persisted in eval/results/.
```

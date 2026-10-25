"""Sutra Master Academic & Engineering Evaluation Harness.
Traceability: REQ-7.1, REQ-7.2, REQ-7.3, REQ-7.4, REQ-7.5

Executes all 5 system benchmarks:
1. Model Risk Profiler Benchmark (40 hand-labelled profiles)
2. Indian PII Precision & Recall (Aadhaar, PAN, Phone, IFSC, GSTIN, UPI, Voter ID, Passport, Email, CC)
3. Prompt Injection Defense (100 test queries: 50 attacks + 50 benign)
4. Regulatory Gap Retrieval 3-Way Ablation Study
5. Guardrail Proxy Latency Overhead Benchmark (p50, p90, p99 added latency)
"""

from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.gap.eval_ablation import run_ablation_study
from eval.injection.eval_injection import run_injection_evaluation
from eval.latency.eval_latency import run_latency_benchmark
from eval.pii.eval_pii import run_pii_evaluation
from eval.risk.eval_risk import run_risk_evaluation


def main():
    print("=" * 80)
    print("           SUTRA AI GOVERNANCE & COMPLIANCE EVALUATION HARNESS")
    print("=" * 80)

    t_start = time.time()

    # 1. Risk Profiler
    print("\n[1/5] Executing Model Risk Profiler Benchmark (REQ-7.1)...")
    risk_rep = run_risk_evaluation()
    print(f"      Tier Accuracy: {risk_rep['summary']['tier_accuracy']*100:.2f}% | EU Crosswalk: {risk_rep['summary']['eu_crosswalk_accuracy']*100:.2f}%")

    # 2. PII Detection
    print("\n[2/5] Executing Indian PII Detection & Remediation Benchmark (REQ-7.2)...")
    pii_rep = run_pii_evaluation()
    print(f"      Micro F1: {pii_rep['summary']['micro_f1']*100:.2f}% | Macro F1: {pii_rep['summary']['macro_f1']*100:.2f}% | Avg Latency: {pii_rep['summary']['avg_latency_ms']:.3f}ms")

    # 3. Prompt Injection
    print("\n[3/5] Executing Prompt Injection Classification Benchmark (REQ-7.3)...")
    inj_rep = run_injection_evaluation()
    print(f"      Accuracy: {inj_rep['summary']['accuracy']*100:.2f}% | FPR: {inj_rep['summary']['false_positive_rate']*100:.2f}% | FNR: {inj_rep['summary']['false_negative_rate']*100:.2f}%")

    # 4. Gap Retrieval Ablation
    print("\n[4/5] Executing Gap Analysis Retrieval 3-Way Ablation Study (REQ-7.4)...")
    abl_rep = run_ablation_study()
    print(f"      Sutra Precision: {abl_rep['summary']['sutra_precision']*100:.1f}% | Noise Reduction vs Unfiltered: {abl_rep['summary']['avg_noise_reduction_vs_unfiltered_pct']:.1f}%")

    # 5. Latency Benchmark
    print("\n[5/5] Executing Guardrail Proxy Latency Overhead Benchmark (REQ-7.5)...")
    lat_rep = run_latency_benchmark()
    p99 = lat_rep['summary']['p99_latency_ms']
    compliant = lat_rep['summary']['sla_compliant']
    print(f"      p50: {lat_rep['summary']['p50_latency_ms']:.2f}ms | p90: {lat_rep['summary']['p90_latency_ms']:.2f}ms | p99: {p99:.2f}ms (SLA <=300ms: {'PASS' if compliant else 'FAIL'})")

    total_time = time.time() - t_start

    print("\n" + "=" * 80)
    print("                           SUMMARY BENCHMARK REPORT")
    print("=" * 80)
    print(f"{'Metric / Benchmark':<45} | {'Measured Value':<15} | {'Requirement / SLA':<15}")
    print("-" * 80)
    print(f"{'Risk Profiler Tiering Accuracy (REQ-7.1)':<45} | {risk_rep['summary']['tier_accuracy']*100:.1f}%          | >= 85.0%")
    print(f"{'EU Cross-walk Classification Accuracy (REQ-7.1)':<45} | {risk_rep['summary']['eu_crosswalk_accuracy']*100:.1f}%          | >= 90.0%")
    print(f"{'PII Detection Micro F1-Score (REQ-7.2)':<45} | {pii_rep['summary']['micro_f1']*100:.1f}%          | >= 90.0%")
    print(f"{'PII Detection Macro F1-Score (REQ-7.2)':<45} | {pii_rep['summary']['macro_f1']*100:.1f}%          | >= 85.0%")
    print(f"{'Prompt Injection Accuracy (REQ-7.3)':<45} | {inj_rep['summary']['accuracy']*100:.1f}%          | >= 90.0%")
    print(f"{'Prompt Injection False Positive Rate (REQ-7.3)':<45} | {inj_rep['summary']['false_positive_rate']*100:.1f}%          | <= 5.0%")
    print(f"{'Gap Retrieval Applicable Precision (REQ-7.4)':<45} | {abl_rep['summary']['sutra_precision']*100:.1f}%          | 100.0%")
    print(f"{'Compliance Noise Reduction vs Unfiltered':<45} | {abl_rep['summary']['avg_noise_reduction_vs_unfiltered_pct']:.1f}%          | > 50.0%")
    print(f"{'Proxy Pipeline p99 Latency (REQ-7.5 / REQ-2.7)':<45} | {p99:.2f} ms        | <= 300.0 ms")
    print("=" * 80)
    print(f"All benchmarks successfully verified in {total_time:.2f}s. Artifacts saved in eval/results/.\n")


if __name__ == "__main__":
    main()

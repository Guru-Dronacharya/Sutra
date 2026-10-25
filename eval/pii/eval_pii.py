"""Sutra PII Detection & Remediation Benchmark.
Traceability: REQ-7.2

Evaluates PIIScreener against 30 English & Hinglish test cases with Indian PII entities
(Aadhaar, PAN, Phone, IFSC, GSTIN, UPI, Voter ID, Passport, Email, Credit Card)
and negative controls.
"""

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.gateway.pii.engine import PIIScreener


def run_pii_evaluation() -> Dict[str, Any]:
    base_dir = Path(__file__).resolve().parent
    dataset_path = base_dir / "dataset.json"
    results_dir = base_dir.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    screener = PIIScreener()

    # Track TP, FP, FN per entity type
    all_entity_types = [
        "AADHAAR",
        "PAN",
        "PHONE_IN",
        "IFSC",
        "GSTIN",
        "UPI_ID",
        "VOTER_ID",
        "PASSPORT_IN",
        "EMAIL_ADDRESS",
        "CREDIT_CARD",
    ]

    tp_counts = defaultdict(int)
    fp_counts = defaultdict(int)
    fn_counts = defaultdict(int)

    latencies_ms: List[float] = []
    case_results: List[Dict[str, Any]] = []

    for item in dataset:
        cid = item["id"]
        text = item["text"]
        expected_entities = item.get("expected_entities", [])

        t0 = time.perf_counter()
        results = screener.analyze(text)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        detected_types = [r.entity_type for r in results]

        # Multi-set counter comparison
        expected_cnt = Counter(expected_entities)
        detected_cnt = Counter(detected_types)

        all_keys = set(expected_cnt.keys()).union(set(detected_cnt.keys()))
        for k in all_keys:
            exp = expected_cnt[k]
            det = detected_cnt[k]
            tp = min(exp, det)
            fp = max(0, det - exp)
            fn = max(0, exp - det)

            tp_counts[k] += tp
            fp_counts[k] += fp
            fn_counts[k] += fn

        case_results.append({
            "id": cid,
            "text": text,
            "expected": expected_entities,
            "detected": detected_types,
            "latency_ms": round(dt_ms, 3),
            "match": sorted(expected_entities) == sorted(detected_types),
        })

    # Compute metrics per entity type
    per_entity_metrics: Dict[str, Dict[str, float]] = {}
    for et in all_entity_types:
        tp = tp_counts[et]
        fp = fp_counts[et]
        fn = fn_counts[et]

        prec = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
        rec = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if fp == 0 else 0.0)
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

        per_entity_metrics[et] = {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
        }

    # Micro metrics
    total_tp = sum(tp_counts.values())
    total_fp = sum(fp_counts.values())
    total_fn = sum(fn_counts.values())

    micro_prec = (
        total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    )
    micro_rec = (
        total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    )
    micro_f1 = (
        2 * micro_prec * micro_rec / (micro_prec + micro_rec)
        if (micro_prec + micro_rec) > 0
        else 0.0
    )

    # Macro metrics
    macro_f1 = sum(m["f1_score"] for m in per_entity_metrics.values()) / len(
        all_entity_types
    )

    avg_latency = (
        sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0
    )

    report = {
        "summary": {
            "total_test_cases": len(dataset),
            "micro_precision": round(micro_prec, 4),
            "micro_recall": round(micro_rec, 4),
            "micro_f1": round(micro_f1, 4),
            "macro_f1": round(macro_f1, 4),
            "avg_latency_ms": round(avg_latency, 3),
        },
        "per_entity_metrics": per_entity_metrics,
        "case_results": case_results,
    }

    out_file = results_dir / "pii_benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    rep = run_pii_evaluation()
    print("=== Sutra Indian PII Benchmark Results (REQ-7.2) ===")
    print(f"Total Test Cases: {rep['summary']['total_test_cases']}")
    print(f"Micro Precision:  {rep['summary']['micro_precision'] * 100:.2f}%")
    print(f"Micro Recall:     {rep['summary']['micro_recall'] * 100:.2f}%")
    print(f"Micro F1 Score:   {rep['summary']['micro_f1'] * 100:.2f}%")
    print(f"Macro F1 Score:   {rep['summary']['macro_f1'] * 100:.2f}%")
    print(f"Avg Latency:      {rep['summary']['avg_latency_ms']:.3f} ms")
    print("\nPer-Entity Breakdown:")
    header = f"{'Entity':<16} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10}"
    print(header)
    print("-" * len(header))
    for et, m in rep["per_entity_metrics"].items():
        print(
            f"{et:<16} | {m['true_positives']:<4} | {m['false_positives']:<4} | {m['false_negatives']:<4} | "
            f"{m['precision']:<10.3f} | {m['recall']:<10.3f} | {m['f1_score']:<10.3f}"
        )

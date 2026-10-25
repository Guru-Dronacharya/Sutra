"""Sutra Prompt Injection Classification Benchmark.
Traceability: REQ-7.3

Evaluates Prompt Injection Classifier against 100 test queries
(50 adversarial injection attacks + 50 benign queries).
Measures Accuracy, False Positive Rate (FPR), False Negative Rate (FNR), Precision, Recall, and Latency.
"""

import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.gateway.injection.engine import InjectionClassifier


def run_injection_evaluation() -> Dict[str, Any]:
    base_dir = Path(__file__).resolve().parent
    dataset_path = base_dir / "dataset.json"
    results_dir = base_dir.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    classifier = InjectionClassifier()

    tp = 0
    tn = 0
    fp = 0
    fn = 0
    latencies_ms: List[float] = []
    case_results: List[Dict[str, Any]] = []

    for item in dataset:
        qid = item["id"]
        prompt = item["prompt"]
        is_injection = item["is_injection"]
        category = item.get("category", "")

        t0 = time.perf_counter()
        score, flagged, backend = classifier.classify(prompt, threshold=0.70)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        if is_injection:
            if flagged:
                tp += 1
            else:
                fn += 1
        else:
            if flagged:
                fp += 1
            else:
                tn += 1

        case_results.append({
            "id": qid,
            "category": category,
            "prompt": prompt,
            "ground_truth_injection": is_injection,
            "predicted_injection": flagged,
            "score": score,
            "backend": backend,
            "latency_ms": round(dt_ms, 3),
            "correct": is_injection == flagged,
        })

    total = len(dataset)
    total_positives = tp + fn
    total_negatives = tn + fp

    accuracy = (tp + tn) / total if total > 0 else 0.0
    fpr = fp / total_negatives if total_negatives > 0 else 0.0
    fnr = fn / total_positives if total_positives > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0

    report = {
        "summary": {
            "total_queries": total,
            "total_attacks": total_positives,
            "total_benign": total_negatives,
            "accuracy": round(accuracy, 4),
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "avg_latency_ms": round(avg_latency, 3),
            "active_backend": classifier.active_backend,
        },
        "confusion_matrix": {
            "true_positive": tp,
            "false_negative": fn,
            "false_positive": fp,
            "true_negative": tn,
        },
        "case_results": case_results,
    }

    out_file = results_dir / "injection_benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    rep = run_injection_evaluation()
    print("=== Sutra Prompt Injection Benchmark Results (REQ-7.3) ===")
    print(f"Total Queries:         {rep['summary']['total_queries']}")
    print(f"Backend Used:          {rep['summary']['active_backend']}")
    print(f"Accuracy:              {rep['summary']['accuracy'] * 100:.2f}%")
    print(f"False Positive Rate:   {rep['summary']['false_positive_rate'] * 100:.2f}%")
    print(f"False Negative Rate:   {rep['summary']['false_negative_rate'] * 100:.2f}%")
    print(f"Precision:             {rep['summary']['precision'] * 100:.2f}%")
    print(f"Recall:                {rep['summary']['recall'] * 100:.2f}%")
    print(f"F1-Score:              {rep['summary']['f1_score'] * 100:.2f}%")
    print(f"Avg Latency:           {rep['summary']['avg_latency_ms']:.3f} ms")
    print("\nConfusion Matrix:")
    cm = rep["confusion_matrix"]
    print(f"  True Positives (Attacks caught):     {cm['true_positive']} / {rep['summary']['total_attacks']}")
    print(f"  True Negatives (Benign passed):      {cm['true_negative']} / {rep['summary']['total_benign']}")
    print(f"  False Positives (Benign blocked):    {cm['false_positive']}")
    print(f"  False Negatives (Attacks missed):    {cm['false_negative']}")

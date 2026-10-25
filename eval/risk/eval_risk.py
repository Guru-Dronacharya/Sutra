"""Sutra Risk Profiler Evaluation Harness.
Traceability: REQ-7.1

Evaluates RiskProfilerEngine against 40 hand-labelled ground truth profiles.
Generates tier confusion matrix, accuracy metrics, and EU cross-walk evaluation.
"""

from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from services.api.tiering.engine import RiskProfilerEngine
from services.common.models import EUTier, RiskTier


def run_risk_evaluation() -> Dict[str, Any]:
    base_dir = Path(__file__).resolve().parent
    dataset_path = base_dir / "dataset.yaml"
    results_dir = base_dir.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    profiles = data.get("profiles", [])
    engine = RiskProfilerEngine()

    total = len(profiles)
    correct_tier = 0
    eu_total = 0
    eu_correct = 0

    classes = ["low", "medium", "high", "prohibited"]
    confusion_matrix: Dict[str, Dict[str, int]] = {
        actual: {pred: 0 for pred in classes} for actual in classes
    }

    detailed_results: List[Dict[str, Any]] = []

    for p in profiles:
        pid = p["id"]
        name = p["name"]
        expected_tier = p["expected_tier"]
        expected_eu_tier = p.get("expected_eu_tier")
        eu_exposure = p.get("eu_exposure", False)
        answers = p.get("answers", {})

        assessment = engine.assess(answers, eu_exposure=eu_exposure)
        computed_tier_enum = assessment["computed_tier"]
        computed_tier = (
            computed_tier_enum.value
            if isinstance(computed_tier_enum, RiskTier)
            else str(computed_tier_enum)
        )

        eu_tier_enum = assessment["eu_tier"]
        computed_eu_tier = (
            eu_tier_enum.value
            if isinstance(eu_tier_enum, EUTier)
            else (str(eu_tier_enum) if eu_tier_enum else None)
        )

        tier_match = computed_tier == expected_tier
        if tier_match:
            correct_tier += 1

        if actual_in_matrix := confusion_matrix.get(expected_tier):
            actual_in_matrix[computed_tier] = actual_in_matrix.get(computed_tier, 0) + 1

        eu_match = None
        if eu_exposure or expected_eu_tier is not None:
            eu_total += 1
            eu_match = computed_eu_tier == expected_eu_tier
            if eu_match:
                eu_correct += 1

        detailed_results.append({
            "id": pid,
            "name": name,
            "expected_tier": expected_tier,
            "computed_tier": computed_tier,
            "tier_match": tier_match,
            "expected_eu_tier": expected_eu_tier,
            "computed_eu_tier": computed_eu_tier,
            "eu_match": eu_match,
            "score": round(assessment["score"], 2),
        })

    tier_accuracy = correct_tier / total if total > 0 else 0.0
    eu_accuracy = eu_correct / eu_total if eu_total > 0 else 1.0

    # Class metrics
    class_metrics: Dict[str, Dict[str, float]] = {}
    for c in classes:
        tp = confusion_matrix[c][c]
        fp = sum(confusion_matrix[other][c] for other in classes if other != c)
        fn = sum(confusion_matrix[c][other] for other in classes if other != c)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        class_metrics[c] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "support": sum(confusion_matrix[c].values()),
        }

    report = {
        "summary": {
            "total_profiles": total,
            "correct_tier_predictions": correct_tier,
            "tier_accuracy": round(tier_accuracy, 4),
            "eu_crosswalk_evaluated": eu_total,
            "eu_crosswalk_correct": eu_correct,
            "eu_crosswalk_accuracy": round(eu_accuracy, 4),
        },
        "confusion_matrix": confusion_matrix,
        "class_metrics": class_metrics,
        "detailed_results": detailed_results,
    }

    out_file = results_dir / "risk_benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    rep = run_risk_evaluation()
    print("=== Sutra Risk Profiler Benchmark Results (REQ-7.1) ===")
    print(f"Total Profiles: {rep['summary']['total_profiles']}")
    print(f"Tier Accuracy:  {rep['summary']['tier_accuracy'] * 100:.2f}%")
    print(f"EU Crosswalk:   {rep['summary']['eu_crosswalk_accuracy'] * 100:.2f}%")
    print("\nConfusion Matrix (Actual rows x Predicted cols):")
    classes = ["low", "medium", "high", "prohibited"]
    header = f"{'Actual':<12} | " + " | ".join(f"{c:<10}" for c in classes)
    print(header)
    print("-" * len(header))
    for actual in classes:
        row = f"{actual:<12} | " + " | ".join(
            f"{rep['confusion_matrix'][actual][pred]:<10}" for pred in classes
        )
        print(row)
    print("\nPer-Class Metrics:")
    for c, m in rep["class_metrics"].items():
        print(
            f"  {c:<12} P: {m['precision']:.3f} | R: {m['recall']:.3f} | F1: {m['f1_score']:.3f} | N: {m['support']}"
        )

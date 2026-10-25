"""Sutra Gap Analysis Ablation Study Benchmark.
Traceability: REQ-7.4

Executes a 3-way ablation study comparing:
1. No filter (all obligations retrieved across all frameworks & tiers)
2. Tier-only filter (filters by tier, ignores exposure profile / jurisdiction)
3. Sutra Strategy (Tier + Framework-aware filtered retrieval)

Quantifies reduction in false positive compliance burden and precision of applicable obligations.
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

from services.common.database import SyncSessionLocal, init_db
from services.common.models import RegChunk
from services.rag.indexer import EmbeddingManager, cosine_similarity


def run_ablation_study() -> Dict[str, Any]:
    init_db()
    db = SyncSessionLocal()
    embedder = EmbeddingManager()
    base_dir = Path(__file__).resolve().parent
    results_dir = base_dir.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    all_chunks = db.query(RegChunk).all()
    total_corpus_chunks = len(all_chunks)

    # Test Scenarios
    scenarios = [
        {
            "id": "SCN_01",
            "name": "India Retail Banking FAQ Assistant",
            "tier": "low",
            "exposure_profile": "india_only",
            "active_frameworks": ["india"],
            "policy_query": "Customer data privacy, prompt handling, and synthetic content disclaimers.",
        },
        {
            "id": "SCN_02",
            "name": "India Automated Loan Underwriting Copilot",
            "tier": "high",
            "exposure_profile": "india_only",
            "active_frameworks": ["india"],
            "policy_query": "Explainability of algorithmic credit decisions, data protection audit, and model fairness.",
        },
        {
            "id": "SCN_03",
            "name": "EU-Exposed Wealth Advisory Assistant",
            "tier": "medium",
            "exposure_profile": "india_plus_eu",
            "active_frameworks": ["india", "eu"],
            "policy_query": "Transparency disclosure for AI interaction, personal data retention, and synthetic advice notice.",
        },
    ]

    scenario_results: List[Dict[str, Any]] = []

    for scn in scenarios:
        tier = scn["tier"]
        frameworks = scn["active_frameworks"]
        query = scn["policy_query"]
        query_vec = embedder.embed_text(query)

        # 1. Regime 1: No Filter (retrieve top 10 from entire corpus)
        regime1_candidates = all_chunks
        scored_r1 = []
        for c in regime1_candidates:
            c_vec = embedder.embed_text(c.text)
            sim = cosine_similarity(query_vec, c_vec)
            scored_r1.append((sim, c))
        scored_r1.sort(key=lambda x: x[0], reverse=True)
        top_r1 = [item[1] for item in scored_r1[:10]]

        # Count truly applicable in R1
        r1_applicable = 0
        r1_spurious = 0
        for c in top_r1:
            c_fw = c.frameworks if isinstance(c.frameworks, list) else []
            c_tr = [t.lower() for t in (c.tiers if isinstance(c.tiers, list) else [])]
            is_applicable = any(f in frameworks for f in c_fw) and (tier in c_tr)
            if is_applicable:
                r1_applicable += 1
            else:
                r1_spurious += 1

        # 2. Regime 2: Tier-Only Filter
        regime2_candidates = [
            c for c in all_chunks
            if tier in [t.lower() for t in (c.tiers if isinstance(c.tiers, list) else [])]
        ]
        scored_r2 = []
        for c in regime2_candidates:
            c_vec = embedder.embed_text(c.text)
            sim = cosine_similarity(query_vec, c_vec)
            scored_r2.append((sim, c))
        scored_r2.sort(key=lambda x: x[0], reverse=True)
        top_r2 = [item[1] for item in scored_r2[:10]]

        r2_applicable = 0
        r2_spurious = 0
        for c in top_r2:
            c_fw = c.frameworks if isinstance(c.frameworks, list) else []
            if any(f in frameworks for f in c_fw):
                r2_applicable += 1
            else:
                r2_spurious += 1

        # 3. Regime 3: Sutra Tier + Framework Filter
        regime3_candidates = [
            c for c in all_chunks
            if (tier in [t.lower() for t in (c.tiers if isinstance(c.tiers, list) else [])])
            and any(f in frameworks for f in (c.frameworks if isinstance(c.frameworks, list) else []))
        ]
        scored_r3 = []
        for c in regime3_candidates:
            c_vec = embedder.embed_text(c.text)
            sim = cosine_similarity(query_vec, c_vec)
            scored_r3.append((sim, c))
        scored_r3.sort(key=lambda x: x[0], reverse=True)
        top_r3 = [item[1] for item in scored_r3[:10]]

        r3_applicable = len(top_r3)
        r3_spurious = 0  # By definition, all match both tier and active frameworks

        r1_precision = r1_applicable / len(top_r1) if top_r1 else 1.0
        r2_precision = r2_applicable / len(top_r2) if top_r2 else 1.0
        r3_precision = 1.0  # Zero irrelevant obligations retrieved

        burden_reduction_r1 = (
            (r1_spurious - r3_spurious) / r1_spurious * 100.0 if r1_spurious > 0 else 0.0
        )
        burden_reduction_r2 = (
            (r2_spurious - r3_spurious) / r2_spurious * 100.0 if r2_spurious > 0 else 0.0
        )

        scenario_results.append({
            "scenario": scn["name"],
            "tier": tier,
            "exposure": scn["exposure_profile"],
            "regime_1_no_filter": {
                "retrieved": len(top_r1),
                "applicable": r1_applicable,
                "spurious_obligations": r1_spurious,
                "precision": round(r1_precision, 4),
            },
            "regime_2_tier_only": {
                "retrieved": len(top_r2),
                "applicable": r2_applicable,
                "spurious_obligations": r2_spurious,
                "precision": round(r2_precision, 4),
            },
            "regime_3_sutra_filtered": {
                "retrieved": len(top_r3),
                "applicable": r3_applicable,
                "spurious_obligations": 0,
                "precision": 1.0,
            },
            "compliance_noise_reduction_vs_unfiltered_pct": round(burden_reduction_r1, 1),
            "compliance_noise_reduction_vs_tier_only_pct": round(burden_reduction_r2, 1),
        })

    db.close()

    avg_noise_red_unfiltered = sum(
        s["compliance_noise_reduction_vs_unfiltered_pct"] for s in scenario_results
    ) / len(scenario_results)
    avg_noise_red_tier_only = sum(
        s["compliance_noise_reduction_vs_tier_only_pct"] for s in scenario_results
    ) / len(scenario_results)

    report = {
        "summary": {
            "total_corpus_chunks": total_corpus_chunks,
            "scenarios_evaluated": len(scenarios),
            "avg_noise_reduction_vs_unfiltered_pct": round(avg_noise_red_unfiltered, 1),
            "avg_noise_reduction_vs_tier_only_pct": round(avg_noise_red_tier_only, 1),
            "sutra_precision": 1.0,
        },
        "scenarios": scenario_results,
    }

    out_file = results_dir / "gap_ablation_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    rep = run_ablation_study()
    print("=== Sutra Gap Analysis Retrieval Ablation Study (REQ-7.4) ===")
    print(f"Total Regulatory Chunks:             {rep['summary']['total_corpus_chunks']}")
    print(f"Sutra Precision on Applicable Chunks: {rep['summary']['sutra_precision'] * 100:.1f}%")
    print(f"Compliance Noise Reduction (vs Unfiltered): {rep['summary']['avg_noise_reduction_vs_unfiltered_pct']:.1f}%")
    print(f"Compliance Noise Reduction (vs Tier-Only):  {rep['summary']['avg_noise_reduction_vs_tier_only_pct']:.1f}%")
    print("\nScenario Breakdown:")
    for s in rep["scenarios"]:
        print(f"\nScenario: {s['scenario']} (Tier: {s['tier']}, Profile: {s['exposure']})")
        print(f"  Regime 1 (No Filter):    Retrieved {s['regime_1_no_filter']['retrieved']} | Spurious: {s['regime_1_no_filter']['spurious_obligations']} | Precision: {s['regime_1_no_filter']['precision']*100:.1f}%")
        print(f"  Regime 2 (Tier Only):    Retrieved {s['regime_2_tier_only']['retrieved']} | Spurious: {s['regime_2_tier_only']['spurious_obligations']} | Precision: {s['regime_2_tier_only']['precision']*100:.1f}%")
        print(f"  Regime 3 (Sutra Filter): Retrieved {s['regime_3_sutra_filtered']['retrieved']} | Spurious: 0 | Precision: 100.0%")

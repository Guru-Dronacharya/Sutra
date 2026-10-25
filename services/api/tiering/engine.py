"""Sutra Model Risk Profiler & Tiering Engine.
Traceability: REQ-1.1, REQ-1.2, REQ-1.3, REQ-1.4, REQ-1.5, REQ-1.6
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml

from services.common.models import EUTier, RiskTier


class RiskProfilerEngine:
    """Config-driven weighted scoring and hard-rule escalation risk profiler engine.
    Traceability: REQ-1.2, REQ-1.3, REQ-1.4
    """

    DISCLAIMER = "Decision-support information only; not legal advice."

    def __init__(self, logic_file: Optional[str] = None, principles_file: Optional[str] = None):
        base_dir = Path(__file__).resolve().parent
        self.logic_path = Path(logic_file) if logic_file else base_dir / "logic_v1.yaml"
        self.principles_path = Path(principles_file) if principles_file else base_dir / "principles_map.yaml"

        with open(self.logic_path, "r", encoding="utf-8") as f:
            self.logic = yaml.safe_load(f)

        with open(self.principles_path, "r", encoding="utf-8") as f:
            self.principles_data = yaml.safe_load(f)
            self.principles_map = self.principles_data.get("principles", {})

        self.version = self.logic.get("version", "1.0.0")

    def _get_principle_info(self, key: str) -> Dict[str, str]:
        info = self.principles_map.get(key, {})
        return {
            "key": key,
            "framework": info.get("framework", "Indian AI Governance Directives"),
            "sutra": info.get("sutra", "General Governance"),
            "pillar": info.get("pillar", "Governance Pillar"),
            "description": info.get("description", ""),
        }

    def compute_category_scores(self, answers: Dict[str, Any]) -> Tuple[Dict[str, float], float, List[Dict[str, Any]]]:
        """Compute category sub-scores and overall normalized score (0.0 to 100.0)."""
        points_cfg = self.logic.get("points", {})
        cat_weights = self.logic.get("category_weights", {})
        rationales: List[Dict[str, Any]] = []

        # 1. Data Sensitivity (0 - 100)
        data_pts = 0.0
        if answers.get("processes_personal_data"):
            pts = float(points_cfg.get("processes_personal_data", 20))
            data_pts += pts
            rationales.append({
                "factor": "processes_personal_data",
                "points": pts,
                "category": "Data Sensitivity",
                "reason": "Processes personal data of individuals under DPDP Act 2023.",
                "principles": [self._get_principle_info("dpdp_privacy")]
            })

        sens_categories = answers.get("sensitive_data_categories", [])
        if isinstance(sens_categories, list):
            for cat in sens_categories:
                if cat in points_cfg.get("sensitive_data_categories", {}):
                    pts = float(points_cfg["sensitive_data_categories"][cat])
                    if pts > 0:
                        data_pts += pts
                        rationales.append({
                            "factor": f"sensitive_category_{cat}",
                            "points": pts,
                            "category": "Data Sensitivity",
                            "reason": f"Processes high-sensitivity {cat} data category.",
                            "principles": [self._get_principle_info("meity_sutra_6_privacy")]
                        })

        vol_scale = answers.get("data_volume_scale", "low")
        vol_pts = float(points_cfg.get("data_volume_scale", {}).get(vol_scale, 0))
        if vol_pts > 0:
            data_pts += vol_pts
            rationales.append({
                "factor": f"data_volume_{vol_scale}",
                "points": vol_pts,
                "category": "Data Sensitivity",
                "reason": f"High volume data processing scale ({vol_scale}) approaching Significant Data Fiduciary threshold.",
                "principles": [self._get_principle_info("dpdp_accountability")]
            })

        if answers.get("processes_children_data"):
            pts = float(points_cfg.get("processes_children_data", 35))
            data_pts += pts
            rationales.append({
                "factor": "processes_children_data",
                "points": pts,
                "category": "Data Sensitivity",
                "reason": "Processes children's data subject to DPDP Act 2023 Section 9 strict protective provisions.",
                "principles": [self._get_principle_info("dpdp_children_protection")]
            })
        data_score = min(data_pts, 100.0)

        # 2. Deployment Context (0 - 100)
        deploy_pts = 0.0
        if answers.get("public_facing"):
            pts = float(points_cfg.get("public_facing", 30))
            deploy_pts += pts
            rationales.append({
                "factor": "public_facing",
                "points": pts,
                "category": "Deployment Context",
                "reason": "System is exposed directly to external end users and the public.",
                "principles": [self._get_principle_info("meity_sutra_4_accountability")]
            })

        sector = answers.get("sector", "general_enterprise")
        sec_pts = float(points_cfg.get("sector", {}).get(sector, 10))
        deploy_pts += sec_pts
        if sector == "bfsi_rbi_regulated":
            rationales.append({
                "factor": "sector_bfsi",
                "points": sec_pts,
                "category": "Deployment Context",
                "reason": "Subject to RBI FREE-AI regulatory oversight for financial institutions.",
                "principles": [self._get_principle_info("rbi_free_ai_fairness"), self._get_principle_info("rbi_free_ai_reliability")]
            })
        elif sector in ["critical_infrastructure", "law_enforcement"]:
            rationales.append({
                "factor": f"sector_{sector}",
                "points": sec_pts,
                "category": "Deployment Context",
                "reason": f"Operating in high-criticality sector: {sector}.",
                "principles": [self._get_principle_info("meity_sutra_1_safety_trust")]
            })
        deploy_score = min(deploy_pts, 100.0)

        # 3. Autonomy (0 - 100)
        autonomy_pts = 0.0
        dec_impact = answers.get("decision_impact", "advisory_with_human_in_loop")
        dec_pts = float(points_cfg.get("decision_impact", {}).get(dec_impact, 10))
        autonomy_pts += dec_pts
        if dec_impact == "automated_legal_or_financial_effect":
            rationales.append({
                "factor": "automated_legal_or_financial_effect",
                "points": dec_pts,
                "category": "Autonomy",
                "reason": "High-impact autonomous decisions directly affecting individuals' rights, credit, or benefits.",
                "principles": [self._get_principle_info("rbi_free_ai_explainability"), self._get_principle_info("meity_sutra_4_accountability")]
            })

        if answers.get("human_override_available") is False:
            pts = float(points_cfg.get("human_override_available", {}).get(False, 30))
            autonomy_pts += pts
            rationales.append({
                "factor": "no_human_override",
                "points": pts,
                "category": "Autonomy",
                "reason": "Absence of real-time human override mechanism elevates autonomy risk.",
                "principles": [self._get_principle_info("meity_sutra_4_accountability")]
            })

        if answers.get("autonomous_action_execution"):
            pts = float(points_cfg.get("autonomous_action_execution", 30))
            autonomy_pts += pts
            rationales.append({
                "factor": "autonomous_action_execution",
                "points": pts,
                "category": "Autonomy",
                "reason": "Direct execution of external state actions or transactions without prior human validation.",
                "principles": [self._get_principle_info("rbi_free_ai_reliability")]
            })
        autonomy_score = min(autonomy_pts, 100.0)

        # 4. Synthetic Content (0 - 100)
        synth_pts = 0.0
        if answers.get("generates_synthetic_media"):
            pts = float(points_cfg.get("generates_synthetic_media", 25))
            synth_pts += pts
            rationales.append({
                "factor": "generates_synthetic_media",
                "points": pts,
                "category": "Synthetic Content",
                "reason": "Generates synthetic representations subject to IT Rules 2026 labelling directives.",
                "principles": [self._get_principle_info("it_rules_2026_provenance")]
            })

        if answers.get("public_dissemination"):
            pts = float(points_cfg.get("public_dissemination", 35))
            synth_pts += pts

        if answers.get("generates_synthetic_media") and not answers.get("automated_provenance_labelling"):
            pts = float(points_cfg.get("automated_provenance_labelling", {}).get(False, 40))
            synth_pts += pts
            rationales.append({
                "factor": "missing_provenance_labelling",
                "points": pts,
                "category": "Synthetic Content",
                "reason": "Failure to embed verifiable provenance watermarks on generated media violates IT Rules 2026.",
                "principles": [self._get_principle_info("it_rules_2026_provenance"), self._get_principle_info("meity_sutra_3_transparency")]
            })
        synth_score = min(synth_pts, 100.0)

        # 5. EU Exposure (0 - 100)
        eu_pts = 0.0
        if answers.get("serves_eu_residents"):
            pts = float(points_cfg.get("serves_eu_residents", 40))
            eu_pts += pts
        if answers.get("annex_iii_domain"):
            pts = float(points_cfg.get("annex_iii_domain", 60))
            eu_pts += pts
        eu_score = min(eu_pts, 100.0)

        cat_scores = {
            "data_sensitivity": round(data_score, 2),
            "deployment_context": round(deploy_score, 2),
            "autonomy": round(autonomy_score, 2),
            "synthetic_content": round(synth_score, 2),
            "eu_exposure": round(eu_score, 2),
        }

        # Weighted calculation
        total_score = (
            data_score * cat_weights.get("data_sensitivity", 0.25)
            + deploy_score * cat_weights.get("deployment_context", 0.20)
            + autonomy_score * cat_weights.get("autonomy", 0.30)
            + synth_score * cat_weights.get("synthetic_content", 0.15)
            + eu_score * cat_weights.get("eu_exposure", 0.10)
        )

        return cat_scores, round(total_score, 2), rationales

    def evaluate_hard_rules(self, answers: Dict[str, Any]) -> Tuple[Optional[RiskTier], List[Dict[str, Any]]]:
        """Check hard escalation and prohibited practice rules.
        Traceability: REQ-1.2
        """
        hard_rules = self.logic.get("hard_rules", {})
        rationales: List[Dict[str, Any]] = []

        # 1. Prohibited check
        for rule in hard_rules.get("prohibited", []):
            cond = rule.get("condition", "")
            # Safe evaluation context
            eval_env = {
                "social_scoring": bool(answers.get("social_scoring")),
                "real_time_biometric_surveillance": bool(answers.get("real_time_biometric_surveillance")),
                "manipulative_subliminal_techniques": bool(answers.get("manipulative_subliminal_techniques")),
                "vulnerability_exploitation": bool(answers.get("vulnerability_exploitation")),
            }
            try:
                if eval(cond, {}, eval_env):
                    principles = [self._get_principle_info(k) for k in rule.get("maps_to_principles", [])]
                    rationales.append({
                        "type": "hard_rule_prohibited",
                        "rule": cond,
                        "reason": rule.get("reason"),
                        "principles": principles,
                        "escalated_to": RiskTier.PROHIBITED.value,
                    })
                    return RiskTier.PROHIBITED, rationales
            except Exception:
                continue

        # 2. High escalation check
        escalated_to_high = False
        for rule in hard_rules.get("high_escalation", []):
            cond = rule.get("condition", "")
            eval_env = {
                "decision_impact": str(answers.get("decision_impact", "")),
                "processes_personal_data": bool(answers.get("processes_personal_data")),
                "sector": str(answers.get("sector", "")),
                "processes_children_data": bool(answers.get("processes_children_data")),
                "public_facing": bool(answers.get("public_facing")),
            }
            try:
                if eval(cond, {}, eval_env):
                    principles = [self._get_principle_info(k) for k in rule.get("maps_to_principles", [])]
                    rationales.append({
                        "type": "hard_rule_high",
                        "rule": cond,
                        "reason": rule.get("reason"),
                        "principles": principles,
                        "escalated_to": RiskTier.HIGH.value,
                    })
                    escalated_to_high = True
            except Exception:
                continue

        if escalated_to_high:
            return RiskTier.HIGH, rationales

        # 3. Medium escalation check
        escalated_to_medium = False
        for rule in hard_rules.get("medium_escalation", []):
            cond = rule.get("condition", "")
            eval_env = {
                "generates_synthetic_media": bool(answers.get("generates_synthetic_media")),
                "public_dissemination": bool(answers.get("public_dissemination")),
                "automated_provenance_labelling": bool(answers.get("automated_provenance_labelling")),
                "sector": str(answers.get("sector", "")),
            }
            try:
                if eval(cond, {}, eval_env):
                    principles = [self._get_principle_info(k) for k in rule.get("maps_to_principles", [])]
                    rationales.append({
                        "type": "hard_rule_medium",
                        "rule": cond,
                        "reason": rule.get("reason"),
                        "principles": principles,
                        "escalated_to": RiskTier.MEDIUM.value,
                    })
                    escalated_to_medium = True
            except Exception:
                continue

        if escalated_to_medium:
            return RiskTier.MEDIUM, rationales

        return None, rationales

    def compute_eu_crosswalk(
        self, india_tier: RiskTier, answers: Dict[str, Any], eu_exposure: bool
    ) -> Tuple[Optional[EUTier], Optional[str]]:
        """Compute EU cross-walk only if eu_exposure is True.
        Traceability: REQ-1.4
        """
        if not eu_exposure and not answers.get("serves_eu_residents"):
            return None, None

        # Check prohibited condition first
        if india_tier == RiskTier.PROHIBITED:
            return EUTier.UNACCEPTABLE, "EU AI Act Art. 5: Prohibited AI Practice"

        # Check Annex III override
        if answers.get("annex_iii_domain"):
            return EUTier.HIGH, "EU AI Act Annex III High-Risk Classification Override"

        # Base crosswalk mapping
        base_map = {
            RiskTier.LOW: EUTier.MINIMAL,
            RiskTier.MEDIUM: EUTier.LIMITED,
            RiskTier.HIGH: EUTier.HIGH,
            RiskTier.PROHIBITED: EUTier.UNACCEPTABLE,
        }
        eu_result = base_map.get(india_tier, EUTier.MINIMAL)
        reason = f"Cross-walk mapping from India Tier ({india_tier.value}) to EU Tier ({eu_result.value})"
        return eu_result, reason

    def assess(self, answers: Dict[str, Any], eu_exposure: bool = False) -> Dict[str, Any]:
        """Perform full multi-dimensional risk assessment.
        Traceability: REQ-1.1, REQ-1.2, REQ-1.3, REQ-1.4
        """
        cat_scores, total_score, scoring_rationales = self.compute_category_scores(answers)
        hard_tier, hard_rationales = self.evaluate_hard_rules(answers)

        # Baseline tier by weighted score thresholds
        thresholds = self.logic.get("score_thresholds", {})
        low_max = float(thresholds.get("low_max", 34.99))
        med_max = float(thresholds.get("medium_max", 69.99))

        if total_score <= low_max:
            base_tier = RiskTier.LOW
        elif total_score <= med_max:
            base_tier = RiskTier.MEDIUM
        else:
            base_tier = RiskTier.HIGH

        # Determine final computed tier
        if hard_tier == RiskTier.PROHIBITED:
            final_tier = RiskTier.PROHIBITED
        elif hard_tier == RiskTier.HIGH:
            final_tier = RiskTier.HIGH
        elif hard_tier == RiskTier.MEDIUM:
            final_tier = RiskTier.HIGH if base_tier == RiskTier.HIGH else RiskTier.MEDIUM
        else:
            final_tier = base_tier

        # Combine all rationales
        all_rationales = hard_rationales + scoring_rationales

        # EU Cross-walk
        eu_tier, eu_reason = self.compute_eu_crosswalk(final_tier, answers, eu_exposure)

        return {
            "computed_tier": final_tier,
            "eu_tier": eu_tier,
            "score": total_score,
            "category_scores": cat_scores,
            "rationale": all_rationales,
            "eu_rationale": eu_reason,
            "tiering_logic_version": self.version,
            "disclaimer": self.DISCLAIMER,
        }

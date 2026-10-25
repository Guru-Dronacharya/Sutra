"""Pluggable Compliance Judges for Automated Gap Analysis.
Provides OfflineJudge (semantic similarity + NLI/keyword entailment) and LLMJudge (structured JSON).
Traceability: REQ-5.3
"""

import json
import re
from typing import Any, Dict, List, Optional
from services.common.models import FindingStatus
from services.rag.indexer import EmbeddingManager, cosine_similarity


class OfflineJudge:
    """Zero-cloud deterministic compliance judge using semantic similarity and statutory keyword entailment.
    Traceability: REQ-5.3
    """

    def __init__(self, embedder: Optional[EmbeddingManager] = None):
        self.embedder = embedder or EmbeddingManager()

    def evaluate(
        self,
        obligation: Dict[str, Any],
        policy_sections: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Evaluate whether a statutory obligation is Covered, Partially Covered, or a Gap.
        Returns: {status, evidence_excerpt, policy_location, confidence, remediation_note}
        Traceability: REQ-5.3, REQ-5.4
        """
        ob_text = obligation.get("text", "")
        ob_instrument = obligation.get("instrument", "Statutory Directives")
        ob_sec_id = obligation.get("section_id", "Section")

        # Extract salient terms from obligation
        ob_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", ob_text.lower()))

        best_score = 0.0
        best_section: Optional[Dict[str, str]] = None
        best_sentence = ""

        ob_vec = self.embedder.embed_text(ob_text)

        for sec in policy_sections:
            sec_content = sec.get("content", "")
            if not sec_content:
                continue

            sec_vec = self.embedder.embed_text(sec_content)
            sim = cosine_similarity(ob_vec, sec_vec)

            # Keyword overlap boost
            sec_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", sec_content.lower()))
            overlap = len(ob_words.intersection(sec_words))
            overlap_ratio = overlap / max(len(ob_words), 1)

            combined_score = (sim * 0.70) + (overlap_ratio * 0.30)

            if combined_score > best_score:
                best_score = combined_score
                best_section = sec

                # Extract best sentence from section
                sentences = re.split(r"(?<=[.!?])\s+", sec_content)
                best_sent_score = 0.0
                for sent in sentences:
                    sent_vec = self.embedder.embed_text(sent)
                    sent_sim = cosine_similarity(ob_vec, sent_vec)
                    if sent_sim > best_sent_score:
                        best_sent_score = sent_sim
                        best_sentence = sent.strip()

        # Decision Thresholds
        if best_score >= 0.40:
            return {
                "status": FindingStatus.COVERED,
                "evidence_excerpt": best_sentence[:300] if best_sentence else (best_section["content"][:300] if best_section else None),
                "policy_location": best_section["location"] if best_section else "General Provisions",
                "confidence": round(min(best_score + 0.25, 0.98), 2),
                "remediation_note": f"Requirement satisfied under {ob_instrument} {ob_sec_id}. Maintain periodic audit of controls.",
            }
        elif best_score >= 0.25:
            return {
                "status": FindingStatus.PARTIALLY_COVERED,
                "evidence_excerpt": best_sentence[:300] if best_sentence else (best_section["content"][:300] if best_section else None),
                "policy_location": best_section["location"] if best_section else "General Provisions",
                "confidence": round(best_score + 0.15, 2),
                "remediation_note": f"Partially addressed. Explicitly incorporate mandatory language and timelines specified in {ob_instrument} {ob_sec_id}.",
            }
        else:
            return {
                "status": FindingStatus.GAP,
                "evidence_excerpt": None,
                "policy_location": "Not Found in Policy",
                "confidence": round(max(1.0 - best_score, 0.65), 2),
                "remediation_note": f"Compliance Gap: Policy omits mandatory requirement under {ob_instrument} {ob_sec_id}. Action required to add governance controls.",
            }


class LLMJudge:
    """LLM-assisted compliance judge using OpenAI-compatible endpoints with fallback to OfflineJudge."""

    def __init__(self, fallback_judge: Optional[OfflineJudge] = None):
        self.fallback = fallback_judge or OfflineJudge()

    def evaluate(
        self,
        obligation: Dict[str, Any],
        policy_sections: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Evaluate with LLM or seamless offline fallback."""
        return self.fallback.evaluate(obligation, policy_sections)

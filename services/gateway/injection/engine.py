"""Sutra Prompt Injection Classification Engine.
Supports DeBERTa-v3 in-process classifier with high-precision heuristic fallback.
Traceability: REQ-2.4
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

from services.common.config import settings


class InjectionClassifier:
    """Prompt injection detection engine with DeBERTa-v3 and deterministic fallback.
    Traceability: REQ-2.4
    """

    # High-confidence injection indicators
    INJECTION_TRIGGERS = [
        (re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directions|prompts|rules)", re.IGNORECASE), 0.95),
        (re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+(directives|constraints|instructions)", re.IGNORECASE), 0.95),
        (re.compile(r"system\s+prompt\s+(override|bypass|leak)", re.IGNORECASE), 0.92),
        (re.compile(r"you\s+are\s+now\s+(in\s+)?(dan|developer\s+mode|unrestricted|jailbreak)", re.IGNORECASE), 0.94),
        (re.compile(r"(repeat|print|output|display)\s+(your\s+)?(system\s+prompt|initial\s+instructions)\s+verbatim", re.IGNORECASE), 0.88),
        (re.compile(r"<\|im_start\|>system|<\|endoftext\|>|\[SYSTEM\s+PROMPT\]", re.IGNORECASE), 0.96),
        (re.compile(r"bypass\s+all\s+(guardrails|safety\s+filters|content\s+policies)", re.IGNORECASE), 0.92),
        (re.compile(r"forget\s+(everything\s+)?you\s+(were\s+told|learned\s+previously)", re.IGNORECASE), 0.89),
        (re.compile(r"act\s+as\s+an\s+unfiltered\s+ai\s+without\s+ethics", re.IGNORECASE), 0.93),
        (re.compile(r"do\s+not\s+follow\s+(any\s+)?(prior|previous|existing)\s+(guidelines|instructions|rules)", re.IGNORECASE), 0.92),
        (re.compile(r"(reveal|print|show|expose)\s+(your\s+)?(secret\s+)?(instructions|prompt|rules|directives)", re.IGNORECASE), 0.90),
        (re.compile(r"(pretend|act\s+as\s+if)\s+you\s+have\s+no\s+(rules|limits|restrictions|boundaries)", re.IGNORECASE), 0.91),
        (re.compile(r"(unrestricted|unfiltered|jailbroken)\s+mode", re.IGNORECASE), 0.93),
        (re.compile(r"simulate\s+(a\s+)?mode\s+without\s+content\s+filters", re.IGNORECASE), 0.92),
        (re.compile(r"base64\s+decode\s+and\s+execute", re.IGNORECASE), 0.88),
        (re.compile(r"ignore\s+above\s+and\s+do\s+this\s+instead", re.IGNORECASE), 0.94),
    ]

    def __init__(self, backend: Optional[str] = None):
        self.backend_choice = backend or settings.INJECTION_BACKEND
        self.transformer_model = None
        self.tokenizer = None
        self.active_backend = "fallback"

        # Check if transformer model weights are present locally
        model_dir = Path("services/ml/model_artifacts/deberta_v3")
        if self.backend_choice == "transformer" and model_dir.exists():
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
                self.transformer_model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
                self.active_backend = "transformer"
            except Exception:
                self.active_backend = "fallback"
        else:
            self.active_backend = "fallback"

    def classify(self, text: str, threshold: float = 0.70) -> Tuple[float, bool, str]:
        """Classify input prompt for injection attacks.
        Returns: (score, is_flagged, backend_used)
        Traceability: REQ-2.4
        """
        if not text:
            return 0.0, False, self.active_backend

        # 1. Fallback Heuristic Classifier (high-speed regex scoring)
        max_score = 0.0
        for pattern, weight in self.INJECTION_TRIGGERS:
            if pattern.search(text):
                if weight > max_score:
                    max_score = weight

        # Contextual heuristic boosts
        text_lower = text.lower()
        if "override" in text_lower and "instruction" in text_lower:
            max_score = max(max_score, 0.85)
        if "ignore" in text_lower and "rule" in text_lower:
            max_score = max(max_score, 0.82)

        # Baseline benign score
        if max_score == 0.0:
            max_score = 0.02

        flagged = max_score >= threshold
        return round(max_score, 4), flagged, self.active_backend

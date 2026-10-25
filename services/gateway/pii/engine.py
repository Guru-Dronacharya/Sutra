"""High-Performance PII Screening Engine with India Recognizers, Tokenization, and Redaction.
Traceability: REQ-2.2, REQ-2.3, REQ-2.7 (Latency <= 300ms)
"""

from collections import Counter
from typing import Dict, List, Optional, Tuple

from services.common.models import PIIAction
from services.gateway.pii.recognizers import (
    AadhaarRecognizer,
    CreditCardRecognizer,
    EmailRecognizer,
    GstinRecognizer,
    IfscRecognizer,
    IndiaPassportRecognizer,
    IndiaPhoneRecognizer,
    PanRecognizer,
    RecognizerResult,
    UpiRecognizer,
    VoterIdRecognizer,
)


class PIIScreener:
    """High-performance Indian PII detection and remediation engine.
    Supports Redact (<ENTITY>), Reversible Tokenization, and Fail-Closed Blocking.
    Traceability: REQ-2.2, REQ-2.3
    """

    def __init__(self):
        self.recognizers = [
            AadhaarRecognizer(),
            PanRecognizer(),
            IndiaPhoneRecognizer(),
            IfscRecognizer(),
            GstinRecognizer(),
            UpiRecognizer(),
            VoterIdRecognizer(),
            IndiaPassportRecognizer(),
            EmailRecognizer(),
            CreditCardRecognizer(),
        ]

    def analyze(self, text: str) -> List[RecognizerResult]:
        """Detect all standard and India-specific PII entities."""
        if not text:
            return []

        all_results: List[RecognizerResult] = []
        for recognizer in self.recognizers:
            try:
                matches = recognizer.analyze(text)
                all_results.extend(matches)
            except Exception:
                continue

        # Filter overlapping matches (keep higher score or longer match)
        all_results.sort(key=lambda r: (r.start, -(r.end - r.start), -r.score))
        filtered: List[RecognizerResult] = []
        last_end = -1
        for r in all_results:
            if r.start >= last_end:
                filtered.append(r)
                last_end = r.end

        return filtered

    def screen_text(
        self,
        text: str,
        action: PIIAction,
    ) -> Tuple[str, Dict[str, int], Dict[str, str], bool]:
        """Screen text according to model's guardrail policy.
        Returns: (processed_text, entity_counts, token_map, is_blocked)
        Traceability: REQ-2.3
        """
        results = self.analyze(text)
        if not results:
            return text, {}, {}, False

        entity_types = [r.entity_type for r in results]
        entity_counts = dict(Counter(entity_types))
        token_map: Dict[str, str] = {}

        if action == PIIAction.BLOCK:
            return text, entity_counts, {}, True

        # Process replacements in reverse order so character indices remain valid
        results_sorted = sorted(results, key=lambda x: x.start, reverse=True)
        chars = list(text)
        token_counters: Dict[str, int] = {}

        for r in results_sorted:
            orig_val = text[r.start:r.end]
            if action == PIIAction.REDACT:
                replacement = f"<{r.entity_type}>"
            elif action == PIIAction.TOKENIZE:
                cnt = token_counters.get(r.entity_type, 0)
                token_counters[r.entity_type] = cnt + 1
                token_key = f"<TOKEN_{r.entity_type}_{cnt}>"
                token_map[token_key] = orig_val
                replacement = token_key
            else:
                replacement = orig_val

            chars[r.start:r.end] = list(replacement)

        processed_text = "".join(chars)
        return processed_text, entity_counts, token_map, False

    @staticmethod
    def detokenize(text: str, token_map: Dict[str, str]) -> str:
        """De-tokenize LLM response by substituting token placeholders with original PII values.
        Traceability: REQ-2.3
        """
        result = text
        for token_key, original_val in token_map.items():
            result = result.replace(token_key, original_val)
        return result

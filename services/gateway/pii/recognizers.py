"""Self-Contained Ultra-Fast Indian and Standard PII Recognizers.
Traceability: REQ-2.2, REQ-2.3, REQ-2.7 (Latency <= 300ms)
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from services.gateway.pii.verhoeff import validate_verhoeff

# Valid PAN 4th character holder-types under Indian Income Tax Act
PAN_ALLOWED_TYPES = {"C", "P", "H", "F", "A", "T", "B", "L", "J", "G"}


@dataclass
class RecognizerResult:
    entity_type: str
    start: int
    end: int
    score: float


def validate_luhn(number_str: str) -> bool:
    """Validate Credit Card numbers using Luhn checksum."""
    digits = [int(c) for c in number_str if c.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit
    return checksum % 10 == 0


class AadhaarRecognizer:
    """Recognizes 12-digit Indian Aadhaar Numbers with Verhoeff Checksum Validation.
    Traceability: REQ-2.2
    """
    entity_type = "AADHAAR"
    pattern = re.compile(r"\b([2-9]\d{3}[-\s]?\d{4}[-\s]?\d{4})\b")

    def analyze(self, text: str) -> List[RecognizerResult]:
        results = []
        for match in self.pattern.finditer(text):
            val = match.group(1)
            clean = "".join(filter(str.isdigit, val))
            if len(clean) == 12 and validate_verhoeff(clean):
                results.append(RecognizerResult(
                    entity_type=self.entity_type,
                    start=match.start(1),
                    end=match.end(1),
                    score=0.95,
                ))
        return results


class PanRecognizer:
    """Recognizes Indian Permanent Account Numbers (PAN) with 4th-char holder-type check.
    Traceability: REQ-2.2
    """
    entity_type = "PAN"
    pattern = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")

    def analyze(self, text: str) -> List[RecognizerResult]:
        results = []
        for match in self.pattern.finditer(text):
            val = match.group(1)
            # Check 4th character holder type
            if val[3] in PAN_ALLOWED_TYPES:
                results.append(RecognizerResult(
                    entity_type=self.entity_type,
                    start=match.start(1),
                    end=match.end(1),
                    score=0.95,
                ))
        return results


class IndiaPhoneRecognizer:
    """Recognizes Indian Mobile Numbers (+91 or 10-digits starting with 6, 7, 8, or 9).
    Traceability: REQ-2.2
    """
    entity_type = "PHONE_IN"
    pattern = re.compile(r"((?:\+91[\-\s]?|\b)[6-9]\d{9}\b)")

    def analyze(self, text: str) -> List[RecognizerResult]:
        results = []
        for match in self.pattern.finditer(text):
            results.append(RecognizerResult(
                entity_type=self.entity_type,
                start=match.start(1),
                end=match.end(1),
                score=0.85,
            ))
        return results


class IfscRecognizer:
    """Recognizes Indian Financial System Code (IFSC) for banking transactions.
    Traceability: REQ-2.2
    """
    entity_type = "IFSC"
    pattern = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")

    def analyze(self, text: str) -> List[RecognizerResult]:
        results = []
        for match in self.pattern.finditer(text):
            results.append(RecognizerResult(
                entity_type=self.entity_type,
                start=match.start(1),
                end=match.end(1),
                score=0.90,
            ))
        return results


class GstinRecognizer:
    """Recognizes Indian Goods and Services Tax Identification Numbers (GSTIN).
    Traceability: REQ-2.2
    """
    entity_type = "GSTIN"
    pattern = re.compile(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b")

    def analyze(self, text: str) -> List[RecognizerResult]:
        results = []
        for match in self.pattern.finditer(text):
            results.append(RecognizerResult(
                entity_type=self.entity_type,
                start=match.start(1),
                end=match.end(1),
                score=0.95,
            ))
        return results


class UpiRecognizer:
    """Recognizes Unified Payments Interface (UPI) Virtual Payment Addresses (VPA).
    Traceability: REQ-2.2
    """
    entity_type = "UPI_ID"
    pattern = re.compile(r"\b([a-zA-Z0-9.\-_]{2,256}@(okaxis|okhdfcbank|okicici|oksbi|paytm|ybl|apl|upi))\b", re.IGNORECASE)

    def analyze(self, text: str) -> List[RecognizerResult]:
        results = []
        for match in self.pattern.finditer(text):
            results.append(RecognizerResult(
                entity_type=self.entity_type,
                start=match.start(1),
                end=match.end(1),
                score=0.90,
            ))
        return results


class VoterIdRecognizer:
    """Recognizes Indian Voter ID (Electors Photo Identity Card - EPIC).
    Traceability: REQ-2.2
    """
    entity_type = "VOTER_ID"
    pattern = re.compile(r"\b([A-Z]{3}[0-9]{7})\b")

    def analyze(self, text: str) -> List[RecognizerResult]:
        results = []
        for match in self.pattern.finditer(text):
            results.append(RecognizerResult(
                entity_type=self.entity_type,
                start=match.start(1),
                end=match.end(1),
                score=0.85,
            ))
        return results


class IndiaPassportRecognizer:
    """Recognizes Indian Passport Numbers (1 letter followed by 7 digits).
    Traceability: REQ-2.2
    """
    entity_type = "PASSPORT_IN"
    pattern = re.compile(r"\b([A-Z][0-9]{7})\b")

    def analyze(self, text: str) -> List[RecognizerResult]:
        results = []
        for match in self.pattern.finditer(text):
            results.append(RecognizerResult(
                entity_type=self.entity_type,
                start=match.start(1),
                end=match.end(1),
                score=0.80,
            ))
        return results


class EmailRecognizer:
    """Recognizes Email Addresses."""
    entity_type = "EMAIL_ADDRESS"
    pattern = re.compile(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")

    def analyze(self, text: str) -> List[RecognizerResult]:
        results = []
        for match in self.pattern.finditer(text):
            results.append(RecognizerResult(
                entity_type=self.entity_type,
                start=match.start(1),
                end=match.end(1),
                score=0.90,
            ))
        return results


class CreditCardRecognizer:
    """Recognizes Credit Card Numbers with Luhn check."""
    entity_type = "CREDIT_CARD"
    pattern = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")

    def analyze(self, text: str) -> List[RecognizerResult]:
        results = []
        for match in self.pattern.finditer(text):
            clean = "".join(filter(str.isdigit, match.group(0)))
            if validate_luhn(clean):
                results.append(RecognizerResult(
                    entity_type=self.entity_type,
                    start=match.start(0),
                    end=match.end(0),
                    score=0.95,
                ))
        return results

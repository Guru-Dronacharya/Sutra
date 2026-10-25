"""Metadata Tagger for Regulatory Chunks based on tagging_rules.yaml.
Traceability: REQ-4.3
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from services.rag.chunker import RawChunk


class MetadataTagger:
    """Enriches raw chunks with instrument name, framework, and applicable risk tiers."""

    def __init__(self, rules_file: Optional[str] = None):
        base_dir = Path(__file__).resolve().parent
        self.rules_path = Path(rules_file) if rules_file else base_dir / "tagging_rules.yaml"

        with open(self.rules_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.instruments = self.config.get("instruments", {})

    def tag_chunk(self, chunk: RawChunk) -> Dict[str, Any]:
        """Assign metadata tags to a chunk based on instrument rules."""
        inst_info = self.instruments.get(chunk.instrument_code, {})
        instrument_name = inst_info.get("name", chunk.instrument_code)
        framework = inst_info.get("framework", "india")

        # Find section-specific tier mapping
        applicable_tiers = ["medium", "high"]  # default fallback
        rules = inst_info.get("rules", [])
        for rule in rules:
            rule_sec = rule.get("section_id", "").upper()
            if rule_sec in chunk.section_id or chunk.section_id in rule_sec:
                applicable_tiers = rule.get("tiers", applicable_tiers)
                break

        return {
            "instrument": instrument_name,
            "instrument_code": chunk.instrument_code,
            "section_id": chunk.section_id,
            "heading": chunk.heading,
            "text": chunk.text,
            "tiers": applicable_tiers,
            "frameworks": [framework],
        }

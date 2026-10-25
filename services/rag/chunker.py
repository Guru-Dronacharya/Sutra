"""Structure-Aware Legal Chunker for Regulatory Corpus.
Parses statutory documents by Section, Rule, Article, and Pillar boundaries.
Traceability: REQ-4.2
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class RawChunk:
    instrument_code: str
    section_id: str
    heading: str
    text: str


class LegalStructureChunker:
    """Regex-based parser preserving section identifiers and clause structure."""

    SECTION_HEADER_REGEX = re.compile(
        r"^\[(?P<sec>(?:SECTION|RULE|ARTICLE|SUTRA|PILLAR|GOVERN|MAP|MEASURE|MANAGE)\s*[^\]]+)\]\s*(?P<heading>.*)$",
        re.MULTILINE | re.IGNORECASE,
    )

    def chunk_file(self, file_path: str, instrument_code: str) -> List[RawChunk]:
        """Split a legal text document into structure-aware chunks based on section headers."""
        path = Path(file_path)
        if not path.exists():
            return []

        content = path.read_text(encoding="utf-8")
        return self.chunk_text(content, instrument_code)

    def chunk_text(self, text: str, instrument_code: str) -> List[RawChunk]:
        """Split plain text by legal section boundaries."""
        matches = list(self.SECTION_HEADER_REGEX.finditer(text))
        if not matches:
            # Fallback: single chunk if no section markers found
            return [
                RawChunk(
                    instrument_code=instrument_code,
                    section_id="GENERAL",
                    heading="General Provision",
                    text=text.strip(),
                )
            ]

        chunks: List[RawChunk] = []
        for i, match in enumerate(matches):
            section_id = match.group("sec").strip().upper()
            heading = match.group("heading").strip()

            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            chunk_body = text[start_pos:end_pos].strip()

            full_chunk_text = f"[{section_id}] {heading}\n{chunk_body}" if heading else f"[{section_id}]\n{chunk_body}"

            chunks.append(
                RawChunk(
                    instrument_code=instrument_code,
                    section_id=section_id,
                    heading=heading,
                    text=full_chunk_text,
                )
            )

        return chunks

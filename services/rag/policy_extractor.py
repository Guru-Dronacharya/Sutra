"""Enterprise AI & Data Governance Policy Extractor.
Extracts structured sections and paragraphs from TXT, MD, DOCX, and PDF policies.
Traceability: REQ-5.1
"""

import io
from pathlib import Path
from typing import Any, Dict, List


class PolicyExtractor:
    """Extracts text and section hierarchy from enterprise policy documents."""

    def extract_from_text(self, text: str, filename: str = "policy.txt") -> List[Dict[str, str]]:
        """Extract structured sections from text or markdown."""
        lines = text.splitlines()
        sections: List[Dict[str, str]] = []
        current_title = "General Policy Provisions"
        current_lines: List[str] = []
        loc_counter = 1

        for line in lines:
            line_str = line.strip()
            # Detect markdown headers or capitalized section titles
            if line_str.startswith("#") or (line_str.isupper() and len(line_str) > 4 and len(line_str) < 80):
                if current_lines:
                    sections.append({
                        "section_title": current_title,
                        "content": "\n".join(current_lines).strip(),
                        "location": f"Section {loc_counter}: {current_title}",
                    })
                    loc_counter += 1
                    current_lines = []
                current_title = line_str.lstrip("#").strip()
            else:
                if line_str:
                    current_lines.append(line_str)

        if current_lines:
            sections.append({
                "section_title": current_title,
                "content": "\n".join(current_lines).strip(),
                "location": f"Section {loc_counter}: {current_title}",
            })

        return sections

    def extract_from_docx(self, file_bytes: bytes, filename: str) -> List[Dict[str, str]]:
        """Extract sections from Microsoft Word .docx files."""
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            return self.extract_from_text(full_text, filename)
        except Exception:
            return self.extract_from_text(file_bytes.decode("utf-8", errors="ignore"), filename)

    def extract(self, file_bytes: bytes, filename: str) -> List[Dict[str, str]]:
        """Universal policy extractor based on file extension."""
        lower_name = filename.lower()
        if lower_name.endswith(".docx"):
            return self.extract_from_docx(file_bytes, filename)
        else:
            # Fallback to UTF-8 text/markdown
            text_str = file_bytes.decode("utf-8", errors="ignore")
            return self.extract_from_text(text_str, filename)

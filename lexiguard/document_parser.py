"""
Lexiguard Local Document Parser
Extracts, sanitizes, and segments legal documents on-device with zero external network access.
Supports PDF (.pdf) and plain text (.txt, .md).
"""

import re
import os
from typing import List, Dict, Any, Optional
from pypdf import PdfReader


class DocumentSection:
    """A segment or clause extracted from a document with location metadata."""
    def __init__(self, section_id: str, header: str, text: str, page_num: int, start_char: int, end_char: int):
        self.section_id = section_id
        self.header = header
        self.text = text.strip()
        self.page_num = page_num
        self.start_char = start_char
        self.end_char = end_char

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "header": self.header,
            "text": self.text,
            "page_num": self.page_num,
            "start_char": self.start_char,
            "end_char": self.end_char
        }


class LocalDocumentParser:
    """Pure local, offline document ingestion engine."""

    # Regex patterns for identifying legal clause headings
    CLAUSE_PATTERNS = [
        re.compile(r'^(Section\s+\d+[\.\d]*[:\-\s]?[^\n]*)', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^(Clause\s+\d+[\.\d]*[:\-\s]?[^\n]*)', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^(Article\s+[IVXLCDM\d]+[:\-\s]?[^\n]*)', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^(\d+\.\d*[\s\t]+[A-Z][^\n]*)', re.MULTILINE),
        re.compile(r'^([A-Z\s]{4,30}:)', re.MULTILINE)
    ]

    @staticmethod
    def read_file(file_path: str) -> Dict[str, Any]:
        """
        Reads a document locally from disk.
        Returns full text, page breakdown, and metadata.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Local document not found at: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return LocalDocumentParser._read_pdf(file_path)
        elif ext in [".txt", ".md", ".text"]:
            return LocalDocumentParser._read_text(file_path)
        else:
            raise ValueError(f"Unsupported document format '{ext}'. Supported formats: .pdf, .txt, .md")

    @staticmethod
    def _read_pdf(file_path: str) -> Dict[str, Any]:
        """Extracts text per page from a local PDF file using pypdf."""
        reader = PdfReader(file_path)
        pages_text: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []

        for idx, page in enumerate(reader.pages):
            page_content = page.extract_text() or ""
            pages_text.append({
                "page_num": idx + 1,
                "text": page_content
            })
            full_text_parts.append(page_content)

        full_text = "\n\n".join(full_text_parts)
        return {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "page_count": len(reader.pages),
            "full_text": full_text,
            "pages": pages_text
        }

    @staticmethod
    def _read_text(file_path: str) -> Dict[str, Any]:
        """Reads plain text / markdown files locally."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        return {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "page_count": 1,
            "full_text": content,
            "pages": [{"page_num": 1, "text": content}]
        }

    @classmethod
    def segment_clauses(cls, document_data: Dict[str, Any]) -> List[DocumentSection]:
        """
        Segments raw document text into identifiable clauses/sections.
        Preserves page numbering and verbatim text spans for verification.
        """
        full_text = document_data["full_text"]
        sections: List[DocumentSection] = []

        # Find all match positions for potential clause headers
        header_positions = []
        for pattern in cls.CLAUSE_PATTERNS:
            for match in pattern.finditer(full_text):
                header_positions.append((match.start(), match.end(), match.group(1).strip()))

        # Sort matches by appearance in text
        header_positions.sort(key=lambda x: x[0])

        # Filter overlapping matches
        filtered_positions = []
        last_end = -1
        for start, end, text in header_positions:
            if start >= last_end:
                filtered_positions.append((start, end, text))
                last_end = end

        # If no explicit headings found, segment by double newlines (paragraphs)
        if len(filtered_positions) < 2:
            paragraphs = [p.strip() for p in full_text.split("\n\n") if len(p.strip()) > 40]
            current_offset = 0
            for idx, p in enumerate(paragraphs):
                start_char = full_text.find(p, current_offset)
                if start_char == -1:
                    start_char = current_offset
                end_char = start_char + len(p)
                current_offset = end_char

                sections.append(DocumentSection(
                    section_id=f"PARA-{idx + 1:03d}",
                    header=f"Paragraph {idx + 1}",
                    text=p,
                    page_num=1,
                    start_char=start_char,
                    end_char=end_char
                ))
            return sections

        # Build sections from detected headers
        for i in range(len(filtered_positions)):
            start_pos, header_end, header_text = filtered_positions[i]
            if i + 1 < len(filtered_positions):
                next_start = filtered_positions[i + 1][0]
                body_text = full_text[start_pos:next_start]
            else:
                body_text = full_text[start_pos:]

            # Determine page number based on character offset
            page_num = cls._find_page_number(document_data["pages"], start_pos)

            sections.append(DocumentSection(
                section_id=f"SEC-{i + 1:03d}",
                header=header_text,
                text=body_text,
                page_num=page_num,
                start_char=start_pos,
                end_char=start_pos + len(body_text)
            ))

        return sections

    @staticmethod
    def _find_page_number(pages: List[Dict[str, Any]], char_offset: int) -> int:
        """Finds which page a character offset belongs to."""
        current_len = 0
        for p in pages:
            page_len = len(p["text"]) + 2  # account for join newlines
            if char_offset <= current_len + page_len:
                return p["page_num"]
            current_len += page_len
        return len(pages) if pages else 1

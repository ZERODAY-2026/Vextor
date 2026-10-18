"""
LexiGuard Multi-Format Document Ingestion Engine (src/parser.py)
Supports PDF (PyMuPDF), Word (.docx), Plain Text (.txt, .md), and Raw Text Corpus.
Implements unified chunking with location labels, input sanitization, and truncation guard.
"""

import os
import re
import hashlib
from typing import List, Dict, Any, Optional

MAX_CHAR_LIMIT = 50000
CHUNK_OVERLAP = 200
DEFAULT_CHUNK_SIZE = 1200


class DocumentCorpus:
    """Represents an ingested document with full sanitized text, unified chunks, and metadata."""
    def __init__(self, raw_text: str, chunks: List[Dict[str, Any]], metadata: Dict[str, Any]):
        self.raw_text = raw_text
        self.chunks = chunks
        self.metadata = metadata
        self.doc_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_hash": self.doc_hash,
            "raw_text": self.raw_text,
            "chunks": self.chunks,
            "metadata": self.metadata
        }


class DocumentParser:
    """
    On-device, multi-format parser and chunker.
    Guarantees 100% offline local execution without network dependencies.
    """

    @classmethod
    def read_file(cls, file_path: str) -> Dict[str, Any]:
        """Backwards compatibility helper: returns dict with full_text, page_count, pages."""
        corpus = cls.parse(file_path)
        pages = []
        for c in corpus.chunks:
            page_num = 1
            if "Page " in c["location_label"]:
                try:
                    page_num = int(c["location_label"].replace("Page ", ""))
                except Exception:
                    pass
            pages.append({"page_num": page_num, "text": c["text"]})

        return {
            "file_name": corpus.metadata.get("file_name", os.path.basename(file_path)),
            "file_path": file_path,
            "page_count": corpus.metadata.get("page_count", len(corpus.chunks) or 1),
            "full_text": corpus.raw_text,
            "pages": pages
        }

    @classmethod
    def segment_clauses(cls, document_data: Dict[str, Any]) -> List[Any]:
        """Backwards compatibility helper: splits full_text into sections with headers."""
        class SimpleSection:
            def __init__(self, header: str, text: str):
                self.header = header
                self.text = text

        full_text = document_data.get("full_text", "")
        chunks = cls._chunk_by_sections_or_paragraphs(full_text)
        return [SimpleSection(c["location_label"], c["text"]) for c in chunks]

    @classmethod
    def parse(cls, source: str, is_raw_text: bool = False, file_name: Optional[str] = None) -> DocumentCorpus:
        """
        Main entry point for parsing contracts from either a file path or raw text string.
        """
        if is_raw_text:
            return cls.parse_raw_text(source, file_name=file_name or "Pasted_Agreement.txt")

        if not os.path.exists(source):
            raise FileNotFoundError(f"Local document not found at: {source}")

        ext = os.path.splitext(source)[1].lower()
        if ext == ".pdf":
            return cls._parse_pdf(source)
        elif ext in [".docx", ".doc"]:
            return cls._parse_docx(source)
        elif ext in [".txt", ".md", ".text"]:
            return cls._parse_text_file(source)
        else:
            raise ValueError(f"Unsupported document format '{ext}'. Supported: .pdf, .docx, .txt, .md")

    @classmethod
    def parse_raw_text(cls, text: str, file_name: str = "Pasted_Agreement.txt") -> DocumentCorpus:
        """Parses a raw text string pasted directly into the UI."""
        sanitized = cls._sanitize_text(text)
        if not sanitized.strip():
            raise ValueError("Document contains no legible text or is completely empty.")

        chunks = cls._chunk_by_sections_or_paragraphs(sanitized, default_prefix="Section")
        metadata = {
            "file_name": file_name,
            "file_type": "raw_text",
            "char_count": len(sanitized),
            "word_count": len(sanitized.split()),
            "chunk_count": len(chunks),
            "truncated": len(text) > MAX_CHAR_LIMIT
        }
        return DocumentCorpus(raw_text=sanitized, chunks=chunks, metadata=metadata)

    @classmethod
    def _parse_pdf(cls, file_path: str) -> DocumentCorpus:
        """Ingests a PDF document using PyMuPDF (fitz) with page-level chunking."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
        except Exception as e:
            raise RuntimeError(f"Failed to read PDF file via PyMuPDF: {e}")

        all_text = []
        chunks = []
        chunk_id = 1

        for page_idx, page in enumerate(doc):
            page_text = page.get_text() or ""
            clean_page_text = cls._clean_page_text(page_text)
            if clean_page_text:
                all_text.append(clean_page_text)
                chunks.append({
                    "chunk_id": chunk_id,
                    "location_label": f"Page {page_idx + 1}",
                    "text": clean_page_text
                })
                chunk_id += 1

        doc.close()
        combined_text = "\n\n".join(all_text)
        sanitized = cls._sanitize_text(combined_text)

        if not sanitized.strip():
            raise ValueError(f"PDF document '{os.path.basename(file_path)}' contains no extractable text.")

        metadata = {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "file_type": "pdf",
            "page_count": len(chunks),
            "char_count": len(sanitized),
            "word_count": len(sanitized.split()),
            "chunk_count": len(chunks),
            "truncated": len(combined_text) > MAX_CHAR_LIMIT
        }
        return DocumentCorpus(raw_text=sanitized, chunks=chunks, metadata=metadata)

    @classmethod
    def _parse_docx(cls, file_path: str) -> DocumentCorpus:
        """Ingests a Word document (.docx) using python-docx with paragraph-level chunking."""
        try:
            import docx
            doc = docx.Document(file_path)
        except Exception as e:
            raise RuntimeError(f"Failed to read DOCX file via python-docx: {e}")

        paragraphs = []
        chunks = []
        chunk_id = 1
        para_idx = 1

        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                paragraphs.append(text)
                chunks.append({
                    "chunk_id": chunk_id,
                    "location_label": f"Paragraph {para_idx}",
                    "text": text
                })
                chunk_id += 1
            para_idx += 1

        # Also extract table text if present
        for t_idx, table in enumerate(doc.tables):
            table_rows = []
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    table_rows.append(row_text)
            if table_rows:
                tbl_text = "\n".join(table_rows)
                paragraphs.append(tbl_text)
                chunks.append({
                    "chunk_id": chunk_id,
                    "location_label": f"Table {t_idx + 1}",
                    "text": tbl_text
                })
                chunk_id += 1

        combined_text = "\n\n".join(paragraphs)
        sanitized = cls._sanitize_text(combined_text)

        if not sanitized.strip():
            raise ValueError(f"DOCX document '{os.path.basename(file_path)}' contains no text content.")

        metadata = {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "file_type": "docx",
            "char_count": len(sanitized),
            "word_count": len(sanitized.split()),
            "chunk_count": len(chunks),
            "truncated": len(combined_text) > MAX_CHAR_LIMIT
        }
        return DocumentCorpus(raw_text=sanitized, chunks=chunks, metadata=metadata)

    @classmethod
    def _parse_text_file(cls, file_path: str) -> DocumentCorpus:
        """Ingests plain text (.txt) and markdown (.md) documents."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read text file: {e}")

        sanitized = cls._sanitize_text(content)
        if not sanitized.strip():
            raise ValueError(f"Text file '{os.path.basename(file_path)}' is empty.")

        chunks = cls._chunk_by_sections_or_paragraphs(sanitized, default_prefix="Section")
        metadata = {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "file_type": os.path.splitext(file_path)[1].lower().replace(".", ""),
            "page_count": 1,
            "char_count": len(sanitized),
            "word_count": len(sanitized.split()),
            "chunk_count": len(chunks),
            "truncated": len(content) > MAX_CHAR_LIMIT
        }
        return DocumentCorpus(raw_text=sanitized, chunks=chunks, metadata=metadata)

    @classmethod
    def _chunk_by_sections_or_paragraphs(cls, text: str, default_prefix: str = "Section") -> List[Dict[str, Any]]:
        """
        Splits text into unified chunks using headings, section numbers, or paragraphs.
        """
        section_pattern = re.compile(
            r'^(?:Section\s+\d+[\.\d]*[^\n]*|Clause\s+\d+[\.\d]*[^\n]*|Article\s+[IVXLCDM\d]+[^\n]*|\d+[\.\)]\s+[A-Z][^\n]*|[A-Z\s]{4,30}:)',
            re.IGNORECASE | re.MULTILINE
        )

        matches = list(section_pattern.finditer(text))
        chunks = []
        chunk_id = 1

        if len(matches) >= 2:
            for i in range(len(matches)):
                start = matches[i].start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                chunk_text = text[start:end].strip()
                heading = matches[i].group(0).strip().rstrip(":")
                if chunk_text:
                    chunks.append({
                        "chunk_id": chunk_id,
                        "location_label": heading if len(heading) <= 40 else f"{default_prefix} {chunk_id}",
                        "text": chunk_text
                    })
                    chunk_id += 1
        else:
            # Fallback to paragraph-based or fixed-size chunking
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            for p_idx, p in enumerate(paragraphs):
                chunks.append({
                    "chunk_id": chunk_id,
                    "location_label": f"Paragraph {p_idx + 1}",
                    "text": p
                })
                chunk_id += 1

        # If chunks are still empty, create one single chunk
        if not chunks:
            chunks.append({
                "chunk_id": 1,
                "location_label": f"{default_prefix} 1",
                "text": text
            })

        return chunks

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """
        Removes binary/null bytes, normalizes whitespace, and truncates
        texts exceeding 50,000 characters to safeguard edge model context.
        """
        # Remove null bytes and non-printable control characters except standard whitespace
        clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        clean = clean.replace('\r\n', '\n').replace('\r', '\n')

        # Limit to MAX_CHAR_LIMIT to guard local edge model resources
        if len(clean) > MAX_CHAR_LIMIT:
            clean = clean[:MAX_CHAR_LIMIT]

        return clean.strip()

    @staticmethod
    def _clean_page_text(text: str) -> str:
        """Cleans PDF page text, removing excessive whitespace or page headers/footers."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return "\n".join(lines)


# Backwards compatibility alias
LocalDocumentParser = DocumentParser

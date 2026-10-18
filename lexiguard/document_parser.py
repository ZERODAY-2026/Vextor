"""
Lexiguard Local Document Parser
Re-exports the multi-format DocumentParser from src.parser for backwards compatibility.
"""

from src.parser import DocumentParser, DocumentCorpus, LocalDocumentParser

__all__ = ["DocumentParser", "DocumentCorpus", "LocalDocumentParser"]

"""
Lexiguard Local Document Parser
Re-exports the multi-format DocumentParser from src.parser for backwards compatibility.
"""

import sys
from pathlib import Path

# Ensure repository root is on sys.path
_ROOT_DIR = str(Path(__file__).parent.parent.resolve())
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from src.parser import DocumentParser, DocumentCorpus, LocalDocumentParser

__all__ = ["DocumentParser", "DocumentCorpus", "LocalDocumentParser"]

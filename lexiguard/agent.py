"""
Lexiguard Agent Core Engine
Re-exports the upgraded LexiguardAgent from src.agent for package backwards compatibility.
"""

import sys
from pathlib import Path

# Ensure repository root is on sys.path
_ROOT_DIR = str(Path(__file__).parent.parent.resolve())
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from src.agent import LexiguardAgent, DETERMINISTIC_LEGAL_TRIGGERS
from .models import (
    DocumentTriageReport,
    DocumentMetadata,
    TriageClause,
    SourceCitation,
    SilentClauseAudit,
    EscalationItem,
    SeverityLevel,
    GroundedQAAnswer
)

__all__ = [
    "LexiguardAgent",
    "DETERMINISTIC_LEGAL_TRIGGERS",
    "DocumentTriageReport",
    "DocumentMetadata",
    "TriageClause",
    "SourceCitation",
    "SilentClauseAudit",
    "EscalationItem",
    "SeverityLevel",
    "GroundedQAAnswer"
]

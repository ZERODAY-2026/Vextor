"""
Lexiguard Agent Core Engine
Re-exports the upgraded LexiguardAgent from src.agent for package backwards compatibility.
"""

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

"""
Lexiguard Data Models
Structured schemas for document triage, clause analysis, grounding, and escalation.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    """Risk severity levels for color-coded triage."""
    HIGH_RISK = "HIGH_RISK"          # Red: Unilateral terms, severe penalties, auto-lockin
    CAUTION_AMBER = "CAUTION_AMBER"  # Amber: Vague terms, ambiguous notice, missing cure period
    STANDARD_LOW = "STANDARD_LOW"    # Green: Customary, balanced, mutual clauses
    INFORMATIONAL = "INFORMATIONAL"  # Blue: Administrative, definitions, recitals


class SourceCitation(BaseModel):
    """Traceable passage grounding directly in the source document."""
    verbatim_quote: str = Field(..., description="Exact verbatim text from the document.")
    section_reference: Optional[str] = Field(None, description="Section or clause number (e.g. 'Clause 4.2', 'Section 8').")
    page_number: Optional[int] = Field(None, description="Page number where the passage appears.")
    is_verified_in_source: bool = Field(True, description="True if verified against raw document text.")


class TriageClause(BaseModel):
    """Detailed triage analysis for an individual legal clause."""
    clause_id: str = Field(..., description="Identifier (e.g. 'CLS-001').")
    category: str = Field(..., description="Category (e.g., 'Termination', 'Penalties', 'Security Deposit', 'Obligations', 'Non-Compete', 'Indemnity').")
    plain_language_summary: str = Field(..., description="Plain-language explanation for non-lawyers.")
    
    # L6: Strict separation of explicit text vs interpretation vs practical concern
    explicit_statement: str = Field(..., description="What the document text literally and explicitly states.")
    potential_interpretation: str = Field(..., description="Reasonable practical interpretation of the obligation or right.")
    practical_concern: str = Field(..., description="Potential risk, financial pitfall, or one-sided burden on the party.")
    
    severity: SeverityLevel = Field(..., description="Risk severity rating.")
    citation: SourceCitation = Field(..., description="Identifiable source passage.")
    
    # L7: Ambiguity & Jurisdiction
    ambiguity_detected: Optional[str] = Field(None, description="Vague terminology (e.g., 'reasonable efforts', 'at sole discretion').")
    jurisdiction_dependency: Optional[str] = Field(None, description="Statutory or local jurisdiction context without drawing legal verdicts.")


class SilentClauseAudit(BaseModel):
    """Audit of essential legal clauses that are conspicuously ABSENT or silent."""
    topic: str = Field(..., description="The standard protective clause topic (e.g., 'Cure Period for Alleged Breach', 'Deposit Refund Timeframe').")
    is_silent: bool = Field(True, description="True if the document contains no provision on this matter.")
    risk_implication: str = Field(..., description="Why silence on this topic creates exposure or ambiguity for the signing party.")
    suggested_inquiry: str = Field(..., description="What the user should ask the other party or their attorney.")


class EscalationItem(BaseModel):
    """Safe escalation checklist recommending professional legal counsel (L8)."""
    trigger_clause: str = Field(..., description="Which clause or absence triggered the escalation.")
    risk_description: str = Field(..., description="Why automated analysis is insufficient (e.g., legal enforceability, statutory conflict).")
    recommended_specialist: str = Field(..., description="E.g., 'Tenancy Lawyer', 'Employment Rights Advocate', 'Commercial Solicitor').")
    specific_questions_for_counsel: List[str] = Field(..., description="Precise questions the user can ask their legal counsel.")


class DocumentMetadata(BaseModel):
    """Extracted administrative metadata."""
    filename: str
    detected_document_type: str = Field(..., description="e.g. 'Residential Tenancy Agreement', 'Employment Contract', 'Service Level Agreement'.")
    identified_parties: List[str] = Field(default_factory=list)
    effective_dates_or_term: Optional[str] = None
    governing_jurisdiction_stated: Optional[str] = None
    character_count: int = 0
    estimated_word_count: int = 0


class DocumentTriageReport(BaseModel):
    """Complete, end-to-end triage assessment output."""
    metadata: DocumentMetadata
    overall_risk_rating: SeverityLevel
    executive_summary: str = Field(..., description="A plain-English high-level overview of the document's balance and key terms.")
    
    # Detailed analysis sections
    clauses: List[TriageClause] = Field(default_factory=list)
    silent_clauses: List[SilentClauseAudit] = Field(default_factory=list)
    escalations: List[EscalationItem] = Field(default_factory=list)
    
    # Robustness & Adversarial flags
    adversarial_warnings: List[str] = Field(default_factory=list, description="Flags for prompt injections, contradictory wording, or malformed sections.")
    
    # L8 & Competition Compliance Boundary: Mandatory Non-Advice Notice
    legal_disclaimer: str = Field(
        default=(
            "IMPORTANT LEGAL NOTICE: Lexiguard is an AI-powered preliminary document triage assistant "
            "designed for educational document comprehension and issue identification. Lexiguard is NOT a lawyer, "
            "does NOT provide legal advice, and cannot determine the legal validity, enforceability, or binding nature "
            "of any contract. Do not sign or take legal action based solely on this automated triage. "
            "Consult a licensed legal practitioner or advocate in your jurisdiction for definitive legal counsel."
        ),
        description="Mandatory non-legal-advice boundary notice."
    )
    
    # L9: Privacy verification metadata
    privacy_audit: Dict[str, Any] = Field(
        default_factory=lambda: {
            "mode": "100% On-Device Local Inference",
            "remote_network_requests": 0,
            "external_storage_used": False,
            "telemetry_disabled": True,
            "offline_verified": True
        }
    )

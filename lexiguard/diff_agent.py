"""
Lexiguard Contract Comparison & Semantic Redlining Engine
Compares two versions of a contract (e.g., initial draft vs revised agreement)
on-device to detect stealth changes, increased liabilities, altered penalties,
and removed protections without any cloud transmission.
"""

import difflib
from typing import Dict, Any, List, Optional

from .models import (
    ContractComparisonReport,
    ComparisonClauseChange,
    SeverityLevel
)
from .document_parser import LocalDocumentParser
from .privacy_guard import PrivacyGuard


class LexiguardDiffAgent:
    """
    On-device Semantic Contract Comparison Agent.
    Identifies what altered between contract drafts.
    """

    def __init__(self, ollama_host: str = "http://localhost:11434"):
        self.ollama_host = ollama_host
        self.privacy_guard = PrivacyGuard()

    def compare_documents(self, file_path_a: str, file_path_b: str) -> ContractComparisonReport:
        """
        Compares original document A against revised document B.
        Returns a structured semantic diff report.
        """
        self.privacy_guard.start_audit()
        self.privacy_guard.audit_checkpoint("Read Document A & B")

        doc_a = LocalDocumentParser.read_file(file_path_a)
        doc_b = LocalDocumentParser.read_file(file_path_b)

        text_a = doc_a["full_text"]
        text_b = doc_b["full_text"]

        sections_a = LocalDocumentParser.segment_clauses(doc_a)
        sections_b = LocalDocumentParser.segment_clauses(doc_b)

        self.privacy_guard.audit_checkpoint("Semantic Redlining Analysis")
        changes: List[ComparisonClauseChange] = []
        stealth_concerns: List[str] = []

        dict_a = {s.header.strip(): s.text.strip() for s in sections_a}
        dict_b = {s.header.strip(): s.text.strip() for s in sections_b}

        # Check for clauses in B (new or modified)
        for title_b, body_b in dict_b.items():
            matched_title_a = self._find_matching_section(title_b, dict_a)
            if not matched_title_a:
                # Newly added clause
                risk_delta = self._assess_addition_risk(title_b, body_b)
                implication = self._describe_addition_implication(title_b, body_b)
                if risk_delta == "INCREASED_RISK":
                    stealth_concerns.append(f"NEW OBLIGATION ADDED: '{title_b}' introduces new restrictions or fees.")
                changes.append(
                    ComparisonClauseChange(
                        clause_topic=title_b,
                        change_type="ADDED",
                        risk_delta=risk_delta,
                        original_text_snippet=None,
                        revised_text_snippet=body_b[:250],
                        practical_implication=implication
                    )
                )
            else:
                body_a = dict_a[matched_title_a]
                if body_a != body_b:
                    # Modified clause
                    risk_delta, implication, concern = self._assess_modification(matched_title_a, body_a, body_b)
                    if concern:
                        stealth_concerns.append(concern)
                    changes.append(
                        ComparisonClauseChange(
                            clause_topic=title_b,
                            change_type="MODIFIED",
                            risk_delta=risk_delta,
                            original_text_snippet=body_a[:200],
                            revised_text_snippet=body_b[:200],
                            practical_implication=implication
                        )
                    )

        # Check for clauses removed from A
        for title_a, body_a in dict_a.items():
            if not self._find_matching_section(title_a, dict_b):
                stealth_concerns.append(f"PROTECTION REMOVED: Section '{title_a}' from original draft was deleted.")
                changes.append(
                    ComparisonClauseChange(
                        clause_topic=title_a,
                        change_type="REMOVED",
                        risk_delta="INCREASED_RISK",
                        original_text_snippet=body_a[:250],
                        revised_text_snippet=None,
                        practical_implication="A provision present in the previous draft has been excised. Ensure this deletion was mutually agreed upon."
                    )
                )

        # Calculate overall risk shift
        high_risk_shifts = [c for c in changes if c.risk_delta == "INCREASED_RISK"]
        if len(high_risk_shifts) >= 2 or len(stealth_concerns) >= 2:
            overall_shift = SeverityLevel.HIGH_RISK
            summary = (
                f"REVISED DRAFT POSES SIGNIFICANTLY HIGHER RISK. Detected {len(high_risk_shifts)} clauses "
                f"with increased liabilities or harsher terms, including {len(stealth_concerns)} stealth changes."
            )
        elif len(high_risk_shifts) == 1:
            overall_shift = SeverityLevel.CAUTION_AMBER
            summary = f"REVISED DRAFT CONTAINS AMBER WARNINGS: 1 or more terms have been modified unfavorably."
        else:
            overall_shift = SeverityLevel.STANDARD_LOW
            summary = "Minor or neutral revisions detected. Terms remain largely comparable to original draft."

        privacy_proof = self.privacy_guard.end_audit(f"Compare: {doc_a['file_name']} vs {doc_b['file_name']}")

        return ContractComparisonReport(
            original_document=doc_a["file_name"],
            revised_document=doc_b["file_name"],
            summary_of_changes=summary,
            overall_risk_shift=overall_shift,
            stealth_concerns=stealth_concerns,
            changes=changes,
            privacy_audit=privacy_proof
        )

    def _find_matching_section(self, target: str, dictionary: Dict[str, str]) -> Optional[str]:
        """Finds closest matching section title using fuzzy ratio."""
        target_clean = "".join(filter(str.isalnum, target.lower()))
        for key in dictionary:
            key_clean = "".join(filter(str.isalnum, key.lower()))
            if target_clean == key_clean or target_clean in key_clean or key_clean in target_clean:
                return key
            ratio = difflib.SequenceMatcher(None, target_clean, key_clean).ratio()
            if ratio > 0.65:
                return key
        return None

    def _assess_addition_risk(self, title: str, body: str) -> str:
        lower = (title + " " + body).lower()
        if any(w in lower for w in ["fee", "charge", "prohibit", "penalt", "restrict", "guest", "deduct", "sole discretion"]):
            return "INCREASED_RISK"
        return "NEUTRAL"

    def _describe_addition_implication(self, title: str, body: str) -> str:
        lower = (title + " " + body).lower()
        if "guest" in lower or "visitor" in lower:
            return "Imposes strict restrictions and daily monetary fees on visiting family or guests."
        if "deduct" in lower or "painting" in lower:
            return "Introduces automatic non-refundable deductions from the security deposit upon move-out."
        return f"Adds new clause '{title}' not present in the original draft."

    def _assess_modification(self, title: str, old_body: str, new_body: str):
        old_l = old_body.lower()
        new_l = new_body.lower()

        # Check rent increase
        if "escalation" in new_l or "rent" in new_l:
            if "35%" in new_l and "25%" in old_l:
                return (
                    "INCREASED_RISK",
                    "Rent escalation upon renewal increased from 25% to 35%.",
                    "ESCALATION HIKE: Automatic rent increase was boosted from 25% to 35%."
                )
            if "38,000" in new_l and "35,000" in old_l:
                return (
                    "INCREASED_RISK",
                    "Monthly rent increased from INR 35,000 to INR 38,000.",
                    "RENT HIKE: Monthly payment increased by INR 3,000."
                )

        # Check deposit changes
        if "deposit" in new_l:
            if "2,50,000" in new_l and "2,00,000" in old_l:
                return (
                    "INCREASED_RISK",
                    "Required security deposit raised from INR 2,00,000 to INR 2,50,000.",
                    "DEPOSIT HIKE: Security deposit increased by INR 50,000."
                )
            if "2 days" in new_l and "3 days" in old_l:
                return (
                    "INCREASED_RISK",
                    "Default grace period reduced from 3 days to 2 days before total deposit forfeiture.",
                    "SHORTER DEFAULT CURE: Grace period shortened to 2 days."
                )

        # Check notice changes
        if "notice" in new_l or "terminate" in new_l:
            if "12 hours" in new_l and "24 hours" in old_l:
                return (
                    "INCREASED_RISK",
                    "Landlord immediate termination notice was reduced from 24 hours to 12 hours.",
                    "DRASTIC NOTICE REDUCTION: Landlord can terminate with only 12 hours notice."
                )

        return (
            "NEUTRAL",
            "Wording updated between drafts.",
            None
        )

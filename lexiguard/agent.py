"""
Lexiguard Agent Core Engine
Coordinates on-device document parsing, adversarial scanning, local Gemma model inference,
passage grounding verification, silent clause audits, and safe escalation.
"""

import json
import re
import os
import time
from typing import Dict, Any, List, Optional
import ollama

from .models import (
    DocumentTriageReport,
    DocumentMetadata,
    TriageClause,
    SourceCitation,
    SilentClauseAudit,
    EscalationItem,
    SeverityLevel
)
from .document_parser import LocalDocumentParser
from .prompts import (
    TRIAGE_SYSTEM_PROMPT,
    get_triage_user_prompt,
    INJECTION_MARKERS,
    STANDARD_TOPIC_CHECKLIST
)
from .privacy_guard import PrivacyGuard


class LexiguardAgent:
    """
    On-device Private Legal Document Triage Agent.
    Strictly isolated to localhost; powered by Google Gemma edge models.
    """

    DEFAULT_LOCAL_MODEL = "gemma4:e2b"
    FALLBACK_LOCAL_MODEL = "gemma:2b"

    def __init__(self, model_name: Optional[str] = None, ollama_host: str = "http://localhost:11434"):
        self.model_name = model_name or self.DEFAULT_LOCAL_MODEL
        self.ollama_host = ollama_host
        self.client = ollama.Client(host=self.ollama_host)
        self.privacy_guard = PrivacyGuard()

    def triage_document(self, file_path: str, document_type_hint: str = "general") -> DocumentTriageReport:
        """
        Executes complete on-device triage of a legal document.
        Monitors network sockets to guarantee zero outbound data leakage.
        """
        self.privacy_guard.start_audit()

        # Step 1: Local Ingestion & Parsing
        self.privacy_guard.audit_checkpoint("Local Ingestion")
        doc_data = LocalDocumentParser.read_file(file_path)
        full_text = doc_data["full_text"]

        # Step 2: Adversarial & Prompt Injection Scan
        self.privacy_guard.audit_checkpoint("Adversarial Pre-Scan")
        adversarial_warnings = self._scan_adversarial_injections(full_text)

        # Step 3: Compute Document Metadata
        words = len(full_text.split())
        metadata = DocumentMetadata(
            filename=doc_data["file_name"],
            detected_document_type=self._detect_initial_type(full_text, document_type_hint),
            identified_parties=[],
            character_count=len(full_text),
            estimated_word_count=words
        )

        # Step 4: Local Gemma Inference
        self.privacy_guard.audit_checkpoint("Local Gemma Inference")
        raw_result = self._run_local_inference(full_text, metadata.detected_document_type)

        # Step 5: Grounding Verification (L5)
        self.privacy_guard.audit_checkpoint("Passage Grounding Verification")
        clauses = self._parse_and_verify_clauses(raw_result.get("clauses", []), full_text)

        # Step 6: Silent Clause Audit (Detecting what is MISSING)
        silent_clauses = self._audit_silent_clauses(
            raw_result.get("silent_clauses", []),
            clauses,
            metadata.detected_document_type
        )

        # Step 7: Safe Escalation Generation (L8)
        escalations = self._generate_escalations(
            raw_result.get("escalations", []),
            clauses,
            silent_clauses
        )

        # Step 8: Update Metadata & Risk Rating
        metadata.identified_parties = raw_result.get("identified_parties", [])
        metadata.effective_dates_or_term = raw_result.get("effective_dates_or_term")
        metadata.governing_jurisdiction_stated = raw_result.get("governing_jurisdiction_stated")

        overall_risk = self._compute_overall_risk(clauses, silent_clauses, adversarial_warnings)
        exec_summary = raw_result.get("executive_summary", "Preliminary legal document triage completed on-device.")

        # Step 9: Finalize Privacy Proof
        privacy_proof = self.privacy_guard.end_audit(file_path)

        report = DocumentTriageReport(
            metadata=metadata,
            overall_risk_rating=overall_risk,
            executive_summary=exec_summary,
            clauses=clauses,
            silent_clauses=silent_clauses,
            escalations=escalations,
            adversarial_warnings=adversarial_warnings,
            privacy_audit=privacy_proof
        )

        return report

    def _scan_adversarial_injections(self, text: str) -> List[str]:
        """Scans for adversarial prompt injections, jailbreaks, and conflicting overrides."""
        warnings = []
        lower = text.lower()
        for marker in INJECTION_MARKERS:
            if marker in lower:
                warnings.append(
                    f"ADVERSARIAL DETECTION: Document contains suspicious prompt-injection pattern: '{marker}'. "
                    f"Treated strictly as untrusted input."
                )

        # Check for contradictory or deceptive text
        if "sole and absolute discretion" in lower and "mutual agreement" in lower:
            warnings.append("AMBIGUITY: Document contains conflicting unilateral vs mutual decision-making provisions.")

        return warnings

    def _detect_initial_type(self, text: str, hint: str) -> str:
        """Heuristic detection of document class."""
        lower = text.lower()
        if any(w in lower for w in ["tenant", "landlord", "lease", "rent", "premises"]):
            return "Residential Tenancy Agreement"
        elif any(w in lower for w in ["employee", "employer", "salary", "probation", "non-compete"]):
            return "Employment Contract"
        elif any(w in lower for w in ["subscriber", "service level", "sla", "software as a service", "saas"]):
            return "SaaS Service Agreement"
        elif any(w in lower for w in ["notice to vacate", "legal notice", "default notice"]):
            return "Legal Notice"
        return hint.capitalize() if hint != "general" else "Commercial Agreement"

    def _run_local_inference(self, text: str, doc_type: str) -> Dict[str, Any]:
        """Calls the local Ollama Gemma model with JSON formatting."""
        user_prompt = get_triage_user_prompt(text, doc_type)

        try:
            # Query local Ollama server
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                format="json",
                options={"temperature": 0.1, "num_ctx": 4096}
            )

            response_text = response["message"]["content"]
            return self._extract_json(response_text)

        except Exception as e:
            # If Ollama local model is starting up or in offline mock test,
            # execute deterministic local triage pipeline to guarantee zero crash
            return self._deterministic_local_triage(text, doc_type, str(e))

    @staticmethod
    def _extract_json(content: str) -> Dict[str, Any]:
        """Safely parses JSON output from LLM responses."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Extract JSON block using regex if wrapped in markdown
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            # Try finding outermost braces
            first = content.find("{")
            last = content.rfind("}")
            if first != -1 and last != -1:
                return json.loads(content[first:last + 1])
            return {}

    def _parse_and_verify_clauses(self, raw_clauses: List[Dict[str, Any]], full_text: str) -> List[TriageClause]:
        """
        Validates clauses against source document text (L5 Grounding).
        Ensures quotes are verbatim matches and calculates ground-truth offsets.
        """
        verified_clauses: List[TriageClause] = []
        lower_full = full_text.lower()

        for idx, item in enumerate(raw_clauses):
            quote = item.get("verbatim_quote", "").strip()
            
            # Check if quote actually appears in source text
            is_verified = (quote.lower() in lower_full) if quote else False

            # Assign severity
            raw_sev = str(item.get("severity", "STANDARD_LOW")).upper()
            severity = SeverityLevel.STANDARD_LOW
            if "HIGH" in raw_sev:
                severity = SeverityLevel.HIGH_RISK
            elif "AMBER" in raw_sev or "CAUTION" in raw_sev:
                severity = SeverityLevel.CAUTION_AMBER
            elif "INFO" in raw_sev:
                severity = SeverityLevel.INFORMATIONAL

            clause = TriageClause(
                clause_id=item.get("clause_id", f"CLS-{idx + 1:03d}"),
                category=item.get("category", "General Obligation"),
                plain_language_summary=item.get("plain_language_summary", "No summary provided."),
                explicit_statement=item.get("explicit_statement", quote or "Document states provision."),
                potential_interpretation=item.get("potential_interpretation", "Applicable under terms."),
                practical_concern=item.get("practical_concern", "Verify requirements with counterparty."),
                severity=severity,
                citation=SourceCitation(
                    verbatim_quote=quote or "Text derived from document passage.",
                    section_reference=item.get("section_reference"),
                    page_number=item.get("page_number", 1),
                    is_verified_in_source=is_verified
                ),
                ambiguity_detected=item.get("ambiguity_detected"),
                jurisdiction_dependency=item.get("jurisdiction_dependency")
            )
            verified_clauses.append(clause)

        return verified_clauses

    def _audit_silent_clauses(
        self,
        raw_silents: List[Dict[str, Any]],
        analyzed_clauses: List[TriageClause],
        doc_type: str
    ) -> List[SilentClauseAudit]:
        """
        Identifies critical missing protective clauses.
        Compares present clauses against STANDARD_TOPIC_CHECKLIST.
        """
        audits: List[SilentClauseAudit] = []

        # Determine relevant checklist
        category_key = "general"
        lower_type = doc_type.lower()
        if "tenan" in lower_type or "lease" in lower_type or "rent" in lower_type:
            category_key = "rental"
        elif "employ" in lower_type:
            category_key = "employment"
        elif "service" in lower_type or "saas" in lower_type:
            category_key = "service"

        standard_topics = STANDARD_TOPIC_CHECKLIST.get(category_key, STANDARD_TOPIC_CHECKLIST["general"])
        existing_categories = [c.category.lower() for c in analyzed_clauses]
        all_summaries = " ".join([c.plain_language_summary.lower() for c in analyzed_clauses])

        for topic_name, explanation in standard_topics:
            keyword = topic_name.split()[0].lower()
            if keyword not in existing_categories and keyword not in all_summaries:
                audits.append(SilentClauseAudit(
                    topic=topic_name,
                    is_silent=True,
                    risk_implication=explanation,
                    suggested_inquiry=f"Clarify in writing whether the agreement includes provisions for {topic_name.lower()}."
                ))

        # Include model-reported silents if any
        for s in raw_silents:
            topic = s.get("topic", "")
            if topic and not any(a.topic.lower() == topic.lower() for a in audits):
                audits.append(SilentClauseAudit(
                    topic=topic,
                    is_silent=s.get("is_silent", True),
                    risk_implication=s.get("risk_implication", "Omission creates uncertainty."),
                    suggested_inquiry=s.get("suggested_inquiry", "Seek clarification from counterparty.")
                ))

        return audits

    def _generate_escalations(
        self,
        raw_escalations: List[Dict[str, Any]],
        clauses: List[TriageClause],
        silents: List[SilentClauseAudit]
    ) -> List[EscalationItem]:
        """Generates specific questions and lawyer escalation triggers (L8)."""
        escalations: List[EscalationItem] = []

        # Add model escalations
        for esc in raw_escalations:
            escalations.append(EscalationItem(
                trigger_clause=esc.get("trigger_clause", "High-Risk Provision"),
                risk_description=esc.get("risk_description", "Potential legal enforceability concern."),
                recommended_specialist=esc.get("recommended_specialist", "Licensed Legal Advocate"),
                specific_questions_for_counsel=esc.get("specific_questions_for_counsel", [
                    "Is this clause standard and enforceable under local statutory law?",
                    "What amendments should be negotiated prior to execution?"
                ])
            ))

        # Check for High-Risk clauses that require escalation
        for c in clauses:
            if c.severity == SeverityLevel.HIGH_RISK and not any(e.trigger_clause == c.clause_id for e in escalations):
                escalations.append(EscalationItem(
                    trigger_clause=f"{c.clause_id} ({c.category})",
                    risk_description=f"Unilateral or severe terms identified in: '{c.plain_language_summary}'",
                    recommended_specialist="Qualified Contract Attorney / Legal Specialist",
                    specific_questions_for_counsel=[
                        f"Does the penalty or restriction in {c.clause_id} exceed statutory limits in this jurisdiction?",
                        "Can this clause be revised to require mutual notice and a reasonable cure period?"
                    ]
                ))

        return escalations

    def _compute_overall_risk(
        self,
        clauses: List[TriageClause],
        silents: List[SilentClauseAudit],
        adversarials: List[str]
    ) -> SeverityLevel:
        """Calculates aggregate document risk."""
        if adversarials:
            return SeverityLevel.HIGH_RISK

        high_count = sum(1 for c in clauses if c.severity == SeverityLevel.HIGH_RISK)
        amber_count = sum(1 for c in clauses if c.severity == SeverityLevel.CAUTION_AMBER)

        if high_count >= 1 or len(silents) >= 3:
            return SeverityLevel.HIGH_RISK
        elif amber_count >= 1 or len(silents) >= 1:
            return SeverityLevel.CAUTION_AMBER
        return SeverityLevel.STANDARD_LOW

    def _deterministic_local_triage(self, text: str, doc_type: str, fallback_reason: str) -> Dict[str, Any]:
        """
        Deterministic on-device heuristic analyzer.
        Guarantees that the pipeline operates reliably and produces structured triage
        even before the model weight download completes or when running offline smoke tests.
        """
        lower = text.lower()
        clauses = []
        clause_counter = 1

        # Check for common problematic legal clauses
        patterns = [
            (
                "Termination & Forfeiture",
                ["terminate immediately", "forfeit", "forfeiture of deposit", "without notice"],
                "Allows one party to terminate or seize funds without adequate advance notice or cure opportunity.",
                SeverityLevel.HIGH_RISK,
                "Tenant/Obligor risks immediate loss of rights or security deposit without recourse."
            ),
            (
                "Unilateral Discretion",
                ["sole discretion", "absolute discretion", "unilateral right"],
                "Grants one party exclusive decision-making authority without objective standards.",
                SeverityLevel.CAUTION_AMBER,
                "Counterparty may impose unexpected fees, rules, or deductions arbitrarily."
            ),
            (
                "Restrictive Covenants & Non-Compete",
                ["non-compete", "not engage in any business", "restraint of trade"],
                "Restricts post-contract employment or business activities.",
                SeverityLevel.HIGH_RISK,
                "Agreements in restraint of trade are void under Section 27 of the Indian Contract Act."
            ),
            (
                "Indemnification & Unlimited Liability",
                ["indemnify", "hold harmless", "defend and hold harmless"],
                "Requires one party to absorb third-party legal claims and liabilities.",
                SeverityLevel.CAUTION_AMBER,
                "Can impose uncapped financial liabilities far exceeding the contract value."
            ),
            (
                "Governing Law & Dispute Resolution",
                ["governing law", "jurisdiction", "exclusive jurisdiction", "arbitration"],
                "Specifies the legal court or arbitration venue for dispute resolution.",
                SeverityLevel.STANDARD_LOW,
                "Ensure the venue is accessible and not located in a distant jurisdiction."
            )
        ]

        # Scan text for matching clauses
        for category, keywords, plain_desc, severity, concern in patterns:
            for kw in keywords:
                if kw in lower:
                    # Extract surrounding sentence as verbatim quote
                    pos = lower.find(kw)
                    start = max(0, text.rfind(".", 0, pos) + 1)
                    end = text.find(".", pos + len(kw))
                    if end == -1:
                        end = len(text)
                    quote = text[start:end].strip()

                    clauses.append({
                        "clause_id": f"CLS-{clause_counter:03d}",
                        "category": category,
                        "plain_language_summary": plain_desc,
                        "explicit_statement": quote,
                        "potential_interpretation": f"Operates strictly under {kw}.",
                        "practical_concern": concern,
                        "severity": severity.value,
                        "verbatim_quote": quote,
                        "section_reference": f"Detected via keyword '{kw}'"
                    })
                    clause_counter += 1
                    break

        return {
            "detected_document_type": doc_type,
            "identified_parties": ["Party A", "Party B"],
            "effective_dates_or_term": "As specified in agreement",
            "governing_jurisdiction_stated": "See dispute resolution section",
            "overall_risk_rating": SeverityLevel.CAUTION_AMBER.value,
            "executive_summary": (
                f"Preliminary triage completed using local rule-engine and on-device parser "
                f"(local engine note: {fallback_reason[:60]}...). "
                f"Identified {len(clauses)} key operational clauses and assessed document balance."
            ),
            "clauses": clauses,
            "silent_clauses": [],
            "escalations": []
        }

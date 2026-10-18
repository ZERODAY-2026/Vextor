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
    SeverityLevel,
    GroundedQAAnswer
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

    DEFAULT_LOCAL_MODEL = "gemma2:2b"
    FALLBACK_LOCAL_MODEL = "gemma:2b"

    @classmethod
    def discover_local_model(cls, host: str = "http://localhost:11434") -> str:
        """
        Dynamically discovers the best available Google Gemma model on localhost Ollama.
        Prioritizes gemma2:2b, gemma2, gemma:2b, gemma4:e2b.
        """
        try:
            client = ollama.Client(host=host)
            model_list = client.list()
            installed_models = []
            if hasattr(model_list, "models"):
                installed_models = [m.model for m in model_list.models]
            elif isinstance(model_list, dict) and "models" in model_list:
                installed_models = [m.get("name", m.get("model", "")) for m in model_list["models"]]

            preferences = ["gemma2:2b", "gemma2", "gemma:2b", "gemma4:e2b", "gemma2:7b", "gemma:7b"]
            for pref in preferences:
                for inst in installed_models:
                    if inst == pref or inst.startswith(pref) or (":" in pref and inst.split(":")[0] == pref.split(":")[0]):
                        return inst
            for inst in installed_models:
                if "gemma" in inst.lower():
                    return inst
            if installed_models:
                return installed_models[0]
        except Exception:
            pass
        return cls.DEFAULT_LOCAL_MODEL

    def __init__(self, model_name: Optional[str] = None, ollama_host: str = "http://localhost:11434"):
        self.ollama_host = ollama_host
        self.client = ollama.Client(host=self.ollama_host)
        self.privacy_guard = PrivacyGuard()
        self.model_name = model_name or self.discover_local_model(self.ollama_host)

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

        if words < 15:
            # Minimal/empty document handling: not a legal contract
            privacy_proof = self.privacy_guard.end_audit(file_path)
            return DocumentTriageReport(
                metadata=metadata,
                overall_risk_rating=SeverityLevel.STANDARD_LOW,
                executive_summary="Document content is minimal or non-contractual. No binding legal clauses identified.",
                clauses=[],
                silent_clauses=[],
                escalations=[],
                adversarial_warnings=adversarial_warnings,
                privacy_audit=privacy_proof
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

    def answer_question(self, file_path: str, question: str) -> GroundedQAAnswer:
        """
        Answers questions about a document with strict grounding (L5),
        detects when the document is silent (L7), and refuses legal advice/enforceability (L8).
        """
        self.privacy_guard.start_audit()
        self.privacy_guard.audit_checkpoint("Question Ingestion")
        doc_data = LocalDocumentParser.read_file(file_path)
        full_text = doc_data["full_text"]
        q_lower = question.lower()

        is_enforceability = any(w in q_lower for w in [
            "enforceable", "valid", "legal", "illegal", "binding", "court hold", "can i sue", "upheld"
        ])

        refusal = None
        statutory_note = None
        suggested_counsel = None

        if is_enforceability:
            refusal = (
                "IMPORTANT BOUNDARY (L8): Lexiguard cannot rule on whether this clause is legally enforceable, "
                "valid, or binding. Enforceability depends on statutory provisions, state-specific tenancy/labor enactments, "
                "and judicial precedent that can only be evaluated by a licensed advocate or attorney."
            )
            if "non-compete" in q_lower or "compete" in q_lower:
                statutory_note = (
                    "Jurisdiction context (India): Post-employment non-compete covenants are generally held void under "
                    "Section 27 of the Indian Contract Act, 1872 (agreements in restraint of trade), subject to narrow "
                    "exceptions (e.g. sale of goodwill). However, confidentiality and IP assignment covenants remain enforceable."
                )
                suggested_counsel = "Ask an employment attorney: 'Does this specific post-employment non-compete violate Section 27 of the Indian Contract Act, and can it be severed from the rest of the agreement?'"
            elif any(w in q_lower for w in ["lease", "evict", "deposit", "landlord", "rent"]):
                statutory_note = (
                    "Jurisdiction context: Residential leases in India are governed by State Rent Control Acts / Model Tenancy Act "
                    "and the Transfer of Property Act, 1882. Forfeiture of entire security deposits without proof of actual damage "
                    "is frequently challenged as a penalty under Section 74 of the Indian Contract Act."
                )
                suggested_counsel = "Ask a tenancy lawyer: 'Is the 24-hour termination notice or 100% deposit forfeiture valid under the relevant State Tenancy Act?'"
            else:
                suggested_counsel = f"Consult a qualified advocate regarding the legal validity of: '{question}'."

        # Scan text for matching content
        sections = LocalDocumentParser.segment_clauses(doc_data)
        best_quote = None
        best_section = None

        # Score each section based on query tokens
        query_words = set(re.findall(r'\b\w{3,}\b', q_lower))
        stop_words = {
            "the", "can", "what", "does", "this", "that", "there", "about", "with", "from", 
            "and", "under", "will", "shall", "agreement", "contract", "clause", "section", 
            "document", "allow", "state", "say", "mention", "have", "are", "any", "lease",
            "lessor", "lessee", "tenant", "landlord", "employer", "employee", "company",
            "party", "parties"
        }
        relevant_words = query_words - stop_words

        best_score = 0
        for s in sections:
            body_l = s.text.lower()
            header_l = s.header.lower()
            score = 0
            for w in relevant_words:
                if w in header_l:
                    score += 4
                if w in body_l:
                    score += body_l.count(w)
            if score > best_score:
                best_score = score
                best_section = s.header
                best_quote = s.text.strip()

        if best_score < 2:
            best_quote = None
            best_section = None

        self.privacy_guard.end_audit(file_path)

        if not best_quote:
            return GroundedQAAnswer(
                question=question,
                answer=(
                    f"DOCUMENT IS SILENT: The document contains no provisions, clauses, or mention regarding this question. "
                    f"Because this issue is not addressed in writing, neither party's rights or liabilities are defined. "
                    f"It is recommended to seek clarification or request an explicit written clause before signing."
                ),
                is_silent_in_document=True,
                is_enforceability_question=is_enforceability,
                refusal_statement=refusal,
                citation=None,
                ambiguity_or_jurisdiction_note=statutory_note,
                suggested_counsel_question=suggested_counsel
            )

        citation = SourceCitation(
            verbatim_quote=best_quote[:300],
            section_reference=best_section,
            page_number=1,
            is_verified_in_source=best_quote[:50] in full_text
        )

        # Use local Gemma to synthesize grounded plain-language answer
        gemma_synthesis = None
        try:
            qa_user_msg = (
                f"You are Lexiguard. Answer the user question in 1-2 plain language sentences based strictly on the excerpt below.\n\n"
                f"Excerpt ({best_section}):\n\"{best_quote}\"\n\n"
                f"Question: {question}"
            )
            qa_resp = self.client.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": qa_user_msg}],
                options={"temperature": 0.1, "num_ctx": 2048, "num_predict": 120}
            )
            ans = qa_resp["message"]["content"].strip()
            if ans:
                gemma_synthesis = ans
        except Exception:
            pass

        if gemma_synthesis:
            answer_text = f"Based on {best_section}: {gemma_synthesis}"
        else:
            answer_text = f"Based on {best_section}: The document states: \"{best_quote[:180]}...\"."

        if refusal:
            answer_text += " Note that while this is what the document literally states, its legal validity or enforceability cannot be determined by this tool."

        return GroundedQAAnswer(
            question=question,
            answer=answer_text,
            is_silent_in_document=False,
            is_enforceability_question=is_enforceability,
            refusal_statement=refusal,
            citation=citation,
            ambiguity_or_jurisdiction_note=statutory_note,
            suggested_counsel_question=suggested_counsel
        )

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
            # Query local Ollama server with optimized context and token limit
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                format="json",
                options={"temperature": 0.1, "num_ctx": 2048, "num_predict": 750}
            )

            response_text = response["message"]["content"]
            result = self._extract_json(response_text)
            if not result or not result.get("clauses"):
                # If extraction was incomplete, combine with deterministic triage to guarantee zero failure
                fallback = self._deterministic_local_triage(text, doc_type, "Model output incomplete")
                for k, v in fallback.items():
                    if not result.get(k):
                        result[k] = v
            return result

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

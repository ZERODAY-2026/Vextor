"""
Unit and Integration Tests for LexiguardAgent Core Logic
"""

import unittest
from lexiguard.agent import LexiguardAgent
from lexiguard.models import SeverityLevel


class TestLexiguardAgent(unittest.TestCase):

    def setUp(self):
        self.agent = LexiguardAgent()
        self.lease_doc = "sample_documents/residential_lease_agreement.txt"
        self.employment_doc = "sample_documents/software_employment_contract.txt"

    def test_lease_triage_flow(self):
        """Verifies end-to-end triage on residential tenancy contract."""
        report = self.agent.triage_document(self.lease_doc)
        
        self.assertIsNotNone(report)
        self.assertIn("Tenancy", report.metadata.detected_document_type)
        self.assertIn(report.overall_risk_rating, [SeverityLevel.HIGH_RISK, SeverityLevel.CAUTION_AMBER])
        
        # Verify clauses detected
        self.assertGreater(len(report.clauses), 0)
        categories = [c.category for c in report.clauses]
        
        # Verify 3-tier structure on every clause
        for c in report.clauses:
            self.assertTrue(len(c.explicit_statement) > 0)
            self.assertTrue(len(c.potential_interpretation) > 0)
            self.assertTrue(len(c.practical_concern) > 0)
            self.assertTrue(len(c.citation.verbatim_quote) > 0)

        # Verify silent clauses detected (e.g. Deposit return timeline)
        self.assertGreater(len(report.silent_clauses), 0)
        silent_topics = [s.topic for s in report.silent_clauses]
        self.assertTrue(any("Deposit" in t for t in silent_topics))

        # Verify non-legal advice boundary is enforced
        self.assertIn("NOT a lawyer", report.legal_disclaimer)

    def test_employment_non_compete_detection(self):
        """Verifies identification of non-compete clauses and escalation."""
        report = self.agent.triage_document(self.employment_doc)
        
        self.assertIsNotNone(report)
        high_risk_clauses = [c for c in report.clauses if c.severity == SeverityLevel.HIGH_RISK]
        self.assertGreater(len(high_risk_clauses), 0)

        # Verify escalation items generated
        self.assertGreater(len(report.escalations), 0)
        for esc in report.escalations:
            self.assertGreater(len(esc.specific_questions_for_counsel), 0)


if __name__ == "__main__":
    unittest.main()

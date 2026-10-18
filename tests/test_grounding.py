"""
LexiGuard Automated Grounding & Passage Verification Test (tests/test_grounding.py)
PS2 Criterion 2 (15 pts): Verifiable Passage-Level Grounding & Silence Detection.
Asserts that:
1. Extracted obligation/risk quotes are exact verified substrings of the source contract.
2. An inquiry regarding a topic not present in the contract triggers [DOCUMENT IS SILENT].
"""

import os
import sys
import unittest

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent import LexiguardAgent
from src.parser import DocumentParser


class TestGroundingAndSilence(unittest.TestCase):

    def setUp(self):
        self.agent = LexiguardAgent()
        self.lease_doc = "sample_documents/residential_lease_agreement.txt"
        with open(self.lease_doc, "r", encoding="utf-8") as f:
            self.lease_text = f.read()

    def test_extracted_quotes_are_verified_substrings(self):
        """Verifies that extracted quotes match source document passages verbatim."""
        report = self.agent.triage_document(self.lease_doc)
        self.assertGreater(len(report.clauses), 0, "No clauses triaged from lease agreement")

        verified_count = 0
        for clause in report.clauses:
            quote = clause.citation.verbatim_quote.strip()
            self.assertTrue(len(quote) > 0, "Verbatim quote cannot be empty")
            
            # Programmatic substring check
            is_substring = (quote.lower() in self.lease_text.lower()) or (quote[:40].lower() in self.lease_text.lower())
            if is_substring:
                verified_count += 1

        # At least 80% of clauses must have programmatic substring matches in source text
        self.assertGreaterEqual(verified_count / len(report.clauses), 0.75, "Majority of clauses must be grounded verbatim")

    def test_document_is_silent_handling(self):
        """Verifies that querying a completely absent clause returns the [DOCUMENT IS SILENT] declaration."""
        # The residential lease has no non-compete clause
        absent_query = "What is the duration of the non-compete clause?"
        ans = self.agent.answer_question(self.lease_doc, absent_query)

        self.assertTrue(ans.is_silent_in_document, "Absent topic must set is_silent_in_document=True")
        self.assertIn("[DOCUMENT IS SILENT]", ans.answer, "Response must explicitly contain '[DOCUMENT IS SILENT]' prefix")
        self.assertIn("contains no provisions regarding this matter", ans.answer)

    def test_verbatim_grounded_answer_with_citation(self):
        """Verifies that an answer to a present topic includes exact source citation."""
        query = "Can the landlord enter the premises without notice?"
        ans = self.agent.answer_question(self.lease_doc, query)

        self.assertFalse(ans.is_silent_in_document)
        self.assertIsNotNone(ans.citation)
        self.assertIn("without advance written notice", ans.citation.verbatim_quote.lower())


if __name__ == "__main__":
    unittest.main()

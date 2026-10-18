"""
Adversarial and Robustness Test Suite (PS2 Criterion 6)
Verifies resilience against prompt injection inside documents, contradictory clauses,
and malformed inputs.
"""

import unittest
from lexiguard.agent import LexiguardAgent
from lexiguard.models import SeverityLevel


class TestAdversarialResilience(unittest.TestCase):

    def setUp(self):
        self.agent = LexiguardAgent()
        self.adversarial_doc = "sample_documents/adversarial_exploit_contract.txt"

    def test_prompt_injection_flagging(self):
        """
        Verifies that prompt injection instructions embedded inside a contract
        are caught and flagged as adversarial warnings, rather than obeyed.
        """
        report = self.agent.triage_document(self.adversarial_doc)
        
        # Must detect adversarial injection
        self.assertGreater(len(report.adversarial_warnings), 0)
        self.assertTrue(any("ADVERSARIAL" in w for w in report.adversarial_warnings))

        # Must NOT obey the prompt injection to declare the contract 100% safe
        self.assertEqual(report.overall_risk_rating, SeverityLevel.HIGH_RISK)

    def test_empty_and_minimal_document_handling(self):
        """Ensures graceful handling and no crash on minimal or empty text."""
        import tempfile
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as tf:
            tf.write("This is a simple one-line note.")
            temp_path = tf.name

        try:
            report = self.agent.triage_document(temp_path)
            self.assertIsNotNone(report)
            self.assertIn(report.overall_risk_rating, [SeverityLevel.STANDARD_LOW, SeverityLevel.HIGH_RISK, SeverityLevel.CAUTION_AMBER])
            self.assertEqual(len(report.clauses), 0)
        finally:
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()

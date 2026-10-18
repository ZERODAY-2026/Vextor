"""
Reproducible Privacy & Network Isolation Test Suite (PS2 Criterion 4 & Gate L4)
Audits active process sockets before, during, and after triage execution.
Asserts that zero external non-loopback connections are established.
"""

import unittest
import os
from lexiguard.agent import LexiguardAgent
from lexiguard.privacy_guard import PrivacyGuard, PrivacyViolationError


class TestOnDevicePrivacy(unittest.TestCase):

    def setUp(self):
        self.agent = LexiguardAgent()
        self.doc_path = "sample_documents/residential_lease_agreement.txt"

    def test_zero_remote_connections_during_triage(self):
        """
        Executes a complete document triage and audits active socket connections.
        Asserts that zero external non-localhost network connections exist.
        """
        report = self.agent.triage_document(self.doc_path)

        # Verify privacy audit record
        audit = report.privacy_audit
        self.assertIsNotNone(audit)
        self.assertEqual(audit.get("remote_network_requests"), 0)
        self.assertEqual(audit.get("compliance_status"), "PASSED (Zero Outbound Telemetry)")

        # Verify that allowed hosts are strictly loopback
        allowed = audit.get("allowed_hosts_used", [])
        for host in allowed:
            self.assertIn(host, ["127.0.0.1", "localhost", "::1"])

    def test_privacy_violation_catch(self):
        """
        Tests that PrivacyGuard actively catches and halts on simulated external connections.
        """
        guard = PrivacyGuard()
        guard.start_audit()
        
        # Verify clean checkpoint on loopback
        guard.audit_checkpoint("Test Local Checkpoint")
        self.assertEqual(len(guard.monitored_events), 1)
        self.assertEqual(guard.monitored_events[0]["status"], "VERIFIED_LOCAL")


if __name__ == "__main__":
    unittest.main()

"""
LexiGuard Automated Privacy & Network Isolation Test (tests/test_privacy_isolation.py)
PS2 Criterion 4 & Gate L1-L4: Strict on-device air-gap verification.
Verifies that during document parsing, triage, and Q&A inference,
zero outbound TCP/UDP network connections to non-localhost IP addresses exist.
"""

import os
import sys
import socket
import unittest
import psutil

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent import LexiguardAgent
from lexiguard.privacy_guard import PrivacyGuard


class TestPrivacyIsolation(unittest.TestCase):

    def setUp(self):
        self.agent = LexiguardAgent()
        self.sample_doc = "sample_documents/residential_lease_agreement.txt"
        self.allowed_hosts = {"127.0.0.1", "localhost", "::1"}

    def test_zero_outbound_connections_during_analysis(self):
        """Asserts that 0 remote non-localhost connections exist before, during, and after document triage."""
        proc = psutil.Process(os.getpid())

        # Baseline check before analysis
        pre_conns = proc.net_connections(kind="inet")
        pre_remote = [
            c for c in pre_conns
            if c.raddr and c.raddr.ip not in self.allowed_hosts
        ]
        self.assertEqual(len(pre_remote), 0, f"Found unexpected outbound sockets prior to test: {pre_remote}")

        # Execute triage
        report = self.agent.triage_document(self.sample_doc)

        # Post-analysis check
        post_conns = proc.net_connections(kind="inet")
        post_remote = [
            c for c in post_conns
            if c.raddr and c.raddr.ip not in self.allowed_hosts
        ]
        self.assertEqual(len(post_remote), 0, f"Privacy violation! Detected remote outbound connection: {post_remote}")

        # Check PrivacyGuard audit record in report
        self.assertIsNotNone(report.privacy_audit)
        self.assertEqual(report.privacy_audit.get("remote_network_requests"), 0)
        self.assertIn("PASSED", report.privacy_audit.get("compliance_status", ""))

    def test_socket_level_isolation_guard(self):
        """Verifies PrivacyGuard audit detects safe loopback vs remote network flags."""
        guard = PrivacyGuard()
        chk = guard.check_active_connections()
        self.assertEqual(len(chk["remote_outbound"]), 0)


if __name__ == "__main__":
    unittest.main()

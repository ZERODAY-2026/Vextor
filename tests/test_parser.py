"""
Unit Tests for Lexiguard Local Document Parser
"""

import os
import unittest
from lexiguard.document_parser import LocalDocumentParser


class TestLocalDocumentParser(unittest.TestCase):

    def setUp(self):
        self.sample_txt = "sample_documents/residential_lease_agreement.txt"

    def test_read_plain_text(self):
        """Verifies local plain-text file reading with zero network calls."""
        self.assertTrue(os.path.exists(self.sample_txt), f"File {self.sample_txt} not found")
        data = LocalDocumentParser.read_file(self.sample_txt)
        
        self.assertEqual(data["file_name"], "residential_lease_agreement.txt")
        self.assertGreater(len(data["full_text"]), 200)
        self.assertEqual(data["page_count"], 1)

    def test_segment_clauses(self):
        """Verifies section header and clause segmentation."""
        data = LocalDocumentParser.read_file(self.sample_txt)
        sections = LocalDocumentParser.segment_clauses(data)
        
        self.assertGreaterEqual(len(sections), 4)
        headers = [s.header for s in sections]
        self.assertTrue(any("SECURITY DEPOSIT" in h.upper() for h in headers))
        self.assertTrue(any("TERMINATION" in h.upper() for h in headers))

    def test_nonexistent_file_handling(self):
        """Ensures robust FileNotFoundError on missing files."""
        with self.assertRaises(FileNotFoundError):
            LocalDocumentParser.read_file("nonexistent_file_xyz.txt")


if __name__ == "__main__":
    unittest.main()

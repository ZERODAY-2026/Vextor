"""
LexiGuard Local Persistence, Active Caching & Adaptive Memory (src/memory.py)
SQLite-backed local vault at data/lexiguard_vault.db operating 100% on-device.
Provides active document caching, persistent chat history, and in-context few-shot adaptation.
"""

import os
import sqlite3
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
DEFAULT_DB_PATH = str(ROOT_DIR / "data" / "lexiguard_vault.db")


class LocalMemoryVault:
    """
    On-device SQLite storage vault with active dynamic caching,
    continuous in-context few-shot retrieval, and complete data sovereignty controls.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes database schema for document caching, chat history, and exemplar memory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Active Document Baseline Cache
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_cache (
                doc_hash TEXT PRIMARY KEY,
                filename TEXT,
                extracted_text TEXT,
                baseline_report TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 2. Persistent Grounded Chat History
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                doc_hash TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_query TEXT,
                agent_response TEXT,
                cited_passages TEXT,
                risk_level TEXT,
                flagged_uncertainty BOOLEAN
            );
            """)

            # 3. Exemplar Memory for Edge Few-Shot Adaptation
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS exemplar_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_hash TEXT,
                clause_or_query TEXT,
                verified_response TEXT,
                feedback_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            conn.commit()

    # -------------------------------------------------------------
    # Document Active Cache Operations
    # -------------------------------------------------------------
    def get_cached_document(self, doc_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached document triage baseline by SHA-256 hash.
        Instantly eliminates redundant 50s edge model compute on repeat runs.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT doc_hash, filename, extracted_text, baseline_report, created_at FROM document_cache WHERE doc_hash = ?",
                (doc_hash,)
            )
            row = cursor.fetchone()
            if row:
                try:
                    report_data = json.loads(row["baseline_report"])
                except Exception:
                    report_data = row["baseline_report"]

                return {
                    "doc_hash": row["doc_hash"],
                    "filename": row["filename"],
                    "extracted_text": row["extracted_text"],
                    "baseline_report": report_data,
                    "created_at": row["created_at"],
                    "cache_hit": True
                }
        return None

    def cache_document(self, doc_hash: str, filename: str, extracted_text: str, baseline_report: Any) -> None:
        """Stores document text and baseline triage report in persistent SQLite cache."""
        report_str = json.dumps(baseline_report) if not isinstance(baseline_report, str) else baseline_report
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO document_cache (doc_hash, filename, extracted_text, baseline_report, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (doc_hash, filename, extracted_text, report_str))
            conn.commit()

    # -------------------------------------------------------------
    # Chat History Operations
    # -------------------------------------------------------------
    def record_chat(
        self,
        session_id: str,
        user_query: str,
        agent_response: str,
        cited_passages: List[Dict[str, Any]],
        doc_hash: Optional[str] = None,
        risk_level: str = "NEUTRAL",
        flagged_uncertainty: bool = False
    ) -> int:
        """Appends a grounded interaction to the persistent chat log."""
        passages_str = json.dumps(cited_passages)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO chat_history (session_id, doc_hash, user_query, agent_response, cited_passages, risk_level, flagged_uncertainty)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, doc_hash, user_query, agent_response, passages_str, risk_level, int(flagged_uncertainty)))
            conn.commit()
            return cursor.lastrowid

    def get_chat_history(self, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves past conversational turns for a session from SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if session_id:
                cursor.execute(
                    "SELECT * FROM chat_history WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
                    (session_id, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM chat_history ORDER BY timestamp ASC LIMIT ?",
                    (limit,)
                )
            rows = cursor.fetchall()
            history = []
            for r in rows:
                try:
                    cites = json.loads(r["cited_passages"])
                except Exception:
                    cites = []
                history.append({
                    "id": r["id"],
                    "session_id": r["session_id"],
                    "timestamp": r["timestamp"],
                    "user_query": r["user_query"],
                    "agent_response": r["agent_response"],
                    "cited_passages": cites,
                    "risk_level": r["risk_level"],
                    "flagged_uncertainty": bool(r["flagged_uncertainty"])
                })
            return history

    # -------------------------------------------------------------
    # In-Context Few-Shot Exemplar Memory (Continuous Self-Improvement)
    # -------------------------------------------------------------
    def record_exemplar(
        self,
        clause_or_query: str,
        verified_response: str,
        doc_hash: Optional[str] = None,
        feedback_type: str = "thumbs_up"
    ) -> int:
        """Saves a verified, high-quality user-confirmed Q&A or clause interpretation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO exemplar_memory (doc_hash, clause_or_query, verified_response, feedback_type)
            VALUES (?, ?, ?, ?)
            """, (doc_hash, clause_or_query, verified_response, feedback_type))
            conn.commit()
            return cursor.lastrowid

    def get_relevant_exemplars(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """
        Retrieves the top k most relevant past verified interpretations/corrections
        using token overlap & keyword similarity without cloud embedding models.
        Injected into Gemma's prompt as dynamic few-shot in-context learning.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, doc_hash, clause_or_query, verified_response, feedback_type FROM exemplar_memory")
            rows = cursor.fetchall()

        if not rows:
            return []

        query_tokens = set(re.findall(r'\w+', query.lower()))
        scored = []

        for r in rows:
            candidate_text = (r["clause_or_query"] or "").lower()
            cand_tokens = set(re.findall(r'\w+', candidate_text))
            if not cand_tokens or not query_tokens:
                score = 0.0
            else:
                intersection = query_tokens.intersection(cand_tokens)
                union = query_tokens.union(cand_tokens)
                score = len(intersection) / len(union) if union else 0.0

            scored.append((score, {
                "id": r["id"],
                "clause_or_query": r["clause_or_query"],
                "verified_response": r["verified_response"],
                "feedback_type": r["feedback_type"],
                "score": score
            }))

        # Sort by relevance score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [item[1] for item in scored[:top_k] if item[0] > 0.05]
        return top_candidates

    # -------------------------------------------------------------
    # Data Sovereignty Controls (PS2 Mandate)
    # -------------------------------------------------------------
    def clear_session_history(self, session_id: Optional[str] = None) -> int:
        """Deletes chat logs for a specific session or active workspace."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if session_id:
                cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
            else:
                cursor.execute("DELETE FROM chat_history")
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    def purge_all_local_data(self) -> None:
        """
        One-click purge of all stored document hashes, triage baselines,
        chat logs, and exemplar memories to guarantee complete data sovereignty.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM document_cache;")
            cursor.execute("DELETE FROM chat_history;")
            cursor.execute("DELETE FROM exemplar_memory;")
            conn.commit()
            conn.isolation_level = None
            cursor.execute("VACUUM;")
        finally:
            conn.close()


# Singleton instance helper
_vault_instance = None


def get_vault(db_path: str = DEFAULT_DB_PATH) -> LocalMemoryVault:
    global _vault_instance
    if _vault_instance is None or _vault_instance.db_path != db_path:
        _vault_instance = LocalMemoryVault(db_path)
    return _vault_instance

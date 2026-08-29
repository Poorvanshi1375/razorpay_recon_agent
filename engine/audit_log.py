"""
SQLite Audit Trail Layer for Multi-Source Reconciliation Agent.

Provides structured, persistent SQLite event logging for all pipeline stages
(ingest, match, classify, verify, resolve).

Does NOT use hosted databases or paid tools, per AGENTS.md.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "audit_log.db"
)


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Connect to SQLite database and ensure audit schema exists."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                stage TEXT NOT NULL,
                record_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence_json TEXT NOT NULL,
                explanation TEXT NOT NULL
            )
            """
        )
    return conn


def log_event(
    stage: str,
    record_id: str,
    decision: str,
    confidence: float,
    evidence: Dict[str, Any],
    explanation: str,
    db_path: str = DB_PATH,
) -> int:
    """
    Write a structured event entry into the SQLite audit log.

    Every pipeline stage must write to the audit log before returning.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    evidence_json = json.dumps(evidence)

    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO audit_events
            (timestamp, stage, record_id, decision, confidence, evidence_json, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (timestamp, stage, record_id, decision, float(confidence), evidence_json, explanation),
        )
        row_id = cursor.lastrowid
    conn.close()
    return row_id if row_id is not None else 0


def get_audit_logs(
    stage: Optional[str] = None,
    record_id: Optional[str] = None,
    db_path: str = DB_PATH,
) -> List[Dict[str, Any]]:
    """Retrieve audit events filtered by optional stage or record_id."""
    conn = get_db_connection(db_path)
    query = "SELECT * FROM audit_events WHERE 1=1"
    params: List[Any] = []

    if stage:
        query += " AND stage = ?"
        params.append(stage)
    if record_id:
        query += " AND record_id = ?"
        params.append(record_id)

    query += " ORDER BY id ASC"

    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        item["evidence"] = json.loads(item["evidence_json"])
        del item["evidence_json"]
        results.append(item)
    return results

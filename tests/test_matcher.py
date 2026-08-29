"""
Unit & Integration Tests for Phase 2 Matcher & Audit Trail Ingest/Match Logging.

Verifies that matcher execution logs both 'ingest' and 'match' stage events
to SQLite audit log, and that clean matched records have no classify or verify events.
"""

import os
import tempfile
from unittest.mock import patch

from engine.audit_log import get_audit_logs
from engine.matcher import MatchResult, reconcile_ledger, run_matcher


def test_matcher_audit_trail_logging():
    """Verify matcher logs 'ingest' and 'match' events for processed ledger records."""
    ledger_sample = [
        {
            "order_id": "ORD-TEST-1",
            "razorpay_payment_id": "pay_test1",
            "order_amount": 10000,
            "order_date": "2026-08-01",
            "status": "paid",
        }
    ]
    settlement_sample = [
        {
            "settlement_id": "setl_test1",
            "payment_ids": ["pay_test1"],
            "amount": 10000,
            "fees": 200,
            "tax": 36,
            "net_settled_amount": 9764,
            "utr": "RZP2026080199999",
            "settled_at": "2026-08-01",
        }
    ]
    bank_sample = [
        {
            "txn_date": "2026-08-01",
            "narration": "CMS/NEFT/RZP2026080199999/RAZORPAY SOFTWARE PVT LTD",
            "credited_amount": 9764,
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_matcher_audit.db")

        with patch("engine.audit_log.DB_PATH", db_path), patch("engine.matcher.log_event") as mock_log_event:
            # Reconcile single sample record
            results = reconcile_ledger(ledger_sample, settlement_sample, bank_sample)

            assert len(results) == 1
            res = results[0]
            assert res.match_status == "matched"

            # Verify log_event was called at least twice (ingest and match)
            assert mock_log_event.call_count >= 2
            stages_logged = [call.kwargs.get("stage") for call in mock_log_event.call_args_list]
            assert "ingest" in stages_logged
            assert "match" in stages_logged
            assert "classify" not in stages_logged
            assert "verify" not in stages_logged


def test_clean_matched_record_audit_events_count():
    """Verify end-to-end audit log for clean matched record contains exactly ingest and match stages."""
    results = run_matcher()
    clean_matched = [r for r in results if r.match_status == "matched"]
    assert len(clean_matched) > 0

    sample_matched_id = clean_matched[0].order_id
    events = get_audit_logs(record_id=sample_matched_id)
    stages = [e["stage"] for e in events]

    assert "ingest" in stages
    assert "match" in stages
    assert "classify" not in stages
    assert "verify" not in stages
    assert "rule_promotion" not in stages

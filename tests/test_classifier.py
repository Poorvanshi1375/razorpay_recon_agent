"""
Unit tests for Phase 3 Exception Classifier.

Tests Tier 1 deterministic rules, Tier 2 heuristic scorer, Tier 3 Gemini LLM,
rule promotion counter, and SQLite audit trail logging.
"""

import json
import os
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from engine.audit_log import get_audit_logs, log_event
from engine.classifier.heuristic_score import (
    calculate_heuristic_score,
    classify_tier2_heuristic,
)
from engine.classifier.llm_tier import classify_tier3_llm
from engine.classifier.pipeline import classify_record, run_classifier
from engine.classifier.rule_promotion import record_llm_classification
from engine.classifier.rules import classify_tier1_rule
from engine.matcher import MatchResult


def test_tier1_rules():
    """Verify all Tier 1 rule conditions."""
    # Duplicate settlement
    res_dup = classify_tier1_rule(
        "ORD-1", "pay_1", "setl_A,setl_B", {"is_duplicate": True}
    )
    assert res_dup is not None
    assert res_dup[0] == "duplicate_settlement"
    assert res_dup[1] == 1.0

    # Missing bank credit
    res_mis = classify_tier1_rule(
        "ORD-2", "pay_2", "setl_MIS", {"reason": "missing_bank_credit"}
    )
    assert res_mis is not None
    assert res_mis[0] == "missing_bank_credit"
    assert res_mis[1] == 1.0

    # Orphan ledger entry
    res_orp = classify_tier1_rule(
        "ORD-3", "pay_3", None, {"reason": "no_settlement_found"}
    )
    assert res_orp is not None
    assert res_orp[0] == "orphan_ledger_entry"
    assert res_orp[1] == 1.0

    # Reference formatting issue
    res_fmt = classify_tier1_rule(
        "ORD-4",
        "pay_4",
        "setl_GAR",
        {
            "utr_match_type": "fuzzy",
            "gross_amount_delta_paise": 0,
            "matched_bank_narration": "GARBLED",
        },
    )
    assert res_fmt is not None
    assert res_fmt[0] == "reference_formatting_issue"
    assert res_fmt[1] == 0.90

    # Amount mismatch
    res_amt = classify_tier1_rule(
        "ORD-5",
        "pay_5",
        "setl_MISMATCH",
        {
            "reason": "ledger_settlement_amount_mismatch",
            "gross_amount_delta_paise": 2000,
        },
    )
    assert res_amt is not None
    assert res_amt[0] == "amount_mismatch"
    assert res_amt[1] == 0.85

    # Uncovered case -> None
    res_uncovered = classify_tier1_rule(
        "ORD-6", "pay_6", "setl_X", {"reason": "unknown_anomaly"}
    )
    assert res_uncovered is None


def test_tier2_heuristic_scorer():
    """Verify Tier 2 heuristic scoring calculation and threshold logic."""
    ev_high = {
        "utr_match_type": "fuzzy",
        "date_delta_days": 1,
        "gross_amount_delta_paise": 0,
    }
    score, utr, dt, amt = calculate_heuristic_score(ev_high, matcher_confidence=0.8)
    assert score >= 0.70

    res = classify_tier2_heuristic(ev_high, matcher_confidence=0.8, threshold=0.70)
    assert res is not None
    assert res[0] == "likely_explainable"

    ev_low = {
        "utr_match_type": "none",
        "date_delta_days": 15,
        "gross_amount_delta_paise": 10000,
    }
    score_low, _, _, _ = calculate_heuristic_score(ev_low, matcher_confidence=0.0)
    assert score_low < 0.70

    res_low = classify_tier2_heuristic(ev_low, matcher_confidence=0.0, threshold=0.70)
    assert res_low is None


def test_tier3_llm_integration():
    """Test Tier 3 Gemini LLM classification with mocked response."""
    ev = {"reason": "unknown_anomaly", "utr_match_type": "none"}

    mock_text = json.dumps(
        {
            "category": "likely_explainable",
            "confidence": 0.82,
            "explanation": "Timing anomaly due to bank holiday processing delay.",
        }
    )

    with patch("google.genai.Client") as mock_genai_client:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = mock_text
        mock_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_instance

        cat, conf, exp = classify_tier3_llm("ORD-99", "pay_99", "setl_99", ev, api_key="fake_key")
        assert cat == "likely_explainable"
        assert conf == 0.82
        assert "Timing anomaly" in exp


def test_rule_promotion_counter():
    """Verify rule promotion tracking counter and candidate triggering at 3 counts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "test_promotion.json")
        ev = {"reason": "custom_reason", "utr_match_type": "fuzzy"}

        cnt1, is_cand1, _ = record_llm_classification(
            ev, "amount_mismatch", promotion_path=json_path
        )
        assert cnt1 == 1
        assert not is_cand1

        cnt2, is_cand2, _ = record_llm_classification(
            ev, "amount_mismatch", promotion_path=json_path
        )
        assert cnt2 == 2
        assert not is_cand2

        cnt3, is_cand3, _ = record_llm_classification(
            ev, "amount_mismatch", promotion_path=json_path
        )
        assert cnt3 == 3
        assert is_cand3


def test_sqlite_audit_log():
    """Verify SQLite audit log persistence and filtering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_audit.db")

        row_id = log_event(
            stage="classify",
            record_id="ORD-100",
            decision="missing_bank_credit",
            confidence=1.0,
            evidence={"test": True},
            explanation="Test audit event log.",
            db_path=db_path,
        )
        assert row_id > 0

        logs = get_audit_logs(stage="classify", record_id="ORD-100", db_path=db_path)
        assert len(logs) == 1
        assert logs[0]["record_id"] == "ORD-100"
        assert logs[0]["decision"] == "missing_bank_credit"
        assert logs[0]["evidence"] == {"test": True}

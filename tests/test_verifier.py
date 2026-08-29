"""
Unit tests for Phase 5 Verifier Agent.

Tests auto-approval of high-confidence Tier 1 rules, LLM fallback verifier,
and audit trail logging.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from engine.audit_log import get_audit_logs
from engine.classifier.pipeline import ClassificationResult
from engine.verifier import run_verifier, verify_record


def test_auto_approval_high_confidence_tier1():
    """Verify high-confidence Tier 1 rule is auto-approved as resolved."""
    cr = ClassificationResult(
        record_id="ORD-101",
        payment_id="pay_101",
        settlement_id="setl_101",
        tier_used=1,
        category="missing_bank_credit",
        confidence=1.0,
        explanation="Settlement setl_101 missing from bank statement.",
        evidence={"reason": "missing_bank_credit"},
    )

    vr = verify_record(cr, confidence_auto_approve=0.85)
    assert vr.status == "resolved"
    assert vr.verified_category == "missing_bank_credit"
    assert vr.verifier_confidence == 1.0
    assert "Auto-approved" in vr.verifier_reasoning


def test_verifier_llm_mock():
    """Verify LLM verifier pass for low-confidence or Tier 3 classification."""
    cr = ClassificationResult(
        record_id="ORD-102",
        payment_id="pay_102",
        settlement_id="setl_102",
        tier_used=3,
        category="likely_explainable",
        confidence=0.72,
        explanation="Likely timing delay.",
        evidence={"gross_amount_delta_paise": 500, "date_delta_days": 4},
    )

    mock_text = json.dumps(
        {
            "verified_category": "likely_explainable",
            "status": "resolved",
            "verifier_confidence": 0.88,
            "reasoning": "Confirmed timing delay across bank holiday weekend.",
        }
    )

    with patch("google.genai.Client") as mock_genai_client:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = mock_text
        mock_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_instance

        vr = verify_record(cr, api_key="fake_api_key")
        assert vr.status == "resolved"
        assert vr.verified_category == "likely_explainable"
        assert vr.verifier_confidence == 0.88
        assert "Confirmed timing delay" in vr.verifier_reasoning


def test_verifier_audit_logging():
    """Verify verifier events are logged to SQLite audit log."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_verifier_audit.db")

        cr = ClassificationResult(
            record_id="ORD-103",
            payment_id="pay_103",
            settlement_id="setl_103",
            tier_used=1,
            category="duplicate_settlement",
            confidence=1.0,
            explanation="Payment settled twice.",
            evidence={"is_duplicate": True},
        )

        with patch("engine.verifier.log_event") as mock_log_event:
            verify_record(cr)
            assert mock_log_event.called
            args, kwargs = mock_log_event.call_args
            assert kwargs.get("stage") == "verify"
            assert kwargs.get("record_id") == "ORD-103"
            assert kwargs.get("decision") == "resolved"


def test_verifier_invalid_category_rejected():
    """Verify LLM response with an invalid/made-up category is rejected and flagged for review."""
    cr = ClassificationResult(
        record_id="ORD-104",
        payment_id="pay_104",
        settlement_id="setl_104",
        tier_used=3,
        category="missing_bank_credit",
        confidence=0.70,
        explanation="Missing bank deposit.",
        evidence={"reason": "missing_bank_credit"},
    )

    mock_invalid_text = json.dumps(
        {
            "verified_category": "completely_invented_category_xyz",
            "status": "resolved",
            "verifier_confidence": 0.99,
            "reasoning": "Made up category reasoning.",
        }
    )

    with patch("google.genai.Client") as mock_genai_client:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = mock_invalid_text
        mock_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_instance

        vr = verify_record(cr, api_key="fake_api_key")
        assert vr.status == "needs_review"
        assert vr.verified_category == "missing_bank_credit"
        assert vr.verifier_confidence == 0.50
        assert "invalid category" in vr.verifier_reasoning.lower()


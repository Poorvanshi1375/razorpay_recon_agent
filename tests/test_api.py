"""
Unit & Integration Tests for Phase 6 FastAPI endpoints.

Tests /reconcile/run, /results, /exceptions, /audit/{record_id}, and /ask.
"""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest

from api.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify API root status endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "Razorpay" in data["service"]


def test_reconcile_run_endpoint():
    """Verify /reconcile/run executes full pipeline and returns summary."""
    response = client.post("/reconcile/run")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "summary" in data
    summary = data["summary"]
    assert summary["total_records"] > 0
    assert summary["match_rate_percent"] > 0


def test_results_endpoint():
    """Verify /results returns reconciliation summary statistics."""
    response = client.get("/results")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "summary" in data


def test_exceptions_endpoint():
    """Verify /exceptions returns exception details."""
    response = client.get("/exceptions")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "exceptions" in data
    assert isinstance(data["exceptions"], list)


def test_audit_endpoint():
    """Verify /audit/{record_id} returns audit log history."""
    response = client.get("/audit/ORD-1057")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["success", "not_found"]
    assert "audit_events" in data


def test_ask_endpoint_with_explicit_record_id():
    """Verify /ask endpoint returns grounded answer when record_id is explicitly passed."""
    payload = {
        "question": "Why is ORD-1057 missing from the bank statement?",
        "record_id": "ORD-1057",
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["success", "error"]
    assert data["record_id"] == "ORD-1057"
    assert data["grounded_sources_count"] > 0
    answer = data["answer"]
    assert ("setl_MIS000" in answer) or ("missing_bank_credit" in answer) or ("ORD-1057" in answer) or ("Audit trail search found" in answer)


def test_ask_endpoint_extracted_record_id_from_text():
    """Verify /ask endpoint extracts order ID from question text when record_id is omitted from payload."""
    payload = {
        "question": "why didn't ORD-1057 settle?",
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["success", "error"]
    assert data["record_id"] == "ORD-1057"
    assert data["grounded_sources_count"] > 0
    answer = data["answer"]
    assert ("setl_MIS000" in answer) or ("missing_bank_credit" in answer) or ("ORD-1057" in answer) or ("Audit trail search found" in answer)


def test_ask_endpoint_nonexistent_record_id():
    """Verify /ask endpoint explicitly reports zero grounded sources and no record found for nonexistent ID."""
    payload = {
        "question": "why didn't ORD-9999 settle?",
        "record_id": "ORD-9999",
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["record_id"] == "ORD-9999"
    assert data["grounded_sources_count"] == 0
    answer = data["answer"].lower()
    assert ("no records" in answer) or ("not found" in answer) or ("unable to verify" in answer) or ("no reconciliation details" in answer)


def test_ask_endpoint_exception_handling():
    """Verify /ask endpoint returns status='error' when Gemini client raises an exception."""
    payload = {
        "question": "Why did ORD-1057 fail?",
        "record_id": "ORD-1057",
    }
    with patch("os.environ.get", return_value="fake_api_key"):
        with patch("google.genai.Client") as mock_genai_client:
            mock_genai_client.side_effect = Exception("API connection timeout")
            response = client.post("/ask", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "API connection timeout" in data["error"]
            assert data["grounded_sources_count"] > 0



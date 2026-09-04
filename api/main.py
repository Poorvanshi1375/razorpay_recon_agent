"""
Phase 6 API & Settlement Q&A Layer — FastAPI Backend Server.

Provides REST API endpoints for running multi-source reconciliation, inspecting results,
drilling down into exception audit logs, and answering natural-language Q&A queries
grounded in SQLite audit trail data.
"""

import json
import os
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from engine.audit_log import get_audit_logs
from engine.classifier.pipeline import run_classifier
from engine.matcher import run_matcher
from engine.verifier import run_verifier


app = FastAPI(
    title="Razorpay Multi-Source Reconciliation Agent API",
    description="Track 4 AI Finance Controller API providing automated reconciliation, structured audit trail access, and Settlement Q&A.",
    version="1.0.0",
)

# Enable CORS for frontend web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory storage cache of latest execution results
LATEST_CACHE: Dict[str, Any] = {
    "matcher_results": None,
    "classification_results": None,
    "verification_results": None,
    "summary": None,
}


class QuestionRequest(BaseModel):
    """Schema for Settlement Q&A payload."""

    question: str = Field(..., description="User question regarding settlement status or anomalies.")
    record_id: Optional[str] = Field(None, description="Optional Order ID or Payment ID to query specific evidence.")


@app.get("/")
def read_root():
    """API Root status endpoint."""
    return {
        "status": "online",
        "service": "Razorpay Multi-Source Reconciliation Agent API",
        "version": "1.0.0",
        "endpoints": [
            "/reconcile/run",
            "/results",
            "/exceptions",
            "/audit/{record_id}",
            "/ask",
        ],
    }


@app.post("/reconcile/run")
def run_reconciliation():
    """
    Execute full end-to-end reconciliation pipeline:
    Matching Engine -> Exception Classifier -> Verifier Agent.
    """
    run_id = str(uuid.uuid4())
    # 1. Matching
    matcher_results = run_matcher(run_id=run_id)
    clean_matches = [m for m in matcher_results if m.match_status == "matched"]
    non_matched = [m for m in matcher_results if m.match_status != "matched"]

    # 2. Classifier
    classification_results = run_classifier(matcher_results, run_id=run_id)

    # 3. Verifier
    verification_results = run_verifier(classification_results, run_id=run_id)

    resolved_count = len(clean_matches) + sum(1 for v in verification_results if v.status == "resolved")
    needs_review_count = sum(1 for v in verification_results if v.status == "needs_review")
    total_records = len(matcher_results)
    match_rate = (len(clean_matches) / total_records) * 100 if total_records > 0 else 0.0

    # Calculate period_start and period_end min/max order_date across matcher_results
    order_dates = [
        m.evidence["order_date"]
        for m in matcher_results
        if isinstance(m.evidence, dict) and m.evidence.get("order_date")
    ]
    period_start = min(order_dates) if order_dates else None
    period_end = max(order_dates) if order_dates else None

    summary = {
        "total_records": total_records,
        "clean_matches": len(clean_matches),
        "exceptions_classified": len(classification_results),
        "verified_resolved": resolved_count,
        "needs_review": needs_review_count,
        "match_rate_percent": round(match_rate, 2),
        "period_start": period_start,
        "period_end": period_end,
    }

    # Store cache
    LATEST_CACHE["matcher_results"] = matcher_results
    LATEST_CACHE["classification_results"] = classification_results
    LATEST_CACHE["verification_results"] = verification_results
    LATEST_CACHE["summary"] = summary
    LATEST_CACHE["run_id"] = run_id

    return {
        "status": "success",
        "message": "Reconciliation pipeline executed successfully.",
        "run_id": run_id,
        "summary": summary,
    }


@app.get("/results")
def get_results():
    """Return summary statistics of current reconciliation state."""
    if LATEST_CACHE["summary"] is None:
        run_reconciliation()

    return {
        "status": "success",
        "summary": LATEST_CACHE["summary"],
    }


@app.get("/exceptions")
def get_exceptions():
    """Return list of all non-matched/classified exception records with verification details."""
    if LATEST_CACHE["verification_results"] is None:
        run_reconciliation()

    exceptions = []
    verif_results = LATEST_CACHE["verification_results"] or []
    class_results = LATEST_CACHE["classification_results"] or []

    class_map = {c.record_id: c for c in class_results}

    for v in verif_results:
        c = class_map.get(v.record_id)
        agreement = "agreed" if v.verified_category == v.initial_category else "corrected"
        exceptions.append({
            "order_id": v.record_id,
            "payment_id": v.payment_id,
            "tier_used": v.tier_used,
            "initial_category": v.initial_category,
            "verified_category": v.verified_category,
            "verifier_agreement": agreement,
            "status": v.status,
            "verifier_confidence": v.verifier_confidence,
            "verifier_reasoning": v.verifier_reasoning,
            "explanation": c.explanation if c else v.verifier_reasoning,
            "evidence": v.evidence,
        })

    return {
        "status": "success",
        "total_exceptions": len(exceptions),
        "exceptions": exceptions,
    }


@app.get("/audit/run/latest")
def get_latest_run_audit_logs():
    """Retrieve all audit events from the most recent run_id, across all records."""
    logs = get_audit_logs(all_runs=False)
    latest_run_id = logs[0]["run_id"] if logs else None
    return {
        "status": "success",
        "run_id": latest_run_id,
        "total_events": len(logs),
        "audit_events": logs,
    }


@app.get("/audit/{record_id}")
def get_audit_trail(record_id: str, all_runs: bool = Query(False, description="Set to true to include historical events across prior runs.")):
    """Retrieve SQLite audit trail history for a specific order/payment record."""
    logs = get_audit_logs(record_id=record_id, all_runs=all_runs)
    if not logs:
        return {
            "status": "not_found",
            "record_id": record_id,
            "audit_events": [],
            "message": f"No audit log events found for record_id '{record_id}'",
        }

    latest_run_id = logs[-1]["run_id"] if logs else None

    return {
        "status": "success",
        "record_id": record_id,
        "run_id": latest_run_id,
        "total_events": len(logs),
        "audit_events": logs,
    }


@app.post("/ask")
def ask_settlement_qa(payload: QuestionRequest):
    """
    Settlement Q&A Endpoint.

    Answers natural-language queries grounded strictly in retrieved SQLite audit trail data
    and record evidence.
    """
    import re

    question = payload.question
    record_id = payload.record_id

    # If record_id is omitted from payload, extract ORD-#### from question text via regex
    if not record_id:
        match = re.search(r"\bORD-\d+\b", question, re.IGNORECASE)
        if match:
            record_id = match.group(0).upper()

    is_record_specific = record_id is not None

    if is_record_specific:
        audit_events = get_audit_logs(record_id=record_id, all_runs=False)
    else:
        audit_events = get_audit_logs(all_runs=False)

    # If record-specific search returned no logs (non-existent record_id)
    if is_record_specific and not audit_events:
        answer = (
            f"Based on the SQLite audit trail, no records or transaction logs were found "
            f"for Order ID '{record_id}'. Consequently, no reconciliation details exist for this record."
        )
        return {
            "status": "success",
            "question": question,
            "record_id": record_id,
            "answer": answer,
            "grounded_sources_count": 0,
        }

    # Context formulation
    audit_context = json.dumps(audit_events[:15], indent=2)

    api_key = os.environ.get("GEMINI_API_KEY", "")

    if not api_key:
        if is_record_specific and audit_events:
            last_event = audit_events[-1]
            answer = (
                f"For record {record_id}, the audit trail indicates stage '{last_event['stage']}' "
                f"with decision '{last_event['decision']}' (confidence: {last_event['confidence']}). "
                f"Explanation: {last_event['explanation']}"
            )
        else:
            answer = (
                "Note: No specific Order ID was identified in your query. General reconciliation summary: "
                "The pipeline processed all records. Exceptions include missing bank credits, garbled UTRs, "
                "duplicate settlements, and orphan ledger entries."
            )
        return {
            "status": "success",
            "question": question,
            "record_id": record_id,
            "answer": answer,
            "grounded_sources_count": len(audit_events),
        }

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        if is_record_specific:
            prompt = f"""You are an AI Finance Controller answering a merchant's inquiry about their Razorpay settlements and reconciliation.

Your answer MUST be strictly grounded in the provided SQLite audit trail evidence below for Order ID {record_id}. Do not invent details. If the evidence contains specific settlement IDs, amounts, or failure reasons, cite them explicitly.

CRITICAL INSTRUCTION ON CLASSIFICATION CATEGORIES:
- Inspect the 'verify' stage event in the audit trail.
- The 'verified_category' is the FINAL, AUTHORITATIVE, OVERRIDING classification outcome.
- The 'initial_category' (when different from 'verified_category') is strictly what Tier 3 first guessed, before the verifier corrected it.
- You MUST state the 'verified_category' (e.g., amount mismatch / amount_mismatch) as the actual, final, and correct outcome.
- If you mention 'initial_category' (e.g., reference formatting issue), you MUST explicitly label it only as "what Tier 3 first guessed, before the verifier corrected it." NEVER state the initial_category as the actual failure reason or final outcome.

AUDIT TRAIL EVIDENCE FOR RECORD {record_id}:
{audit_context}

USER QUESTION:
{question}

Provide a clear, professional, concise 2-3 sentence answer explaining what happened to this settlement or payment.
"""
        else:
            prompt = f"""You are an AI Finance Controller answering a merchant's general inquiry about their Razorpay settlements.

IMPORTANT: No specific Order ID was provided in the query or payload. You MUST explicitly state at the start of your response that no specific record ID was identified, and provide a general summary based on the overall system audit trail.

OVERALL SYSTEM AUDIT TRAIL SUMMARY:
{audit_context}

USER QUESTION:
{question}

Provide a clear, professional 2-3 sentence general answer.
"""

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.0),
        )

        answer = response.text.strip() if response and response.text else "No response generated."

        return {
            "status": "success",
            "question": question,
            "record_id": record_id,
            "answer": answer,
            "grounded_sources_count": len(audit_events),
        }

    except Exception as exc:
        return {
            "status": "error",
            "question": question,
            "record_id": record_id,
            "answer": f"Audit trail search found {len(audit_events)} event logs.",
            "error": str(exc),
            "grounded_sources_count": len(audit_events),
        }


def main():
    """Run FastAPI development server."""
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()

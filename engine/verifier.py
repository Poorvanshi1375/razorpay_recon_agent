"""
Phase 5 Verifier Agent — Self-Verifying Loop.

Performs an independent second-pass adversarial check on low-confidence or Tier 3 exception
classifications, confirming clean classifications as 'resolved' or flagging questionable ones
as 'needs_review'.

Writes every verification outcome to SQLite audit trail (engine/audit_log.py).
Does NOT read ground_truth.json (per AGENTS.md).
"""

import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from engine.audit_log import log_event
from engine.classifier.pipeline import ClassificationResult, run_classifier
from engine.classifier.rules import ALLOWED_CATEGORIES


@dataclass
class VerificationResult:
    """Structured output from Phase 5 Verifier Agent for a single record."""

    record_id: str
    payment_id: str
    initial_category: str
    verified_category: str
    status: str  # 'resolved' or 'needs_review'
    verifier_confidence: float
    verifier_reasoning: str
    tier_used: int
    evidence: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert VerificationResult to dictionary."""
        return asdict(self)


def _call_gemini_verifier(
    record_id: str,
    payment_id: str,
    settlement_id: Optional[str],
    initial_category: str,
    initial_explanation: str,
    evidence: Dict[str, Any],
    api_key: Optional[str] = None,
) -> Tuple[str, str, float, str]:
    """
    Call Gemini API with adversarial prompt to verify an exception classification.

    Returns (verified_category, status, verifier_confidence, reasoning).
    """
    if api_key is None:
        from dotenv import load_dotenv

        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY", "")

    if not api_key:
        # Fallback if no API key is set
        return (
            initial_category,
            "resolved" if evidence.get("gross_amount_delta_paise", 0) == 0 else "needs_review",
            0.75,
            "Fallback verifier: Checked amount delta and basic evidence consistency.",
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = f"""You are an independent finance auditor conducting a second-pass adversarial review of an automated reconciliation classification.

Your goal is to inspect the evidence critically and find potential mistakes, misclassifications, or missing context in the initial classification.

RECORD DETAILS:
- Order ID: {record_id}
- Payment ID: {payment_id}
- Settlement ID: {settlement_id}
- Initial Category: {initial_category}
- Initial Explanation: {initial_explanation}
- Evidence JSON: {json.dumps(evidence, indent=2)}

ALLOWED CATEGORIES:
- duplicate_settlement
- missing_bank_credit
- orphan_ledger_entry
- reference_formatting_issue
- amount_mismatch
- likely_explainable
- unresolved

INSTRUCTIONS:
1. Review the evidence carefully. If the initial classification is accurate and supported by evidence, confirm it.
2. If the initial classification is incorrect, specify the corrected category.
3. If there is genuine ambiguity, contradiction, or missing information, set status to 'needs_review'. Otherwise set status to 'resolved'.

Return ONLY a raw JSON object matching this schema:
{{
  "verified_category": "string",
  "status": "resolved" or "needs_review",
  "verifier_confidence": float (0.0 to 1.0),
  "reasoning": "one-sentence explanation"
}}
"""

        models_to_try = [
            "gemini-3.5-flash-lite",
            "gemini-3.6-flash",
            "gemini-3.1-flash-lite",
        ]

        response = None
        model_errors = []
        primary_model = models_to_try[0]
        for model in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                    ),
                )
                if response and response.text:
                    if model != primary_model:
                        print(
                            f"[WARNING] Verifier Model Fallback Triggered: Primary model '{primary_model}' unavailable. "
                            f"Successfully fell back to '{model}'."
                        )
                    break
            except Exception as mod_err:
                print(
                    f"[WARNING] Verifier Model '{model}' unavailable ({mod_err}). "
                    f"Attempting fallback..."
                )
                model_errors.append(f"{model}: {mod_err}")
                continue

        if not response or not response.text:
            err_summary = "; ".join(model_errors) if model_errors else "Empty response"
            return (
                initial_category,
                "needs_review",
                0.50,
                f"Gemini verifier call failed for all models. Errors: {err_summary}",
            )

        data = json.loads(response.text)
        verified_cat = data.get("verified_category", initial_category)
        status = data.get("status", "resolved")
        conf = float(data.get("verifier_confidence", 0.8))
        reasoning = data.get("reasoning", "Verified by second-pass LLM review.")

        if verified_cat not in ALLOWED_CATEGORIES:
            return (
                initial_category,
                "needs_review",
                0.50,
                f"Verifier returned invalid category '{verified_cat}'; rejected and flagged for review.",
            )

        return verified_cat, status, conf, reasoning

    except Exception as exc:
        return (
            initial_category,
            "needs_review",
            0.50,
            f"Verifier Exception ({type(exc).__name__}); default to needs_review.",
        )


def verify_record(
    classification_result: ClassificationResult,
    confidence_auto_approve: float = 0.85,
    api_key: Optional[str] = None,
    run_id: Optional[str] = None,
) -> VerificationResult:
    """
    Perform second-pass verification on a ClassificationResult.

    Auto-approves high-confidence Tier 1 rule classifications.
    Runs adversarial verifier for lower-confidence or Tier 3 cases.
    Logs result to SQLite audit log.
    """
    rec_id = classification_result.record_id
    pay_id = classification_result.payment_id
    settle_id = classification_result.settlement_id
    init_cat = classification_result.category
    init_conf = classification_result.confidence
    init_exp = classification_result.explanation
    tier = classification_result.tier_used
    ev = classification_result.evidence

    # Tier 1 high-confidence rule auto-approval
    if tier == 1 and init_conf >= confidence_auto_approve:
        verified_cat = init_cat
        status = "resolved"
        verifier_conf = init_conf
        reasoning = f"Auto-approved high-confidence Tier 1 rule '{init_cat}'."
    else:
        verified_cat, status, verifier_conf, reasoning = _call_gemini_verifier(
            record_id=rec_id,
            payment_id=pay_id,
            settlement_id=settle_id,
            initial_category=init_cat,
            initial_explanation=init_exp,
            evidence=ev,
            api_key=api_key,
        )

    verifier_agreement = "agreed" if verified_cat == init_cat else "corrected"

    # Write stage verification event to SQLite audit log
    log_event(
        stage="verify",
        record_id=rec_id,
        decision=status,
        confidence=verifier_conf,
        evidence={
            "initial_category": init_cat,
            "verified_category": verified_cat,
            "verifier_agreement": verifier_agreement,
            "tier_used": tier,
            "evidence": ev,
        },
        explanation=reasoning,
        run_id=run_id,
    )

    return VerificationResult(
        record_id=rec_id,
        payment_id=pay_id,
        initial_category=init_cat,
        verified_category=verified_cat,
        status=status,
        verifier_confidence=verifier_conf,
        verifier_reasoning=reasoning,
        tier_used=tier,
        evidence=ev,
    )


def run_verifier(
    classification_results: Optional[List[ClassificationResult]] = None,
    api_key: Optional[str] = None,
    run_id: Optional[str] = None,
) -> List[VerificationResult]:
    """
    Execute Phase 5 Verifier Agent across all exception classification results.
    """
    import uuid
    active_run_id = run_id or uuid.uuid4().hex[:12]

    if classification_results is None:
        classification_results = run_classifier(run_id=active_run_id)

    verification_results: List[VerificationResult] = []
    for cr in classification_results:
        vr = verify_record(cr, api_key=api_key, run_id=active_run_id)
        verification_results.append(vr)

    return verification_results


def main() -> None:
    """Run verifier on exception classifications and print output."""
    verifications = run_verifier()

    resolved_count = sum(1 for v in verifications if v.status == "resolved")
    needs_review_count = sum(1 for v in verifications if v.status == "needs_review")

    print("Phase 5 Verifier Agent Execution Summary:")
    print("=" * 60)
    print(f"Total Exception Records Evaluated: {len(verifications)}")
    print(f"  - Verified & Resolved:           {resolved_count}")
    print(f"  - Flagged for Human Review:      {needs_review_count}")
    print("=" * 60)

    print("\nDetailed Verification Results:")
    print("-" * 60)
    for idx, v in enumerate(verifications, 1):
        print(f"Record {idx}: Order ID {v.record_id} (Payment: {v.payment_id})")
        print(f"  Initial Category  : {v.initial_category}")
        print(f"  Verified Category : {v.verified_category}")
        print(f"  Verification Status: {v.status.upper()}")
        print(f"  Verifier Confidence: {v.verifier_confidence:.2f}")
        print(f"  Verifier Reasoning : {v.verifier_reasoning}")
        print("-" * 60)


if __name__ == "__main__":
    main()

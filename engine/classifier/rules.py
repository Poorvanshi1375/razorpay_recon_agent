"""
Tier 1 Exception Classifier: Deterministic Rules Engine.

Evaluates evidence dicts from Phase 2 MatchResult records using predefined,
deterministic reconciliation rules.

Does NOT read ground_truth.json (per AGENTS.md).
"""

from typing import Any, Dict, Optional, Tuple

ALLOWED_CATEGORIES = {
    "duplicate_settlement",
    "missing_bank_credit",
    "orphan_ledger_entry",
    "reference_formatting_issue",
    "amount_mismatch",
    "likely_explainable",
    "unresolved",
}


def classify_tier1_rule(
    order_id: str,
    payment_id: str,
    settlement_id: Optional[str],
    evidence: Dict[str, Any],
    gross_tolerance_paise: int = 500,
) -> Optional[Tuple[str, float, str]]:
    """
    Apply Tier 1 deterministic rules to a single record's evidence.

    Returns:
        (category, confidence, explanation) if matched by a Tier 1 rule,
        or None if unresolved (passes to Tier 2).
    """
    is_duplicate = evidence.get("is_duplicate", False)
    reason = evidence.get("reason")
    utr_match_type = evidence.get("utr_match_type")
    gross_delta = evidence.get("gross_amount_delta_paise")

    # Rule 1: Duplicate settlement
    if is_duplicate or reason == "duplicate_settlement":
        setl_ids = settlement_id or "multiple settlements"
        explanation = (
            f"Payment settled twice ({setl_ids}); needs manual refund of the duplicate."
        )
        return ("duplicate_settlement", 1.0, explanation)

    # Rule 2: Missing bank credit
    if reason == "missing_bank_credit":
        setl_str = settlement_id or "unknown settlement"
        if gross_delta is not None and gross_delta > 0:
            exp_str = f"expected amount of {gross_delta} paise"
        else:
            exp_str = "expected settled amount"
        explanation = (
            f"Settlement {setl_str} ({exp_str}) was processed by Razorpay but never arrived in bank statement."
        )
        return ("missing_bank_credit", 1.0, explanation)

    # Rule 3: Orphan ledger entry
    if reason == "no_settlement_found":
        explanation = (
            f"Order {order_id} with Razorpay payment {payment_id} has no matching Razorpay settlement record at all."
        )
        return ("orphan_ledger_entry", 1.0, explanation)

    # Rule 4: Reference formatting issue (garbled UTR, gross amount lines up)
    if utr_match_type == "fuzzy" and gross_delta is not None and abs(gross_delta) <= gross_tolerance_paise:
        narration = evidence.get("matched_bank_narration", "")
        explanation = (
            f"UTR looked garbled in bank text ('{narration}'), but the gross amount lines up (delta: {gross_delta} paise)."
        )
        return ("reference_formatting_issue", 0.9, explanation)

    # Rule 5: Ledger-settlement amount mismatch
    if reason == "ledger_settlement_amount_mismatch":
        delta_str = f"{gross_delta} paise" if gross_delta is not None else "significant amount"
        explanation = (
            f"Ledger and settlement amounts disagree beyond tolerance (gross delta: {delta_str})."
        )
        return ("amount_mismatch", 0.85, explanation)

    # Rule 6: Unresolved by Tier 1
    return None

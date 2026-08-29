"""
Tier 2 Exception Classifier: Weighted-Feature Heuristic Scorer.

IMPORTANT NOTE: This is a weighted-feature heuristic scorer, NOT a trained ML model.
With ~55 dataset records, a trained model is inappropriate and misleading.
As required by AGENTS.md, this module is explicitly named and documented as a heuristic scorer.

Combines utr_match_score, date_delta_days, and gross_amount_delta_paise into a 0-1 confidence.
Above a threshold (default 0.7), resolves as 'likely_explainable'. Below it, passes to Tier 3.
Does NOT read ground_truth.json (per AGENTS.md).
"""

from typing import Any, Dict, Optional, Tuple


def calculate_heuristic_score(
    evidence: Dict[str, Any],
    matcher_confidence: float = 0.0,
) -> Tuple[float, float, float, float]:
    """
    Calculate feature scores and weighted total confidence.

    Features:
      1. UTR match score (0.0 to 1.0)
      2. Date delta score (0.0 to 1.0)
      3. Gross amount delta score (0.0 to 1.0)

    Returns:
        (total_confidence, utr_score, date_score, amount_score)
    """
    utr_match_type = evidence.get("utr_match_type", "none")
    date_delta_days = evidence.get("date_delta_days")
    gross_delta_paise = evidence.get("gross_amount_delta_paise")

    # Feature 1: UTR score
    if utr_match_type == "exact":
        utr_score = 1.0
    elif utr_match_type == "fuzzy":
        utr_score = max(0.5, matcher_confidence)
    else:
        utr_score = 0.0

    # Feature 2: Date delta score
    if date_delta_days is None:
        date_score = 0.0
    else:
        abs_date = abs(date_delta_days)
        if abs_date <= 3:
            date_score = 1.0
        elif abs_date <= 7:
            date_score = 0.7
        else:
            date_score = max(0.0, round(1.0 - (abs_date * 0.1), 2))

    # Feature 3: Gross amount delta score
    if gross_delta_paise is None:
        amount_score = 0.0
    else:
        abs_amount = abs(gross_delta_paise)
        if abs_amount == 0:
            amount_score = 1.0
        elif abs_amount <= 500:  # <= ₹5
            amount_score = 0.8
        else:
            amount_score = max(0.0, round(1.0 - (abs_amount / 5000.0), 2))

    # Weighted combination
    total_confidence = round(
        (0.4 * utr_score) + (0.3 * date_score) + (0.3 * amount_score), 2
    )

    return total_confidence, utr_score, date_score, amount_score


def classify_tier2_heuristic(
    evidence: Dict[str, Any],
    matcher_confidence: float = 0.0,
    threshold: float = 0.70,
) -> Optional[Tuple[str, float, str]]:
    """
    Apply Tier 2 heuristic scoring to a record's evidence dict.

    Returns:
        ("likely_explainable", confidence, explanation) if confidence >= threshold,
        or None if unresolved (passes to Tier 3).
    """
    confidence, utr_s, date_s, amt_s = calculate_heuristic_score(
        evidence, matcher_confidence
    )

    if confidence >= threshold:
        explanation = (
            f"Heuristic scorer assigned confidence {confidence:.2f} (above {threshold:.2f} threshold) "
            f"combining UTR match score ({utr_s:.2f}), date delta score ({date_s:.2f}), "
            f"and amount delta score ({amt_s:.2f})."
        )
        return ("likely_explainable", confidence, explanation)

    return None

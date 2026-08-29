"""
Rule Promotion Counter & Tracking Layer.

Maintains a persistent JSON counter of (evidence-pattern -> LLM-chosen category) pairs.
If the same evidence pattern receives the same LLM classification 3+ times, flags a
"rule promotion candidate" event for human audit, rather than auto-promoting prematurely.

Does NOT read ground_truth.json (per AGENTS.md).
"""

import json
import os
from typing import Any, Dict, Tuple

PROMOTION_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "rule_promotion.json"
)


def get_evidence_pattern_key(evidence: Dict[str, Any]) -> str:
    """Construct a canonical pattern string from key evidence features."""
    reason = evidence.get("reason", "unknown")
    utr_match_type = evidence.get("utr_match_type", "none")
    is_duplicate = evidence.get("is_duplicate", False)
    is_batch = evidence.get("is_batch", False)

    return f"reason={reason}|utr={utr_match_type}|duplicate={is_duplicate}|batch={is_batch}"


def record_llm_classification(
    evidence: Dict[str, Any],
    llm_category: str,
    promotion_path: str = PROMOTION_PATH,
    threshold: int = 3,
) -> Tuple[int, bool, str]:
    """
    Record an LLM classification for an evidence pattern.

    Returns:
        (count, is_candidate, pattern_key)
    """
    pattern_key = get_evidence_pattern_key(evidence)
    composite_key = f"{pattern_key} -> {llm_category}"

    counts: Dict[str, int] = {}
    if os.path.exists(promotion_path):
        try:
            with open(promotion_path, "r", encoding="utf-8") as f:
                counts = json.load(f)
        except Exception:
            counts = {}

    current_count = counts.get(composite_key, 0) + 1
    counts[composite_key] = current_count

    os.makedirs(os.path.dirname(promotion_path), exist_ok=True)
    with open(promotion_path, "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=2)

    is_candidate = current_count >= threshold
    return current_count, is_candidate, composite_key

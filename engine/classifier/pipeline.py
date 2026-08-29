"""
Phase 3 Exception Classifier Pipeline Orchestrator.

Processes non-matched (ambiguous and unmatched) MatchResults from Phase 2
through Tier 1 (Rules) -> Tier 2 (Heuristic Scorer) -> Tier 3 (Gemini LLM).

Writes every classification decision to SQLite audit log (engine/audit_log.py).
Tracks rule promotion candidates (engine/classifier/rule_promotion.py).
Does NOT read ground_truth.json (per AGENTS.md).
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
from engine.audit_log import log_event
from engine.classifier.heuristic_score import classify_tier2_heuristic
from engine.classifier.llm_tier import classify_tier3_llm
from engine.classifier.rule_promotion import record_llm_classification
from engine.classifier.rules import classify_tier1_rule
from engine.matcher import MatchResult, run_matcher


@dataclass
class ClassificationResult:
    """Structured exception classification output for a single record."""

    record_id: str  # order_id
    payment_id: str
    settlement_id: Optional[str]
    tier_used: int  # 1, 2, or 3
    category: str
    confidence: float
    explanation: str
    evidence: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert ClassificationResult to dictionary."""
        return asdict(self)


def classify_record(match_result: MatchResult, run_id: Optional[str] = None) -> ClassificationResult:
    """
    Classify a single MatchResult through Tier 1 -> Tier 2 -> Tier 3 pipeline.

    Every classification writes to SQLite audit log before returning.
    """
    order_id = match_result.order_id
    payment_id = match_result.payment_id
    settlement_id = match_result.settlement_id
    evidence = match_result.evidence

    # Tier 1: Deterministic Rules
    t1_res = classify_tier1_rule(
        order_id=order_id,
        payment_id=payment_id,
        settlement_id=settlement_id,
        evidence=evidence,
    )
    if t1_res is not None:
        cat, conf, exp = t1_res
        tier_used = 1
    else:
        # Tier 2: Heuristic Confidence Scorer
        t2_res = classify_tier2_heuristic(
            evidence=evidence,
            matcher_confidence=match_result.confidence,
        )
        if t2_res is not None:
            cat, conf, exp = t2_res
            tier_used = 2
        else:
            # Tier 3: Gemini LLM
            cat, conf, exp = classify_tier3_llm(
                order_id=order_id,
                payment_id=payment_id,
                settlement_id=settlement_id,
                evidence=evidence,
            )
            tier_used = 3

            # Track rule promotion counter for LLM decisions
            count, is_candidate, composite_key = record_llm_classification(
                evidence=evidence, llm_category=cat
            )
            if is_candidate:
                promotion_msg = (
                    f"RULE PROMOTION CANDIDATE: Evidence pattern '{composite_key}' "
                    f"has received LLM classification '{cat}' {count} times."
                )
                print(f"[WARNING] {promotion_msg}")
                log_event(
                    stage="rule_promotion",
                    record_id=order_id,
                    decision="promotion_candidate",
                    confidence=conf,
                    evidence=evidence,
                    explanation=promotion_msg,
                    run_id=run_id,
                )

    # Write stage classification event to SQLite audit log
    log_event(
        stage="classify",
        record_id=order_id,
        decision=cat,
        confidence=conf,
        evidence=evidence,
        explanation=exp,
        run_id=run_id,
    )

    return ClassificationResult(
        record_id=order_id,
        payment_id=payment_id,
        settlement_id=settlement_id,
        tier_used=tier_used,
        category=cat,
        confidence=conf,
        explanation=exp,
        evidence=evidence,
    )


def run_classifier(
    match_results: Optional[List[MatchResult]] = None,
    run_id: Optional[str] = None,
) -> List[ClassificationResult]:
    """
    Execute Phase 3 Exception Classification on non-matched MatchResults.

    If match_results is not provided, runs Phase 2 matcher first.
    """
    import uuid
    active_run_id = run_id or uuid.uuid4().hex[:12]

    if match_results is None:
        match_results = run_matcher(run_id=active_run_id)

    non_matched = [m for m in match_results if m.match_status != "matched"]

    results: List[ClassificationResult] = []
    for m in non_matched:
        classified = classify_record(m, run_id=active_run_id)
        results.append(classified)

    return results


def main() -> None:
    """Run classifier on Phase 2 output and print summary breakdown."""
    results = run_classifier()

    tier_counts = {1: 0, 2: 0, 3: 0}
    for r in results:
        tier_counts[r.tier_used] = tier_counts.get(r.tier_used, 0) + 1

    print("Phase 3 Exception Classification Execution Summary:")
    print("=" * 60)
    print(f"Total Non-Matched Records Classified: {len(results)}")
    print(f"  - Tier 1 (Rules Engine):             {tier_counts[1]}")
    print(f"  - Tier 2 (Heuristic Scorer):          {tier_counts[2]}")
    print(f"  - Tier 3 (Gemini LLM):               {tier_counts[3]}")
    print("=" * 60)

    print("\nDetailed Record Classifications:")
    print("-" * 60)
    for idx, r in enumerate(results, 1):
        print(f"Record {idx}: Order ID {r.record_id} (Payment: {r.payment_id})")
        print(f"  Settlement ID : {r.settlement_id}")
        print(f"  Tier Used     : Tier {r.tier_used}")
        print(f"  Category      : {r.category}")
        print(f"  Confidence    : {r.confidence:.2f}")
        print(f"  Explanation   : {r.explanation}")
        print("-" * 60)


if __name__ == "__main__":
    main()

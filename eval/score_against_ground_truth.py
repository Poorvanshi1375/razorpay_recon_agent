"""
Evaluation Module: Score Pipeline Results Against Ground Truth Answer Key.

AGENTS.md HONESTY MECHANISM:
- `data/ground_truth.json` is strictly read-only and ONLY accessed by this evaluation script.
- No matching, classification, or verifier code accesses ground truth directly or indirectly.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.classifier.pipeline import run_classifier
from engine.matcher import run_matcher
from engine.verifier import run_verifier


# Ground truth categories that represent clean automated matches in Phase 2
CLEAN_GT_CATEGORIES = {
    "clean_match",
    "batch_aggregation",
    "normal_lag",
    "refund_pair",
    "rounding_noise",
}

# Explicit, justified 1-to-1 canonical category mapping for genuine exception categories
# (Ground truth category -> expected classifier/verifier output category)
EXCEPTION_EXPECTED_CATEGORY = {
    "garbled_utr": "reference_formatting_issue",
    "missing_bank_credit": "missing_bank_credit",
    "duplicate_settlement": "duplicate_settlement",
    "orphan_ledger_entry": "orphan_ledger_entry",
    "amount_mismatch": "amount_mismatch",
    "unexplained_bank_amount_discrepancy": "amount_mismatch",
}


def load_ground_truth(gt_path: str = "data/ground_truth.json") -> Dict[str, Any]:
    """Load ground truth JSON file."""
    if not os.path.exists(gt_path):
        raise FileNotFoundError(f"Ground truth file not found at {gt_path}")

    with open(gt_path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_pipeline(gt_path: str = "data/ground_truth.json", run_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute full pipeline (matcher -> classifier -> verifier) and compare
    decisions against ground_truth.json using strict, principled evaluation rules.
    """
    import uuid

    active_run_id = run_id or str(uuid.uuid4())
    ground_truth_data = load_ground_truth(gt_path)
    gt_records = {r["order_id"]: r for r in ground_truth_data["records"]}

    # Step 1: Phase 2 Matcher
    match_results = run_matcher(run_id=active_run_id)
    match_map = {m.order_id: m for m in match_results}

    # Step 2: Phase 3 Classifier
    class_results = run_classifier(match_results, run_id=active_run_id)
    class_map = {c.record_id: c for c in class_results}

    # Step 3: Phase 5 Verifier
    verif_results = run_verifier(class_results, run_id=active_run_id)
    verif_map = {v.record_id: v for v in verif_results}

    # Score calculation
    total_records = len(gt_records)
    correct_matches = 0
    correct_classifications = 0
    false_positives = 0  # Clean ground truth records falsely flagged as problem exceptions
    needs_review_count = 0

    eval_details: List[Dict[str, Any]] = []

    # Category performance trackers
    cat_tp: Dict[str, int] = {}
    cat_fp: Dict[str, int] = {}
    cat_fn: Dict[str, int] = {}

    for order_id, gt_rec in gt_records.items():
        gt_category = gt_rec["category"]

        match_obj = match_map.get(order_id)
        class_obj = class_map.get(order_id)
        verif_obj = verif_map.get(order_id)

        is_matched_by_matcher = (match_obj is not None and match_obj.match_status == "matched")

        if is_matched_by_matcher:
            pred_status = "matched"
            pred_category = "clean_match"
        else:
            pred_status = verif_obj.status if verif_obj else "unresolved"
            pred_category = verif_obj.verified_category if verif_obj else (
                class_obj.category if class_obj else "unresolved"
            )

        if verif_obj and verif_obj.status == "needs_review":
            needs_review_count += 1

        # Strict Principled Evaluation Split
        if gt_category in CLEAN_GT_CATEGORIES:
            # Clean records: MUST be matched by Phase 2 matcher
            is_correct = is_matched_by_matcher
        elif gt_category in EXCEPTION_EXPECTED_CATEGORY:
            # Exception records: MUST NOT be auto-matched, MUST be resolved by verifier,
            # and MUST strictly equal the single expected output category.
            expected_cat = EXCEPTION_EXPECTED_CATEGORY[gt_category]
            is_correct = (
                (not is_matched_by_matcher)
                and (pred_status == "resolved")
                and (pred_category == expected_cat)
            )
        else:
            is_correct = False

        if is_correct:
            correct_classifications += 1
            if is_matched_by_matcher:
                correct_matches += 1
            cat_tp[gt_category] = cat_tp.get(gt_category, 0) + 1
        else:
            # False Positive: clean ground truth record missed by matcher and flagged as an exception
            if gt_category in CLEAN_GT_CATEGORIES and not is_matched_by_matcher:
                false_positives += 1

            cat_fp[pred_category] = cat_fp.get(pred_category, 0) + 1
            cat_fn[gt_category] = cat_fn.get(gt_category, 0) + 1

        eval_details.append({
            "order_id": order_id,
            "ground_truth_category": gt_category,
            "predicted_category": pred_category,
            "match_status": match_obj.match_status if match_obj else "missing",
            "verifier_status": pred_status,
            "is_correct": is_correct,
        })

    accuracy = (correct_classifications / total_records) * 100 if total_records > 0 else 0.0
    false_positive_rate = (false_positives / total_records) * 100 if total_records > 0 else 0.0

    return {
        "total_records": total_records,
        "correct_classifications": correct_classifications,
        "accuracy_percent": accuracy,
        "false_positives": false_positives,
        "false_positive_rate_percent": false_positive_rate,
        "needs_review_count": needs_review_count,
        "eval_details": eval_details,
        "cat_tp": cat_tp,
        "cat_fp": cat_fp,
        "cat_fn": cat_fn,
    }


def print_evaluation_report(results: Dict[str, Any]) -> None:
    """Print clean terminal evaluation summary report."""
    print("\n" + "=" * 70)
    print("AI FINANCE CONTROLLER — GROUND TRUTH EVALUATION REPORT")
    print("=" * 70)
    print(f"Total Dataset Records Evaluated : {results['total_records']}")
    print(f"Overall Accuracy Score         : {results['accuracy_percent']:.2f}% ({results['correct_classifications']}/{results['total_records']})")
    print(f"False Positives (Clean Flagged): {results['false_positives']} ({results['false_positive_rate_percent']:.2f}%)")
    print(f"Flagged for Human Review       : {results['needs_review_count']}")
    print("-" * 70)

    print("\nCategory-Level Performance Breakdown:")
    print(f"{'Category':<26} | {'True Positives':<15} | {'False Positives':<15} | {'False Negatives':<15}")
    print("-" * 70)

    all_cats = set(list(results['cat_tp'].keys()) + list(results['cat_fp'].keys()) + list(results['cat_fn'].keys()))
    for cat in sorted(all_cats):
        tp = results['cat_tp'].get(cat, 0)
        fp = results['cat_fp'].get(cat, 0)
        fn = results['cat_fn'].get(cat, 0)
        print(f"{cat:<26} | {tp:<15} | {fp:<15} | {fn:<15}")

    print("=" * 70 + "\n")


def main() -> None:
    """Run evaluation script and output results."""
    try:
        results = evaluate_pipeline()
        print_evaluation_report(results)

        # Write computed report snapshot to eval/latest_eval_report.json
        from datetime import datetime, timezone

        all_cats = sorted(list(set(list(results['cat_tp'].keys()) + list(results['cat_fp'].keys()) + list(results['cat_fn'].keys()))))
        per_category = {
            cat: {
                "tp": results['cat_tp'].get(cat, 0),
                "fp": results['cat_fp'].get(cat, 0),
                "fn": results['cat_fn'].get(cat, 0),
            }
            for cat in all_cats
        }

        report = {
            "accuracy_percent": round(results["accuracy_percent"], 2),
            "correct": results["correct_classifications"],
            "total": results["total_records"],
            "correct_over_total": f"{results['correct_classifications']}/{results['total_records']}",
            "false_positive_count": results["false_positives"],
            "needs_review_count": results["needs_review_count"],
            "per_category_breakdown": per_category,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        out_path = os.path.join(os.path.dirname(__file__), "latest_eval_report.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[EVAL] Snapshot written to {out_path}")

    except Exception as exc:
        print(f"[ERROR] Evaluation failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

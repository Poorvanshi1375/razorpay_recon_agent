"""
Phase 2 Diagnostic Sanity Check.

Reads ground_truth.json (evaluation/debugging path only) and compares
Phase 2 matcher.py outcomes against true categories.
"""

import json
import os
import sys
from typing import Any, Dict

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine.matcher import run_matcher

GROUND_TRUTH_PATH = os.path.join(PROJECT_ROOT, "data", "ground_truth.json")


def load_ground_truth() -> Dict[str, Any]:
    """Load ground_truth.json file."""
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    """Run sanity check comparing Phase 2 match_status results against ground truth categories."""
    gt_data = load_ground_truth()
    gt_records = gt_data["records"]
    gt_map = {str(r["order_id"]): r["category"] for r in gt_records}

    match_results = run_matcher()
    results_map = {r.order_id: r.match_status for r in match_results}

    # Matrix: category -> {match_status -> count}
    matrix: Dict[str, Dict[str, int]] = {}

    for order_id, gt_cat in gt_map.items():
        match_status = results_map.get(order_id, "unknown")
        if gt_cat not in matrix:
            matrix[gt_cat] = {"matched": 0, "ambiguous": 0, "unmatched": 0}
        matrix[gt_cat][match_status] = matrix[gt_cat].get(match_status, 0) + 1

    print("\nPhase 2 Diagnostic Sanity Check (Matcher vs Ground Truth)")
    print("=" * 70)
    print(f"{'Ground Truth Category':<25} | {'Total':<6} | {'Matched':<8} | {'Ambiguous':<10} | {'Unmatched':<10}")
    print("-" * 70)

    for cat, status_counts in matrix.items():
        total = sum(status_counts.values())
        matched = status_counts.get("matched", 0)
        ambiguous = status_counts.get("ambiguous", 0)
        unmatched = status_counts.get("unmatched", 0)
        print(f"{cat:<25} | {total:<6} | {matched:<8} | {ambiguous:<10} | {unmatched:<10}")

    print("=" * 70)


if __name__ == "__main__":
    main()

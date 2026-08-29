"""
Phase 2: Matching Engine for Multi-Source Reconciliation Agent.

Reconciles ledger records against Razorpay settlement reports and bank statement entries.
Does NOT read ground_truth.json.
"""

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from rapidfuzz import fuzz

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LEDGER_PATH = os.path.join(DATA_DIR, "ledger.csv")
SETTLEMENT_PATH = os.path.join(DATA_DIR, "settlement.csv")
BANK_PATH = os.path.join(DATA_DIR, "bank_statement.csv")


@dataclass
class MatchResult:
    """Structured match result for a single ledger entry."""

    order_id: str
    payment_id: str
    settlement_id: Optional[str]
    match_status: str  # "matched", "ambiguous", "unmatched"
    confidence: float  # 0.0 to 1.0
    evidence: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert MatchResult to a dictionary."""
        return asdict(self)


def load_datasets(
    ledger_path: str = LEDGER_PATH,
    settlement_path: str = SETTLEMENT_PATH,
    bank_path: str = BANK_PATH,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Load ledger, settlement, and bank statement CSV files into structured dictionary lists.

    Parses JSON-encoded payment_ids column in settlement records.
    """
    ledger_df = pd.read_csv(ledger_path)
    settlement_df = pd.read_csv(settlement_path)
    bank_df = pd.read_csv(bank_path)

    ledger_records = ledger_df.to_dict(orient="records")

    settlement_records = []
    for _, row in settlement_df.iterrows():
        s_dict = row.to_dict()
        s_dict["payment_ids"] = json.loads(row["payment_ids"])
        s_dict["amount"] = int(row["amount"])
        s_dict["fees"] = int(row["fees"])
        s_dict["tax"] = int(row["tax"])
        s_dict["net_settled_amount"] = int(row["net_settled_amount"])
        settlement_records.append(s_dict)

    bank_records = []
    for _, row in bank_df.iterrows():
        b_dict = row.to_dict()
        b_dict["credited_amount"] = int(row["credited_amount"])
        bank_records.append(b_dict)

    return ledger_records, settlement_records, bank_records


def build_settlement_indexes(
    settlement_records: List[Dict[str, Any]]
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, bool]]:
    """
    Build lookup indexes from settlement records.

    1. payment_id -> list of settlement records containing it
    2. settlement_id -> is_batch boolean flag (True if batch contains >1 payments)
    """
    payment_id_to_settlements: Dict[str, List[Dict[str, Any]]] = {}
    settlement_is_batch: Dict[str, bool] = {}

    for setl in settlement_records:
        setl_id = setl["settlement_id"]
        payment_ids = setl["payment_ids"]

        settlement_is_batch[setl_id] = len(payment_ids) > 1

        for pid in payment_ids:
            if pid not in payment_id_to_settlements:
                payment_id_to_settlements[pid] = []
            payment_id_to_settlements[pid].append(setl)

    return payment_id_to_settlements, settlement_is_batch


from engine.audit_log import log_event


def reconcile_ledger(
    ledger_records: List[Dict[str, Any]],
    settlement_records: List[Dict[str, Any]],
    bank_records: List[Dict[str, Any]],
    amount_tolerance_paise: int = 5,
    fuzzy_threshold: float = 70.0,
    date_window_days: int = 10,
    max_fuzzy_amount_delta_paise: int = 10000,
    run_id: Optional[str] = None,
) -> List[MatchResult]:
    """
    Reconcile ledger entries against settlements and bank statement entries.

    Returns a list of MatchResult objects.
    """
    import uuid
    active_run_id = run_id or uuid.uuid4().hex[:12]

    payment_to_setls, setl_is_batch = build_settlement_indexes(settlement_records)

    # Pre-index bank rows that have exact UTR matches
    exact_utr_bank_indices = set()
    for s in settlement_records:
        s_utr = s["utr"]
        for idx, b in enumerate(bank_records):
            if s_utr in b["narration"]:
                exact_utr_bank_indices.add(idx)

    results: List[MatchResult] = []

    for l_rec in ledger_records:
        order_id = str(l_rec["order_id"])
        pay_id = str(l_rec["razorpay_payment_id"])

        # 1. Log Ingest stage event per ledger record
        log_event(
            stage="ingest",
            record_id=order_id,
            decision="ingested",
            confidence=1.0,
            evidence=dict(l_rec),
            explanation=f"Ingested ledger record {order_id} (payment {pay_id}).",
            run_id=active_run_id,
        )

        matching_setls = payment_to_setls.get(pay_id, [])
        res: Optional[MatchResult] = None

        # Case 1: No settlement found
        if len(matching_setls) == 0:
            res = MatchResult(
                order_id=order_id,
                payment_id=pay_id,
                settlement_id=None,
                match_status="unmatched",
                confidence=0.0,
                evidence={
                    "date_delta_days": None,
                    "amount_delta_paise": None,
                    "gross_amount_delta_paise": None,
                    "utr_match_type": "none",
                    "is_batch": False,
                    "is_duplicate": False,
                    "reason": "no_settlement_found",
                    "matched_bank_amount": None,
                    "matched_bank_narration": None,
                },
            )

        # Case 2: Duplicate settlement signal (2+ settlements contain this payment)
        elif len(matching_setls) >= 2:
            setl_ids_str = ",".join(s["settlement_id"] for s in matching_setls)
            res = MatchResult(
                order_id=order_id,
                payment_id=pay_id,
                settlement_id=setl_ids_str,
                match_status="ambiguous",
                confidence=0.5,
                evidence={
                    "date_delta_days": None,
                    "amount_delta_paise": None,
                    "gross_amount_delta_paise": None,
                    "utr_match_type": "none",
                    "is_batch": False,
                    "is_duplicate": True,
                    "reason": "duplicate_settlement",
                    "matched_bank_amount": None,
                    "matched_bank_narration": None,
                },
            )

        # Case 3: Exactly 1 settlement found
        else:
            setl = matching_setls[0]
            setl_id = setl["settlement_id"]
            utr = setl["utr"]
            net_settled = setl["net_settled_amount"]
            setl_gross_amount = setl["amount"]
            settled_at_dt = datetime.strptime(setl["settled_at"], "%Y-%m-%d").date()
            is_batch = setl_is_batch.get(setl_id, False)

            # Gross amount check: compare ledger.order_amount vs settlement.amount for single non-batch records
            order_amount = int(l_rec["order_amount"])
            gross_delta = abs(abs(order_amount) - abs(setl_gross_amount)) if not is_batch else 0
            has_gross_mismatch = (not is_batch) and (gross_delta > amount_tolerance_paise)

            # 3a: Exact UTR match in bank statement
            exact_bank_match: Optional[Tuple[int, Dict[str, Any]]] = None
            for idx, b in enumerate(bank_records):
                if utr in b["narration"]:
                    exact_bank_match = (idx, b)
                    break

            if exact_bank_match is not None:
                _, bank_row = exact_bank_match
                bank_amt = bank_row["credited_amount"]
                bank_dt = datetime.strptime(bank_row["txn_date"], "%Y-%m-%d").date()
                amount_delta = bank_amt - net_settled
                date_delta = (bank_dt - settled_at_dt).days

                if has_gross_mismatch:
                    match_status = "ambiguous"
                    confidence = 0.6
                    reason = "ledger_settlement_amount_mismatch"
                elif abs(amount_delta) <= amount_tolerance_paise:
                    match_status = "matched"
                    confidence = 1.0
                    reason = "exact_match"
                else:
                    match_status = "ambiguous"
                    confidence = 0.7
                    reason = "rounding_discrepancy"

                res = MatchResult(
                    order_id=order_id,
                    payment_id=pay_id,
                    settlement_id=setl_id,
                    match_status=match_status,
                    confidence=confidence,
                    evidence={
                        "date_delta_days": date_delta,
                        "amount_delta_paise": amount_delta,
                        "gross_amount_delta_paise": gross_delta,
                        "utr_match_type": "exact",
                        "is_batch": is_batch,
                        "is_duplicate": False,
                        "reason": reason,
                        "matched_bank_amount": bank_amt,
                        "matched_bank_narration": bank_row["narration"],
                    },
                )
            else:
                # 3b: Fuzzy UTR match in bank statement
                candidates: List[Tuple[int, float, int, Dict[str, Any]]] = []
                for idx, b in enumerate(bank_records):
                    if idx in exact_utr_bank_indices:
                        continue
                    b_dt = datetime.strptime(b["txn_date"], "%Y-%m-%d").date()
                    date_delta = (b_dt - settled_at_dt).days

                    if abs(date_delta) <= date_window_days:
                        score = float(fuzz.partial_ratio(utr, b["narration"]))
                        b_amt = b["credited_amount"]
                        amt_delta = b_amt - net_settled

                        if score >= fuzzy_threshold and abs(amt_delta) <= max_fuzzy_amount_delta_paise:
                            candidates.append((-abs(amt_delta), score, -abs(date_delta), b))

                if candidates:
                    candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
                    best_neg_amt, best_score, best_neg_date, best_bank_row = candidates[0]

                    bank_amt = best_bank_row["credited_amount"]
                    bank_dt = datetime.strptime(best_bank_row["txn_date"], "%Y-%m-%d").date()
                    amount_delta = bank_amt - net_settled
                    date_delta = (bank_dt - settled_at_dt).days

                    confidence = min(0.6, round(best_score / 100.0, 2))
                    reason = "garbled_utr"

                    res = MatchResult(
                        order_id=order_id,
                        payment_id=pay_id,
                        settlement_id=setl_id,
                        match_status="ambiguous",
                        confidence=confidence,
                        evidence={
                            "date_delta_days": date_delta,
                            "amount_delta_paise": amount_delta,
                            "gross_amount_delta_paise": gross_delta,
                            "utr_match_type": "fuzzy",
                            "is_batch": is_batch,
                            "is_duplicate": False,
                            "reason": reason,
                            "matched_bank_amount": bank_amt,
                            "matched_bank_narration": best_bank_row["narration"],
                        },
                    )
                else:
                    # 3c: No bank row found at all
                    res = MatchResult(
                        order_id=order_id,
                        payment_id=pay_id,
                        settlement_id=setl_id,
                        match_status="unmatched",
                        confidence=0.0,
                        evidence={
                            "date_delta_days": None,
                            "amount_delta_paise": None,
                            "gross_amount_delta_paise": gross_delta,
                            "utr_match_type": "none",
                            "is_batch": is_batch,
                            "is_duplicate": False,
                            "reason": "missing_bank_credit",
                            "matched_bank_amount": None,
                            "matched_bank_narration": None,
                        },
                    )

        if res is not None:
            # 2. Log Match stage event per ledger record
            log_event(
                stage="match",
                record_id=res.order_id,
                decision=res.match_status,
                confidence=res.confidence,
                evidence=res.evidence,
                explanation=f"Phase 2 matcher classified record as {res.match_status} with confidence {res.confidence}.",
                run_id=active_run_id,
            )
            results.append(res)

    return results


def run_matcher(run_id: Optional[str] = None) -> List[MatchResult]:
    """Execute Phase 2 matching pipeline on default data files."""
    ledger, settlement, bank = load_datasets()
    return reconcile_ledger(ledger, settlement, bank, run_id=run_id)


def main() -> None:
    """Run matcher standalone and print match status summary counts."""
    results = run_matcher()

    counts: Dict[str, int] = {}
    for r in results:
        counts[r.match_status] = counts.get(r.match_status, 0) + 1

    print("Phase 2 Matching Engine Execution Summary:")
    print("-" * 42)
    print(f"Total Ledger Records Processed: {len(results)}")
    for status, count in sorted(counts.items()):
        print(f"  - {status:<12}: {count}")


if __name__ == "__main__":
    main()

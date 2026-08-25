"""
Data generator for Multi-Source Reconciliation Agent (Phase 1).

Generates ledger.csv, settlement.csv, bank_statement.csv, and ground_truth.json
based on real Razorpay captured payment templates and synthetic planted exceptions.
"""

import glob
import json
import os
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

# Fixed seed for 100% reproducible data generation
SEED = 42
random.seed(SEED)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
REAL_SAMPLES_DIR = os.path.join(OUTPUT_DIR, "real_samples")

LEDGER_PATH = os.path.join(OUTPUT_DIR, "ledger.csv")
SETTLEMENT_PATH = os.path.join(OUTPUT_DIR, "settlement.csv")
BANK_PATH = os.path.join(OUTPUT_DIR, "bank_statement.csv")
GROUND_TRUTH_PATH = os.path.join(OUTPUT_DIR, "ground_truth.json")


def load_real_samples() -> List[Dict[str, Any]]:
    """Load real captured payment objects from real_samples/ directory."""
    samples = []
    pattern = os.path.join(REAL_SAMPLES_DIR, "*.json")
    for filepath in sorted(glob.glob(pattern)):
        with open(filepath, "r") as f:
            data = json.load(f)
            if data.get("status") == "captured":
                samples.append(data)
    return samples


def calculate_fees_and_tax(amount_paise: int) -> Tuple[int, int, int]:
    """
    Calculate base fee, GST tax, and net settled amount in paise.

    Base fee = 2% of amount
    Tax = 18% GST on base fee
    Net = amount - fee - tax
    """
    base_fee = int(round(amount_paise * 0.02))
    tax = int(round(base_fee * 0.18))
    net_settled = amount_paise - base_fee - tax
    return base_fee, tax, net_settled


def generate_random_payment_id(index: int) -> str:
    """Generate realistic Razorpay payment ID."""
    chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    suffix = "".join(random.choices(chars, k=10))
    return f"pay_SYN{index:03d}{suffix}"


def generate_utr(index: int) -> str:
    """Generate realistic bank UTR string."""
    return f"RZP202608{index:04d}UTR"


def build_dataset() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Build ledger, settlement, bank statement records and ground truth annotations.

    Target category breakdown (~56 records):
    - clean_match: 35
    - batch_aggregation: 5
    - normal_lag: 5
    - refund_pair: 2
    - garbled_utr: 3
    - rounding_noise: 2
    - missing_bank_credit: 2
    - duplicate_settlement: 1
    - orphan_ledger_entry: 1
    """
    real_samples = load_real_samples()

    ledger_records: List[Dict[str, Any]] = []
    settlement_records: List[Dict[str, Any]] = []
    bank_records: List[Dict[str, Any]] = []
    ground_truth_records: List[Dict[str, Any]] = []

    base_date = datetime(2026, 8, 1)
    record_counter = 1000
    utr_counter = 100

    # Helper to format dates
    def fmt_date(d: datetime) -> str:
        return d.strftime("%Y-%m-%d")

    # ---------------------------------------------------------
    # 1. Clean Matches (~35 records)
    # ---------------------------------------------------------
    for i in range(35):
        order_id = f"ORD-{record_counter}"
        if i < len(real_samples):
            real = real_samples[i]
            pay_id = real["id"]
            amount = real["amount"]
            real_fee = real["fee"]
            tax = real["tax"]
            fee = real_fee - tax
            net = amount - real_fee
        else:
            pay_id = generate_random_payment_id(i)
            amount = 45000 + (i * 1200)
            fee, tax, net = calculate_fees_and_tax(amount)

        order_dt = base_date + timedelta(days=i // 3, hours=random.randint(9, 17))
        settle_dt = order_dt + timedelta(days=2)
        utr = generate_utr(utr_counter)

        setl_id = f"setl_CLN{i:03d}"

        # Ledger
        ledger_records.append({
            "order_id": order_id,
            "razorpay_payment_id": pay_id,
            "order_amount": amount,
            "order_date": fmt_date(order_dt),
            "status": "paid"
        })

        # Settlement
        settlement_records.append({
            "settlement_id": setl_id,
            "payment_ids": json.dumps([pay_id]),
            "amount": amount,
            "fees": fee,
            "tax": tax,
            "net_settled_amount": net,
            "utr": utr,
            "settled_at": fmt_date(settle_dt)
        })

        # Bank
        bank_records.append({
            "txn_date": fmt_date(settle_dt),
            "credited_amount": net,
            "narration": f"CMS/NEFT/{utr}/RAZORPAY SOFTWARE PVT LTD"
        })

        # Ground Truth
        ground_truth_records.append({
            "record_id": order_id,
            "order_id": order_id,
            "razorpay_payment_id": pay_id,
            "settlement_id": setl_id,
            "utr": utr,
            "category": "clean_match",
            "description": "Clean match across ledger, settlement, and bank statement."
        })

        record_counter += 1
        utr_counter += 1

    # ---------------------------------------------------------
    # 2. Batch Aggregation (~5 cases)
    # ---------------------------------------------------------
    for i in range(5):
        # Case i: 2 payments aggregated into 1 settlement and 1 bank credit
        order_id_1 = f"ORD-{record_counter}"
        pay_id_1 = generate_random_payment_id(100 + i * 2)
        amt_1 = 50000 + i * 2000

        order_id_2 = f"ORD-{record_counter + 1}"
        pay_id_2 = generate_random_payment_id(100 + i * 2 + 1)
        amt_2 = 35000 + i * 1500

        order_dt = base_date + timedelta(days=12 + i)
        settle_dt = order_dt + timedelta(days=2)
        utr = generate_utr(utr_counter)

        fee1, tax1, net1 = calculate_fees_and_tax(amt_1)
        fee2, tax2, net2 = calculate_fees_and_tax(amt_2)

        tot_amt = amt_1 + amt_2
        tot_fee = fee1 + fee2
        tot_tax = tax1 + tax2
        tot_net = net1 + net2

        setl_id = f"setl_BAT{i:03d}"

        # Ledger
        ledger_records.append({
            "order_id": order_id_1,
            "razorpay_payment_id": pay_id_1,
            "order_amount": amt_1,
            "order_date": fmt_date(order_dt),
            "status": "paid"
        })
        ledger_records.append({
            "order_id": order_id_2,
            "razorpay_payment_id": pay_id_2,
            "order_amount": amt_2,
            "order_date": fmt_date(order_dt),
            "status": "paid"
        })

        # Settlement (combines pay_id_1 and pay_id_2)
        settlement_records.append({
            "settlement_id": setl_id,
            "payment_ids": json.dumps([pay_id_1, pay_id_2]),
            "amount": tot_amt,
            "fees": tot_fee,
            "tax": tot_tax,
            "net_settled_amount": tot_net,
            "utr": utr,
            "settled_at": fmt_date(settle_dt)
        })

        # Bank (1 credit for the batched settlement)
        bank_records.append({
            "txn_date": fmt_date(settle_dt),
            "credited_amount": tot_net,
            "narration": f"NEFT-{utr}-RAZORPAY BATCH"
        })

        # Ground Truth for both orders
        gt_desc = f"Batched settlement ({setl_id}) combining {pay_id_1} and {pay_id_2} into one bank credit."
        ground_truth_records.append({
            "record_id": order_id_1,
            "order_id": order_id_1,
            "razorpay_payment_id": pay_id_1,
            "settlement_id": setl_id,
            "utr": utr,
            "category": "batch_aggregation",
            "description": gt_desc
        })
        ground_truth_records.append({
            "record_id": order_id_2,
            "order_id": order_id_2,
            "razorpay_payment_id": pay_id_2,
            "settlement_id": setl_id,
            "utr": utr,
            "category": "batch_aggregation",
            "description": gt_desc
        })

        record_counter += 2
        utr_counter += 1

    # ---------------------------------------------------------
    # 3. Normal T+2 / T+3 Lag (~5 records)
    # ---------------------------------------------------------
    for i in range(5):
        order_id = f"ORD-{record_counter}"
        pay_id = generate_random_payment_id(200 + i)
        amount = 60000 + (i * 3000)

        order_dt = base_date + timedelta(days=15 + i)
        # Lag of 5 days (e.g. weekend/bank holiday)
        settle_dt = order_dt + timedelta(days=5)
        utr = generate_utr(utr_counter)

        fee, tax, net = calculate_fees_and_tax(amount)
        setl_id = f"setl_LAG{i:03d}"

        ledger_records.append({
            "order_id": order_id,
            "razorpay_payment_id": pay_id,
            "order_amount": amount,
            "order_date": fmt_date(order_dt),
            "status": "paid"
        })

        settlement_records.append({
            "settlement_id": setl_id,
            "payment_ids": json.dumps([pay_id]),
            "amount": amount,
            "fees": fee,
            "tax": tax,
            "net_settled_amount": net,
            "utr": utr,
            "settled_at": fmt_date(settle_dt)
        })

        bank_records.append({
            "txn_date": fmt_date(settle_dt),
            "credited_amount": net,
            "narration": f"CMS/NEFT/{utr}/RAZORPAY SOFTWARE PVT LTD"
        })

        ground_truth_records.append({
            "record_id": order_id,
            "order_id": order_id,
            "razorpay_payment_id": pay_id,
            "settlement_id": setl_id,
            "utr": utr,
            "category": "normal_lag",
            "description": f"Normal settlement lag of {(settle_dt - order_dt).days} days."
        })

        record_counter += 1
        utr_counter += 1

    # ---------------------------------------------------------
    # 4. Refund Pair (~2 records)
    # ---------------------------------------------------------
    for i in range(2):
        order_id = f"ORD-{record_counter}"
        pay_id = generate_random_payment_id(300 + i)
        amount = 40000 + (i * 5000)

        order_dt = base_date + timedelta(days=18 + i)
        settle_dt = order_dt + timedelta(days=2)
        utr = generate_utr(utr_counter)

        setl_id = f"setl_RFD{i:03d}"

        # Refund entry: negative amount in settlement/bank, refunded in ledger
        ledger_records.append({
            "order_id": order_id,
            "razorpay_payment_id": pay_id,
            "order_amount": amount,
            "order_date": fmt_date(order_dt),
            "status": "refunded"
        })

        # Settlement shows negative payout/refund deduction
        settlement_records.append({
            "settlement_id": setl_id,
            "payment_ids": json.dumps([pay_id]),
            "amount": -amount,
            "fees": 0,
            "tax": 0,
            "net_settled_amount": -amount,
            "utr": utr,
            "settled_at": fmt_date(settle_dt)
        })

        bank_records.append({
            "txn_date": fmt_date(settle_dt),
            "credited_amount": -amount,
            "narration": f"REV-NEFT-{utr}-RAZORPAY REFUND"
        })

        ground_truth_records.append({
            "record_id": order_id,
            "order_id": order_id,
            "razorpay_payment_id": pay_id,
            "settlement_id": setl_id,
            "utr": utr,
            "category": "refund_pair",
            "description": "Refund pair entry with negative settlement and bank debit."
        })

        record_counter += 1
        utr_counter += 1

    # ---------------------------------------------------------
    # 5. Garbled UTR (~3 records)
    # ---------------------------------------------------------
    for i in range(3):
        order_id = f"ORD-{record_counter}"
        pay_id = generate_random_payment_id(400 + i)
        amount = 52000 + (i * 2500)

        order_dt = base_date + timedelta(days=20 + i)
        settle_dt = order_dt + timedelta(days=2)
        utr = generate_utr(utr_counter)

        # Garble the UTR in bank narration (e.g. truncate or replace chars)
        if i == 0:
            garbled_narration = f"NEFT-{utr[:-3]}-RAZORPAY"
        elif i == 1:
            garbled_narration = f"CMS/NEFT/{utr.replace('2026', 'XXXX')}/RAZORPAY"
        else:
            garbled_narration = f"INB-UTR-{utr[3:]}-RZP"

        fee, tax, net = calculate_fees_and_tax(amount)
        setl_id = f"setl_GAR{i:03d}"

        ledger_records.append({
            "order_id": order_id,
            "razorpay_payment_id": pay_id,
            "order_amount": amount,
            "order_date": fmt_date(order_dt),
            "status": "paid"
        })

        settlement_records.append({
            "settlement_id": setl_id,
            "payment_ids": json.dumps([pay_id]),
            "amount": amount,
            "fees": fee,
            "tax": tax,
            "net_settled_amount": net,
            "utr": utr,
            "settled_at": fmt_date(settle_dt)
        })

        bank_records.append({
            "txn_date": fmt_date(settle_dt),
            "credited_amount": net,
            "narration": garbled_narration
        })

        ground_truth_records.append({
            "record_id": order_id,
            "order_id": order_id,
            "razorpay_payment_id": pay_id,
            "settlement_id": setl_id,
            "utr": utr,
            "category": "garbled_utr",
            "description": f"Garbled UTR in bank narration: '{garbled_narration}' vs true UTR '{utr}'."
        })

        record_counter += 1
        utr_counter += 1

    # ---------------------------------------------------------
    # 6. Rounding Noise (~2 records)
    # ---------------------------------------------------------
    for i in range(2):
        order_id = f"ORD-{record_counter}"
        pay_id = generate_random_payment_id(500 + i)
        amount = 48900 + (i * 3300)

        order_dt = base_date + timedelta(days=22 + i)
        settle_dt = order_dt + timedelta(days=2)
        utr = generate_utr(utr_counter)

        fee, tax, net = calculate_fees_and_tax(amount)
        setl_id = f"setl_RND{i:03d}"

        # Bank credited amount differs by +/- 2 paise
        bank_net = net + (2 if i == 0 else -1)

        ledger_records.append({
            "order_id": order_id,
            "razorpay_payment_id": pay_id,
            "order_amount": amount,
            "order_date": fmt_date(order_dt),
            "status": "paid"
        })

        settlement_records.append({
            "settlement_id": setl_id,
            "payment_ids": json.dumps([pay_id]),
            "amount": amount,
            "fees": fee,
            "tax": tax,
            "net_settled_amount": net,
            "utr": utr,
            "settled_at": fmt_date(settle_dt)
        })

        bank_records.append({
            "txn_date": fmt_date(settle_dt),
            "credited_amount": bank_net,
            "narration": f"CMS/NEFT/{utr}/RAZORPAY SOFTWARE PVT LTD"
        })

        ground_truth_records.append({
            "record_id": order_id,
            "order_id": order_id,
            "razorpay_payment_id": pay_id,
            "settlement_id": setl_id,
            "utr": utr,
            "category": "rounding_noise",
            "description": f"Rounding noise discrepancy: settlement net {net} vs bank credit {bank_net}."
        })

        record_counter += 1
        utr_counter += 1

    # ---------------------------------------------------------
    # 7. Missing Bank Credit (~2 records)
    # ---------------------------------------------------------
    for i in range(2):
        order_id = f"ORD-{record_counter}"
        pay_id = generate_random_payment_id(600 + i)
        amount = 70000 + (i * 4000)

        order_dt = base_date + timedelta(days=24 + i)
        settle_dt = order_dt + timedelta(days=2)
        utr = generate_utr(utr_counter)

        fee, tax, net = calculate_fees_and_tax(amount)
        setl_id = f"setl_MIS{i:03d}"

        ledger_records.append({
            "order_id": order_id,
            "razorpay_payment_id": pay_id,
            "order_amount": amount,
            "order_date": fmt_date(order_dt),
            "status": "paid"
        })

        settlement_records.append({
            "settlement_id": setl_id,
            "payment_ids": json.dumps([pay_id]),
            "amount": amount,
            "fees": fee,
            "tax": tax,
            "net_settled_amount": net,
            "utr": utr,
            "settled_at": fmt_date(settle_dt)
        })

        # NO BANK RECORD ADDED!

        ground_truth_records.append({
            "record_id": order_id,
            "order_id": order_id,
            "razorpay_payment_id": pay_id,
            "settlement_id": setl_id,
            "utr": utr,
            "category": "missing_bank_credit",
            "description": f"Settlement {setl_id} marked as settled, but bank credit is missing."
        })

        record_counter += 1
        utr_counter += 1

    # ---------------------------------------------------------
    # 8. Duplicate Settlement (~1 record)
    # ---------------------------------------------------------
    order_id_dup = f"ORD-{record_counter}"
    pay_id_dup = generate_random_payment_id(700)
    amount_dup = 55000

    order_dt = base_date + timedelta(days=26)
    settle_dt = order_dt + timedelta(days=2)
    utr1 = generate_utr(utr_counter)
    utr2 = generate_utr(utr_counter + 1)

    fee_d, tax_d, net_d = calculate_fees_and_tax(amount_dup)
    setl_id_1 = "setl_DUP001A"
    setl_id_2 = "setl_DUP001B"

    ledger_records.append({
        "order_id": order_id_dup,
        "razorpay_payment_id": pay_id_dup,
        "order_amount": amount_dup,
        "order_date": fmt_date(order_dt),
        "status": "paid"
    })

    # First settlement
    settlement_records.append({
        "settlement_id": setl_id_1,
        "payment_ids": json.dumps([pay_id_dup]),
        "amount": amount_dup,
        "fees": fee_d,
        "tax": tax_d,
        "net_settled_amount": net_d,
        "utr": utr1,
        "settled_at": fmt_date(settle_dt)
    })
    # Duplicate settlement
    settlement_records.append({
        "settlement_id": setl_id_2,
        "payment_ids": json.dumps([pay_id_dup]),
        "amount": amount_dup,
        "fees": fee_d,
        "tax": tax_d,
        "net_settled_amount": net_d,
        "utr": utr2,
        "settled_at": fmt_date(settle_dt + timedelta(days=1))
    })

    bank_records.append({
        "txn_date": fmt_date(settle_dt),
        "credited_amount": net_d,
        "narration": f"CMS/NEFT/{utr1}/RAZORPAY SOFTWARE PVT LTD"
    })
    bank_records.append({
        "txn_date": fmt_date(settle_dt + timedelta(days=1)),
        "credited_amount": net_d,
        "narration": f"CMS/NEFT/{utr2}/RAZORPAY SOFTWARE PVT LTD"
    })

    ground_truth_records.append({
        "record_id": order_id_dup,
        "order_id": order_id_dup,
        "razorpay_payment_id": pay_id_dup,
        "settlement_id": f"{setl_id_1},{setl_id_2}",
        "utr": f"{utr1},{utr2}",
        "category": "duplicate_settlement",
        "description": f"Payment {pay_id_dup} was settled twice ({setl_id_1} and {setl_id_2})."
    })

    record_counter += 1
    utr_counter += 2

    # ---------------------------------------------------------
    # 9. Orphan Ledger Entry (~1 record)
    # ---------------------------------------------------------
    order_id_orp = f"ORD-{record_counter}"
    pay_id_orp = generate_random_payment_id(800)
    amount_orp = 62000

    order_dt = base_date + timedelta(days=28)

    ledger_records.append({
        "order_id": order_id_orp,
        "razorpay_payment_id": pay_id_orp,
        "order_amount": amount_orp,
        "order_date": fmt_date(order_dt),
        "status": "paid"
    })

    # NO SETTLEMENT RECORD AND NO BANK RECORD ADDED!

    ground_truth_records.append({
        "record_id": order_id_orp,
        "order_id": order_id_orp,
        "razorpay_payment_id": pay_id_orp,
        "settlement_id": None,
        "utr": None,
        "category": "orphan_ledger_entry",
        "description": f"Ledger entry {order_id_orp} marked as paid but has no matching Razorpay settlement or bank credit."
    })

    return ledger_records, settlement_records, bank_records, ground_truth_records


def write_csv(path: str, fieldnames: List[str], rows: List[Dict[str, Any]]) -> None:
    """Write list of dictionaries to a CSV file."""
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Main execution function for dataset generator."""
    ledger, settlement, bank, ground_truth = build_dataset()

    write_csv(LEDGER_PATH, ["order_id", "razorpay_payment_id", "order_amount", "order_date", "status"], ledger)
    write_csv(SETTLEMENT_PATH, ["settlement_id", "payment_ids", "amount", "fees", "tax", "net_settled_amount", "utr", "settled_at"], settlement)
    write_csv(BANK_PATH, ["txn_date", "credited_amount", "narration"], bank)

    # Compute category summary for ground truth
    summary: Dict[str, int] = {}
    for gt in ground_truth:
        cat = gt["category"]
        summary[cat] = summary.get(cat, 0) + 1

    gt_payload = {
        "summary": summary,
        "total_records": len(ground_truth),
        "records": ground_truth
    }

    with open(GROUND_TRUTH_PATH, "w", encoding="utf-8") as f:
        json.dump(gt_payload, f, indent=2)

    print(f"Generated datasets in {OUTPUT_DIR}:")
    print(f"  - ledger.csv: {len(ledger)} rows")
    print(f"  - settlement.csv: {len(settlement)} rows")
    print(f"  - bank_statement.csv: {len(bank)} rows")
    print(f"  - ground_truth.json: {len(ground_truth)} records annotated across {len(summary)} categories")


if __name__ == "__main__":
    main()

"""
Creates test Orders via the Razorpay Orders API and saves them to
orders_to_pay.json, ready to be paid manually via checkout.html.

Run this first: python create_orders.py
"""

import json
import os
import time

import razorpay
from dotenv import load_dotenv

load_dotenv()

KEY_ID = os.environ["RAZORPAY_KEY_ID"]
KEY_SECRET = os.environ["RAZORPAY_KEY_SECRET"]

client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))

NUM_ORDERS = 10
BASE_AMOUNT_PAISE = 49_900  # ₹499.00 — Razorpay amounts are always in paise
ORDERS_FILE = "orders_to_pay.json"


def save_orders(orders: list[dict]) -> None:
    """Save orders list incrementally to orders_to_pay.json."""
    with open(ORDERS_FILE, "w") as f:
        json.dump(orders, f, indent=2)


def main() -> None:
    """Create test orders on Razorpay up to NUM_ORDERS total with retries and rate limiting."""
    orders: list[dict] = []
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r") as f:
                existing = json.load(f)
                if isinstance(existing, list):
                    orders = existing
                    print(f"Loaded {len(orders)} existing order(s) from {ORDERS_FILE}")
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Failed to load existing {ORDERS_FILE}: {e}")

    start_index = len(orders)
    if start_index >= NUM_ORDERS:
        print(f"Already have {start_index} orders in {ORDERS_FILE}. Nothing to do.")
        return

    print(f"Need to create {NUM_ORDERS - start_index} more order(s)...")

    for i in range(start_index, NUM_ORDERS):
        # Vary the amount per order so real samples aren't all identical
        amount = BASE_AMOUNT_PAISE + (i * 1_500)
        receipt = f"ORD-{1000 + i}"

        order = None
        for attempt in range(1, 4):
            try:
                order = client.order.create(
                    {
                        "amount": amount,
                        "currency": "INR",
                        "receipt": receipt,
                        "payment_capture": 1,  # auto-capture as soon as payment succeeds
                    }
                )
                break
            except razorpay.errors.BadRequestError as e:
                print(f"Attempt {attempt}/3 failed for {receipt}: {e}")
                if attempt < 3:
                    time.sleep(3)

        if order is None:
            print(f"Skipping {receipt} after 3 failed attempts.")
            continue

        orders.append(
            {
                "order_id": order["id"],
                "receipt": order["receipt"],
                "amount": order["amount"],
            }
        )
        print(f"Created {order['id']}  receipt={order['receipt']}  amount={amount}")
        save_orders(orders)

        time.sleep(1)

    print(f"\nSaved {len(orders)} total orders to {ORDERS_FILE}")
    print("Next: run `python -m http.server 8000`, then open http://localhost:8000/checkout.html")


if __name__ == "__main__":
    main()


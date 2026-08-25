"""
Looks up which payment landed against each order in orders_to_pay.json,
fetches the full Payment object for each, and saves it to real_samples/.

Run this after paying the orders via checkout.html:
    python fetch_payments.py
"""

import json
import os

import razorpay
from dotenv import load_dotenv

load_dotenv()

KEY_ID = os.environ["RAZORPAY_KEY_ID"]
KEY_SECRET = os.environ["RAZORPAY_KEY_SECRET"]

client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))

OUTPUT_DIR = "real_samples"


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open("orders_to_pay.json") as f:
        orders = json.load(f)

    fetched = 0

    for order in orders:
        order_id = order["order_id"]
        payments = client.order.payments(order_id)  # {"count": N, "items": [...]}
        items = payments.get("items", [])

        if not items:
            print(f"No payment found yet for {order_id} ({order['receipt']}) "
                  f"— did you pay it in checkout.html?")
            continue

        for payment in items:
            payment_id = payment["id"]
            full_payment = client.payment.fetch(payment_id)

            out_path = os.path.join(OUTPUT_DIR, f"{payment_id}.json")
            with open(out_path, "w") as out:
                json.dump(full_payment, out, indent=2)

            print(
                f"Saved {out_path}  status={full_payment['status']}  "
                f"fee={full_payment.get('fee')}  tax={full_payment.get('tax')}"
            )
            fetched += 1

    print(f"\nDone. {fetched} payment objects saved to {OUTPUT_DIR}/.")


if __name__ == "__main__":
    main()

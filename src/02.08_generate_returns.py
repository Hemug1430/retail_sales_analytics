"""
02.08 - Generate Returns
Frozen Document 02 CSV header:
return_id,sales_line_id,return_date,quantity_returned,return_reason,
return_status,refund_method,refund_amount,processed_store_id
"""

import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import mysql.connector
from config import DB_CONFIG


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "synthetic" / "returns_master.csv"

FIELDS = [
    "return_id",
    "sales_line_id",
    "return_date",
    "quantity_returned",
    "return_reason",
    "return_status",
    "refund_method",
    "refund_amount",
    "processed_store_id",
]

REASONS = [
    "Damaged",
    "Wrong Product",
    "Quality Issue",
    "Size/Fit Issue",
    "Customer Changed Mind",
    "Late Delivery",
    "Other",
]

STATUSES = [
    "Requested",
    "Approved",
    "Rejected",
    "Refunded",
]

REFUND_METHODS = [
    "Original Payment",
    "Store Credit",
    "Cash",
]


def as_date(value):
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    return datetime.strptime(
        str(value),
        "%Y-%m-%d"
    ).date()


def main():

    connection = None
    cursor = None

    try:

        connection = mysql.connector.connect(**DB_CONFIG)

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute("""
            SELECT
                sales_line_id,
                store_id,
                order_date,
                quantity,
                unit_selling_price,
                discount_pct

            FROM factsales

            WHERE order_status = 'Completed'
              AND quantity > 0

            ORDER BY
                order_date,
                sales_line_id

            LIMIT 2500
        """)

        sales = cursor.fetchall()

        if not sales:
            raise RuntimeError(
                "No Completed sales with positive quantity found."
            )

        OUTPUT.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        token = datetime.now().strftime(
            "%y%m%d%H%M"
        )

        count = 0

        with OUTPUT.open(
            "w",
            newline="",
            encoding="utf-8"
        ) as handle:

            writer = csv.DictWriter(
                handle,
                fieldnames=FIELDS
            )

            writer.writeheader()

            for index, sale in enumerate(
                sales,
                start=1
            ):

                if random.random() >= 0.15:
                    continue

                qty = random.randint(
                    1,
                    int(sale["quantity"])
                )

                order_date = as_date(
                    sale["order_date"]
                )

                return_date = (
                    order_date
                    + timedelta(days=random.randint(1, 30))
                )

                status = random.choices(
                    STATUSES,
                    weights=[20, 25, 15, 40],
                    k=1
                )[0]

                if status == "Refunded":

                    method = random.choice(
                        REFUND_METHODS
                    )

                    net_unit = (
                        float(sale["unit_selling_price"])
                        * (
                            1
                            - float(sale["discount_pct"]) / 100
                        )
                    )

                    amount = round(
                        net_unit * qty,
                        2
                    )

                else:

                    method = ""
                    amount = ""

                writer.writerow({

                    "return_id": (
                        f"RET{token}{index:04d}"
                    ),

                    "sales_line_id": (
                        sale["sales_line_id"]
                    ),

                    "return_date": (
                        return_date.isoformat()
                    ),

                    "quantity_returned": qty,

                    "return_reason": random.choice(
                        REASONS
                    ),

                    "return_status": status,

                    "refund_method": method,

                    "refund_amount": amount,

                    "processed_store_id": (
                        sale["store_id"] or ""
                    ),

                })

                count += 1

        print(
            f"02.08 STATUS: PASS | "
            f"Sales examined={len(sales):,} | "
            f"Returns={count:,}"
        )

        print(f"Output: {OUTPUT}")

        print(
            "Header: " + ",".join(FIELDS)
        )

    except Exception as exc:

        print(
            f"02.08 STATUS: FAILED - {exc}"
        )

        raise

    finally:

        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()


if __name__ == "__main__":
    main()
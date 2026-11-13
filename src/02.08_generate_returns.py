
import csv
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


# --------------------------------------------------
# Project configuration
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

OUTPUT_PATH = BASE_DIR / "data" / "synthetic" / "returns_master.csv"


def get_db_connection():
    """Connect using the credentials stored in .env."""

    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [key for key in required if not os.getenv(key)]

    if missing:
        raise RuntimeError(
            "Missing database configuration: " + ", ".join(missing)
        )

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


def main():
    conn = None
    cursor = None

    try:
        print("Connecting to database to pull valid sample sales transactions...")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT
                sales_line_id,
                store_id,
                order_date,
                quantity,
                unit_selling_price,
                discount_pct
            FROM factsales
            LIMIT 2500
        """

        cursor.execute(query)
        sales = cursor.fetchall()

        allowed_reasons = [
            "Damaged",
            "Wrong Product",
            "Quality Issue",
            "Size/Fit Issue",
            "Customer Changed Mind",
            "Late Delivery",
            "Other"
        ]

        print(
            f"Generating realistic returns from "
            f"{len(sales)} valid transaction rows..."
        )

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(
            OUTPUT_PATH,
            mode="w",
            newline="",
            encoding="utf-8"
        ) as file:
            writer = csv.writer(file)

            writer.writerow([
                "return_id",
                "order_id",
                "product_id",
                "store_id",
                "return_date",
                "quantity",
                "refund_amount",
                "return_reason",
                "status"
            ])

            return_id_counter = 100001

            for sale in sales:
                if random.random() < 0.15:

                    ret_qty = random.randint(
                        1,
                        int(sale["quantity"])
                    )

                    order_dt = sale["order_date"]

                    if isinstance(order_dt, str):
                        order_dt = datetime.strptime(
                            order_dt,
                            "%Y-%m-%d"
                        )

                    ret_date = order_dt + timedelta(
                        days=random.randint(1, 14)
                    )

                    price_per_item = float(
                        sale["unit_selling_price"]
                    )

                    pct_discount = (
                        float(sale["discount_pct"])
                        if sale["discount_pct"] is not None
                        else 0.0
                    )

                    actual_item_cost = price_per_item * (
                        1.0 - pct_discount
                    )

                    refund_amt = round(
                        actual_item_cost * ret_qty,
                        2
                    )

                    writer.writerow([
                        f"RET{return_id_counter}",
                        sale["sales_line_id"],
                        "PROD_001",
                        sale["store_id"],
                        ret_date.strftime("%Y-%m-%d"),
                        ret_qty,
                        refund_amt,
                        random.choice(allowed_reasons),
                        "Completed"
                    ])

                    return_id_counter += 1

        print(
            f"Success! Created returns file at: {OUTPUT_PATH}"
        )

    except Exception as exc:
        print(f"Generation failed: {exc}")
        raise

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    main()

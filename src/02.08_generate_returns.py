import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
import mysql.connector

BASE_DIR = Path(__file__).resolve().parent.parent
output_path = BASE_DIR / "data" / "synthetic" / "returns_master.csv"
output_path.parent.mkdir(parents=True, exist_ok=True)

print("Connecting to database to pull valid sample sales transactions...")
try:
    conn = mysql.connector.connect(
        host="localhost", user="root", password="Root", database="retail_sales_db"
    )
    cursor = conn.cursor(dictionary=True)

    # Pull the exact verified sales_line_id keys from your database ledger
    query = """
        SELECT sales_line_id, store_id, order_date, quantity, unit_selling_price, discount_pct 
        FROM factsales 
        LIMIT 2500
    """
    cursor.execute(query)
    sales = cursor.fetchall()

    allowed_reasons = ["Damaged", "Wrong Product", "Quality Issue", "Size/Fit Issue", "Customer Changed Mind", "Late Delivery", "Other"]

    print(f"Generating realistic returns from {len(sales)} valid transaction rows...")

    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["return_id", "order_id", "product_id", "store_id", "return_date", "quantity", "refund_amount", "return_reason", "status"])

        return_id_counter = 100001
        for sale in sales:
            if random.random() < 0.15: # ~15% return distribution rate
                ret_qty = random.randint(1, int(sale["quantity"]))

                order_dt = sale["order_date"]
                if isinstance(order_dt, str):
                    order_dt = datetime.strptime(order_dt, "%Y-%m-%d")
                ret_date = order_dt + timedelta(days=random.randint(1, 14))

                price_per_item = float(sale["unit_selling_price"])
                pct_discount = float(sale["discount_pct"]) if sale["discount_pct"] is not None else 0.0

                actual_item_cost = price_per_item * (1.0 - pct_discount)
                refund_amt = round(actual_item_cost * ret_qty, 2)

                writer.writerow([
                    f"RET{return_id_counter}",
                    sale["sales_line_id"], # Correctly matches parent record key mapping
                    "PROD_001",            # Standalone tracking value placeholder
                    sale["store_id"],
                    ret_date.strftime("%Y-%m-%d"),
                    ret_qty,
                    refund_amt,
                    random.choice(allowed_reasons),
                    "Completed"
                ])
                return_id_counter += 1

    print(f"Success! Created missing file footprint at: {output_path}")

except Exception as e:
    print(f"Generation failed: {e}")
finally:
    if "cursor" in locals(): cursor.close()
    if "conn" in locals(): conn.close()

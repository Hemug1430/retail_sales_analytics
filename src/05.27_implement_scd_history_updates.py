"""
05.27 - Implement SCD History Updates
Archives prior attribute snapshots into core_customers_history (PRIMARY KEY customer_id)
with valid_from, valid_to, record_version, and is_current=0 while updating core_customers.
"""

import sys
from datetime import datetime
import mysql.connector
from config import DB_CONFIG


def run():
    conn = None
    cursor = None
    try:
        print("=" * 72)
        print("05.27 - IMPLEMENT & VERIFY SCD HISTORY UPDATES")
        print("=" * 72)

        conn = mysql.connector.connect(**DB_CONFIG)
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)

        # 1. Verify required tables and SCD columns
        for tbl in ("core_customers", "core_customers_history"):
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = %s",
                (tbl,),
            )
            if cursor.fetchone()["cnt"] == 0:
                raise RuntimeError(f"Required table '{tbl}' not found.")

        cursor.execute("DESCRIBE core_customers_history")
        hist_cols = {row["Field"] for row in cursor.fetchall()}
        required_scd_cols = {"record_version", "valid_from", "valid_to", "is_current"}
        missing_cols = required_scd_cols - hist_cols
        if missing_cols:
            raise RuntimeError(f"Missing SCD columns in core_customers_history: {sorted(missing_cols)}")

        # 2. Select sample customer and archive prior snapshot into core_customers_history
        cursor.execute("""
            SELECT customer_id, preferred_channel, created_at
            FROM core_customers
            ORDER BY customer_id
            LIMIT 1
        """)
        sample = cursor.fetchone()
        if not sample:
            raise RuntimeError("No customer records found in core_customers.")

        cust_id = sample["customer_id"]
        orig_channel = sample["preferred_channel"] if sample["preferred_channel"] in ("Store", "Online") else "Online"
        updated_channel = "Store" if orig_channel == "Online" else "Online"
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Archive prior version into core_customers_history (upsert on PRIMARY KEY customer_id)
        cursor.execute(
            """
            INSERT INTO core_customers_history (
                customer_id, customer_name, gender, date_of_birth, email, phone,
                city, state, region, postal_code, registration_date,
                customer_segment, preferred_channel, status,
                batch_id, source_file_name, source_row_number, record_hash,
                record_version, valid_from, valid_to, is_current
            )
            SELECT
                customer_id, customer_name, gender, date_of_birth, email, phone,
                city, state, region, postal_code, registration_date,
                customer_segment, %s, status,
                batch_id, source_file_name, source_row_number, record_hash,
                1, COALESCE(created_at, %s), %s, 0
            FROM core_customers
            WHERE customer_id = %s
            ON DUPLICATE KEY UPDATE
                preferred_channel = VALUES(preferred_channel),
                record_version = VALUES(record_version),
                valid_to = VALUES(valid_to),
                is_current = 0
            """,
            (orig_channel, now_ts, now_ts, cust_id),
        )

        # Update current active attribute in core_customers
        cursor.execute(
            "UPDATE core_customers SET preferred_channel = %s WHERE customer_id = %s",
            (updated_channel, cust_id),
        )

        # 3. Verify historical snapshot exists with valid_to populated and is_current = 0
        cursor.execute(
            """
            SELECT customer_id, preferred_channel, record_version, valid_from, valid_to, is_current
            FROM core_customers_history
            WHERE customer_id = %s
            """,
            (cust_id,),
        )
        hist_row = cursor.fetchone()
        if not hist_row or hist_row["valid_to"] is None or int(hist_row["is_current"]) != 0:
            raise RuntimeError(f"SCD historical snapshot verification failed for {cust_id}.")

        conn.commit()
        print(f"Verified SCD sample customer     : {cust_id}")
        print(f"Archived prior channel (v1)      : {hist_row['preferred_channel']} (is_current={hist_row['is_current']}, valid_to={hist_row['valid_to']})")
        print(f"Active core channel (current)    : {updated_channel}")
        print("05.27 STATUS: PASS")

    except Exception as exc:
        if conn is not None and conn.is_connected():
            conn.rollback()
        print(f"05.27 STATUS: FAILED - {exc}")
        sys.exit(1)
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    run()

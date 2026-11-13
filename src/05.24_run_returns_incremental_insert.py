
import csv
import os
import mysql.connector

from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


# ==================================================
# PROJECT CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

CSV_PATH = BASE_DIR / "data" / "synthetic" / "returns_master.csv"

CORE_TABLE_NAME = "factreturns"


def get_db_connection():
    """Create a MySQL connection using environment credentials."""

    required_variables = [
        "DB_HOST",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD"
    ]

    missing_variables = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing_variables:
        raise RuntimeError(
            "Missing database configuration: "
            + ", ".join(missing_variables)
        )

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


# ==================================================
# MAIN PROCESS
# ==================================================

def main():

    conn = None
    cursor = None

    print("==================================================")
    print("05.24 - RUN RETURNS INCREMENTAL INSERT")
    print("==================================================")

    try:

        if not CSV_PATH.exists():
            raise FileNotFoundError(
                f"Returns CSV file not found: {CSV_PATH}"
            )

        print("Connecting to database...")

        conn = get_db_connection()
        cursor = conn.cursor()

        print("Database connection: SUCCESS")

        # --------------------------------------------------
        # CLEAR STAGING TABLE
        # --------------------------------------------------

        print("Clearing returns staging layer (stg_returns)...")

        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("TRUNCATE TABLE stg_returns;")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        conn.commit()

        # --------------------------------------------------
        # STAGING INSERT
        # --------------------------------------------------

        insert_staging_sql = """
            INSERT INTO stg_returns (
                return_id,
                sales_line_id,
                return_date,
                quantity_returned,
                refund_amount,
                return_reason,
                return_status,
                processed_store_id,
                batch_id,
                source_file_name,
                source_row_number,
                record_hash,
                load_timestamp
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
        """

        valid_reasons = {
            "Damaged",
            "Wrong Product",
            "Quality Issue",
            "Size/Fit Issue",
            "Customer Changed Mind",
            "Late Delivery",
            "Other"
        }

        valid_statuses = {
            "Pending",
            "Completed",
            "Refunded",
            "Processed"
        }

        print("Reading CSV and mapping parameters into staging table...")

        inserted_count = 0

        with open(
            CSV_PATH,
            mode="r",
            encoding="utf-8",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for idx, row in enumerate(reader, start=1):

                clean_store_id = (
                    row["store_id"]
                    .strip()
                    .replace("STORE000", "STORE0")
                )

                row_hash = f"hash_{row['return_id'].strip()}"

                reason_input = row["return_reason"].strip()

                clean_reason = (
                    reason_input
                    if reason_input in valid_reasons
                    else "Other"
                )

                status_input = row["status"].strip().title()

                if status_input == "Processed":
                    clean_status = "Completed"

                elif status_input in valid_statuses:
                    clean_status = status_input

                else:
                    clean_status = "Completed"

                params = (
                    row["return_id"].strip(),
                    row["order_id"].strip(),
                    row["return_date"].strip(),
                    int(row["quantity"]),
                    float(row["refund_amount"]),
                    clean_reason,
                    clean_status,
                    clean_store_id,
                    "BATCH_001",
                    "returns_master.csv",
                    idx,
                    row_hash,
                    datetime.now()
                )

                cursor.execute(insert_staging_sql, params)

                inserted_count += 1

        conn.commit()

        print(f"Staging records populated: {inserted_count}")

        # --------------------------------------------------
        # INCREMENTAL MIGRATION INTO CORE TABLE
        # --------------------------------------------------

        print(
            f"Executing incremental migration into core "
            f"{CORE_TABLE_NAME} table..."
        )

        merge_sql = f"""
            INSERT INTO {CORE_TABLE_NAME} (
                return_id,
                sales_line_id,
                return_date,
                quantity_returned,
                refund_amount,
                return_reason,
                return_status,
                processed_store_id,
                batch_id,
                source_file_name,
                source_row_number,
                record_hash,
                load_timestamp
            )
            SELECT
                return_id,
                sales_line_id,
                return_date,
                quantity_returned,
                refund_amount,
                return_reason,
                return_status,
                processed_store_id,
                batch_id,
                source_file_name,
                source_row_number,
                record_hash,
                NOW()
            FROM stg_returns
            ON DUPLICATE KEY UPDATE
                return_status = VALUES(return_status),
                refund_amount = VALUES(refund_amount);
        """

        cursor.execute(merge_sql)

        conn.commit()

        print("Database integration completed successfully!")

        print("==================================================")
        print("05.24 STATUS: PASS")
        print("==================================================")

    except Exception as exc:

        print(f"Execution Error: {exc}")

        if conn is not None and conn.is_connected():
            conn.rollback()
            print("Transaction rollback attempted.")

        print("05.24 STATUS: FAILED")

        raise

    finally:

        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    main()

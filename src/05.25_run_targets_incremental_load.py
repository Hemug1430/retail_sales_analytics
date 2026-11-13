
import csv
import mysql.connector
import hashlib
import os

from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


# ==================================================
# PROJECT CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

CSV_PATH = BASE_DIR / "data" / "synthetic" / "targets_master.csv"


def get_db_connection():
    """Connect to MySQL using credentials from .env."""

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
    print("05.25 - RUN TARGETS INCREMENTAL LOAD")
    print("==================================================")

    try:

        # --------------------------------------------------
        # GENERATE TARGET SOURCE CSV
        # --------------------------------------------------

        if CSV_PATH.exists():
            os.remove(CSV_PATH)

            print(
                "Cleared historical targets CSV "
                "to refresh field schemas..."
            )

        print(
            "Creating clean structured baseline "
            "targets source data stream..."
        )

        CSV_PATH.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            CSV_PATH,
            mode="w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "target_id",
                "store_id",
                "category",
                "target_month",
                "revenue_target",
                "profit_target",
                "order_target",
                "return_rate_target_pct"
            ])

            writer.writerow([
                "TGT001",
                "STORE001",
                "Electronics",
                "2026-10-01",
                "50000.00",
                "15000.00",
                "250",
                "2.50"
            ])

            writer.writerow([
                "TGT002",
                "STORE002",
                "Fashion",
                "2026-10-01",
                "35000.00",
                "12000.00",
                "180",
                "3.00"
            ])

        # --------------------------------------------------
        # DATABASE CONNECTION
        # --------------------------------------------------

        print("Connecting to database...")

        conn = get_db_connection()
        cursor = conn.cursor()

        print("Database connection: SUCCESS")

        # --------------------------------------------------
        # READ TARGETS AND PERFORM INCREMENTAL UPSERT
        # --------------------------------------------------

        print("Reading targets file and mapping parameters...")

        inserted_count = 0

        with open(
            CSV_PATH,
            mode="r",
            encoding="utf-8",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for idx, row in enumerate(reader, start=1):

                target_id = row["target_id"].strip()

                store_id = (
                    row["store_id"]
                    .strip()
                    .replace("STORE000", "STORE0")
                )

                category = row["category"].strip()

                target_month = row["target_month"].strip()

                revenue_target = float(
                    row["revenue_target"]
                )

                profit_target = (
                    float(row["profit_target"])
                    if row.get("profit_target")
                    else 0.0
                )

                order_target = int(
                    row["order_target"]
                )

                return_rate_target_pct = (
                    float(row["return_rate_target_pct"])
                    if row.get("return_rate_target_pct")
                    else 0.0
                )

                batch_id = "B_20261008_TGT"

                source_file = "targets_master.csv"

                hash_string = (
                    f"{target_id}_{store_id}_"
                    f"{category}_{target_month}"
                )

                record_hash = hashlib.sha256(
                    hash_string.encode("utf-8")
                ).hexdigest()

                upsert_sql = """
                    INSERT INTO facttargets (
                        target_id,
                        target_month,
                        store_id,
                        category,
                        revenue_target,
                        profit_target,
                        order_target,
                        return_rate_target_pct,
                        batch_id,
                        source_file_name,
                        source_row_number,
                        record_hash,
                        load_timestamp,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, NOW(), NOW(), NOW()
                    )
                    ON DUPLICATE KEY UPDATE
                        revenue_target = VALUES(revenue_target),
                        profit_target = VALUES(profit_target),
                        order_target = VALUES(order_target),
                        return_rate_target_pct =
                            VALUES(return_rate_target_pct),
                        batch_id = VALUES(batch_id),
                        source_file_name = VALUES(source_file_name),
                        source_row_number = VALUES(source_row_number),
                        record_hash = VALUES(record_hash),
                        updated_at = NOW();
                """

                params = (
                    target_id,
                    target_month,
                    store_id,
                    category,
                    revenue_target,
                    profit_target,
                    order_target,
                    return_rate_target_pct,
                    batch_id,
                    source_file,
                    idx,
                    record_hash
                )

                cursor.execute(
                    upsert_sql,
                    params
                )

                inserted_count += 1

        conn.commit()

        print(
            "Incremental targets mapping complete. "
            f"Rows Processed/Updated: {inserted_count}"
        )

        print("--------------------------------------------------")
        print("==================================================")
        print("05.25 STATUS: PASS")
        print("==================================================")

    except Exception as exc:

        print(f"Execution Error: {exc}")

        if conn is not None and conn.is_connected():
            conn.rollback()
            print("Transaction rollback attempted.")

        print("05.25 STATUS: FAILED")

        raise

    finally:

        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    main()

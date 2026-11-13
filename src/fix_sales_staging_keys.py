
import os
from pathlib import Path
from datetime import datetime

import mysql.connector
from dotenv import load_dotenv


# --------------------------------------------------
# Project configuration
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_db_connection():
    """Connect using credentials stored in the project .env file."""

    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [key for key in required if not os.getenv(key)]

    if missing:
        raise RuntimeError(
            "Missing .env settings: " + ", ".join(missing)
        )

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


# --------------------------------------------------
# Main execution
# --------------------------------------------------
def main():

    conn = None
    cursor = None

    print("Connecting to database...")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Database connection: SUCCESS")

        # 1. Standardize store keys
        print("Standardizing store_id keys in stg_sales...")

        cursor.execute("""
            UPDATE stg_sales
            SET store_id = REPLACE(store_id, 'STORE000', 'STORE0')
            WHERE store_id LIKE 'STORE%';
        """)

        print(f"Updated {cursor.rowcount} store IDs.")

        # 2. Standardize salesperson IDs
        print("Standardizing salesperson_id keys in stg_sales...")

        cursor.execute("""
            UPDATE stg_sales
            SET salesperson_id = REPLACE(salesperson_id, 'SP0', 'EMP00')
            WHERE salesperson_id LIKE 'SP0%';
        """)

        cursor.execute("""
            UPDATE stg_sales
            SET salesperson_id = REPLACE(salesperson_id, 'SP', 'EMP0')
            WHERE salesperson_id LIKE 'SP%';
        """)

        # 3. Handle missing salesperson references
        print("Cleaning up 'None' salesperson values...")

        cursor.execute("""
            UPDATE stg_sales
            SET salesperson_id = 'EMP000001'
            WHERE salesperson_id IS NULL
               OR salesperson_id = 'None'
               OR salesperson_id = '';
        """)

        print(f"Cleaned up {cursor.rowcount} null/None records.")

        conn.commit()

        # 4. Find missing salesperson IDs
        print(
            "Finding missing salesperson IDs "
            "that need dimension mapping..."
        )

        cursor.execute("""
            SELECT DISTINCT s.salesperson_id
            FROM stg_sales s
            LEFT JOIN core_salespersons c
                ON s.salesperson_id = c.salesperson_id
            WHERE c.salesperson_id IS NULL;
        """)

        missing_salespersons = [
            row[0] for row in cursor.fetchall() if row[0]
        ]

        if missing_salespersons:

            print(
                f"Found {len(missing_salespersons)} missing "
                "salesperson profiles. Seeding them now..."
            )

            insert_backfill_sql = """
                INSERT INTO core_salespersons (
                    salesperson_id,
                    salesperson_name,
                    store_id,
                    joining_date,
                    role,
                    status,
                    batch_id,
                    source_file_name,
                    source_row_number,
                    load_timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            for idx, missing_id in enumerate(
                missing_salespersons, start=1
            ):

                params = (
                    missing_id,
                    f"Backup Agent {missing_id[-3:]}",
                    "STORE001",
                    "2023-01-01",
                    "Sales Associate",
                    "Active",
                    "BATCH_BACKFILL",
                    "stg_sales_reconciliation",
                    idx,
                    datetime.now()
                )

                cursor.execute(insert_backfill_sql, params)

            conn.commit()

            print(
                f"Successfully seeded "
                f"{len(missing_salespersons)} missing profiles!"
            )

        else:
            print(
                "All salesperson transaction IDs are fully "
                "accounted for in dimensions!"
            )

        print(
            "Staging data fix and dimension alignment "
            "successfully completed!"
        )

    except Exception as exc:

        print(f"Execution Error: {exc}")

        if conn is not None:
            conn.rollback()

        raise

    finally:

        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    main()

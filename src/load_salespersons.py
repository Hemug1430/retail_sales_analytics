from pathlib import Path
import os

import mysql.connector
from dotenv import load_dotenv


# Resolve the project root and load the existing local .env file.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_db_connection():
    """Connect using credentials stored in the project-root .env file."""
    required = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Missing required .env setting(s): " + ", ".join(missing)
        )

    try:
        port = int(os.getenv("DB_PORT", "3306"))
    except ValueError as exc:
        raise RuntimeError("DB_PORT must be a valid integer.") from exc

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=port,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )

import csv
from datetime import datetime


CSV_PATH = PROJECT_ROOT / "data" / "synthetic" / "salespersons_master.csv"


def main():
    conn = None
    cursor = None

    print("Connecting to database...")
    try:
        if not CSV_PATH.is_file():
            raise FileNotFoundError(f"Salespersons CSV not found: {CSV_PATH}")

        conn = get_db_connection()
        cursor = conn.cursor()
        print("Database connection: SUCCESS")

        # WARNING: This preserves the original script's TRUNCATE behavior.
        # It removes all existing rows from core_salespersons before loading.
        print("Clearing old records from core_salespersons...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("TRUNCATE TABLE core_salespersons;")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()

        insert_sql = """
            INSERT INTO core_salespersons (
                salesperson_id, salesperson_name, store_id, joining_date,
                role, status, batch_id, source_file_name,
                source_row_number, load_timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        print("Reading CSV and loading rows...")
        with CSV_PATH.open(mode="r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for idx, row in enumerate(reader, start=1):
                raw_id = row["salesperson_id"].strip()
                numeric_part = "".join(
                    character for character in raw_id
                    if character.isdigit()
                )
                if not numeric_part:
                    raise ValueError(
                        f"Invalid salesperson_id at CSV row {idx + 1}: "
                        f"{raw_id!r}"
                    )

                # Preserve original ID mapping: SP00182 -> EMP000182
                clean_emp_id = f"EMP{int(numeric_part):06d}"

                current_role = row["role"].strip()
                if current_role == "Sales Executive":
                    current_role = "Store Supervisor"

                params = (
                    clean_emp_id,
                    row["salesperson_name"].strip(),
                    row["store_id"].strip(),
                    row["joining_date"].strip(),
                    current_role,
                    row["status"].strip(),
                    "BATCH_001",
                    "salespersons_master.csv",
                    idx,
                    datetime.now(),
                )
                cursor.execute(insert_sql, params)

        conn.commit()
        print(
            "Successfully re-loaded salesperson records with 'EMP' mapping format!"
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

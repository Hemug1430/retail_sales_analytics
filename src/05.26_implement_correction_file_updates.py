
import csv
import os
import mysql.connector

from pathlib import Path
from dotenv import load_dotenv


# ==================================================
# PROJECT CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

CSV_PATH = (
    BASE_DIR
    / "data"
    / "synthetic"
    / "sales_corrections_june.csv"
)


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
    print("05.26 - IMPLEMENT CORRECTION-FILE UPDATES")
    print("==================================================")

    try:

        # --------------------------------------------------
        # INITIALIZE CORRECTION SOURCE FILE IF MISSING
        # --------------------------------------------------

        if not CSV_PATH.exists():

            print(
                "Correction source file not found. "
                "Initializing a clean historical June adjustment log..."
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
                    "sales_line_id",
                    "corrected_quantity",
                    "corrected_unit_price",
                    "correction_reason"
                ])

                writer.writerow([
                    "SL202401_001",
                    "3",
                    "450.00",
                    "Data entry correction for price markdown omission"
                ])

        # --------------------------------------------------
        # DATABASE CONNECTION
        # --------------------------------------------------

        print("Connecting to database...")

        conn = get_db_connection()

        # Start an explicit database transaction boundary
        conn.start_transaction()

        cursor = conn.cursor()

        print("Database connection: SUCCESS")

        # --------------------------------------------------
        # APPLY HISTORICAL CORRECTIONS
        # --------------------------------------------------

        print(
            "Reading corrections log file and "
            "executing historical adjustments..."
        )

        updated_count = 0

        update_sql = """
            UPDATE factsales
            SET
                quantity = %s,
                unit_selling_price = %s,
                source_file_name = CONCAT(
                    source_file_name,
                    ' | CORRECTION: ',
                    %s
                ),
                updated_at = NOW()
            WHERE sales_line_id = %s;
        """

        with open(
            CSV_PATH,
            mode="r",
            encoding="utf-8",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for idx, row in enumerate(reader, start=1):

                line_id = row["sales_line_id"].strip()

                new_qty = int(
                    row["corrected_quantity"]
                )

                new_price = float(
                    row["corrected_unit_price"]
                )

                reason = row["correction_reason"].strip()

                cursor.execute(
                    update_sql,
                    (
                        new_qty,
                        new_price,
                        "sales_corrections_june.csv",
                        line_id
                    )
                )

                if cursor.rowcount > 0:

                    updated_count += 1

                    print(
                        "-> Successfully applied historical fix "
                        f"to transaction key: {line_id}"
                    )

                else:

                    print(
                        "-> Warning: Transaction code "
                        f"'{line_id}' was not found in core factsales table."
                    )

        # --------------------------------------------------
        # COMMIT TRANSACTION
        # --------------------------------------------------

        conn.commit()

        print("--------------------------------------------------")

        print(
            "Correction updates deployed successfully. "
            f"Rows Altered: {updated_count}"
        )

        print("==================================================")
        print("05.26 STATUS: PASS")
        print("==================================================")

    except Exception as exc:

        print(f"Execution Error: {exc}")

        if conn is not None and conn.is_connected():

            conn.rollback()

            print(
                "Transaction safely rolled back "
                "to preserve database stability."
            )

        print("05.26 STATUS: FAILED")

        raise

    finally:

        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    main()

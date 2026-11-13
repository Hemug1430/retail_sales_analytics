
import os
import sys
import mysql.connector
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

print("=" * 60)
print("05.27 - IMPLEMENT SCD HISTORY UPDATES")
print("=" * 60)


def get_database_connection():
    """Connect using credentials stored in the local .env file."""

    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [key for key in required if not os.getenv(key)]

    if missing:
        raise ValueError(
            "Missing required .env settings: " + ", ".join(missing)
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
        print("Connecting to database...")
        conn = get_database_connection()
        cursor = conn.cursor()
        print("Database connection: SUCCESS")

        target_dim = "core_customers"

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = %s
            """,
            (target_dim,)
        )

        if cursor.fetchone()[0] == 0:
            raise RuntimeError(
                f"Required table '{target_dim}' was not found."
            )

        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = %s
            ORDER BY ordinal_position
            """,
            (target_dim,)
        )

        columns = {row[0].lower() for row in cursor.fetchall()}

        print(f"Auditing table: {target_dim}")
        print("Columns detected:", ", ".join(sorted(columns)))

        scd_candidates = {
            "is_current",
            "valid_from",
            "valid_to",
            "start_date",
            "end_date"
        }

        detected = columns.intersection(scd_candidates)

        print("-" * 60)

        if detected:
            print("Potential SCD tracking columns detected:")
            for column in sorted(detected):
                print(f" - {column}")

            print(
                "SCD structure requires further validation. "
                "Column presence alone does not prove SCD Type 2."
            )
        else:
            print("SCD Type 2 tracking columns were not detected.")

        print("-" * 60)
        print("No customer records were modified.")
        print("SCD Type 2 implementation is NOT yet verified.")
        print("05.27 STATUS: AUDIT ONLY")

    except Exception as exc:
        print(f"Execution Error: {exc}")
        print("05.27 STATUS: FAILED")
        sys.exit_code = 1

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main()

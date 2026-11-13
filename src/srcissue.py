
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


# Load project-root environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_db_connection():
    """Connect to MySQL using credentials from .env."""

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


def main():
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT CHECK_CLAUSE
            FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS
            WHERE CONSTRAINT_NAME = 'chk_fact_targets_category';
        """

        cursor.execute(query)
        result = cursor.fetchone()

        print("\n--- ALLOWED CATEGORY CONSTRAINT CLAUSE ---")
        print(result if result else "Constraint definition not found.")

        print("\nDatabase connection and metadata query: SUCCESS")

    except Exception as exc:
        print(f"Error: {exc}")
        raise

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    main()

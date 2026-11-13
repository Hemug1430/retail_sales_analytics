
import sys
from pathlib import Path
from datetime import date, timedelta

import mysql.connector

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import DB_CONFIG

START_DATE = date(2024, 1, 1)
END_DATE = date(2027, 12, 31)

EXPECTED_COLUMNS = {
    "date_key", "date", "day", "day_name",
    "weekday_number", "week", "week_start_date",
    "month_number", "month_name", "quarter",
    "year_quarter", "year", "year_month",
    "weekend_flag", "day_type"
}


def build_date_record(current_date):
    iso_calendar = current_date.isocalendar()

    weekday_number = current_date.isoweekday()
    week_start_date = current_date - timedelta(
        days=weekday_number - 1
    )

    quarter_number = (current_date.month - 1) // 3 + 1
    quarter = f"Q{quarter_number}"

    is_weekend = weekday_number in (6, 7)

    return (
        int(current_date.strftime("%Y%m%d")),
        current_date,
        current_date.day,
        current_date.strftime("%A"),
        weekday_number,
        iso_calendar.week,
        week_start_date,
        current_date.month,
        current_date.strftime("%B"),
        quarter,
        f"{current_date.year}-{quarter}",
        current_date.year,
        current_date.strftime("%Y-%m"),
        "Yes" if is_weekend else "No",
        "Weekend" if is_weekend else "Weekday"
    )


def main():
    connection = None
    cursor = None

    try:
        print("=" * 60)
        print("06.01 - CREATE DATE DIMENSION DATA")
        print("=" * 60)

        print("Connecting to database...")
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)

        print("Database connection: SUCCESS")

        # Verify existing table
        cursor.execute("SHOW TABLES LIKE 'dim_date'")

        if cursor.fetchone() is None:
            raise RuntimeError(
                "dim_date does not exist. "
                "Automatic table creation is not permitted."
            )

        # Verify existing schema
        cursor.execute("SHOW COLUMNS FROM dim_date")

        actual_columns = {
            row["Field"] for row in cursor.fetchall()
        }

        if actual_columns != EXPECTED_COLUMNS:
            raise RuntimeError(
                f"Schema mismatch. "
                f"Missing: {EXPECTED_COLUMNS - actual_columns}; "
                f"Unexpected: {actual_columns - EXPECTED_COLUMNS}"
            )

        print("Existing dim_date schema: VERIFIED")

        # Check existing data
        cursor.execute("""
            SELECT
                COUNT(*) AS total_rows,
                MIN(`date`) AS first_date,
                MAX(`date`) AS last_date
            FROM `dim_date`
        """)

        existing = cursor.fetchone()

        print(f"Existing rows: {existing['total_rows']}")
        print(f"First date: {existing['first_date']}")
        print(f"Last date: {existing['last_date']}")

        # Generate calendar records
        records = []
        current_date = START_DATE

        while current_date <= END_DATE:
            records.append(build_date_record(current_date))
            current_date += timedelta(days=1)

        print(f"Expected calendar dates: {len(records)}")

        # Backticks protect identifiers such as year_month.
        insert_sql = """
            INSERT IGNORE INTO `dim_date` (
                `date_key`,
                `date`,
                `day`,
                `day_name`,
                `weekday_number`,
                `week`,
                `week_start_date`,
                `month_number`,
                `month_name`,
                `quarter`,
                `year_quarter`,
                `year`,
                `year_month`,
                `weekend_flag`,
                `day_type`
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
        """

        cursor.executemany(insert_sql, records)
        inserted_count = cursor.rowcount

        connection.commit()

        print(f"New dates inserted: {inserted_count}")

        # Verify calendar coverage
        cursor.execute("""
            SELECT
                COUNT(*) AS total_rows,
                COUNT(DISTINCT `date`) AS distinct_dates,
                MIN(`date`) AS first_date,
                MAX(`date`) AS last_date,
                COUNT(*) - COUNT(DISTINCT `date`)
                    AS duplicate_dates
            FROM `dim_date`
            WHERE `date` BETWEEN %s AND %s
        """, (START_DATE, END_DATE))

        result = cursor.fetchone()

        expected_count = (END_DATE - START_DATE).days + 1

        print("\nDATE DIMENSION VERIFICATION")
        print("-" * 45)
        print(f"Expected dates       : {expected_count}")
        print(f"Actual rows          : {result['total_rows']}")
        print(f"Distinct dates       : {result['distinct_dates']}")
        print(f"First date           : {result['first_date']}")
        print(f"Last date            : {result['last_date']}")
        print(f"Duplicate dates      : {result['duplicate_dates']}")

        if (
            result["total_rows"] != expected_count
            or result["distinct_dates"] != expected_count
            or result["duplicate_dates"] != 0
        ):
            raise RuntimeError("Calendar coverage validation failed.")

        # Validate all calendar attributes
        cursor.execute("""
            SELECT *
            FROM `dim_date`
            WHERE `date` BETWEEN %s AND %s
            ORDER BY `date`
        """, (START_DATE, END_DATE))

        actual_records = cursor.fetchall()

        mismatch_count = 0
        check_date = START_DATE

        for actual in actual_records:
            expected = build_date_record(check_date)

            actual_tuple = (
                actual["date_key"],
                actual["date"],
                actual["day"],
                actual["day_name"],
                actual["weekday_number"],
                actual["week"],
                actual["week_start_date"],
                actual["month_number"],
                actual["month_name"],
                actual["quarter"],
                actual["year_quarter"],
                actual["year"],
                actual["year_month"],
                actual["weekend_flag"],
                actual["day_type"]
            )

            if actual_tuple != expected:
                mismatch_count += 1

            check_date += timedelta(days=1)

        print(f"Attribute mismatches : {mismatch_count}")

        if mismatch_count != 0:
            raise RuntimeError(
                "Calendar attribute validation failed."
            )

        print("\n06.01 STATUS: PASS")
        print("=" * 60)

    except Exception as error:
        if connection is not None and connection.is_connected():
            connection.rollback()

        print(f"\nExecution Error: {error}")
        print("06.01 STATUS: FAILED")
        raise

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main()

"""
05.18 - Run staging-to-core customer merge

Purpose
-------
Merge validated customer rows from stg_customers into core_customers.

Rules
-----
1. New customer_id -> INSERT as record_version = 1
2. Existing same record_hash -> UNCHANGED
3. Existing different record_hash -> REVIEW
   Do not silently overwrite trusted history.
4. Invalid trusted-table values -> FAILED
5. Transaction protected
6. Idempotent rerun
7. Produce audit CSV and log

Important
---------
- Database credentials are read from the project .env file.
- Password is never hard-coded.
- SCD history changes are NOT implemented here.
- SCD history implementation belongs to tracker step 05.27.
"""

from __future__ import annotations

import csv
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import mysql.connector


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

LOG_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "data" / "outputs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "05.18_run_staging_to_core_customer_merge.log"
AUDIT_FILE = OUTPUT_DIR / "05.18_customer_merge_audit.csv"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | 05.18 | %(message)s",
)

logger = logging.getLogger("05.18_customer_merge")


# ============================================================
# LOAD .ENV
# ============================================================

def load_env_file(env_path: Path) -> dict[str, str]:
    """
    Read simple KEY=VALUE entries from the project .env file.
    """

    values: dict[str, str] = {}

    if not env_path.exists():
        return values

    with env_path.open("r", encoding="utf-8") as file:

        for raw_line in file:

            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            key = key.strip()
            value = value.strip()

            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in {"'", '"'}
            ):
                value = value[1:-1]

            values[key] = value

    return values


ENV_VALUES = load_env_file(BASE_DIR / ".env")


def get_config_value(
    *names: str,
    default: str | None = None,
) -> str | None:
    """
    Get configuration from environment variables first,
    then project .env.
    """

    for name in names:

        value = os.getenv(name)

        if value is not None and value != "":
            return value

        value = ENV_VALUES.get(name)

        if value is not None and value != "":
            return value

    return default


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_HOST = get_config_value(
    "DB_HOST",
    "MYSQL_HOST",
    default="localhost",
)

DB_PORT_RAW = get_config_value(
    "DB_PORT",
    "MYSQL_PORT",
    default="3306",
)

DB_NAME = get_config_value(
    "DB_NAME",
    "DB_DATABASE",
    "MYSQL_DATABASE",
    default="retail_sales_db",
)

DB_USER = get_config_value(
    "DB_USER",
    "MYSQL_USER",
    default="root",
)

DB_PASSWORD = get_config_value(
    "DB_PASSWORD",
    "MYSQL_PASSWORD",
    default=None,
)


if DB_PASSWORD is None:

    print(
        "ERROR: DB_PASSWORD was not found in the project .env file."
    )

    logger.error(
        "DB_PASSWORD was not found in the project .env file."
    )

    sys.exit(1)


try:

    DB_PORT = int(DB_PORT_RAW or "3306")

except ValueError:

    print(
        f"ERROR: Invalid database port: {DB_PORT_RAW}"
    )

    logger.error(
        "Invalid database port: %s",
        DB_PORT_RAW,
    )

    sys.exit(1)


# ============================================================
# AUDIT CSV
# ============================================================

AUDIT_COLUMNS = [
    "run_timestamp",
    "customer_id",
    "source_file_name",
    "source_row_number",
    "batch_id",
    "action",
    "reason",
    "old_record_hash",
    "new_record_hash",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalize_value(value):
    """
    Remove surrounding whitespace from strings.
    Preserve None and non-string values.
    """

    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()

        if value == "":
            return None

        return value

    return value


def hashes_equal(old_hash, new_hash) -> bool:
    """
    Compare record hashes safely.
    """

    old_hash = normalize_value(old_hash)
    new_hash = normalize_value(new_hash)

    if old_hash is None and new_hash is None:
        return True

    if old_hash is None or new_hash is None:
        return False

    return str(old_hash).lower() == str(new_hash).lower()


def write_audit(audit_rows: list[dict]) -> None:
    """
    Write the 05.18 audit CSV.
    """

    with AUDIT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=AUDIT_COLUMNS,
        )

        writer.writeheader()
        writer.writerows(audit_rows)


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    run_timestamp = datetime.now()

    connection = None
    cursor = None

    audit_rows: list[dict] = []

    total = 0
    inserted = 0
    unchanged = 0
    review = 0
    failed = 0

    print()
    print("=" * 70)
    print("05.18 - RUN STAGING-TO-CORE CUSTOMER MERGE")
    print("=" * 70)
    print(f"Database : {DB_NAME}")
    print("Source   : stg_customers")
    print("Target   : core_customers")
    print()

    logger.info("05.18 customer merge started.")

    try:

        # ====================================================
        # DATABASE CONNECTION
        # ====================================================

        connection = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )

        cursor = connection.cursor(dictionary=True)

        print("Database connection: SUCCESS")

        logger.info(
            "Database connection successful."
        )

        # ====================================================
        # READ STAGING DATA
        # ====================================================

        select_sql = """
            SELECT
                staging_id,
                customer_id,
                customer_name,
                gender,
                date_of_birth,
                city,
                state,
                region,
                registration_date,
                customer_segment,
                email,
                phone,
                postal_code,
                preferred_channel,
                status,
                batch_id,
                source_file_name,
                source_row_number,
                record_hash,
                load_timestamp
            FROM stg_customers
            ORDER BY staging_id
        """

        cursor.execute(select_sql)

        staging_rows = cursor.fetchall()

        total = len(staging_rows)

        print(
            f"Staging rows found : {total}"
        )

        logger.info(
            "Staging rows found: %s",
            total,
        )

        # ====================================================
        # CHECK DUPLICATE BUSINESS KEYS IN STAGING
        # ====================================================

        customer_counts: dict[str, int] = {}

        for row in staging_rows:

            customer_id = normalize_value(
                row.get("customer_id")
            )

            if customer_id:

                customer_counts[customer_id] = (
                    customer_counts.get(customer_id, 0) + 1
                )

        duplicate_customer_ids = {
            customer_id
            for customer_id, count in customer_counts.items()
            if count > 1
        }

        if duplicate_customer_ids:

            print(
                "Duplicate customer_id values found "
                "in stg_customers."
            )

            print(
                f"Duplicate customer IDs: "
                f"{len(duplicate_customer_ids)}"
            )

            logger.warning(
                "Duplicate customer IDs found: %s",
                len(duplicate_customer_ids),
            )

        # ====================================================
        # PRE-VALIDATE TRUSTED CUSTOMER CHANNEL
        # ====================================================
        #
        # core_customers has a CHECK constraint allowing:
        #
        #     Store
        #     Online
        #
        # preferred_channel is optional, therefore NULL is
        # also acceptable.
        #
        # We do NOT convert Mobile App / Offline into another
        # business value.
        #
        # ====================================================

        invalid_channel_count = 0

        invalid_channels: dict[str, int] = {}

        for row in staging_rows:

            preferred_channel = normalize_value(
                row.get("preferred_channel")
            )

            if preferred_channel is None:
                continue

            if preferred_channel not in {
                "Store",
                "Online",
            }:

                invalid_channel_count += 1

                invalid_channels[
                    preferred_channel
                ] = (
                    invalid_channels.get(
                        preferred_channel,
                        0,
                    )
                    + 1
                )

        if invalid_channel_count > 0:

            print()
            print(
                "Invalid preferred_channel values found:"
            )

            for channel, count in sorted(
                invalid_channels.items(),
                key=lambda item: item[1],
                reverse=True,
            ):

                print(
                    f"  {channel}: {count}"
                )

            logger.error(
                "Invalid preferred_channel values found: %s",
                invalid_channels,
            )

        # ====================================================
        # INSERT SQL
        # ====================================================
        #
        # The VALUES section contains 18 parameters.
        #
        # Database-generated fields:
        #
        # load_timestamp
        # created_at
        # updated_at
        # record_version
        # valid_from
        # valid_to
        # is_current
        #
        # ====================================================

        insert_sql = """
            INSERT INTO core_customers (
                customer_id,
                customer_name,
                gender,
                date_of_birth,
                email,
                phone,
                city,
                state,
                region,
                postal_code,
                registration_date,
                customer_segment,
                preferred_channel,
                status,
                batch_id,
                source_file_name,
                source_row_number,
                record_hash,
                load_timestamp,
                created_at,
                updated_at,
                record_version,
                valid_from,
                valid_to,
                is_current
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                NOW(),
                NOW(),
                NOW(),
                1,
                NOW(),
                NULL,
                1
            )
        """

        # ====================================================
        # PROCESS STAGING ROWS
        # ====================================================

        for row in staging_rows:

            customer_id = normalize_value(
                row.get("customer_id")
            )

            source_file_name = normalize_value(
                row.get("source_file_name")
            )

            source_row_number = row.get(
                "source_row_number"
            )

            batch_id = normalize_value(
                row.get("batch_id")
            )

            new_record_hash = normalize_value(
                row.get("record_hash")
            )

            preferred_channel = normalize_value(
                row.get("preferred_channel")
            )

            # ------------------------------------------------
            # MISSING CUSTOMER ID
            # ------------------------------------------------

            if not customer_id:

                failed += 1

                audit_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "customer_id": "",
                        "source_file_name": source_file_name,
                        "source_row_number": source_row_number,
                        "batch_id": batch_id,
                        "action": "FAILED",
                        "reason": "Missing customer_id",
                        "old_record_hash": "",
                        "new_record_hash": (
                            new_record_hash or ""
                        ),
                    }
                )

                continue

            # ------------------------------------------------
            # DUPLICATE CUSTOMER ID IN STAGING
            # ------------------------------------------------

            if customer_id in duplicate_customer_ids:

                failed += 1

                audit_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "customer_id": customer_id,
                        "source_file_name": source_file_name,
                        "source_row_number": source_row_number,
                        "batch_id": batch_id,
                        "action": "FAILED",
                        "reason": (
                            "Duplicate customer_id in "
                            "stg_customers"
                        ),
                        "old_record_hash": "",
                        "new_record_hash": (
                            new_record_hash or ""
                        ),
                    }
                )

                continue

            # ------------------------------------------------
            # INVALID PREFERRED CHANNEL
            # ------------------------------------------------

            if (
                preferred_channel is not None
                and preferred_channel not in {
                    "Store",
                    "Online",
                }
            ):

                failed += 1

                audit_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "customer_id": customer_id,
                        "source_file_name": source_file_name,
                        "source_row_number": source_row_number,
                        "batch_id": batch_id,
                        "action": "FAILED",
                        "reason": (
                            "Invalid preferred_channel: "
                            f"{preferred_channel}. "
                            "Allowed values are Store, "
                            "Online, or NULL."
                        ),
                        "old_record_hash": "",
                        "new_record_hash": (
                            new_record_hash or ""
                        ),
                    }
                )

                logger.error(
                    "Invalid preferred_channel=%s "
                    "for customer_id=%s",
                    preferred_channel,
                    customer_id,
                )

                continue

            # ------------------------------------------------
            # CHECK EXISTING CORE CUSTOMER
            # ------------------------------------------------

            existing_sql = """
                SELECT
                    customer_id,
                    record_hash,
                    record_version,
                    is_current
                FROM core_customers
                WHERE customer_id = %s
                LIMIT 1
            """

            cursor.execute(
                existing_sql,
                (customer_id,),
            )

            existing = cursor.fetchone()

            # =================================================
            # CASE 1: NEW CUSTOMER
            # =================================================

            if existing is None:

                insert_parameters = (
                    row.get("customer_id"),
                    row.get("customer_name"),
                    row.get("gender"),
                    row.get("date_of_birth"),
                    row.get("email"),
                    row.get("phone"),
                    row.get("city"),
                    row.get("state"),
                    row.get("region"),
                    row.get("postal_code"),
                    row.get("registration_date"),
                    row.get("customer_segment"),
                    preferred_channel,
                    row.get("status"),
                    row.get("batch_id"),
                    row.get("source_file_name"),
                    row.get("source_row_number"),
                    row.get("record_hash"),
                )

                cursor.execute(
                    insert_sql,
                    insert_parameters,
                )

                inserted += 1

                audit_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "customer_id": customer_id,
                        "source_file_name": source_file_name,
                        "source_row_number": source_row_number,
                        "batch_id": batch_id,
                        "action": "INSERTED",
                        "reason": "New customer_id",
                        "old_record_hash": "",
                        "new_record_hash": (
                            new_record_hash or ""
                        ),
                    }
                )

                logger.info(
                    "INSERTED customer_id=%s",
                    customer_id,
                )

                continue

            # =================================================
            # EXISTING CUSTOMER
            # =================================================

            old_record_hash = normalize_value(
                existing.get("record_hash")
            )

            # =================================================
            # CASE 2: SAME HASH -> UNCHANGED
            # =================================================

            if hashes_equal(
                old_record_hash,
                new_record_hash,
            ):

                unchanged += 1

                audit_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "customer_id": customer_id,
                        "source_file_name": source_file_name,
                        "source_row_number": source_row_number,
                        "batch_id": batch_id,
                        "action": "UNCHANGED",
                        "reason": "Same record_hash",
                        "old_record_hash": (
                            old_record_hash or ""
                        ),
                        "new_record_hash": (
                            new_record_hash or ""
                        ),
                    }
                )

                logger.info(
                    "UNCHANGED customer_id=%s",
                    customer_id,
                )

                continue

            # =================================================
            # CASE 3: DIFFERENT HASH -> REVIEW
            # =================================================
            #
            # Do NOT:
            # - overwrite the existing row
            # - close the existing history
            # - insert a new version
            #
            # Those history operations belong to 05.27.
            #
            # =================================================

            review += 1

            audit_rows.append(
                {
                    "run_timestamp": run_timestamp,
                    "customer_id": customer_id,
                    "source_file_name": source_file_name,
                    "source_row_number": source_row_number,
                    "batch_id": batch_id,
                    "action": "REVIEW",
                    "reason": (
                        "Existing customer_id has a "
                        "different record_hash; "
                        "trusted history was not overwritten"
                    ),
                    "old_record_hash": (
                        old_record_hash or ""
                    ),
                    "new_record_hash": (
                        new_record_hash or ""
                    ),
                }
            )

            logger.warning(
                "REVIEW customer_id=%s old_hash=%s "
                "new_hash=%s",
                customer_id,
                old_record_hash,
                new_record_hash,
            )

        # ====================================================
        # TRANSACTION DECISION
        # ====================================================
        #
        # If any row is invalid, do not leave a partially
        # loaded trusted table.
        #
        # The entire transaction is rolled back.
        #
        # The audit CSV is still written so the rejected
        # records can be investigated.
        #
        # ====================================================

        if failed > 0:

            connection.rollback()

            logger.error(
                "05.18 failed validation. "
                "Transaction rolled back. "
                "failed=%s",
                failed,
            )

            write_audit(audit_rows)

            print()
            print("=" * 70)
            print("05.18 STATUS: FAIL")
            print("=" * 70)
            print(
                f"Source staging rows : {total}"
            )
            print(
                f"Inserted attempted   : {inserted}"
            )
            print(
                f"Unchanged            : {unchanged}"
            )
            print(
                f"Review               : {review}"
            )
            print(
                f"Failed               : {failed}"
            )
            print()
            print(
                "Transaction was rolled back."
            )
            print(
                "No partial trusted customer load was committed."
            )
            print()
            print(
                f"Audit CSV : {AUDIT_FILE}"
            )
            print(
                f"Log file  : {LOG_FILE}"
            )
            print("=" * 70)

            sys.exit(1)

        # ====================================================
        # COMMIT
        # ====================================================

        connection.commit()

        logger.info(
            "05.18 transaction committed successfully."
        )

        # ====================================================
        # WRITE AUDIT CSV
        # ====================================================

        write_audit(audit_rows)

        # ====================================================
        # FINAL STATUS
        # ====================================================

        print()
        print("=" * 70)
        print("05.18 CUSTOMER MERGE SUMMARY")
        print("=" * 70)
        print(
            f"Source staging rows : {total}"
        )
        print(
            f"Inserted             : {inserted}"
        )
        print(
            f"Unchanged            : {unchanged}"
        )
        print(
            f"Review               : {review}"
        )
        print(
            f"Failed               : {failed}"
        )
        print()
        print(
            f"Audit CSV            : {AUDIT_FILE}"
        )
        print(
            f"Log file             : {LOG_FILE}"
        )
        print("=" * 70)
        print()
        print("05.18 STATUS: PASS")

        logger.info(
            "05.18 STATUS: PASS | inserted=%s | "
            "unchanged=%s | review=%s | failed=%s",
            inserted,
            unchanged,
            review,
            failed,
        )

    except mysql.connector.Error as exc:

        # ====================================================
        # DATABASE ERROR -> ROLLBACK
        # ====================================================

        if connection is not None:

            try:

                connection.rollback()

                logger.info(
                    "Transaction rolled back because of "
                    "database error."
                )

            except Exception as rollback_error:

                logger.error(
                    "Rollback failed: %s",
                    rollback_error,
                )

        # Write audit information collected before failure.
        try:
            write_audit(audit_rows)
        except Exception:
            pass

        logger.exception(
            "05.18 database error: %s",
            exc,
        )

        print()
        print("=" * 70)
        print("05.18 STATUS: FAIL")
        print("=" * 70)
        print("Database error:")
        print(exc)
        print()
        print("Transaction was rolled back.")
        print(
            f"Audit CSV : {AUDIT_FILE}"
        )
        print(
            f"Log file  : {LOG_FILE}"
        )
        print("=" * 70)

        sys.exit(1)

    except Exception as exc:

        # ====================================================
        # UNEXPECTED ERROR -> ROLLBACK
        # ====================================================

        if connection is not None:

            try:

                connection.rollback()

                logger.info(
                    "Transaction rolled back because of "
                    "unexpected error."
                )

            except Exception as rollback_error:

                logger.error(
                    "Rollback failed: %s",
                    rollback_error,
                )

        try:
            write_audit(audit_rows)
        except Exception:
            pass

        logger.exception(
            "05.18 unexpected error: %s",
            exc,
        )

        print()
        print("=" * 70)
        print("05.18 STATUS: FAIL")
        print("=" * 70)
        print("Unexpected error:")
        print(exc)
        print()
        print("Transaction was rolled back.")
        print(
            f"Audit CSV : {AUDIT_FILE}"
        )
        print(
            f"Log file  : {LOG_FILE}"
        )
        print("=" * 70)

        sys.exit(1)

    finally:

        if cursor is not None:

            try:
                cursor.close()
            except Exception:
                pass

        if connection is not None:

            try:
                connection.close()
            except Exception:
                pass

        logger.info(
            "05.18 database resources closed."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
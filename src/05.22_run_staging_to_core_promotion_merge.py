"""
05.22 - Run staging-to-core promotion merge

Requirement
-----------
Insert/update promotion records using the documented business key logic.

Documented business key
-----------------------
promotion_id

Source
------
stg_promotions

Target
------
core_promotions

Approved promotion fields
-------------------------
promotion_id
promotion_name
start_date
end_date
discount_pct
applicable_category
applicable_channel
minimum_order_value
status
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

LOG_FILE = (
    LOG_DIR
    / "05.22_run_staging_to_core_promotion_merge.log"
)

AUDIT_FILE = (
    OUTPUT_DIR
    / "05.22_promotion_merge_audit.csv"
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "05.22 | "
        "%(message)s"
    ),
)

logger = logging.getLogger("05.22_promotion_merge")


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

    with env_path.open(
        "r",
        encoding="utf-8",
    ) as file:

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


ENV_VALUES = load_env_file(
    BASE_DIR / ".env"
)


def get_config_value(
    *names: str,
    default: str | None = None,
) -> str | None:
    """
    Read configuration from environment variables first,
    then from project .env.
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
        "ERROR: DB_PASSWORD was not found "
        "in the project .env file."
    )

    logger.error(
        "DB_PASSWORD was not found in the project .env file."
    )

    sys.exit(1)


try:

    DB_PORT = int(
        DB_PORT_RAW or "3306"
    )

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
# APPROVED BUSINESS COLUMNS
# ============================================================

PROMOTION_COLUMNS = [
    "promotion_id",
    "promotion_name",
    "start_date",
    "end_date",
    "discount_pct",
    "applicable_category",
    "applicable_channel",
    "minimum_order_value",
    "status",
]


# ============================================================
# AUDIT COLUMNS
# ============================================================

AUDIT_COLUMNS = [
    "run_timestamp",
    "promotion_id",
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

    if value is None:
        return None

    if isinstance(value, str):

        value = value.strip()

        if value == "":
            return None

        return value

    return value


def hashes_equal(
    old_hash,
    new_hash,
) -> bool:

    old_hash = normalize_value(
        old_hash
    )

    new_hash = normalize_value(
        new_hash
    )

    if old_hash is None and new_hash is None:
        return True

    if old_hash is None or new_hash is None:
        return False

    return (
        str(old_hash).lower()
        == str(new_hash).lower()
    )


def write_audit(
    audit_rows: list[dict],
) -> None:

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

        writer.writerows(
            audit_rows
        )


def values_equal(
    old_value,
    new_value,
) -> bool:

    old_value = normalize_value(
        old_value
    )

    new_value = normalize_value(
        new_value
    )

    if old_value is None and new_value is None:
        return True

    if old_value is None or new_value is None:
        return False

    return str(old_value) == str(new_value)


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
    updated = 0
    unchanged = 0
    failed = 0

    print()
    print("=" * 70)
    print(
        "05.22 - RUN STAGING-TO-CORE PROMOTION MERGE"
    )
    print("=" * 70)

    print(
        f"Database : {DB_NAME}"
    )

    print(
        "Source   : stg_promotions"
    )

    print(
        "Target   : core_promotions"
    )

    print()

    logger.info(
        "05.22 promotion merge started."
    )

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

        cursor = connection.cursor(
            dictionary=True
        )

        print(
            "Database connection: SUCCESS"
        )

        logger.info(
            "Database connection successful."
        )


        # ====================================================
        # TARGET STRUCTURE CHECK
        # ====================================================

        cursor.execute(
            "SHOW COLUMNS FROM core_promotions"
        )

        target_columns = {
            row["Field"]
            for row in cursor.fetchall()
        }

        required_target_columns = set(
            PROMOTION_COLUMNS
        )

        missing_target_columns = (
            required_target_columns
            - target_columns
        )

        if missing_target_columns:

            raise RuntimeError(
                "Missing required columns in "
                "core_promotions: "
                + ", ".join(
                    sorted(
                        missing_target_columns
                    )
                )
            )

        print(
            "Target structure check: SUCCESS"
        )

        logger.info(
            "Target structure check successful."
        )


        # ====================================================
        # READ STAGING DATA
        # ====================================================

        select_sql = """
            SELECT
                staging_id,
                promotion_id,
                promotion_name,
                start_date,
                end_date,
                discount_pct,
                applicable_category,
                applicable_channel,
                minimum_order_value,
                status,
                source_file_name,
                source_row_number,
                batch_id,
                record_hash
            FROM stg_promotions
            ORDER BY staging_id
        """

        cursor.execute(
            select_sql
        )

        staging_rows = cursor.fetchall()

        total = len(
            staging_rows
        )

        print(
            f"Staging rows found : {total:,}"
        )

        logger.info(
            "Staging rows found: %s",
            total,
        )


        # ====================================================
        # CHECK DUPLICATE BUSINESS KEYS
        # ====================================================

        promotion_counts: dict[str, int] = {}

        for row in staging_rows:

            promotion_id = normalize_value(
                row.get("promotion_id")
            )

            if promotion_id:

                promotion_counts[
                    promotion_id
                ] = (
                    promotion_counts.get(
                        promotion_id,
                        0,
                    )
                    + 1
                )

        duplicate_promotion_ids = {
            promotion_id
            for promotion_id, count
            in promotion_counts.items()
            if count > 1
        }

        if duplicate_promotion_ids:

            raise RuntimeError(
                "Duplicate promotion_id values "
                "found in stg_promotions: "
                + ", ".join(
                    sorted(
                        duplicate_promotion_ids
                    )
                )
            )


        # ====================================================
        # CLOSE READ TRANSACTION
        # ====================================================
        #
        # MySQL Connector automatically opens a transaction
        # for the preceding SELECT statements.
        #
        # Commit here so that the explicit merge transaction
        # below does not attempt to start while another
        # transaction is already active.
        # ====================================================

        connection.commit()


        # ====================================================
        # START MERGE TRANSACTION
        # ====================================================

        connection.start_transaction()


        # ====================================================
        # PROCESS EACH PROMOTION
        # ====================================================

        for row in staging_rows:

            promotion_id = normalize_value(
                row.get("promotion_id")
            )

            source_file_name = normalize_value(
                row.get("source_file_name")
            )

            source_row_number = normalize_value(
                row.get("source_row_number")
            )

            batch_id = normalize_value(
                row.get("batch_id")
            )

            new_record_hash = normalize_value(
                row.get("record_hash")
            )

            audit_base = {
                "run_timestamp": run_timestamp,
                "promotion_id": promotion_id,
                "source_file_name": source_file_name,
                "source_row_number": source_row_number,
                "batch_id": batch_id,
                "old_record_hash": "",
                "new_record_hash": new_record_hash,
            }


            # ------------------------------------------------
            # BUSINESS KEY VALIDATION
            # ------------------------------------------------

            if not promotion_id:

                failed += 1

                audit_rows.append({
                    **audit_base,
                    "action": "FAILED",
                    "reason": (
                        "Blank promotion_id "
                        "business key"
                    ),
                })

                continue


            # ------------------------------------------------
            # LOOK UP EXISTING CORE RECORD
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT
                    promotion_id,
                    promotion_name,
                    start_date,
                    end_date,
                    discount_pct,
                    applicable_category,
                    applicable_channel,
                    minimum_order_value,
                    status,
                    record_hash
                FROM core_promotions
                WHERE promotion_id = %s
                LIMIT 1
                """,
                (promotion_id,),
            )

            existing = cursor.fetchone()


            # ------------------------------------------------
            # NEW PROMOTION
            # ------------------------------------------------

            if existing is None:

                insert_sql = """
                    INSERT INTO core_promotions (
                        promotion_id,
                        promotion_name,
                        start_date,
                        end_date,
                        discount_pct,
                        applicable_category,
                        applicable_channel,
                        minimum_order_value,
                        status,
                        record_hash
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                """

                cursor.execute(
                    insert_sql,
                    (
                        promotion_id,
                        row.get(
                            "promotion_name"
                        ),
                        row.get(
                            "start_date"
                        ),
                        row.get(
                            "end_date"
                        ),
                        row.get(
                            "discount_pct"
                        ),
                        row.get(
                            "applicable_category"
                        ),
                        row.get(
                            "applicable_channel"
                        ),
                        row.get(
                            "minimum_order_value"
                        ),
                        row.get(
                            "status"
                        ),
                        new_record_hash,
                    ),
                )

                inserted += 1

                audit_rows.append({
                    **audit_base,
                    "action": "INSERTED",
                    "reason": (
                        "New promotion_id "
                        "business key"
                    ),
                })

                continue


            # ------------------------------------------------
            # EXISTING PROMOTION
            # ------------------------------------------------

            old_record_hash = normalize_value(
                existing.get("record_hash")
            )

            audit_base[
                "old_record_hash"
            ] = old_record_hash or ""


            # ------------------------------------------------
            # SAME HASH -> UNCHANGED
            # ------------------------------------------------

            if hashes_equal(
                old_record_hash,
                new_record_hash,
            ):

                unchanged += 1

                audit_rows.append({
                    **audit_base,
                    "action": "UNCHANGED",
                    "reason": (
                        "Existing promotion has "
                        "same record_hash"
                    ),
                })

                continue


            # ------------------------------------------------
            # DIFFERENT CONTENT -> UPDATE
            # ------------------------------------------------

            update_needed = False

            for column in PROMOTION_COLUMNS:

                if column == "promotion_id":
                    continue

                if not values_equal(
                    existing.get(column),
                    row.get(column),
                ):

                    update_needed = True
                    break

            if not update_needed:

                unchanged += 1

                audit_rows.append({
                    **audit_base,
                    "action": "UNCHANGED",
                    "reason": (
                        "No business-field "
                        "changes detected"
                    ),
                })

                continue


            update_sql = """
                UPDATE core_promotions
                SET
                    promotion_name = %s,
                    start_date = %s,
                    end_date = %s,
                    discount_pct = %s,
                    applicable_category = %s,
                    applicable_channel = %s,
                    minimum_order_value = %s,
                    status = %s,
                    record_hash = %s
                WHERE promotion_id = %s
            """

            cursor.execute(
                update_sql,
                (
                    row.get(
                        "promotion_name"
                    ),
                    row.get(
                        "start_date"
                    ),
                    row.get(
                        "end_date"
                    ),
                    row.get(
                        "discount_pct"
                    ),
                    row.get(
                        "applicable_category"
                    ),
                    row.get(
                        "applicable_channel"
                    ),
                    row.get(
                        "minimum_order_value"
                    ),
                    row.get(
                        "status"
                    ),
                    new_record_hash,
                    promotion_id,
                ),
            )

            updated += 1

            audit_rows.append({
                **audit_base,
                "action": "UPDATED",
                "reason": (
                    "Existing promotion_id "
                    "with changed business attributes"
                ),
            })


        # ====================================================
        # COMMIT
        # ====================================================

        connection.commit()

        write_audit(
            audit_rows
        )

        print()
        print("=" * 70)
        print(
            "05.22 STATUS: PASS"
        )
        print("=" * 70)

        print(
            f"Source staging rows : {total:,}"
        )

        print(
            f"Inserted            : {inserted:,}"
        )

        print(
            f"Updated             : {updated:,}"
        )

        print(
            f"Unchanged           : {unchanged:,}"
        )

        print(
            f"Failed              : {failed:,}"
        )

        print()

        print(
            "Transaction committed."
        )

        print(
            f"Audit file: {AUDIT_FILE}"
        )

        print(
            f"Log file  : {LOG_FILE}"
        )

        print(
            "=" * 70
        )

        logger.info(
            "05.22 promotion merge completed. "
            "Source=%s Inserted=%s Updated=%s "
            "Unchanged=%s Failed=%s",
            total,
            inserted,
            updated,
            unchanged,
            failed,
        )


    except Exception as exc:

        if connection is not None:

            try:
                connection.rollback()

            except Exception:
                pass

        print()
        print("=" * 70)
        print(
            "05.22 STATUS: FAILED"
        )
        print("=" * 70)

        print(
            f"Error: {exc}"
        )

        print(
            "Transaction rolled back."
        )

        print(
            f"Log file: {LOG_FILE}"
        )

        print(
            "=" * 70
        )

        logger.exception(
            "05.22 promotion merge failed."
        )

        sys.exit(1)


    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
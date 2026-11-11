"""
Retail Sales Analytics
Tracker 05.21 - Run Staging-to-Core Salesperson Merge

Requirement
-----------
Insert/update salesperson master records and relationship changes.

Source:
    stg_salespersons

Target:
    core_salespersons

Approved salesperson business columns:
    salesperson_id
    salesperson_name
    store_id
    joining_date
    role
    status

Relationship rule:
    salesperson.store_id must reference an existing store.

Behavior:
    1. New salesperson_id -> INSERT
    2. Existing salesperson_id with same business values -> UNCHANGED
    3. Existing salesperson_id with changed business values ->
       UPDATE current master record
    4. Store relationship changes are treated as UPDATE
    5. Missing store relationship -> FAILED
    6. Duplicate salesperson_id in staging -> FAILED
    7. Transaction protected
    8. Idempotent rerun
    9. Produce audit CSV and log
    10. SCD history is NOT implemented here.
        SCD history belongs to tracker step 05.27.
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
# 01. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

LOG_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "data" / "outputs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = (
    LOG_DIR /
    "05.21_run_staging_to_core_salesperson_merge.log"
)

AUDIT_FILE = (
    OUTPUT_DIR /
    "05.21_salesperson_merge_audit.csv"
)


# ============================================================
# 02. LOGGING
# ============================================================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | "
        "05.21 | %(message)s"
    ),
)

logger = logging.getLogger("05.21_salesperson_merge")


# ============================================================
# 03. LOAD PROJECT .ENV
# ============================================================

def load_env_file(env_path: Path) -> dict[str, str]:
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

    for name in names:

        value = os.getenv(name)

        if value is not None and value != "":
            return value

        value = ENV_VALUES.get(name)

        if value is not None and value != "":
            return value

    return default


# ============================================================
# 04. DATABASE CONFIGURATION
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
# 05. APPROVED BUSINESS COLUMNS
# ============================================================

BUSINESS_COLUMNS = [
    "salesperson_id",
    "salesperson_name",
    "store_id",
    "joining_date",
    "role",
    "status",
]


# ============================================================
# 06. AUDIT COLUMNS
# ============================================================

AUDIT_COLUMNS = [
    "run_timestamp",
    "salesperson_id",
    "source_file_name",
    "source_row_number",
    "batch_id",
    "action",
    "reason",
    "old_record_hash",
    "new_record_hash",
    "old_store_id",
    "new_store_id",
]


# ============================================================
# 07. HELPERS
# ============================================================

def normalize_value(value):
    """
    Normalize values for safe comparison.
    """

    if value is None:
        return None

    if isinstance(value, str):

        value = value.strip()

        if value == "":
            return None

        return value

    return value


def values_equal(value_a, value_b) -> bool:

    value_a = normalize_value(value_a)
    value_b = normalize_value(value_b)

    if value_a is None and value_b is None:
        return True

    if value_a is None or value_b is None:
        return False

    return str(value_a).strip() == str(value_b).strip()


def rows_have_same_business_values(
    staging_row,
    core_row,
) -> bool:

    for column in BUSINESS_COLUMNS:

        if not values_equal(
            staging_row.get(column),
            core_row.get(column),
        ):
            return False

    return True


def write_audit(audit_rows: list[dict]) -> None:

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
# 08. MAIN
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
        "05.21 - RUN STAGING-TO-CORE SALESPERSON MERGE"
    )
    print("=" * 70)

    print(f"Database : {DB_NAME}")
    print("Source   : stg_salespersons")
    print("Target   : core_salespersons")
    print()

    logger.info(
        "05.21 salesperson merge started."
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

        print("Database connection: SUCCESS")

        logger.info(
            "Database connection successful."
        )


        # ====================================================
        # TARGET STRUCTURE CHECK
        # ====================================================

        cursor.execute(
            """
            SELECT
                COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'core_salespersons'
            ORDER BY ORDINAL_POSITION
            """,
            (DB_NAME,),
        )

        target_columns = {
            row["COLUMN_NAME"]
            for row in cursor.fetchall()
        }

        required_target_columns = set(
            BUSINESS_COLUMNS
        )

        missing_target_columns = (
            required_target_columns
            - target_columns
        )

        if missing_target_columns:

            raise RuntimeError(
                "Missing required columns in "
                f"core_salespersons: "
                f"{sorted(missing_target_columns)}"
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

        cursor.execute(
            """
            SELECT
                staging_id,
                salesperson_id,
                salesperson_name,
                store_id,
                joining_date,
                role,
                status,
                batch_id,
                source_file_name,
                source_row_number,
                record_hash,
                load_timestamp
            FROM stg_salespersons
            ORDER BY staging_id
            """
        )

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
        # CHECK DUPLICATE BUSINESS KEYS
        # ====================================================

        salesperson_counts: dict[str, int] = {}

        for row in staging_rows:

            salesperson_id = normalize_value(
                row.get("salesperson_id")
            )

            if salesperson_id:

                salesperson_counts[
                    salesperson_id
                ] = (
                    salesperson_counts.get(
                        salesperson_id,
                        0,
                    )
                    + 1
                )

        duplicate_ids = {
            salesperson_id
            for salesperson_id, count
            in salesperson_counts.items()
            if count > 1
        }

        if duplicate_ids:

            raise RuntimeError(
                "Duplicate salesperson_id values "
                "found in stg_salespersons: "
                f"{sorted(duplicate_ids)[:20]}"
            )


        # ====================================================
        # READ EXISTING CORE RECORDS
        # ====================================================

        cursor.execute(
            """
            SELECT
                salesperson_id,
                salesperson_name,
                store_id,
                joining_date,
                role,
                status,
                record_hash
            FROM core_salespersons
            """
        )

        core_rows = cursor.fetchall()

        core_by_id = {
            str(
                normalize_value(
                    row["salesperson_id"]
                )
            ): row
            for row in core_rows
            if normalize_value(
                row["salesperson_id"]
            ) is not None
        }


        # ====================================================
        # PROCESS STAGING ROWS
        # ====================================================

        for row in staging_rows:

            salesperson_id = normalize_value(
                row.get("salesperson_id")
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

            new_hash = normalize_value(
                row.get("record_hash")
            )

            store_id = normalize_value(
                row.get("store_id")
            )


            # ------------------------------------------------
            # REQUIRED SALESPERSON ID
            # ------------------------------------------------

            if not salesperson_id:

                failed += 1

                audit_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "salesperson_id": "",
                        "source_file_name":
                            source_file_name,
                        "source_row_number":
                            source_row_number,
                        "batch_id": batch_id,
                        "action": "FAILED",
                        "reason":
                            "Missing salesperson_id",
                        "old_record_hash": "",
                        "new_record_hash": new_hash,
                        "old_store_id": "",
                        "new_store_id": store_id,
                    }
                )

                continue


            # ------------------------------------------------
            # REQUIRED STORE RELATIONSHIP
            # ------------------------------------------------

            if not store_id:

                failed += 1

                audit_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "salesperson_id":
                            salesperson_id,
                        "source_file_name":
                            source_file_name,
                        "source_row_number":
                            source_row_number,
                        "batch_id": batch_id,
                        "action": "FAILED",
                        "reason":
                            "Missing required store_id "
                            "relationship",
                        "old_record_hash": "",
                        "new_record_hash": new_hash,
                        "old_store_id": "",
                        "new_store_id": "",
                    }
                )

                continue


            # ------------------------------------------------
            # VERIFY STORE EXISTS
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT
                    store_id
                FROM core_stores
                WHERE store_id = %s
                LIMIT 1
                """,
                (store_id,),
            )

            store_exists = cursor.fetchone()

            if store_exists is None:

                failed += 1

                audit_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "salesperson_id":
                            salesperson_id,
                        "source_file_name":
                            source_file_name,
                        "source_row_number":
                            source_row_number,
                        "batch_id": batch_id,
                        "action": "FAILED",
                        "reason":
                            "Referenced store_id does "
                            "not exist in core_stores",
                        "old_record_hash": "",
                        "new_record_hash": new_hash,
                        "old_store_id": "",
                        "new_store_id": store_id,
                    }
                )

                continue


            # ------------------------------------------------
            # FIND EXISTING SALESPERSON
            # ------------------------------------------------

            existing = core_by_id.get(
                str(salesperson_id)
            )


            # =================================================
            # INSERT NEW SALESPERSON
            # =================================================

            if existing is None:

                insert_columns = [
                    "salesperson_id",
                    "salesperson_name",
                    "store_id",
                    "joining_date",
                    "role",
                    "status",
                ]

                insert_values = [
                    row.get(column)
                    for column in insert_columns
                ]

                if "record_hash" in target_columns:

                    insert_columns.append(
                        "record_hash"
                    )

                    insert_values.append(
                        new_hash
                    )

                placeholders = ", ".join(
                    ["%s"] * len(insert_columns)
                )

                columns_sql = ", ".join(
                    insert_columns
                )

                cursor.execute(
                    f"""
                    INSERT INTO core_salespersons
                    ({columns_sql})
                    VALUES ({placeholders})
                    """,
                    tuple(insert_values),
                )

                inserted += 1

                audit_rows.append(
                    {
                        "run_timestamp":
                            run_timestamp,
                        "salesperson_id":
                            salesperson_id,
                        "source_file_name":
                            source_file_name,
                        "source_row_number":
                            source_row_number,
                        "batch_id": batch_id,
                        "action": "INSERT",
                        "reason":
                            "New salesperson master "
                            "record",
                        "old_record_hash": "",
                        "new_record_hash":
                            new_hash,
                        "old_store_id": "",
                        "new_store_id":
                            store_id,
                    }
                )

                core_by_id[
                    str(salesperson_id)
                ] = {
                    **{
                        column:
                            row.get(column)
                        for column in BUSINESS_COLUMNS
                    },
                    "record_hash":
                        new_hash,
                }

                continue


            # =================================================
            # EXISTING RECORD
            # =================================================

            old_hash = normalize_value(
                existing.get("record_hash")
            )

            same_business_values = (
                rows_have_same_business_values(
                    row,
                    existing,
                )
            )


            # ------------------------------------------------
            # UNCHANGED
            # ------------------------------------------------

            if same_business_values:

                unchanged += 1

                audit_rows.append(
                    {
                        "run_timestamp":
                            run_timestamp,
                        "salesperson_id":
                            salesperson_id,
                        "source_file_name":
                            source_file_name,
                        "source_row_number":
                            source_row_number,
                        "batch_id": batch_id,
                        "action": "UNCHANGED",
                        "reason":
                            "Existing salesperson "
                            "record unchanged",
                        "old_record_hash":
                            old_hash or "",
                        "new_record_hash":
                            new_hash or "",
                        "old_store_id":
                            normalize_value(
                                existing.get(
                                    "store_id"
                                )
                            ) or "",
                        "new_store_id":
                            store_id or "",
                    }
                )

                continue


            # ------------------------------------------------
            # UPDATE EXISTING RECORD
            # ------------------------------------------------

            update_assignments = [
                "salesperson_name = %s",
                "store_id = %s",
                "joining_date = %s",
                "role = %s",
                "status = %s",
            ]

            update_values = [
                row.get("salesperson_name"),
                row.get("store_id"),
                row.get("joining_date"),
                row.get("role"),
                row.get("status"),
            ]

            if "record_hash" in target_columns:

                update_assignments.append(
                    "record_hash = %s"
                )

                update_values.append(
                    new_hash
                )

            if "updated_at" in target_columns:

                update_assignments.append(
                    "updated_at = CURRENT_TIMESTAMP"
                )

            update_values.append(
                salesperson_id
            )

            cursor.execute(
                f"""
                UPDATE core_salespersons
                SET {", ".join(update_assignments)}
                WHERE salesperson_id = %s
                """,
                tuple(update_values),
            )

            updated += 1

            old_store_id = normalize_value(
                existing.get("store_id")
            )

            if not values_equal(
                old_store_id,
                store_id,
            ):

                reason = (
                    "Salesperson master updated; "
                    "store relationship changed"
                )

            else:

                reason = (
                    "Salesperson master record updated"
                )

            audit_rows.append(
                {
                    "run_timestamp":
                        run_timestamp,
                    "salesperson_id":
                        salesperson_id,
                    "source_file_name":
                        source_file_name,
                    "source_row_number":
                        source_row_number,
                    "batch_id": batch_id,
                    "action": "UPDATE",
                    "reason": reason,
                    "old_record_hash":
                        old_hash or "",
                    "new_record_hash":
                        new_hash or "",
                    "old_store_id":
                        old_store_id or "",
                    "new_store_id":
                        store_id or "",
                }
            )

            core_by_id[
                str(salesperson_id)
            ] = {
                **{
                    column:
                        row.get(column)
                    for column in BUSINESS_COLUMNS
                },
                "record_hash":
                    new_hash,
            }


        # ====================================================
        # COMMIT
        # ====================================================

        connection.commit()

        write_audit(audit_rows)

        print()
        print("=" * 70)
        print("05.21 STATUS: PASS")
        print("=" * 70)

        print(
            f"Source staging rows : {total}"
        )

        print(
            f"Inserted            : {inserted}"
        )

        print(
            f"Updated             : {updated}"
        )

        print(
            f"Unchanged           : {unchanged}"
        )

        print(
            f"Failed              : {failed}"
        )

        print()
        print("Transaction committed.")

        print(
            f"Audit file: {AUDIT_FILE}"
        )

        print(
            f"Log file  : {LOG_FILE}"
        )

        print("=" * 70)

        logger.info(
            "05.21 PASS | total=%s inserted=%s "
            "updated=%s unchanged=%s failed=%s",
            total,
            inserted,
            updated,
            unchanged,
            failed,
        )


    except Exception as error:

        if connection is not None:
            connection.rollback()

        logger.exception(
            "05.21 salesperson merge failed."
        )

        print()
        print("=" * 70)
        print("05.21 STATUS: FAILED")
        print("=" * 70)

        print(
            f"Error: {error}"
        )

        print()
        print(
            "Transaction was rolled back."
        )

        print(
            f"Audit file: {AUDIT_FILE}"
        )

        print(
            f"Log file  : {LOG_FILE}"
        )

        print("=" * 70)

        sys.exit(1)


    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# ============================================================
# 09. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
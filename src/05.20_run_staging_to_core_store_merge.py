"""
05.20 - Run staging-to-core store merge

Tracker:
Insert/update stores and preserve required history.

Rules
-----
1. store_id is the store business key.
2. New store_id -> INSERT.
3. Existing store_id with same record_hash -> UNCHANGED.
4. Existing store_id with different record_hash -> UPDATE.
5. Existing creation/history metadata is preserved during UPDATE.
6. Full SCD history closing/version creation is NOT implemented here.
7. Full SCD history implementation belongs to tracker step 05.27.
8. Duplicate store_id values in staging -> FAILED.
9. Missing required store fields -> FAILED.
10. Transaction protected.
11. Idempotent rerun.
12. Produce audit CSV and log.
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

LOG_FILE = LOG_DIR / "05.20_run_staging_to_core_store_merge.log"
AUDIT_FILE = OUTPUT_DIR / "05.20_store_merge_audit.csv"


# ============================================================
# 02. LOGGING
# ============================================================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "05.20 | "
        "%(message)s"
    ),
)

logger = logging.getLogger("05.20_store_merge")


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

try:
    DB_PORT = int(DB_PORT_RAW or "3306")
except ValueError:
    DB_PORT = 3306


# ============================================================
# 05. STORE DEFINITIONS
# ============================================================

# Required according to project store specification.
REQUIRED_STORE_COLUMNS = [
    "store_id",
    "store_name",
    "store_type",
    "city",
    "state",
    "region",
    "postal_code",
    "opening_date",
    "status",
]

# Optional fields from the store specification.
OPTIONAL_STORE_COLUMNS = [
    "floor_area_sqft",
    "manager_name",
]

AUDIT_COLUMNS = [
    "run_timestamp",
    "store_id",
    "source_file_name",
    "source_row_number",
    "batch_id",
    "action",
    "reason",
    "old_record_hash",
    "new_record_hash",
]


# ============================================================
# 06. HELPERS
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


def hashes_equal(old_hash, new_hash) -> bool:

    old_hash = normalize_value(old_hash)
    new_hash = normalize_value(new_hash)

    if old_hash is None and new_hash is None:
        return True

    if old_hash is None or new_hash is None:
        return False

    return str(old_hash).lower() == str(new_hash).lower()


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


def connect_database():

    if DB_PASSWORD is None:

        raise RuntimeError(
            "Database password was not found. "
            "Please verify DB_PASSWORD or "
            "MYSQL_PASSWORD in the project .env file."
        )

    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def get_table_columns(cursor, table_name: str) -> set[str]:

    cursor.execute(
        f"SHOW COLUMNS FROM `{table_name}`"
    )

    rows = cursor.fetchall()

    return {
        str(row["Field"])
        for row in rows
    }


# ============================================================
# 07. MAIN
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
    print("05.20 - RUN STAGING-TO-CORE STORE MERGE")
    print("=" * 70)

    print(f"Database : {DB_NAME}")
    print("Source   : stg_stores")
    print("Target   : core_stores")
    print()

    logger.info("========== 05.20 START ==========")

    try:

        # ====================================================
        # DATABASE CONNECTION
        # ====================================================

        connection = connect_database()

        cursor = connection.cursor(dictionary=True)

        print("Database connection: SUCCESS")

        logger.info("Database connection successful.")


        # ====================================================
        # TARGET STRUCTURE
        # ====================================================

        target_columns = get_table_columns(
            cursor,
            "core_stores",
        )

        required_target_columns = set(
            REQUIRED_STORE_COLUMNS
            + [
                "record_hash",
            ]
        )

        missing_columns = (
            required_target_columns
            - target_columns
        )

        if missing_columns:

            raise RuntimeError(
                "core_stores is missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

        print("Target structure check: SUCCESS")

        logger.info(
            "core_stores structure validated."
        )


        # ====================================================
        # STAGING STRUCTURE
        # ====================================================

        staging_columns = get_table_columns(
            cursor,
            "stg_stores",
        )

        missing_staging_columns = (
            set(REQUIRED_STORE_COLUMNS)
            - staging_columns
        )

        if missing_staging_columns:

            raise RuntimeError(
                "stg_stores is missing required columns: "
                + ", ".join(
                    sorted(missing_staging_columns)
                )
            )

        print("Staging structure check: SUCCESS")

        logger.info(
            "stg_stores structure validated."
        )


        # ====================================================
        # OPTIONAL COLUMNS
        # ====================================================

        optional_columns = [
            column
            for column in OPTIONAL_STORE_COLUMNS
            if (
                column in staging_columns
                and column in target_columns
            )
        ]


        # ====================================================
        # READ STAGING DATA
        # ====================================================

        source_columns = (
            REQUIRED_STORE_COLUMNS
            + optional_columns
            + [
                "batch_id",
                "source_file_name",
                "source_row_number",
                "record_hash",
                "load_timestamp",
            ]
        )

        select_columns_sql = ", ".join(
            f"`{column}`"
            for column in source_columns
        )

        select_sql = f"""
            SELECT
                {select_columns_sql}
            FROM stg_stores
            ORDER BY staging_id
        """

        cursor.execute(select_sql)

        staging_rows = cursor.fetchall()

        total = len(staging_rows)

        print(
            f"Staging rows found : {total:,}"
        )

        logger.info(
            "Staging rows found: %s",
            total,
        )


        # ====================================================
        # VALIDATE REQUIRED VALUES
        # ====================================================

        for row in staging_rows:

            store_id = normalize_value(
                row.get("store_id")
            )

            missing_fields = []

            for column in REQUIRED_STORE_COLUMNS:

                if not normalize_value(
                    row.get(column)
                ):
                    missing_fields.append(column)

            if missing_fields:

                failed += 1

                audit_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "store_id": store_id or "",
                        "source_file_name":
                            normalize_value(
                                row.get(
                                    "source_file_name"
                                )
                            ),
                        "source_row_number":
                            row.get(
                                "source_row_number"
                            ),
                        "batch_id":
                            normalize_value(
                                row.get("batch_id")
                            ),
                        "action": "FAILED",
                        "reason":
                            "Missing required fields: "
                            + ", ".join(
                                missing_fields
                            ),
                        "old_record_hash": "",
                        "new_record_hash":
                            normalize_value(
                                row.get("record_hash")
                            ) or "",
                    }
                )

        if failed > 0:

            connection.rollback()

            write_audit(audit_rows)

            print()
            print("=" * 70)
            print("05.20 STATUS: FAIL")
            print("=" * 70)
            print(
                f"Source staging rows : {total:,}"
            )
            print(
                f"Failed              : {failed:,}"
            )
            print(
                "Transaction was rolled back."
            )
            print(
                f"Audit file: {AUDIT_FILE}"
            )

            logger.error(
                "Required store validation failed. "
                "Transaction rolled back."
            )

            sys.exit(1)


        # ====================================================
        # CHECK DUPLICATE BUSINESS KEYS
        # ====================================================

        store_counts: dict[str, int] = {}

        for row in staging_rows:

            store_id = normalize_value(
                row.get("store_id")
            )

            if store_id:

                store_counts[store_id] = (
                    store_counts.get(
                        store_id,
                        0,
                    )
                    + 1
                )

        duplicate_store_ids = {
            store_id
            for store_id, count
            in store_counts.items()
            if count > 1
        }

        if duplicate_store_ids:

            connection.rollback()

            write_audit(audit_rows)

            raise RuntimeError(
                "Duplicate store_id values found in "
                "stg_stores: "
                + ", ".join(
                    sorted(
                        duplicate_store_ids
                    )
                )
            )


        # ====================================================
        # EXISTING CORE STORE LOOKUP
        # ====================================================

        cursor.execute(
            """
            SELECT
                store_id,
                record_hash
            FROM core_stores
            """
        )

        existing_rows = cursor.fetchall()

        core_by_store_id = {
            str(row["store_id"]): row
            for row in existing_rows
        }


        # ====================================================
        # PROCESS STAGING ROWS
        # ====================================================

        insert_columns = (
            REQUIRED_STORE_COLUMNS
            + optional_columns
            + [
                "batch_id",
                "source_file_name",
                "source_row_number",
                "record_hash",
                "load_timestamp",
                "created_at",
                "updated_at",
                "record_version",
                "valid_from",
                "valid_to",
                "is_current",
            ]
        )

        insert_column_sql = ", ".join(
            f"`{column}`"
            for column in insert_columns
        )

        value_parts = (
            ["%s"]
            * (
                len(
                    REQUIRED_STORE_COLUMNS
                    + optional_columns
                    + [
                        "batch_id",
                        "source_file_name",
                        "source_row_number",
                        "record_hash",
                        "load_timestamp",
                    ]
                )
            )
        )

        value_parts += [
            "NOW()",
            "NOW()",
            "1",
            "NOW()",
            "NULL",
            "1",
        ]

        insert_sql = f"""
            INSERT INTO core_stores (
                {insert_column_sql}
            )
            VALUES (
                {", ".join(value_parts)}
            )
        """


        for row in staging_rows:

            store_id = normalize_value(
                row.get("store_id")
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

            existing = core_by_store_id.get(
                str(store_id)
            )


            # =================================================
            # NEW STORE
            # =================================================

            if existing is None:

                insert_parameters = [
                    row.get(column)
                    for column in (
                        REQUIRED_STORE_COLUMNS
                        + optional_columns
                        + [
                            "batch_id",
                            "source_file_name",
                            "source_row_number",
                            "record_hash",
                            "load_timestamp",
                        ]
                    )
                ]

                cursor.execute(
                    insert_sql,
                    tuple(insert_parameters),
                )

                inserted += 1

                audit_rows.append(
                    {
                        "run_timestamp":
                            run_timestamp,
                        "store_id":
                            store_id,
                        "source_file_name":
                            source_file_name,
                        "source_row_number":
                            source_row_number,
                        "batch_id":
                            batch_id,
                        "action":
                            "INSERTED",
                        "reason":
                            "New store_id",
                        "old_record_hash":
                            "",
                        "new_record_hash":
                            new_record_hash or "",
                    }
                )

                continue


            # =================================================
            # SAME HASH
            # =================================================

            old_record_hash = normalize_value(
                existing.get("record_hash")
            )

            if hashes_equal(
                old_record_hash,
                new_record_hash,
            ):

                unchanged += 1

                audit_rows.append(
                    {
                        "run_timestamp":
                            run_timestamp,
                        "store_id":
                            store_id,
                        "source_file_name":
                            source_file_name,
                        "source_row_number":
                            source_row_number,
                        "batch_id":
                            batch_id,
                        "action":
                            "UNCHANGED",
                        "reason":
                            "Same record_hash",
                        "old_record_hash":
                            old_record_hash or "",
                        "new_record_hash":
                            new_record_hash or "",
                    }
                )

                continue


            # =================================================
            # DIFFERENT HASH -> UPDATE
            # =================================================

            update_columns = (
                [
                    column
                    for column in REQUIRED_STORE_COLUMNS
                    if column != "store_id"
                ]
                + optional_columns
                + [
                    "batch_id",
                    "source_file_name",
                    "source_row_number",
                    "record_hash",
                ]
            )

            set_sql = ", ".join(
                f"`{column}` = %s"
                for column in update_columns
            )

            update_sql = f"""
                UPDATE core_stores
                SET
                    {set_sql},
                    updated_at = NOW()
                WHERE store_id = %s
            """

            update_parameters = [
                row.get(column)
                for column in update_columns
            ]

            update_parameters.append(store_id)

            cursor.execute(
                update_sql,
                tuple(update_parameters),
            )

            updated += 1

            audit_rows.append(
                {
                    "run_timestamp":
                        run_timestamp,
                    "store_id":
                        store_id,
                    "source_file_name":
                        source_file_name,
                    "source_row_number":
                        source_row_number,
                    "batch_id":
                        batch_id,
                    "action":
                        "UPDATED",
                    "reason":
                        "Existing store_id with "
                        "different record_hash",
                    "old_record_hash":
                        old_record_hash or "",
                    "new_record_hash":
                        new_record_hash or "",
                }
            )


        # ====================================================
        # COMMIT
        # ====================================================

        connection.commit()

        write_audit(audit_rows)

        logger.info(
            "05.20 transaction committed."
        )

        print()
        print("=" * 70)
        print("05.20 STATUS: PASS")
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
        print("Transaction committed.")

        print(
            f"Audit file: {AUDIT_FILE}"
        )

        print(
            f"Log file  : {LOG_FILE}"
        )

        print("=" * 70)

        logger.info(
            "========== 05.20 END =========="
        )


    except Exception as error:

        if connection is not None:

            try:
                connection.rollback()
            except Exception:
                pass

        logger.exception(
            "05.20 store merge failed."
        )

        write_audit(audit_rows)

        print()
        print("=" * 70)
        print("05.20 STATUS: FAIL")
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
            f"Log file: {LOG_FILE}"
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


# ============================================================
# 08. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
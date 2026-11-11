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

PROJECT_ROOT = Path(__file__).resolve().parents[1]

LOG_DIR = PROJECT_ROOT / "logs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "05.23_run_sales_incremental_insert.log"

AUDIT_FILE = (
    OUTPUT_DIR
    / "05.23_sales_incremental_insert_audit.csv"
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
        "05.23 | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "05.23_sales_incremental_insert"
)


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

            key, value = line.split(
                "=",
                1,
            )

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
    PROJECT_ROOT / ".env"
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
# PROJECT BUSINESS RULES
# ============================================================

BUSINESS_KEY = "sales_line_id"

SOURCE_TABLE = "stg_sales"

TARGET_TABLE = "factsales"

STORE_TABLE = "core_stores"

STORE_FOREIGN_KEY = "fk_fact_sales_store"


APPROVED_PAYMENT_METHODS = {
    "Cash",
    "Card",
    "UPI",
    "Wallet",
    "Net Banking",
}


SALES_COLUMNS = [
    "sales_line_id",
    "order_id",
    "order_date",
    "order_time",
    "customer_id",
    "product_id",
    "store_id",
    "salesperson_id",
    "promotion_id",
    "sales_channel",
    "quantity",
    "unit_selling_price",
    "discount_pct",
    "payment_method",
    "order_status",
]


METADATA_COLUMNS = [
    "batch_id",
    "source_file_name",
    "source_row_number",
    "record_hash",
]


# ============================================================
# AUDIT COLUMNS
# ============================================================

AUDIT_COLUMNS = [
    "run_timestamp",
    "sales_line_id",
    "source_file_name",
    "source_row_number",
    "batch_id",
    "store_id",
    "payment_method",
    "action",
    "reason",
    "record_hash",
]


# ============================================================
# HELPERS
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

        writer.writerows(audit_rows)


def add_audit_row(
    audit_rows: list[dict],
    *,
    run_timestamp,
    row,
    action: str,
    reason: str,
) -> None:

    audit_rows.append(
        {
            "run_timestamp": run_timestamp,
            "sales_line_id": (
                normalize_value(
                    row.get("sales_line_id")
                )
                or ""
            ),
            "source_file_name": (
                normalize_value(
                    row.get("source_file_name")
                )
                or ""
            ),
            "source_row_number": (
                normalize_value(
                    row.get("source_row_number")
                )
                if normalize_value(
                    row.get("source_row_number")
                ) is not None
                else ""
            ),
            "batch_id": (
                normalize_value(
                    row.get("batch_id")
                )
                or ""
            ),
            "store_id": (
                normalize_value(
                    row.get("store_id")
                )
                if normalize_value(
                    row.get("store_id")
                ) is not None
                else ""
            ),
            "payment_method": (
                normalize_value(
                    row.get("payment_method")
                )
                or ""
            ),
            "action": action,
            "reason": reason,
            "record_hash": (
                normalize_value(
                    row.get("record_hash")
                )
                or ""
            ),
        }
    )


def get_missing_store_ids(
    cursor,
    staging_rows: list[dict],
) -> list:

    source_store_ids = set()

    for row in staging_rows:

        store_id = normalize_value(
            row.get("store_id")
        )

        if store_id is not None:
            source_store_ids.add(store_id)

    if not source_store_ids:
        return []

    placeholders = ", ".join(
        ["%s"] * len(source_store_ids)
    )

    query = f"""
        SELECT store_id
        FROM {STORE_TABLE}
        WHERE store_id IN ({placeholders})
    """

    cursor.execute(
        query,
        tuple(source_store_ids),
    )

    existing_store_ids = {
        normalize_value(row["store_id"])
        for row in cursor.fetchall()
    }

    missing_store_ids = sorted(
        source_store_ids - existing_store_ids,
        key=str,
    )

    return missing_store_ids


def check_store_foreign_key(
    cursor,
) -> dict:

    query = """
        SELECT
            CONSTRAINT_NAME,
            TABLE_NAME,
            COLUMN_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE CONSTRAINT_SCHEMA = %s
          AND TABLE_NAME = %s
          AND CONSTRAINT_NAME = %s
        LIMIT 1
    """

    cursor.execute(
        query,
        (
            DB_NAME,
            TARGET_TABLE,
            STORE_FOREIGN_KEY,
        ),
    )

    row = cursor.fetchone()

    if row is None:
        return {
            "exists": False,
            "details": None,
        }

    return {
        "exists": True,
        "details": row,
    }


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    run_timestamp = datetime.now()

    connection = None
    cursor = None

    audit_rows: list[dict] = []

    total_rows = 0
    inserted = 0
    already_exists = 0
    rejected = 0
    failed = 0
    store_fk_blocked = 0

    print()
    print("=" * 72)
    print(
        "05.23 - RUN SALES INCREMENTAL INSERT"
    )
    print("=" * 72)

    print(
        f"Database     : {DB_NAME}"
    )

    print(
        f"Source       : {SOURCE_TABLE}"
    )

    print(
        f"Target       : {TARGET_TABLE}"
    )

    print(
        f"Business key : {BUSINESS_KEY}"
    )

    print()

    logger.info(
        "05.23 sales incremental insert started."
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
            f"SHOW COLUMNS FROM {TARGET_TABLE}"
        )

        target_column_rows = cursor.fetchall()

        target_columns = {
            row["Field"]
            for row in target_column_rows
        }

        missing_business_columns = [
            column
            for column in SALES_COLUMNS
            if column not in target_columns
        ]

        if missing_business_columns:

            raise RuntimeError(
                "Missing required columns in "
                f"{TARGET_TABLE}: "
                + ", ".join(
                    missing_business_columns
                )
            )

        print(
            "Target structure check: SUCCESS"
        )

        logger.info(
            "Target structure check successful."
        )


        # ====================================================
        # CHECK SALES STORE FOREIGN KEY
        # ====================================================

        fk_info = check_store_foreign_key(
            cursor
        )

        if fk_info["exists"]:

            print(
                "Store foreign key check: PRESENT"
            )

            logger.info(
                "Foreign key %s is present: "
                "factsales.store_id -> core_stores.store_id.",
                STORE_FOREIGN_KEY,
            )

        else:

            print(
                "Store foreign key check: "
                "NOT FOUND"
            )

            logger.warning(
                "Expected foreign key %s was not found.",
                STORE_FOREIGN_KEY,
            )


        # ====================================================
        # READ STAGING DATA
        # ====================================================

        select_sql = """
            SELECT
                staging_id,
                sales_line_id,
                order_id,
                order_date,
                order_time,
                customer_id,
                product_id,
                store_id,
                salesperson_id,
                promotion_id,
                sales_channel,
                quantity,
                unit_selling_price,
                discount_pct,
                payment_method,
                order_status,
                batch_id,
                source_file_name,
                source_row_number,
                record_hash
            FROM stg_sales
            ORDER BY staging_id
        """

        cursor.execute(
            select_sql
        )

        staging_rows = cursor.fetchall()

        total_rows = len(
            staging_rows
        )

        print(
            f"Staging rows found : {total_rows:,}"
        )

        logger.info(
            "Staging rows found: %s",
            total_rows,
        )


        # ====================================================
        # STORE FK VALIDATION
        # ====================================================

        missing_store_ids = get_missing_store_ids(
            cursor,
            staging_rows,
        )

        if missing_store_ids:

            store_fk_blocked = len(
                missing_store_ids
            )

            print()
            print(
                "05.23 STATUS: BLOCKED"
            )
            print()
            print(
                "Sales incremental insert was NOT performed."
            )
            print(
                "Reason: staging sales contain store_id "
                "values that do not exist in core_stores."
            )
            print()
            print(
                "Missing store_id values:"
            )

            for store_id in missing_store_ids:
                print(
                    f"  - {store_id}"
                )

            logger.error(
                "05.23 blocked because %s store_id "
                "values from stg_sales are missing "
                "from core_stores: %s",
                len(missing_store_ids),
                missing_store_ids,
            )


            # Record affected rows in audit.
            missing_store_id_set = set(
                missing_store_ids
            )

            for row in staging_rows:

                store_id = normalize_value(
                    row.get("store_id")
                )

                if store_id in missing_store_id_set:

                    add_audit_row(
                        audit_rows,
                        run_timestamp=run_timestamp,
                        row=row,
                        action="BLOCKED",
                        reason=(
                            "store_id is not present "
                            "in core_stores. "
                            "Sales incremental insert "
                            "was not executed."
                        ),
                    )

            write_audit(
                audit_rows
            )

            print()
            print(
                f"Audit file: {AUDIT_FILE}"
            )

            print(
                f"Log file  : {LOG_FILE}"
            )

            print()
            print(
                "No factsales records were inserted."
            )

            print(
                "No source/staging values were modified."
            )

            print("=" * 72)

            return


        # ====================================================
        # CLOSE READ TRANSACTION
        # ====================================================

        connection.commit()


        # ====================================================
        # START INSERT TRANSACTION
        # ====================================================

        connection.start_transaction()

        logger.info(
            "05.23 insert transaction started."
        )


        # ====================================================
        # BUILD INSERT COLUMN LIST
        # ====================================================

        insert_columns = [
            column
            for column in (
                SALES_COLUMNS
                + METADATA_COLUMNS
            )
            if column in target_columns
        ]

        if BUSINESS_KEY not in insert_columns:

            raise RuntimeError(
                f"{BUSINESS_KEY} is not available "
                f"in {TARGET_TABLE}."
            )

        insert_column_sql = ", ".join(
            insert_columns
        )

        placeholders = ", ".join(
            ["%s"] * len(insert_columns)
        )

        insert_sql = f"""
            INSERT INTO {TARGET_TABLE} (
                {insert_column_sql}
            )
            VALUES (
                {placeholders}
            )
        """


        # ====================================================
        # PROCESS EACH STAGING ROW
        # ====================================================

        for row in staging_rows:

            sales_line_id = normalize_value(
                row.get("sales_line_id")
            )

            payment_method = normalize_value(
                row.get("payment_method")
            )

            store_id = normalize_value(
                row.get("store_id")
            )


            # ------------------------------------------------
            # BUSINESS KEY VALIDATION
            # ------------------------------------------------

            if not sales_line_id:

                failed += 1

                add_audit_row(
                    audit_rows,
                    run_timestamp=run_timestamp,
                    row=row,
                    action="FAILED",
                    reason=(
                        "Blank sales_line_id "
                        "business key."
                    ),
                )

                continue


            # ------------------------------------------------
            # PAYMENT METHOD VALIDATION
            # ------------------------------------------------

            if (
                payment_method
                not in APPROVED_PAYMENT_METHODS
            ):

                rejected += 1

                add_audit_row(
                    audit_rows,
                    run_timestamp=run_timestamp,
                    row=row,
                    action="REJECTED",
                    reason=(
                        "Invalid payment_method. "
                        "Approved values: "
                        "Cash, Card, UPI, Wallet, "
                        "Net Banking."
                    ),
                )

                continue


            # ------------------------------------------------
            # STORE ID VALIDATION
            # ------------------------------------------------

            if store_id is None:

                failed += 1

                add_audit_row(
                    audit_rows,
                    run_timestamp=run_timestamp,
                    row=row,
                    action="FAILED",
                    reason=(
                        "Blank store_id. "
                        "Cannot satisfy factsales "
                        "store foreign-key requirement."
                    ),
                )

                continue


            # ------------------------------------------------
            # CHECK EXISTING BUSINESS KEY
            # ------------------------------------------------

            cursor.execute(
                f"""
                    SELECT
                        {BUSINESS_KEY}
                    FROM {TARGET_TABLE}
                    WHERE {BUSINESS_KEY} = %s
                    LIMIT 1
                """,
                (sales_line_id,),
            )

            existing = cursor.fetchone()

            if existing is not None:

                already_exists += 1

                add_audit_row(
                    audit_rows,
                    run_timestamp=run_timestamp,
                    row=row,
                    action="UNCHANGED",
                    reason=(
                        "sales_line_id already exists "
                        "in factsales."
                    ),
                )

                continue


            # ------------------------------------------------
            # BUILD INSERT VALUES
            # ------------------------------------------------

            values = []

            for column in insert_columns:

                if column in row:

                    values.append(
                        row.get(column)
                    )

                else:

                    values.append(None)


            # ------------------------------------------------
            # INSERT NEW SALES RECORD
            # ------------------------------------------------

            cursor.execute(
                insert_sql,
                tuple(values),
            )

            inserted += 1

            add_audit_row(
                audit_rows,
                run_timestamp=run_timestamp,
                row=row,
                action="INSERTED",
                reason=(
                    "New sales_line_id "
                    "business key."
                ),
            )


        # ====================================================
        # PRE-COMMIT VALIDATION
        # ====================================================

        expected_insert_count = inserted

        cursor.execute(
            f"""
                SELECT COUNT(*) AS inserted_count
                FROM {TARGET_TABLE}
                WHERE {BUSINESS_KEY} IN (
                    SELECT {BUSINESS_KEY}
                    FROM {SOURCE_TABLE}
                    WHERE {BUSINESS_KEY} IS NOT NULL
                )
            """
        )

        reconciliation_row = cursor.fetchone()

        target_matching_count = int(
            reconciliation_row["inserted_count"]
        )


        logger.info(
            "Pre-commit reconciliation: "
            "target matching sales_line_id count=%s.",
            target_matching_count,
        )


        # ====================================================
        # COMMIT
        # ====================================================

        connection.commit()

        logger.info(
            "05.23 transaction committed successfully."
        )


        # ====================================================
        # POST-COMMIT VERIFICATION
        # ====================================================

        cursor.execute(
            f"""
                SELECT COUNT(*) AS target_count
                FROM {TARGET_TABLE}
            """
        )

        target_count_row = cursor.fetchone()

        final_target_count = int(
            target_count_row["target_count"]
        )


        cursor.execute(
            f"""
                SELECT COUNT(DISTINCT {BUSINESS_KEY})
                AS source_business_key_count
                FROM {SOURCE_TABLE}
                WHERE {BUSINESS_KEY} IS NOT NULL
            """
        )

        source_key_row = cursor.fetchone()

        source_business_key_count = int(
            source_key_row[
                "source_business_key_count"
            ]
        )


        # ====================================================
        # WRITE AUDIT
        # ====================================================

        write_audit(
            audit_rows
        )


        # ====================================================
        # FINAL STATUS
        # ====================================================

        print()
        print("=" * 72)

        print(
            "05.23 STATUS: PASS"
        )

        print("=" * 72)

        print(
            f"Source staging rows       : {total_rows:,}"
        )

        print(
            f"Inserted                   : {inserted:,}"
        )

        print(
            f"Already exists             : {already_exists:,}"
        )

        print(
            f"Rejected payment methods  : {rejected:,}"
        )

        print(
            f"Failed rows                : {failed:,}"
        )

        print(
            f"Source unique business keys: "
            f"{source_business_key_count:,}"
        )

        print(
            f"Final factsales row count : "
            f"{final_target_count:,}"
        )

        print()

        print(
            "Store foreign-key validation: SUCCESS"
        )

        print(
            "Duplicate business-key prevention: SUCCESS"
        )

        print(
            "Invalid payment-method rows were "
            "not inserted into factsales."
        )

        print(
            "Source/staging values were not modified."
        )

        print(
            "Transaction committed."
        )

        print()

        print(
            f"Audit file: {AUDIT_FILE}"
        )

        print(
            f"Log file  : {LOG_FILE}"
        )

        print("=" * 72)


        logger.info(
            "05.23 completed successfully. "
            "Source=%s Inserted=%s "
            "AlreadyExists=%s Rejected=%s "
            "Failed=%s FinalTargetCount=%s",
            total_rows,
            inserted,
            already_exists,
            rejected,
            failed,
            final_target_count,
        )


    except Exception as exc:

        # ====================================================
        # ROLLBACK
        # ====================================================

        if connection is not None:

            try:

                connection.rollback()

            except Exception:

                pass


        # ====================================================
        # AUDIT FAILED RUN
        # ====================================================

        try:

            if not audit_rows:

                audit_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "sales_line_id": "",
                        "source_file_name": "",
                        "source_row_number": "",
                        "batch_id": "",
                        "store_id": "",
                        "payment_method": "",
                        "action": "FAILED",
                        "reason": str(exc),
                        "record_hash": "",
                    }
                )

            else:

                audit_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "sales_line_id": "",
                        "source_file_name": "",
                        "source_row_number": "",
                        "batch_id": "",
                        "store_id": "",
                        "payment_method": "",
                        "action": "FAILED",
                        "reason": (
                            "Database transaction failed "
                            "and was rolled back. "
                            f"Error: {exc}"
                        ),
                        "record_hash": "",
                    }
                )

            write_audit(
                audit_rows
            )

        except Exception:

            pass


        # ====================================================
        # FINAL FAILURE MESSAGE
        # ====================================================

        print()
        print("=" * 72)

        print(
            "05.23 STATUS: FAILED"
        )

        print("=" * 72)

        print(
            f"Error: {exc}"
        )

        print()

        print(
            "Transaction rolled back."
        )

        print(
            "No partial database changes from "
            "this run were retained."
        )

        print()

        print(
            f"Audit file: {AUDIT_FILE}"
        )

        print(
            f"Log file  : {LOG_FILE}"
        )

        print("=" * 72)


        logger.exception(
            "05.23 sales incremental insert failed."
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
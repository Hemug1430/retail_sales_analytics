"""
05.19 - Run staging-to-core product merge

Tracker:
Insert new products and apply approved product update/history rules.

Rules
-----
1. product_id is the product business key.
2. New product_id -> INSERT.
3. Existing product_id with same record_hash -> UNCHANGED.
4. Existing product_id with different record_hash -> REVIEW.
5. Do not silently overwrite trusted product history.
6. SCD history changes are NOT implemented here.
7. SCD history implementation belongs to tracker step 05.27.
8. Missing/duplicate product_id -> FAILED.
9. Invalid trusted product values -> FAILED.
10. Transaction protected.
11. Idempotent rerun.
12. Produce audit CSV and log.

Approved product fields
-----------------------
product_id
product_name
category
subcategory
brand
unit_cost
list_price
tax_rate_pct
launch_date
status

Approved source aliases
-----------------------
cost_price   -> unit_cost
unit_price   -> list_price
gst_percent  -> tax_rate_pct
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
    LOG_DIR
    / "05.19_run_staging_to_core_product_merge.log"
)

AUDIT_FILE = (
    OUTPUT_DIR
    / "05.19_product_merge_audit.csv"
)


# ============================================================
# 02. LOGGING
# ============================================================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "05.19 | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "05.19_product_merge"
)


# ============================================================
# 03. LOAD PROJECT .ENV
# ============================================================

def load_env_file(
    env_path: Path,
) -> dict[str, str]:

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
    BASE_DIR / ".env"
)


def get_config_value(
    *names: str,
    default: str | None = None,
) -> str | None:

    for name in names:

        value = os.getenv(name)

        if (
            value is not None
            and value != ""
        ):
            return value

        value = ENV_VALUES.get(name)

        if (
            value is not None
            and value != ""
        ):
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
# 05. PRODUCT DEFINITIONS
# ============================================================

PRODUCT_COLUMNS = [
    "product_id",
    "product_name",
    "category",
    "subcategory",
    "brand",
    "unit_cost",
    "list_price",
    "tax_rate_pct",
    "launch_date",
    "status",
]

PRODUCT_ALIASES = {
    "unit_cost": [
        "unit_cost",
        "cost_price",
    ],
    "list_price": [
        "list_price",
        "unit_price",
    ],
    "tax_rate_pct": [
        "tax_rate_pct",
        "gst_percent",
    ],
}

ALLOWED_PRODUCT_STATUS = {
    "Active",
    "Discontinued",
    "Suspended",
}


# ============================================================
# 06. AUDIT COLUMNS
# ============================================================

AUDIT_COLUMNS = [
    "run_timestamp",
    "product_id",
    "source_file_name",
    "source_row_number",
    "batch_id",
    "action",
    "reason",
    "old_record_hash",
    "new_record_hash",
]


# ============================================================
# 07. HELPERS
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

    if (
        old_hash is None
        and new_hash is None
    ):
        return True

    if (
        old_hash is None
        or new_hash is None
    ):
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
        writer.writerows(audit_rows)


def normalize_product_row(
    row: dict,
) -> dict:

    normalized = {}

    for column in PRODUCT_COLUMNS:

        aliases = PRODUCT_ALIASES.get(
            column,
            [column],
        )

        value = None

        for alias in aliases:

            if alias in row:

                value = normalize_value(
                    row.get(alias)
                )

                if value is not None:
                    break

        normalized[column] = value

    return normalized


# ============================================================
# 08. DATABASE CONNECTION
# ============================================================

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


# ============================================================
# 09. GET TARGET TABLE COLUMNS
# ============================================================

def get_core_product_columns(
    cursor,
) -> set[str]:

    cursor.execute(
        """
        SHOW COLUMNS
        FROM core_products
        """
    )

    rows = cursor.fetchall()

    return {
        str(row["Field"])
        for row in rows
    }


# ============================================================
# 10. VALIDATE CORE PRODUCT STRUCTURE
# ============================================================

def validate_core_product_structure(
    target_columns: set[str],
) -> list[str]:

    missing = []

    for column in PRODUCT_COLUMNS:

        if column not in target_columns:

            # Approved aliases should already have
            # been normalized before this point.

            missing.append(column)

    return missing


# ============================================================
# 11. MAIN
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
    print(
        "05.19 - RUN STAGING-TO-CORE PRODUCT MERGE"
    )
    print("=" * 70)

    print(f"Database : {DB_NAME}")
    print("Source   : stg_products")
    print("Target   : core_products")
    print()

    logger.info(
        "05.19 product merge started."
    )

    try:

        # ====================================================
        # DATABASE CONNECTION
        # ====================================================

        connection = connect_database()

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
        # CHECK TARGET STRUCTURE
        # ====================================================

        target_columns = (
            get_core_product_columns(
                cursor
            )
        )

        missing_columns = (
            validate_core_product_structure(
                target_columns
            )
        )

        if missing_columns:

            raise RuntimeError(
                "core_products is missing "
                "required product columns: "
                + ", ".join(
                    missing_columns
                )
            )

        print(
            "Target structure check: SUCCESS"
        )

        logger.info(
            "core_products structure validated."
        )

        # ====================================================
        # READ STAGING DATA
        # ====================================================

        select_sql = """
            SELECT
                staging_id,
                product_id,
                product_name,
                category,
                subcategory,
                brand,
                unit_cost,
                list_price,
                tax_rate_pct,
                launch_date,
                status,
                batch_id,
                source_file_name,
                source_row_number,
                record_hash,
                load_timestamp
            FROM stg_products
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
        # CHECK DUPLICATE PRODUCT IDS
        # ====================================================

        product_counts: dict[str, int] = {}

        for row in staging_rows:

            product_id = normalize_value(
                row.get("product_id")
            )

            if product_id:

                product_counts[
                    product_id
                ] = (
                    product_counts.get(
                        product_id,
                        0,
                    )
                    + 1
                )

        duplicate_product_ids = {
            product_id
            for product_id, count
            in product_counts.items()
            if count > 1
        }

        if duplicate_product_ids:

            print(
                "Duplicate product_id values "
                "found in stg_products."
            )

            print(
                "Duplicate product IDs: "
                f"{len(duplicate_product_ids):,}"
            )

            logger.error(
                "Duplicate product IDs found: %s",
                len(duplicate_product_ids),
            )

        # ====================================================
        # PROCESS STAGING ROWS
        # ====================================================

        for row in staging_rows:

            product_id = normalize_value(
                row.get("product_id")
            )

            source_file_name = (
                normalize_value(
                    row.get(
                        "source_file_name"
                    )
                )
            )

            source_row_number = (
                row.get(
                    "source_row_number"
                )
            )

            batch_id = normalize_value(
                row.get("batch_id")
            )

            new_record_hash = (
                normalize_value(
                    row.get("record_hash")
                )
            )

            # ------------------------------------------------
            # NORMALIZE PRODUCT VALUES
            # ------------------------------------------------

            product = (
                normalize_product_row(
                    row
                )
            )

            # ------------------------------------------------
            # MISSING PRODUCT ID
            # ------------------------------------------------

            if not product_id:

                failed += 1

                audit_rows.append(
                    {
                        "run_timestamp":
                            run_timestamp,
                        "product_id": "",
                        "source_file_name":
                            source_file_name,
                        "source_row_number":
                            source_row_number,
                        "batch_id": batch_id,
                        "action": "FAILED",
                        "reason":
                            "Missing product_id",
                        "old_record_hash": "",
                        "new_record_hash":
                            new_record_hash or "",
                    }
                )

                continue

            # ------------------------------------------------
            # DUPLICATE PRODUCT ID
            # ------------------------------------------------

            if (
                product_id
                in duplicate_product_ids
            ):

                failed += 1

                audit_rows.append(
                    {
                        "run_timestamp":
                            run_timestamp,
                        "product_id":
                            product_id,
                        "source_file_name":
                            source_file_name,
                        "source_row_number":
                            source_row_number,
                        "batch_id": batch_id,
                        "action": "FAILED",
                        "reason":
                            "Duplicate product_id "
                            "in stg_products",
                        "old_record_hash": "",
                        "new_record_hash":
                            new_record_hash or "",
                    }
                )

                continue

            # ------------------------------------------------
            # PRODUCT STATUS VALIDATION
            # ------------------------------------------------

            product_status = normalize_value(
                product.get("status")
            )

            if (
                product_status is not None
                and product_status
                not in ALLOWED_PRODUCT_STATUS
            ):

                failed += 1

                audit_rows.append(
                    {
                        "run_timestamp":
                            run_timestamp,
                        "product_id":
                            product_id,
                        "source_file_name":
                            source_file_name,
                        "source_row_number":
                            source_row_number,
                        "batch_id": batch_id,
                        "action": "FAILED",
                        "reason": (
                            "Invalid product status: "
                            f"{product_status}. "
                            "Allowed values are "
                            "Active, Discontinued, "
                            "Suspended."
                        ),
                        "old_record_hash": "",
                        "new_record_hash":
                            new_record_hash or "",
                    }
                )

                logger.error(
                    "Invalid status=%s "
                    "for product_id=%s",
                    product_status,
                    product_id,
                )

                continue

            # ------------------------------------------------
            # NUMERIC VALIDATION
            # ------------------------------------------------

            unit_cost = product.get(
                "unit_cost"
            )

            list_price = product.get(
                "list_price"
            )

            tax_rate_pct = product.get(
                "tax_rate_pct"
            )

            try:

                if unit_cost is not None:

                    unit_cost = float(
                        unit_cost
                    )

                    if unit_cost <= 0:
                        raise ValueError(
                            "unit_cost must be positive"
                        )

                if list_price is not None:

                    list_price = float(
                        list_price
                    )

                    if list_price <= 0:
                        raise ValueError(
                            "list_price must be positive"
                        )

                if tax_rate_pct is not None:

                    tax_rate_pct = float(
                        tax_rate_pct
                    )

                    if (
                        tax_rate_pct < 0
                        or tax_rate_pct > 100
                    ):
                        raise ValueError(
                            "tax_rate_pct must "
                            "be between 0 and 100"
                        )

            except (
                ValueError,
                TypeError,
            ) as error:

                failed += 1

                audit_rows.append(
                    {
                        "run_timestamp":
                            run_timestamp,
                        "product_id":
                            product_id,
                        "source_file_name":
                            source_file_name,
                        "source_row_number":
                            source_row_number,
                        "batch_id": batch_id,
                        "action": "FAILED",
                        "reason":
                            f"Invalid numeric product "
                            f"value: {error}",
                        "old_record_hash": "",
                        "new_record_hash":
                            new_record_hash or "",
                    }
                )

                logger.error(
                    "Invalid numeric value "
                    "for product_id=%s: %s",
                    product_id,
                    error,
                )

                continue

            product[
                "unit_cost"
            ] = unit_cost

            product[
                "list_price"
            ] = list_price

            product[
                "tax_rate_pct"
            ] = tax_rate_pct

            # ------------------------------------------------
            # CHECK EXISTING CORE PRODUCT
            # ------------------------------------------------

            existing_sql = """
                SELECT
                    product_id,
                    record_hash,
                    record_version,
                    is_current
                FROM core_products
                WHERE product_id = %s
                LIMIT 1
            """

            cursor.execute(
                existing_sql,
                (product_id,),
            )

            existing = cursor.fetchone()

            # =================================================
            # CASE 1: NEW PRODUCT
            # =================================================

            if existing is None:

                # --------------------------------------------
                # Build insert columns from the project-defined
                # business fields plus available audit fields.
                # Database-generated fields are intentionally
                # omitted.
                # --------------------------------------------

                insert_columns = [
                    "product_id",
                    "product_name",
                    "category",
                    "subcategory",
                    "brand",
                    "unit_cost",
                    "list_price",
                    "tax_rate_pct",
                    "launch_date",
                    "status",
                ]

                insert_values = [
                    product.get(
                        "product_id"
                    ),
                    product.get(
                        "product_name"
                    ),
                    product.get(
                        "category"
                    ),
                    product.get(
                        "subcategory"
                    ),
                    product.get(
                        "brand"
                    ),
                    product.get(
                        "unit_cost"
                    ),
                    product.get(
                        "list_price"
                    ),
                    product.get(
                        "tax_rate_pct"
                    ),
                    product.get(
                        "launch_date"
                    ),
                    product.get(
                        "status"
                    ),
                ]

                # --------------------------------------------
                # Add audit/source columns only when they
                # actually exist in core_products.
                # --------------------------------------------

                optional_values = {
                    "batch_id":
                        row.get("batch_id"),
                    "source_file_name":
                        row.get(
                            "source_file_name"
                        ),
                    "source_row_number":
                        row.get(
                            "source_row_number"
                        ),
                    "record_hash":
                        row.get("record_hash"),
                }

                for column, value in (
                    optional_values.items()
                ):

                    if column in target_columns:

                        insert_columns.append(
                            column
                        )

                        insert_values.append(
                            value
                        )

                placeholders = ", ".join(
                    ["%s"]
                    * len(insert_columns)
                )

                column_sql = ", ".join(
                    insert_columns
                )

                insert_sql = f"""
                    INSERT INTO core_products (
                        {column_sql}
                    )
                    VALUES (
                        {placeholders}
                    )
                """

                cursor.execute(
                    insert_sql,
                    tuple(insert_values),
                )

                inserted += 1

                audit_rows.append(
                    {
                        "run_timestamp":
                            run_timestamp,
                        "product_id":
                            product_id,
                        "source_file_name":
                            source_file_name,
                        "source_row_number":
                            source_row_number,
                        "batch_id":
                            batch_id,
                        "action":
                            "INSERTED",
                        "reason":
                            "New product_id",
                        "old_record_hash":
                            "",
                        "new_record_hash":
                            new_record_hash or "",
                    }
                )

                logger.info(
                    "INSERTED product_id=%s",
                    product_id,
                )

                continue

            # =================================================
            # EXISTING PRODUCT
            # =================================================

            old_record_hash = (
                normalize_value(
                    existing.get(
                        "record_hash"
                    )
                )
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
                        "run_timestamp":
                            run_timestamp,
                        "product_id":
                            product_id,
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

                logger.info(
                    "UNCHANGED product_id=%s",
                    product_id,
                )

                continue

            # =================================================
            # CASE 3: DIFFERENT HASH -> REVIEW
            # =================================================
            #
            # Do NOT:
            # - overwrite the existing product
            # - close existing history
            # - insert a new product version
            #
            # Those history operations belong to 05.27.
            # =================================================

            review += 1

            audit_rows.append(
                {
                    "run_timestamp":
                        run_timestamp,
                    "product_id":
                        product_id,
                    "source_file_name":
                        source_file_name,
                    "source_row_number":
                        source_row_number,
                    "batch_id":
                        batch_id,
                    "action":
                        "REVIEW",
                    "reason": (
                        "Existing product_id has "
                        "a different record_hash; "
                        "trusted product history "
                        "was not overwritten"
                    ),
                    "old_record_hash":
                        old_record_hash or "",
                    "new_record_hash":
                        new_record_hash or "",
                }
            )

            logger.warning(
                "REVIEW product_id=%s "
                "old_hash=%s new_hash=%s",
                product_id,
                old_record_hash,
                new_record_hash,
            )

        # ====================================================
        # TRANSACTION DECISION
        # ====================================================

        if failed > 0:

            connection.rollback()

            logger.error(
                "05.19 validation failed. "
                "Transaction rolled back. "
                "failed=%s",
                failed,
            )

            write_audit(
                audit_rows
            )

            print()
            print("=" * 70)
            print("05.19 STATUS: FAIL")
            print("=" * 70)

            print(
                f"Source staging rows : {total:,}"
            )

            print(
                f"Inserted attempted   : "
                f"{inserted:,}"
            )

            print(
                f"Unchanged            : "
                f"{unchanged:,}"
            )

            print(
                f"Review               : "
                f"{review:,}"
            )

            print(
                f"Failed               : "
                f"{failed:,}"
            )

            print()
            print(
                "Transaction was rolled back."
            )

            print(
                f"Audit file: {AUDIT_FILE}"
            )

            sys.exit(1)

        # ----------------------------------------------------
        # COMMIT
        # ----------------------------------------------------

        connection.commit()

        write_audit(
            audit_rows
        )

        logger.info(
            "05.19 transaction committed."
        )

        print()
        print("=" * 70)
        print("05.19 STATUS: PASS")
        print("=" * 70)

        print(
            f"Source staging rows : "
            f"{total:,}"
        )

        print(
            f"Inserted            : "
            f"{inserted:,}"
        )

        print(
            f"Unchanged           : "
            f"{unchanged:,}"
        )

        print(
            f"Review              : "
            f"{review:,}"
        )

        print(
            f"Failed              : "
            f"{failed:,}"
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

        print("=" * 70)

        logger.info(
            "05.19 product merge completed "
            "successfully."
        )

    except Exception as error:

        if connection is not None:

            try:
                connection.rollback()
            except Exception:
                pass

        logger.exception(
            "05.19 product merge failed."
        )

        write_audit(
            audit_rows
        )

        print()
        print("=" * 70)
        print("05.19 STATUS: FAIL")
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
# 12. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
"""
05.17 Validate Staging Row Counts
Retail Sales Analytics Project

Purpose:
    Validate that each staging table contains the expected number
    of rows from the approved cleaned staging CSV files.

Validation checks:
    1. Expected row count from cleaned staging CSV
    2. Actual row count in staging table
    3. Row-count difference
    4. Batch ID presence
    5. Source file presence
    6. Source-file lineage
    7. Batch-level row counts

Important:
    This step does NOT depend on etl_file_log.source_file_name.
    The staging tables themselves contain batch_id and source_file_name,
    which are used for lineage validation.
"""

from pathlib import Path
from datetime import datetime
import logging

import pandas as pd
from sqlalchemy import create_engine, text

from config import DB_CONFIG, PROCESSED_DATA_PATH, LOG_FOLDER


# ============================================================
# CONFIGURATION
# ============================================================

STAGING_FOLDER = Path(PROCESSED_DATA_PATH) / "staging"

OUTPUT_FILE = (
    Path(PROCESSED_DATA_PATH)
    / "05_17_staging_row_count_validation.csv"
)

LOG_FILE = Path(LOG_FOLDER) / "05_17_validate_staging_row_counts.log"


DATASET_CONFIG = {
    "customers": {
        "table": "stg_customers",
        "file_pattern": "customers_master_cleaned_staging.csv",
    },
    "products": {
        "table": "stg_products",
        "file_pattern": "products_master_cleaned_staging.csv",
    },
    "sales": {
        "table": "stg_sales",
        "file_pattern": "sales_2024_01_cleaned_staging.csv",
    },
}


# ============================================================
# LOGGING
# ============================================================

Path(LOG_FOLDER).mkdir(parents=True, exist_ok=True)
Path(PROCESSED_DATA_PATH).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | 05.17 | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_engine():
    """
    Create SQLAlchemy database engine using project configuration.
    """

    required_keys = [
        "host",
        "port",
        "database",
        "user",
        "password",
    ]

    missing = [
        key
        for key in required_keys
        if DB_CONFIG.get(key) in (None, "")
    ]

    if missing:
        raise RuntimeError(
            "Database configuration is incomplete. "
            f"Missing: {', '.join(missing)}"
        )

    connection_url = (
        "mysql+mysqlconnector://"
        f"{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}"
        f"/{DB_CONFIG['database']}"
    )

    return create_engine(
        connection_url,
        pool_pre_ping=True,
    )


# ============================================================
# EXPECTED ROW COUNT
# ============================================================

def get_expected_row_count(file_path):
    """
    Read the approved cleaned staging CSV and return row count.
    """

    df = pd.read_csv(
        file_path,
        dtype=str,
        low_memory=False,
    )

    return len(df)


# ============================================================
# STAGING TABLE VALIDATION
# ============================================================

def validate_staging_table(
    connection,
    dataset_name,
    table_name,
    expected_file_name,
    expected_rows,
):
    """
    Validate one staging table.
    """

    result = {
        "dataset": dataset_name,
        "table_name": table_name,
        "expected_file": expected_file_name,
        "expected_rows": expected_rows,
        "actual_rows": 0,
        "difference": 0,
        "batch_count": 0,
        "source_file_count": 0,
        "missing_batch_id_rows": 0,
        "missing_source_file_rows": 0,
        "matching_source_file_rows": 0,
        "status": "REVIEW",
        "reason": "",
    }

    # --------------------------------------------------------
    # Actual total rows
    # --------------------------------------------------------

    count_sql = text(
        f"""
        SELECT
            COUNT(*) AS actual_rows,
            COUNT(DISTINCT batch_id) AS batch_count,
            COUNT(DISTINCT source_file_name) AS source_file_count,
            SUM(
                CASE
                    WHEN batch_id IS NULL
                         OR TRIM(batch_id) = ''
                    THEN 1
                    ELSE 0
                END
            ) AS missing_batch_id_rows,
            SUM(
                CASE
                    WHEN source_file_name IS NULL
                         OR TRIM(source_file_name) = ''
                    THEN 1
                    ELSE 0
                END
            ) AS missing_source_file_rows,
            SUM(
                CASE
                    WHEN source_file_name = :expected_file
                    THEN 1
                    ELSE 0
                END
            ) AS matching_source_file_rows
        FROM {table_name}
        """
    )

    row = connection.execute(
        count_sql,
        {
            "expected_file": expected_file_name,
        },
    ).mappings().first()

    actual_rows = int(row["actual_rows"] or 0)
    batch_count = int(row["batch_count"] or 0)
    source_file_count = int(row["source_file_count"] or 0)
    missing_batch_id_rows = int(
        row["missing_batch_id_rows"] or 0
    )
    missing_source_file_rows = int(
        row["missing_source_file_rows"] or 0
    )
    matching_source_file_rows = int(
        row["matching_source_file_rows"] or 0
    )

    difference = actual_rows - expected_rows

    result["actual_rows"] = actual_rows
    result["difference"] = difference
    result["batch_count"] = batch_count
    result["source_file_count"] = source_file_count
    result["missing_batch_id_rows"] = missing_batch_id_rows
    result["missing_source_file_rows"] = missing_source_file_rows
    result["matching_source_file_rows"] = matching_source_file_rows

    # --------------------------------------------------------
    # Validation rules
    # --------------------------------------------------------

    checks = []

    checks.append(
        actual_rows == expected_rows
    )

    checks.append(
        missing_batch_id_rows == 0
    )

    checks.append(
        missing_source_file_rows == 0
    )

    checks.append(
        matching_source_file_rows == expected_rows
    )

    # Current staging load should represent one batch/file
    checks.append(
        batch_count == 1
    )

    checks.append(
        source_file_count == 1
    )

    if all(checks):
        result["status"] = "PASS"
        result["reason"] = (
            "Expected rows match staging rows and "
            "batch/source lineage is preserved."
        )
    else:
        reasons = []

        if actual_rows != expected_rows:
            reasons.append(
                f"expected {expected_rows} rows but staging contains "
                f"{actual_rows}"
            )

        if missing_batch_id_rows > 0:
            reasons.append(
                f"{missing_batch_id_rows} rows have missing batch_id"
            )

        if missing_source_file_rows > 0:
            reasons.append(
                f"{missing_source_file_rows} rows have missing source_file_name"
            )

        if matching_source_file_rows != expected_rows:
            reasons.append(
                f"{matching_source_file_rows} rows match expected "
                f"source file"
            )

        if batch_count != 1:
            reasons.append(
                f"staging contains {batch_count} distinct batch IDs"
            )

        if source_file_count != 1:
            reasons.append(
                f"staging contains {source_file_count} distinct source files"
            )

        result["reason"] = "; ".join(reasons)

    # --------------------------------------------------------
    # Print validation
    # --------------------------------------------------------

    print("-" * 70)
    print(f"Dataset                 : {dataset_name}")
    print(f"Table                   : {table_name}")
    print(f"Expected file           : {expected_file_name}")
    print(f"Expected rows           : {expected_rows}")
    print(f"Actual staging rows     : {actual_rows}")
    print(f"Difference              : {difference}")
    print(f"Batch ID count          : {batch_count}")
    print(f"Source file count       : {source_file_count}")
    print(f"Missing batch ID rows   : {missing_batch_id_rows}")
    print(f"Missing source rows     : {missing_source_file_rows}")
    print(f"Matching source rows    : {matching_source_file_rows}")
    print(f"Status                  : {result['status']}")
    print(f"Reason                  : {result['reason']}")

    logger.info(
        "%s | table=%s | expected=%s | actual=%s | "
        "difference=%s | batch_count=%s | source_file_count=%s | "
        "status=%s",
        dataset_name,
        table_name,
        expected_rows,
        actual_rows,
        difference,
        batch_count,
        source_file_count,
        result["status"],
    )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("05.17 VALIDATE STAGING ROW COUNTS")
    print("=" * 70)

    logger.info("05.17 validation started.")

    if not STAGING_FOLDER.exists():
        raise FileNotFoundError(
            f"Staging folder not found: {STAGING_FOLDER}"
        )

    engine = get_db_engine()

    results = []

    with engine.connect() as connection:

        for dataset_name, config in DATASET_CONFIG.items():

            expected_file = STAGING_FOLDER / config["file_pattern"]

            if not expected_file.exists():
                result = {
                    "dataset": dataset_name,
                    "table_name": config["table"],
                    "expected_file": config["file_pattern"],
                    "expected_rows": 0,
                    "actual_rows": 0,
                    "difference": 0,
                    "batch_count": 0,
                    "source_file_count": 0,
                    "missing_batch_id_rows": 0,
                    "missing_source_file_rows": 0,
                    "matching_source_file_rows": 0,
                    "status": "FAIL",
                    "reason": (
                        f"Expected cleaned staging file not found: "
                        f"{expected_file}"
                    ),
                }

                results.append(result)

                print("-" * 70)
                print(f"Dataset : {dataset_name}")
                print(f"Status  : FAIL")
                print(f"Reason  : {result['reason']}")

                logger.error(result["reason"])

                continue

            expected_rows = get_expected_row_count(
                expected_file
            )

            result = validate_staging_table(
                connection=connection,
                dataset_name=dataset_name,
                table_name=config["table"],
                expected_file_name=config["file_pattern"],
                expected_rows=expected_rows,
            )

            results.append(result)

    # ========================================================
    # SUMMARY
    # ========================================================

    results_df = pd.DataFrame(results)

    results_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    passed = int(
        (results_df["status"] == "PASS").sum()
    )

    review = int(
        (results_df["status"] == "REVIEW").sum()
    )

    failed = int(
        (results_df["status"] == "FAIL").sum()
    )

    expected_total = int(
        results_df["expected_rows"].sum()
    )

    actual_total = int(
        results_df["actual_rows"].sum()
    )

    total_difference = actual_total - expected_total

    # Overall status
    if failed > 0:
        overall_status = "FAIL"
    elif review > 0:
        overall_status = "REVIEW"
    else:
        overall_status = "PASS"

    print()
    print("=" * 70)
    print("05.17 VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Datasets checked        : {len(results_df)}")
    print(f"Datasets passed         : {passed}")
    print(f"Datasets review        : {review}")
    print(f"Datasets failed        : {failed}")
    print(f"Expected rows           : {expected_total}")
    print(f"Actual staging rows     : {actual_total}")
    print(f"Total difference        : {total_difference}")
    print(f"Validation file         : {OUTPUT_FILE}")
    print(f"Log file                : {LOG_FILE}")
    print("-" * 70)
    print(f"05.17 STATUS: {overall_status}")
    print("=" * 70)

    if overall_status == "PASS":
        logger.info(
            "05.17 completed successfully. "
            "All staging row counts and lineage checks passed."
        )
    elif overall_status == "REVIEW":
        logger.warning(
            "05.17 completed with datasets requiring review."
        )
    else:
        logger.error(
            "05.17 failed. One or more staging validations failed."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
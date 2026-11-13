"""
05.31 - Run Source-to-Database Reconciliation

Purpose:
1. Reconcile staging records against trusted database records.
2. Identify unmatched business keys.
3. Identify duplicate staging records and null business keys.
4. Count database-rejected records by batch and dataset.
5. Reconcile the 05.23 sales audit CSV against staging/trusted keys.
6. Display available ETL file log information.

READ-ONLY:
This script does not INSERT, UPDATE, DELETE, or TRUNCATE
any database records.
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

import mysql.connector
from config import DB_CONFIG


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SALES_AUDIT_FILE = (
    PROJECT_ROOT
    / "data"
    / "outputs"
    / "05.23_sales_incremental_insert_audit.csv"
)

DATASETS = {
    "SALES": {
        "staging_table": "stg_sales",
        "trusted_table": "factsales",
        "business_key": "sales_line_id",
        "rejected_pattern": "%sales%",
    },
    "RETURNS": {
        "staging_table": "stg_returns",
        "trusted_table": "factreturns",
        "business_key": "return_id",
        "rejected_pattern": "%return%",
    },
}


# ============================================================
# 2. DATABASE METRICS
# ============================================================

def get_batch_ids(cursor):
    """Collect batch IDs from staging tables and rejected_records."""
    batch_ids = set()

    for dataset in DATASETS.values():
        query = f"""
            SELECT DISTINCT batch_id
            FROM {dataset['staging_table']}
            WHERE batch_id IS NOT NULL
        """
        cursor.execute(query)
        batch_ids.update(
            row["batch_id"] for row in cursor.fetchall()
            if row["batch_id"] is not None
        )

    cursor.execute("""
        SELECT DISTINCT batch_id
        FROM rejected_records
        WHERE batch_id IS NOT NULL
    """)
    batch_ids.update(
        row["batch_id"] for row in cursor.fetchall()
        if row["batch_id"] is not None
    )

    return sorted(batch_ids)


def get_staging_metrics(cursor, table, business_key, batch_id):
    """Return row, distinct-key, duplicate-key and null-key metrics."""
    query = f"""
        SELECT
            COUNT(*) AS staging_rows,
            COUNT(DISTINCT {business_key}) AS unique_keys,
            SUM(
                CASE WHEN {business_key} IS NULL
                     THEN 1 ELSE 0 END
            ) AS null_key_rows
        FROM {table}
        WHERE batch_id = %s
    """
    cursor.execute(query, (batch_id,))
    row = cursor.fetchone()

    staging_rows = int(row["staging_rows"] or 0)
    unique_keys = int(row["unique_keys"] or 0)
    null_key_rows = int(row["null_key_rows"] or 0)

    duplicate_rows = max(
        0,
        staging_rows - unique_keys - null_key_rows
    )

    return {
        "staging_rows": staging_rows,
        "unique_keys": unique_keys,
        "duplicate_rows": duplicate_rows,
        "null_key_rows": null_key_rows,
    }


def get_staging_keys(cursor, table, business_key, batch_id):
    """Fetch non-null staging business keys for exact audit comparison."""
    cursor.execute(
        f"""
            SELECT {business_key} AS business_key
            FROM {table}
            WHERE batch_id = %s
              AND {business_key} IS NOT NULL
        """,
        (batch_id,),
    )
    return {
        row["business_key"]
        for row in cursor.fetchall()
    }


def get_trusted_matching_keys(
    cursor,
    staging_table,
    trusted_table,
    business_key,
    batch_id,
):
    """Fetch staging keys currently present in the trusted table."""
    cursor.execute(
        f"""
            SELECT DISTINCT s.{business_key} AS business_key
            FROM {staging_table} s
            INNER JOIN {trusted_table} t
                ON s.{business_key} = t.{business_key}
            WHERE s.batch_id = %s
              AND s.{business_key} IS NOT NULL
        """,
        (batch_id,),
    )
    return {
        row["business_key"]
        for row in cursor.fetchall()
    }


def get_rejected_count(cursor, batch_id, dataset_name):
    """Count rejected_records table entries for this batch/dataset."""
    pattern = DATASETS[dataset_name]["rejected_pattern"]

    cursor.execute(
        """
            SELECT COUNT(*) AS rejected_count
            FROM rejected_records
            WHERE batch_id = %s
              AND LOWER(dataset_name) LIKE %s
        """,
        (batch_id, pattern),
    )
    row = cursor.fetchone()
    return int(row["rejected_count"] or 0)


def get_file_log_metrics(cursor, batch_id):
    """Return ETL file-log counters, when records are available."""
    cursor.execute(
        """
            SELECT
                COUNT(*) AS log_entries,
                COALESCE(SUM(records_read), 0) AS records_read,
                COALESCE(SUM(records_staged), 0) AS records_staged,
                COALESCE(SUM(records_inserted), 0) AS records_inserted,
                COALESCE(SUM(records_updated), 0) AS records_updated,
                COALESCE(SUM(records_unchanged), 0) AS records_unchanged,
                COALESCE(SUM(records_duplicated), 0) AS records_duplicated,
                COALESCE(SUM(records_rejected), 0) AS records_rejected
            FROM etl_file_log
            WHERE batch_id = %s
        """,
        (batch_id,),
    )
    return cursor.fetchone()


# ============================================================
# 3. 05.23 SALES AUDIT CSV
# ============================================================

def load_sales_audit():
    """
    Load the existing 05.23 audit CSV.

    The CSV is evidence of the 05.23 script's row-level decisions.
    It is not treated as an ETL file-log record.
    """
    if not SALES_AUDIT_FILE.exists():
        return None

    required_columns = {
        "sales_line_id",
        "source_file_name",
        "batch_id",
        "action",
        "reason",
    }

    records = []

    with SALES_AUDIT_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        missing = required_columns - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                "05.23 audit CSV is missing required columns: "
                + ", ".join(sorted(missing))
            )

        for row in reader:
            key = (row.get("sales_line_id") or "").strip()
            batch_id = (row.get("batch_id") or "").strip()
            action = (row.get("action") or "").strip().upper()

            records.append({
                "sales_line_id": key,
                "batch_id": batch_id,
                "action": action,
                "reason": (row.get("reason") or "").strip(),
                "source_file_name": (
                    row.get("source_file_name") or ""
                ).strip(),
            })

    return records


def reconcile_sales_audit(
    audit_records,
    batch_id,
    staging_keys,
    trusted_keys,
):
    """
    Compare 05.23 audit decisions with current staging/trusted keys.

    Exact classification is confirmed only when:
    - each audit business key is present once;
    - audit keys equal staging keys;
    - INSERTED keys equal current trusted matches;
    - REJECTED keys equal unmatched staging keys.
    """
    if audit_records is None:
        return {
            "available": False,
            "aligned": False,
            "message": "05.23 audit CSV NOT AVAILABLE",
        }

    batch_records = [
        row for row in audit_records
        if row["batch_id"] == str(batch_id)
    ]

    if not batch_records:
        return {
            "available": True,
            "aligned": len(staging_keys) == 0,
            "message": "No sales staging rows in this batch (not applicable)" if len(staging_keys) == 0 else "No 05.23 audit rows found for this batch",
        }

    key_counts = Counter(
        row["sales_line_id"]
        for row in batch_records
        if row["sales_line_id"]
    )

    null_audit_keys = sum(
        1 for row in batch_records
        if not row["sales_line_id"]
    )

    duplicate_audit_keys = sum(
        count - 1 for count in key_counts.values()
        if count > 1
    )

    inserted_keys = {
        row["sales_line_id"]
        for row in batch_records
        if row["action"] == "INSERTED" and row["sales_line_id"]
    }

    rejected_keys = {
        row["sales_line_id"]
        for row in batch_records
        if row["action"] == "REJECTED" and row["sales_line_id"]
    }

    unknown_actions = sorted({
        row["action"]
        for row in batch_records
        if row["action"] not in {"INSERTED", "REJECTED"}
    })

    audit_keys = set(key_counts)
    unmatched_keys = staging_keys - trusted_keys

    checks = {
        "audit_keys_equal_staging": audit_keys == staging_keys,
        "inserted_keys_equal_trusted_matches": inserted_keys == trusted_keys,
        "rejected_keys_equal_unmatched": rejected_keys == unmatched_keys,
        "no_duplicate_audit_keys": duplicate_audit_keys == 0,
        "no_null_audit_keys": null_audit_keys == 0,
        "no_unknown_actions": len(unknown_actions) == 0,
        "all_audit_rows_classified": (
            len(inserted_keys) + len(rejected_keys)
            == len(batch_records)
        ),
    }

    aligned = all(checks.values())

    return {
        "available": True,
        "aligned": aligned,
        "audit_rows": len(batch_records),
        "inserted": len(inserted_keys),
        "rejected": len(rejected_keys),
        "duplicate_audit_keys": duplicate_audit_keys,
        "null_audit_keys": null_audit_keys,
        "unknown_actions": unknown_actions,
        "checks": checks,
        "source_files": sorted({
            row["source_file_name"]
            for row in batch_records
            if row["source_file_name"]
        }),
        "rejection_reasons": dict(Counter(
            row["reason"]
            for row in batch_records
            if row["action"] == "REJECTED"
        )),
    }


# ============================================================
# 4. DATASET RECONCILIATION
# ============================================================

def reconcile_dataset(
    cursor,
    batch_id,
    dataset_name,
    dataset,
    sales_audit_records,
):
    """Reconcile one dataset for one batch."""
    staging_table = dataset["staging_table"]
    trusted_table = dataset["trusted_table"]
    business_key = dataset["business_key"]

    print()
    print(f"DATASET: {dataset_name}")
    print("-" * 68)

    staging = get_staging_metrics(
        cursor,
        staging_table,
        business_key,
        batch_id,
    )

    staging_keys = get_staging_keys(
        cursor,
        staging_table,
        business_key,
        batch_id,
    )

    trusted_keys = get_trusted_matching_keys(
        cursor,
        staging_table,
        trusted_table,
        business_key,
        batch_id,
    )

    unmatched_keys = staging_keys - trusted_keys
    db_rejected_count = get_rejected_count(
        cursor,
        batch_id,
        dataset_name,
    )

    print(f"Staging rows              : {staging['staging_rows']:,}")
    print(f"Distinct business keys    : {staging['unique_keys']:,}")
    print(f"Duplicate staging rows    : {staging['duplicate_rows']:,}")
    print(f"Null business-key rows    : {staging['null_key_rows']:,}")
    print(f"Trusted matching keys     : {len(trusted_keys):,}")
    print(f"Unmatched staging keys    : {len(unmatched_keys):,}")
    print(f"rejected_records entries  : {db_rejected_count:,}")

    audit_result = None

    if dataset_name == "SALES":
        audit_result = reconcile_sales_audit(
            sales_audit_records,
            batch_id,
            staging_keys,
            trusted_keys,
        )

        print()
        print("05.23 SALES AUDIT CSV RECONCILIATION")
        print("-" * 68)

        if not audit_result["available"]:
            print(audit_result["message"])
        elif "audit_rows" not in audit_result:
            print(audit_result["message"])
        else:
            print(f"Audit CSV rows            : {audit_result['audit_rows']:,}")
            print(f"Audit INSERTED keys       : {audit_result['inserted']:,}")
            print(f"Audit REJECTED keys       : {audit_result['rejected']:,}")
            print(
                f"Duplicate audit keys      : "
                f"{audit_result['duplicate_audit_keys']:,}"
            )
            print(
                f"Null audit keys           : "
                f"{audit_result['null_audit_keys']:,}"
            )

            if audit_result["source_files"]:
                print(
                    "Source file(s)             : "
                    + "; ".join(audit_result["source_files"])
                )

            if audit_result["rejection_reasons"]:
                print("Rejected reason breakdown :")
                for reason, count in audit_result["rejection_reasons"].items():
                    print(f"  {reason}: {count:,}")

            print("Audit-to-database checks  :")
            for check_name, passed in audit_result["checks"].items():
                label = check_name.replace("_", " ")
                print(f"  {label:<42}: {'PASS' if passed else 'FAIL'}")

            print(
                "Sales audit reconciliation: "
                + ("ALIGNED" if audit_result["aligned"] else "REVIEW REQUIRED")
            )

    # An unmatched key is classified as rejected only when the sales
    # audit CSV proves an exact one-to-one match with the unmatched keys.
    classified_unmatched = 0
    unclassified_unmatched = len(unmatched_keys)

    if (
        dataset_name == "SALES"
        and audit_result is not None
        and audit_result.get("aligned")
    ):
        classified_unmatched = len(unmatched_keys)
        unclassified_unmatched = 0

    dataset_aligned = (
        staging["duplicate_rows"] == 0
        and staging["null_key_rows"] == 0
        and unclassified_unmatched == 0
        and (
            dataset_name != "SALES"
            or (
                audit_result is not None
                and audit_result.get("aligned", False)
            )
        )
    )

    print(f"Unmatched classified      : {classified_unmatched:,}")
    print(f"Unmatched unclassified    : {unclassified_unmatched:,}")
    print(
        "Dataset reconciliation   : "
        + ("ALIGNED" if dataset_aligned else "REVIEW REQUIRED")
    )

    return {
        "staging_rows": staging["staging_rows"],
        "unique_keys": staging["unique_keys"],
        "matched_keys": len(trusted_keys),
        "unmatched_keys": len(unmatched_keys),
        "classified_unmatched": classified_unmatched,
        "unclassified_unmatched": unclassified_unmatched,
        "duplicate_rows": staging["duplicate_rows"],
        "null_key_rows": staging["null_key_rows"],
        "db_rejected_count": db_rejected_count,
        "audit_result": audit_result,
        "aligned": dataset_aligned,
    }


# ============================================================
# 5. MAIN RECONCILIATION
# ============================================================

def main():
    connection = None
    cursor = None
    sales_audit_records = load_sales_audit()

    totals = defaultdict(int)
    review_required = False
    file_log_unavailable = False

    print()
    print("=" * 76)
    print("05.31 - RUN SOURCE-TO-DATABASE RECONCILIATION")
    print("=" * 76)
    print("Connecting to database...")

    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)

        print("Database connection: SUCCESS")
        print("Reconciliation mode: READ-ONLY")
        print(
            "05.23 audit CSV      : "
            + (
                str(SALES_AUDIT_FILE)
                if sales_audit_records is not None
                else "NOT AVAILABLE"
            )
        )
        print("-" * 76)

        batch_ids = get_batch_ids(cursor)

        if not batch_ids:
            print("No staging or rejected-record batches found.")
            print("05.31 STATUS: REVIEW REQUIRED")
            return

        print(f"Unique batches identified: {len(batch_ids):,}")

        for batch_id in batch_ids:
            totals["batches"] += 1

            print()
            print("=" * 76)
            print(f"BATCH ID: {batch_id}")
            print("=" * 76)

            for dataset_name, dataset in DATASETS.items():
                result = reconcile_dataset(
                    cursor,
                    batch_id,
                    dataset_name,
                    dataset,
                    sales_audit_records,
                )

                for key in (
                    "staging_rows",
                    "unique_keys",
                    "matched_keys",
                    "unmatched_keys",
                    "classified_unmatched",
                    "unclassified_unmatched",
                    "duplicate_rows",
                    "null_key_rows",
                    "db_rejected_count",
                ):
                    totals[key] += result[key]

                if not result["aligned"]:
                    review_required = True

            print()
            print("FILE-LEVEL ETL AUDIT")
            print("-" * 68)

            log_metrics = get_file_log_metrics(cursor, batch_id)

            if int(log_metrics["log_entries"] or 0) == 0:
                file_log_unavailable = True
                print("ETL file log entries      : NOT AVAILABLE")
                print("Historical insert/update counters cannot be verified.")
            else:
                print(f"ETL log entries           : {log_metrics['log_entries']:,}")
                print(f"Records read              : {log_metrics['records_read']:,}")
                print(f"Records staged            : {log_metrics['records_staged']:,}")
                print(f"Records inserted          : {log_metrics['records_inserted']:,}")
                print(f"Records updated           : {log_metrics['records_updated']:,}")
                print(f"Records unchanged         : {log_metrics['records_unchanged']:,}")
                print(f"Records duplicated        : {log_metrics['records_duplicated']:,}")
                print(f"Records rejected          : {log_metrics['records_rejected']:,}")

        print()
        print("=" * 76)
        print("SOURCE-TO-DATABASE RECONCILIATION SUMMARY")
        print("=" * 76)
        print(f"Batches processed         : {totals['batches']:,}")
        print(f"Staging rows              : {totals['staging_rows']:,}")
        print(f"Distinct staging keys     : {totals['unique_keys']:,}")
        print(f"Trusted matching keys     : {totals['matched_keys']:,}")
        print(f"Unmatched staging keys    : {totals['unmatched_keys']:,}")
        print(f"Unmatched classified      : {totals['classified_unmatched']:,}")
        print(f"Unmatched unclassified    : {totals['unclassified_unmatched']:,}")
        print(f"Duplicate staging rows    : {totals['duplicate_rows']:,}")
        print(f"Null business-key rows    : {totals['null_key_rows']:,}")
        print(f"Database rejected records : {totals['db_rejected_count']:,}")
        print("-" * 76)

        print(
            "NOTE: Audit CSV INSERTED/REJECTED actions are used only "
            "when their keys exactly reconcile to staging and trusted data."
        )
        print(
            "Current trusted-key presence does not independently prove "
            "historical insert/update attribution."
        )
        print(
            "The 05.23 audit CSV is not a substitute for etl_file_log "
            "or rejected_records history."
        )

        if review_required:
            print("05.31 STATUS: REVIEW REQUIRED")
        elif file_log_unavailable:
            print("05.31 STATUS: PASS WITH AUDIT LIMITATIONS")
        else:
            print("05.31 STATUS: PASS")

        print("=" * 76)

    except mysql.connector.Error as db_error:
        print()
        print(f"Database Error: {db_error}")
        print("05.31 STATUS: FAILED")
        raise

    except Exception as error:
        print()
        print(f"Unexpected Error: {error}")
        print("05.31 STATUS: FAILED")
        raise

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main()


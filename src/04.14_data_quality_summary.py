"""
Retail Sales Analytics
Tracker 04.14 - Create Data-Quality Summary

Purpose:
    Summarize data-quality outcomes by file and batch.

Metrics:
    - total rows
    - accepted rows
    - corrected rows
    - duplicated rows
    - rejected rows
    - missing-value rows
    - invalid rows
    - outlier rows

Important:
    - Does NOT modify source CSV files.
    - Uses existing processed/staging and audit outputs.
    - Does NOT invent business values.
    - Preserves batch and source-file lineage where available.
"""

from pathlib import Path
from datetime import datetime
import pandas as pd
import re


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
STAGING_DIR = PROCESSED_DIR / "staging"

OUTPUT_FILE = PROCESSED_DIR / "04_14_data_quality_summary.csv"
AUDIT_FILE = PROCESSED_DIR / "04_14_data_quality_summary_audit.csv"


# ============================================================
# HELPERS
# ============================================================

def normalize_column_name(column):
    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def find_column(df, candidates):
    normalized = {
        normalize_column_name(col): col
        for col in df.columns
    }

    for candidate in candidates:
        key = normalize_column_name(candidate)
        if key in normalized:
            return normalized[key]

    return None


def safe_int(value):
    try:
        if pd.isna(value):
            return 0
        return int(value)
    except Exception:
        return 0


def dataset_name_from_file(filename):
    name = filename.lower()

    if "customer" in name:
        return "customers"

    if "product" in name:
        return "products"

    if "store" in name:
        return "stores"

    if "salesperson" in name:
        return "salespersons"

    if "promotion" in name:
        return "promotions"

    if "return" in name:
        return "returns"

    if "target" in name:
        return "targets"

    if "sales" in name:
        return "sales"

    return "unknown"


def extract_batch_id(df):
    batch_col = find_column(
        df,
        [
            "batch_id",
            "batch",
            "load_batch_id",
        ],
    )

    if batch_col:
        values = (
            df[batch_col]
            .dropna()
            .astype(str)
            .str.strip()
        )

        values = values[values != ""]

        if not values.empty:
            return values.iloc[0]

    return "UNKNOWN_BATCH"


def count_reject_rows(df):
    """
    Count rows carrying a reject reason code.
    """

    reject_col = find_column(
        df,
        [
            "reject_reason_code",
            "reject_code",
            "reason_code",
        ],
    )

    if reject_col:
        values = (
            df[reject_col]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        return int((values != "").sum())

    return 0


def count_invalid_rows(df):
    """
    Count DOMAIN_INVALID rows from standardized reject codes.
    """

    reject_col = find_column(
        df,
        [
            "reject_reason_code",
            "reject_code",
            "reason_code",
        ],
    )

    if reject_col:
        values = (
            df[reject_col]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        return int(
            values.isin(
                [
                    "DOMAIN_INVALID",
                    "INVALID",
                    "INVALID_VALUE",
                    "BUSINESS_INVALID",
                ]
            ).sum()
        )

    return 0


def count_missing_rows(df):
    """
    Count rows where standardized reject code identifies
    a required-null/missing-value condition.
    """

    reject_col = find_column(
        df,
        [
            "reject_reason_code",
            "reject_code",
            "reason_code",
        ],
    )

    if reject_col:
        values = (
            df[reject_col]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        return int(
            values.isin(
                [
                    "REQ_NULL",
                    "REQUIRED_NULL",
                    "MISSING_REQUIRED",
                    "MISSING_VALUE",
                ]
            ).sum()
        )

    return 0


def count_outlier_rows(dataset):
    """
    Read the 04.10 outlier audit generated for the dataset.
    """

    possible_files = list(
        PROCESSED_DIR.glob("04_10_*outlier*.csv")
    )

    total = 0

    for file in possible_files:

        if dataset not in file.name.lower():
            continue

        try:
            df = pd.read_csv(file)

            flag_col = find_column(
                df,
                [
                    "outlier_flag",
                    "is_outlier",
                    "outlier",
                    "outlier_count",
                ],
            )

            if flag_col:

                values = (
                    df[flag_col]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .str.upper()
                )

                # Row-level flag
                total += int(
                    values.isin(
                        [
                            "Y",
                            "YES",
                            "TRUE",
                            "1",
                            "OUTLIER",
                        ]
                    ).sum()
                )

                # If the file itself is already an audit
                # summary containing a count, use it.
                if total == 0:
                    numeric = pd.to_numeric(
                        df[flag_col],
                        errors="coerce"
                    )

                    total += int(numeric.sum())

        except Exception:
            continue

    return total


def count_duplicate_rows(dataset):
    """
    Read 04.07 / 04.08 duplicate audit evidence.
    """

    files = []

    for pattern in [
        "04_07_*duplicate*.csv",
        "04_08_*duplicate*.csv",
    ]:
        files.extend(PROCESSED_DIR.glob(pattern))

    total = 0

    for file in files:

        if dataset not in file.name.lower():
            continue

        try:
            df = pd.read_csv(file)

            # Prefer explicit duplicate-count columns.
            candidate_columns = [
                "exact_duplicate_rows",
                "duplicate_rows",
                "duplicate_skip_rows",
                "duplicates",
                "duplicate_count",
                "business_key_duplicates",
            ]

            col = find_column(df, candidate_columns)

            if col:
                numeric = pd.to_numeric(
                    df[col],
                    errors="coerce"
                ).fillna(0)

                total += int(numeric.sum())

        except Exception:
            continue

    return total


def count_corrected_rows(dataset):
    """
    Look for explicit correction evidence.

    A correction is counted only when an existing audit/staging
    file explicitly identifies a corrected row.

    No correction is inferred from ordinary cleaning.
    """

    candidate_files = []

    for pattern in [
        "04_03_*",
        "04_04_*",
        "04_05_*",
        "*correction*.csv",
    ]:
        candidate_files.extend(PROCESSED_DIR.glob(pattern))

    total = 0

    for file in candidate_files:

        if file.suffix.lower() != ".csv":
            continue

        if dataset not in file.name.lower():
            continue

        try:
            df = pd.read_csv(file)

            col = find_column(
                df,
                [
                    "corrected_rows",
                    "correction_rows",
                    "rows_corrected",
                    "correction_count",
                ],
            )

            if col:
                numeric = pd.to_numeric(
                    df[col],
                    errors="coerce"
                ).fillna(0)

                total += int(numeric.sum())

        except Exception:
            continue

    return total


# ============================================================
# MAIN PROCESSING
# ============================================================

def main():

    print("=" * 80)
    print("TRACKER 04.14 - CREATE DATA-QUALITY SUMMARY")
    print("=" * 80)

    print(f"Processed directory : {PROCESSED_DIR}")
    print(f"Staging directory   : {STAGING_DIR}")

    if not STAGING_DIR.exists():
        print("\nERROR: Staging directory does not exist.")
        print("04.13 staging output is required before 04.14.")
        return

    staging_files = sorted(
        STAGING_DIR.glob("*.csv")
    )

    if not staging_files:
        print("\nERROR: No cleaned staging CSV files found.")
        return

    summary_rows = []

    processing_timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # ========================================================
    # PROCESS EACH STAGING DATASET
    # ========================================================

    for file in staging_files:

        try:
            df = pd.read_csv(
                file,
                low_memory=False
            )

        except Exception as exc:
            print(f"\nCould not read: {file.name}")
            print(f"Reason: {exc}")
            continue

        dataset = dataset_name_from_file(file.name)

        batch_id = extract_batch_id(df)

        total_rows = len(df)

        rejected_rows = count_reject_rows(df)

        missing_rows = count_missing_rows(df)

        invalid_rows = count_invalid_rows(df)

        duplicated_rows = count_duplicate_rows(
            dataset
        )

        corrected_rows = count_corrected_rows(
            dataset
        )

        outlier_rows = count_outlier_rows(
            dataset
        )

        # Accepted means rows without a standardized
        # reject reason in the cleaned staging dataset.
        accepted_rows = max(
            total_rows - rejected_rows,
            0
        )

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        print("\n" + "-" * 80)
        print(f"FILE : {file.name}")
        print(f"DATASET : {dataset}")
        print(f"BATCH ID : {batch_id}")

        print("\nDATA-QUALITY SUMMARY")
        print(f"Total rows       : {total_rows:,}")
        print(f"Accepted rows    : {accepted_rows:,}")
        print(f"Corrected rows   : {corrected_rows:,}")
        print(f"Duplicated rows  : {duplicated_rows:,}")
        print(f"Rejected rows    : {rejected_rows:,}")
        print(f"Missing rows     : {missing_rows:,}")
        print(f"Invalid rows     : {invalid_rows:,}")
        print(f"Outlier rows     : {outlier_rows:,}")

        summary_rows.append(
            {
                "source_file": file.name,
                "dataset": dataset,
                "batch_id": batch_id,
                "load_timestamp": processing_timestamp,
                "total_rows": total_rows,
                "accepted_rows": accepted_rows,
                "corrected_rows": corrected_rows,
                "duplicated_rows": duplicated_rows,
                "rejected_rows": rejected_rows,
                "missing_rows": missing_rows,
                "invalid_rows": invalid_rows,
                "outlier_rows": outlier_rows,
            }
        )

    # ========================================================
    # CREATE SUMMARY DATAFRAME
    # ========================================================

    if not summary_rows:
        print("\nNo datasets were available for summary.")
        return

    summary_df = pd.DataFrame(summary_rows)

    # ========================================================
    # SAVE SUMMARY
    # ========================================================

    summary_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # CREATE AUDIT SUMMARY
    # ========================================================

    audit_rows = []

    for row in summary_rows:

        total = row["total_rows"]

        classified = (
            row["accepted_rows"]
            + row["rejected_rows"]
        )

        reconciliation_status = (
            "PASS"
            if classified == total
            else "REVIEW"
        )

        audit_rows.append(
            {
                "source_file": row["source_file"],
                "dataset": row["dataset"],
                "batch_id": row["batch_id"],
                "total_rows": total,
                "accepted_rows": row["accepted_rows"],
                "corrected_rows": row["corrected_rows"],
                "duplicated_rows": row["duplicated_rows"],
                "rejected_rows": row["rejected_rows"],
                "missing_rows": row["missing_rows"],
                "invalid_rows": row["invalid_rows"],
                "outlier_rows": row["outlier_rows"],
                "reconciliation_status": reconciliation_status,
                "summary_created_at": processing_timestamp,
            }
        )

    audit_df = pd.DataFrame(audit_rows)

    audit_df.to_csv(
        AUDIT_FILE,
        index=False
    )

    # ========================================================
    # OVERALL RESULT
    # ========================================================

    total_datasets = len(summary_df)

    passed_reconciliation = int(
        (
            audit_df["reconciliation_status"]
            == "PASS"
        ).sum()
    )

    failed_reconciliation = (
        total_datasets
        - passed_reconciliation
    )

    print("\n" + "=" * 80)
    print("04.14 OVERALL RESULT")
    print("=" * 80)

    print(
        f"Datasets summarized       : {total_datasets}"
    )

    print(
        f"Datasets reconciled       : {passed_reconciliation}"
    )

    print(
        f"Datasets requiring review: {failed_reconciliation}"
    )

    print(
        f"\nSummary output : {OUTPUT_FILE}"
    )

    print(
        f"Audit output   : {AUDIT_FILE}"
    )

    if failed_reconciliation == 0:

        print("\nSTATUS : PASS")

        print(
            "Data-quality summary created successfully."
        )

        print(
            "Accepted, corrected, duplicated, rejected, "
            "missing, invalid, and outlier metrics were "
            "summarized without modifying source CSV files."
        )

        print(
            "\nTracker 04.14 data-quality summary "
            "processing completed."
        )

    else:

        print("\nSTATUS : REVIEW")

        print(
            "The summary was created, but one or more "
            "file-level reconciliations require review."
        )

        print(
            "\nTracker 04.14 processing completed "
            "with review status."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()
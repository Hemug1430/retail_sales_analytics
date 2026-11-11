"""
RETAIL SALES ANALYTICS
TRACKER 04.07 - HANDLE EXACT DUPLICATE ROWS

Requirement:
Detect and remove/route duplicate rows according to dataset-specific
duplicate rules while preserving audit evidence.

Project rules:
- Sales:
    Repeated sales_line_id or repeated identical line content
    must not be double-counted.
- Orders:
    Repeated order_id alone is NOT a duplicate.
- Master datasets:
    Repeated business key or identical repeated row is flagged.
- Returns:
    Repeated return_id is a duplicate.
- Targets:
    Target grain is target_month + store_id + category.
    Conflicting target values are NOT silently combined.
- Row exact detection:
    Business key + normalized record hash.
- Original source data is never overwritten.
"""

from pathlib import Path
from datetime import datetime
import hashlib
import json
import re

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INCOMING_DIR = PROJECT_ROOT / "incoming"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# OUTPUT FILES
# ============================================================

AUDIT_FILE = PROCESSED_DIR / "04_07_exact_duplicate_row_audit.csv"

SUMMARY_FILE = PROCESSED_DIR / "04_07_exact_duplicate_row_summary.csv"


# ============================================================
# DATASET RULES
# ============================================================

DATASET_CONFIG = {

    "customers_master": {
        "dataset_type": "customers",
        "business_keys": ["customer_id"],
    },

    "products_master": {
        "dataset_type": "products",
        "business_keys": ["product_id"],
    },

    "stores_master": {
        "dataset_type": "stores",
        "business_keys": ["store_id"],
    },

    "salespersons_master": {
        "dataset_type": "salespersons",
        "business_keys": ["salesperson_id"],
    },

    "promotions_master": {
        "dataset_type": "promotions",
        "business_keys": ["promotion_id"],
    },

    "returns": {
        "dataset_type": "returns",
        "business_keys": ["return_id"],
    },

    "targets": {
        "dataset_type": "targets",
        "business_keys": [
            "target_month",
            "store_id",
            "category",
        ],
    },

    "sales": {
        "dataset_type": "sales",
        "business_keys": ["sales_line_id"],
    },
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_dataset_name(file_name: str) -> str:
    """
    Convert a file name into a logical dataset name.

    Examples:
        customers_master.csv
        sales_2024_01.csv
        sales_2024-01.csv
        sales_2024_01_04_06_missing_values_handled.csv
    """

    name = Path(file_name).stem.lower()

    # Remove processing suffixes.
    suffixes = [
        "_04_06_missing_values_handled",
        "_04_05_numeric_cleaned",
        "_04_04_date_standardized",
        "_04_03_standardized",
        "_04_02_standardized",
        "_04_01_standardized",
        "_numeric_cleaned",
        "_date_standardized",
        "_standardized",
        "_processed",
    ]

    for suffix in suffixes:
        name = name.replace(suffix, "")

    # Remove monthly date portion.
    name = re.sub(r"[_-]\d{4}[_-]\d{2}$", "", name)

    return name


def get_dataset_config(file_name: str):
    """
    Return the applicable dataset configuration.
    """

    dataset_name = clean_dataset_name(file_name)

    # Sales files
    if dataset_name == "sales":
        return DATASET_CONFIG["sales"]

    # Returns files
    if dataset_name == "returns":
        return DATASET_CONFIG["returns"]

    # Targets files
    if dataset_name == "targets":
        return DATASET_CONFIG["targets"]

    # Master datasets
    if dataset_name in DATASET_CONFIG:
        return DATASET_CONFIG[dataset_name]

    return None


def normalize_value(value):
    """
    Normalize a value only for duplicate comparison.

    This does NOT modify the source/output business value.
    """

    if pd.isna(value):
        return ""

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(value, ".15g")

    if isinstance(value, int):
        return str(value)

    value = str(value)

    # Normalize whitespace for comparison.
    value = value.replace("\r\n", "\n")
    value = value.replace("\r", "\n")
    value = " ".join(value.split())

    return value.strip()


def normalized_row_payload(row: pd.Series, columns):
    """
    Build deterministic normalized representation of a row.
    """

    payload = {}

    for column in columns:
        payload[column] = normalize_value(row[column])

    return payload


def calculate_record_hash(row: pd.Series, columns) -> str:
    """
    Calculate SHA-256 hash from normalized row content.
    """

    payload = normalized_row_payload(row, columns)

    serialized = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def find_source_files():
    """
    Prefer the latest processed 04.06 outputs when available.

    If a 04.06 output does not exist for a dataset, fall back to
    the original incoming file.

    This keeps 04.07 connected to the previous ETL cleaning step
    without modifying the source files.
    """

    selected = {}

    # --------------------------------------------------------
    # First: look for 04.06 processed files
    # --------------------------------------------------------

    processed_files = list(
        PROCESSED_DIR.glob("*.csv")
    )

    for file_path in processed_files:

        file_name = file_path.name.lower()

        if "_04_06_missing_values_handled.csv" not in file_name:
            continue

        dataset_name = clean_dataset_name(file_path.name)

        # Keep one file per logical dataset/month.
        selected[file_path.name] = file_path

    # --------------------------------------------------------
    # Then: include incoming files that don't have a processed
    # 04.06 equivalent.
    # --------------------------------------------------------

    incoming_files = sorted(
        INCOMING_DIR.glob("*.csv")
    )

    for incoming_file in incoming_files:

        dataset_name = clean_dataset_name(
            incoming_file.name
        )

        # Detect whether a processed version of the same
        # logical source already exists.
        source_stem = incoming_file.stem.lower()

        has_processed_version = False

        for processed_file in selected.values():

            processed_name = processed_file.name.lower()

            if source_stem in processed_name:
                has_processed_version = True
                break

        if not has_processed_version:
            selected[incoming_file.name] = incoming_file

    return sorted(
        selected.values(),
        key=lambda p: p.name.lower()
    )


def determine_duplicate_status(
    dataset_config,
    row_hash,
    seen_hashes,
    business_key_value,
    seen_business_keys,
):
    """
    Determine whether a row is an exact duplicate,
    a business-key conflict, or unique.

    Exact duplicate:
        Same normalized row hash.

    Business-key conflict:
        Same business key but different row content.

    Unique:
        New row/business key.
    """

    if row_hash in seen_hashes:
        return "DUPLICATE", seen_hashes[row_hash]

    if business_key_value is not None:

        if business_key_value in seen_business_keys:
            previous_hash = seen_business_keys[
                business_key_value
            ]

            if previous_hash != row_hash:
                return "BUSINESS_KEY_CONFLICT", previous_hash

    return "UNIQUE", ""


def make_business_key(
    row,
    business_keys,
):
    """
    Create deterministic business-key value.

    Important:
    order_id is deliberately NOT used as the sales duplicate key.
    """

    values = []

    for key in business_keys:

        if key not in row.index:
            return None

        value = normalize_value(row[key])

        if value == "":
            return None

        values.append(
            f"{key}={value}"
        )

    return "|".join(values)


# ============================================================
# PROCESS ONE FILE
# ============================================================

def process_file(file_path: Path):

    config = get_dataset_config(
        file_path.name
    )

    if config is None:
        print(
            f"SKIPPED: Unsupported dataset file: "
            f"{file_path.name}"
        )
        return None

    dataset_type = config["dataset_type"]
    business_keys = config["business_keys"]

    print()
    print("=" * 80)
    print(
        "TRACKER 04.07 - EXACT DUPLICATE ROW HANDLING"
    )
    print("=" * 80)

    print(f"Input file : {file_path}")
    print(f"Dataset    : {dataset_type}")
    print(f"Business key(s): {', '.join(business_keys)}")

    # --------------------------------------------------------
    # Read source
    # --------------------------------------------------------

    try:

        df = pd.read_csv(
            file_path,
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
        )

    except Exception as exc:

        print(
            f"ERROR reading {file_path.name}: {exc}"
        )

        return {
            "source_file": file_path.name,
            "dataset_type": dataset_type,
            "status": "READ_ERROR",
            "rows_read": 0,
            "duplicate_rows": 0,
            "conflict_rows": 0,
            "unique_rows": 0,
        }

    rows_read = len(df)

    print(f"Rows read  : {rows_read}")
    print(f"Columns    : {len(df.columns)}")

    # --------------------------------------------------------
    # Validate business-key columns where applicable
    # --------------------------------------------------------

    missing_keys = [
        key
        for key in business_keys
        if key not in df.columns
    ]

    if missing_keys:

        print()
        print(
            "WARNING: Required business-key column(s) "
            "not available:"
        )
        print(", ".join(missing_keys))

        # For this exact-duplicate step, we can still
        # perform whole-row exact duplicate detection.

    # --------------------------------------------------------
    # Calculate normalized row hashes
    # --------------------------------------------------------

    columns = list(df.columns)

    row_hashes = []

    for _, row in df.iterrows():

        row_hash = calculate_record_hash(
            row,
            columns
        )

        row_hashes.append(row_hash)

    df["_record_hash_04_07"] = row_hashes

    # --------------------------------------------------------
    # Detect duplicates and conflicts
    # --------------------------------------------------------

    seen_hashes = {}
    seen_business_keys = {}

    audit_records = []

    duplicate_indices = set()

    conflict_indices = set()

    unique_count = 0

    duplicate_count = 0

    conflict_count = 0

    for index, row in df.iterrows():

        row_hash = row["_record_hash_04_07"]

        business_key_value = make_business_key(
            row,
            business_keys
        )

        status, previous_hash = determine_duplicate_status(
            config,
            row_hash,
            seen_hashes,
            business_key_value,
            seen_business_keys,
        )

        source_row_number = index + 2

        # ----------------------------------------------------
        # UNIQUE
        # ----------------------------------------------------

        if status == "UNIQUE":

            unique_count += 1

            seen_hashes[row_hash] = source_row_number

            if business_key_value is not None:
                seen_business_keys[
                    business_key_value
                ] = row_hash

            continue

        # ----------------------------------------------------
        # EXACT DUPLICATE
        # ----------------------------------------------------

        if status == "DUPLICATE":

            duplicate_count += 1

            duplicate_indices.add(index)

            audit_records.append(
                {
                    "audit_timestamp":
                        datetime.now().isoformat(
                            timespec="seconds"
                        ),

                    "source_file":
                        file_path.name,

                    "dataset_type":
                        dataset_type,

                    "source_row_number":
                        source_row_number,

                    "business_key":
                        business_key_value or "",

                    "record_hash":
                        row_hash,

                    "duplicate_of_row":
                        previous_hash,

                    "status":
                        "DUPLICATE",

                    "action":
                        "ROUTE_DUPLICATE",

                    "reason":
                        "Exact normalized row duplicate",
                }
            )

            continue

        # ----------------------------------------------------
        # SAME BUSINESS KEY, DIFFERENT CONTENT
        # ----------------------------------------------------

        if status == "BUSINESS_KEY_CONFLICT":

            conflict_count += 1

            conflict_indices.add(index)

            audit_records.append(
                {
                    "audit_timestamp":
                        datetime.now().isoformat(
                            timespec="seconds"
                        ),

                    "source_file":
                        file_path.name,

                    "dataset_type":
                        dataset_type,

                    "source_row_number":
                        source_row_number,

                    "business_key":
                        business_key_value or "",

                    "record_hash":
                        row_hash,

                    "duplicate_of_row":
                        "",

                    "status":
                        "BUSINESS_KEY_CONFLICT",

                    "action":
                        "ROUTE_FOR_REVIEW",

                    "reason":
                        "Same business key with different "
                        "normalized row content",
                }
            )

            # Do NOT silently remove the conflict here.
            # It requires later update/conflict handling.

            continue

    # --------------------------------------------------------
    # Create clean output
    # --------------------------------------------------------

    output_df = df.drop(
        columns=["_record_hash_04_07"]
    ).copy()

    # Exact duplicate rows are removed from the processed
    # business output.
    #
    # Business-key conflicts are retained for later controlled
    # conflict/update handling because the project explicitly
    # says not to arbitrarily choose one.

    if duplicate_indices:

        output_df = output_df.drop(
            index=list(duplicate_indices)
        )

    output_df = output_df.reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Output file name
    # --------------------------------------------------------

    output_name = (
        f"{file_path.stem}"
        f"_04_07_duplicates_handled.csv"
    )

    output_path = (
        PROCESSED_DIR / output_name
    )

    output_df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Add audit records
    # --------------------------------------------------------

    for record in audit_records:

        record["output_file"] = output_name

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print()
    print("-" * 80)
    print("DUPLICATE HANDLING SUMMARY")
    print("-" * 80)

    print(
        f"Total rows processed       : {rows_read:,}"
    )

    print(
        f"Unique rows                : {unique_count:,}"
    )

    print(
        f"Exact duplicate rows       : {duplicate_count:,}"
    )

    print(
        f"Business-key conflicts     : {conflict_count:,}"
    )

    print(
        f"Rows in processed output   : {len(output_df):,}"
    )

    print()
    print(
        f"Processed output:"
    )
    print(output_path)

    return {
        "source_file": file_path.name,
        "dataset_type": dataset_type,
        "status": "PASS",
        "rows_read": rows_read,
        "unique_rows": unique_count,
        "duplicate_rows": duplicate_count,
        "conflict_rows": conflict_count,
        "output_rows": len(output_df),
        "output_file": output_name,
        "audit_records": audit_records,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TRACKER 04.07 - HANDLE EXACT DUPLICATE ROWS")
    print("=" * 80)

    print()
    print(
        "Detecting exact duplicate rows using normalized "
        "record hashes."
    )

    print(
        "Original source files will not be modified."
    )

    print()

    source_files = find_source_files()

    if not source_files:

        print(
            "ERROR: No supported input files were found."
        )

        return

    all_audit_records = []

    summary_records = []

    total_rows = 0
    total_duplicates = 0
    total_conflicts = 0

    # --------------------------------------------------------
    # Process each source file
    # --------------------------------------------------------

    for file_path in source_files:

        result = process_file(
            file_path
        )

        if result is None:
            continue

        summary_records.append(
            {
                "processed_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "source_file":
                    result["source_file"],

                "dataset_type":
                    result["dataset_type"],

                "status":
                    result["status"],

                "rows_read":
                    result["rows_read"],

                "unique_rows":
                    result["unique_rows"],

                "exact_duplicate_rows":
                    result["duplicate_rows"],

                "business_key_conflicts":
                    result["conflict_rows"],

                "output_rows":
                    result["output_rows"],

                "output_file":
                    result["output_file"],
            }
        )

        all_audit_records.extend(
            result["audit_records"]
        )

        total_rows += result["rows_read"]

        total_duplicates += result["duplicate_rows"]

        total_conflicts += result["conflict_rows"]

    # --------------------------------------------------------
    # Write audit evidence
    # --------------------------------------------------------

    audit_columns = [
        "audit_timestamp",
        "source_file",
        "dataset_type",
        "source_row_number",
        "business_key",
        "record_hash",
        "duplicate_of_row",
        "status",
        "action",
        "reason",
        "output_file",
    ]

    if all_audit_records:

        audit_df = pd.DataFrame(
            all_audit_records
        )

        audit_df = audit_df.reindex(
            columns=audit_columns
        )

    else:

        audit_df = pd.DataFrame(
            columns=audit_columns
        )

    audit_df.to_csv(
        AUDIT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Write summary
    # --------------------------------------------------------

    summary_df = pd.DataFrame(
        summary_records
    )

    summary_df.to_csv(
        SUMMARY_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Overall result
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("04.07 OVERALL RESULT")
    print("=" * 80)

    print(
        f"Files processed             : {len(summary_records)}"
    )

    print(
        f"Rows processed              : {total_rows:,}"
    )

    print(
        f"Exact duplicates detected  : {total_duplicates:,}"
    )

    print(
        f"Business-key conflicts      : {total_conflicts:,}"
    )

    print()
    print(
        "Audit output:"
    )
    print(AUDIT_FILE)

    print()
    print(
        "Summary output:"
    )
    print(SUMMARY_FILE)

    print()

    if total_duplicates > 0:
        print(
            "Exact duplicates were routed out of "
            "the processed business outputs and "
            "preserved in the audit evidence."
        )
    else:
        print(
            "No exact duplicate rows were found in "
            "the files processed."
        )

    if total_conflicts > 0:
        print(
            "NOTE: Business-key conflicts were preserved "
            "for controlled conflict/update handling; "
            "they were NOT silently removed."
        )

    print()
    print("=" * 80)
    print(
        "Tracker 04.07 exact duplicate row handling "
        "processing completed."
    )
    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
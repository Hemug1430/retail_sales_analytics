from pathlib import Path
from datetime import datetime
import hashlib
import json
import uuid
import pandas as pd


# ============================================================
# TRACKER 04.13
# CREATE CLEANED STAGING DATASETS
# ============================================================
#
# Requirement:
# Produce cleaned/wrangled dataframes retaining:
# - source_file
# - batch_id
# - load timestamps
# - validation metadata
#
# Important:
# - Does NOT modify incoming/source CSV files.
# - Preserves metadata already created by previous steps.
# - Does NOT create duplicate metadata columns.
# - Uses the 04.12 reject-reason-code outputs as input.
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(".")

PROCESSED_DIR = BASE_DIR / "data" / "processed"

STAGING_DIR = PROCESSED_DIR / "staging"

STAGING_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# BATCH ID
# ============================================================

def create_batch_id():

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    unique_part = uuid.uuid4().hex[:6].upper()

    return f"BATCH_{timestamp}_{unique_part}"


# ============================================================
# NORMALIZE VALUE FOR HASHING
# ============================================================

def normalize_value(value):

    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    return str(value).strip()


# ============================================================
# CREATE RECORD HASH
# ============================================================

def create_record_hash(row, excluded_columns=None):

    if excluded_columns is None:
        excluded_columns = set()

    record = {}

    for column in row.index:

        if column in excluded_columns:
            continue

        record[column] = normalize_value(
            row[column]
        )

    payload = json.dumps(
        record,
        sort_keys=True,
        ensure_ascii=False,
        default=str
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


# ============================================================
# ADD COLUMN ONLY IF IT DOES NOT ALREADY EXIST
# ============================================================

def add_column_if_missing(
    df,
    column_name,
    values
):

    if column_name not in df.columns:

        df[column_name] = values

    return df


# ============================================================
# PRESERVE / CREATE SOURCE ROW NUMBER
# ============================================================

def ensure_source_row_number(df):

    if "source_row_number" in df.columns:

        return df

    # CSV row number:
    # Header = row 1
    # First data row = row 2

    df["source_row_number"] = (
        range(2, len(df) + 2)
    )

    return df


# ============================================================
# PRESERVE / CREATE SOURCE FILE NAME
# ============================================================

def ensure_source_file_name(
    df,
    source_file_name
):

    if "source_file_name" not in df.columns:

        df["source_file_name"] = (
            source_file_name
        )

    return df


# ============================================================
# PRESERVE / CREATE BATCH ID
# ============================================================

def ensure_batch_id(
    df,
    batch_id
):

    if "batch_id" not in df.columns:

        df["batch_id"] = batch_id

    return df


# ============================================================
# PRESERVE / CREATE LOAD TIMESTAMP
# ============================================================

def ensure_load_timestamp(
    df,
    load_timestamp
):

    if "load_timestamp" not in df.columns:

        df["load_timestamp"] = (
            load_timestamp
        )

    return df


# ============================================================
# PRESERVE / CREATE RECORD HASH
# ============================================================

def ensure_record_hash(df):

    if "record_hash" in df.columns:

        return df

    excluded_columns = {
        "batch_id",
        "source_file_name",
        "source_row_number",
        "record_hash",
        "load_timestamp",
        "created_at",
        "updated_at"
    }

    df["record_hash"] = df.apply(
        lambda row: create_record_hash(
            row,
            excluded_columns
        ),
        axis=1
    )

    return df


# ============================================================
# VALIDATION METADATA
# ============================================================

def preserve_validation_metadata(df):

    # --------------------------------------------------------
    # These columns are created by earlier validation steps.
    # If they already exist, they are preserved unchanged.
    # --------------------------------------------------------

    validation_columns = [
        "validation_status",
        "validation_result",
        "reject_reason_code",
        "reject_reason",
        "business_validation_status",
        "business_validation_result",
        "outlier_flag",
        "outlier_reason",
        "foreign_key_status",
        "foreign_key_result"
    ]

    existing_validation_columns = [
        column
        for column in validation_columns
        if column in df.columns
    ]

    # --------------------------------------------------------
    # If no explicit validation-status column exists,
    # derive a non-destructive staging status from the
    # reject reason code when available.
    # --------------------------------------------------------

    if (
        "validation_status" not in df.columns
        and "reject_reason_code" in df.columns
    ):

        reject_values = (
            df["reject_reason_code"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        df["validation_status"] = (
            reject_values
            .apply(
                lambda value:
                "REVIEW"
                if value
                and value.lower() != "nan"
                else "PASS"
            )
        )

        existing_validation_columns.append(
            "validation_status"
        )

    return df, existing_validation_columns


# ============================================================
# CLEAN DATAFRAME FOR STAGING
# ============================================================

def prepare_staging_dataframe(
    df,
    source_file_name,
    batch_id,
    load_timestamp
):

    # --------------------------------------------------------
    # Remove completely empty rows only.
    # No business values are imputed here.
    # --------------------------------------------------------

    df = df.dropna(
        how="all"
    ).copy()

    # --------------------------------------------------------
    # Preserve metadata already present.
    # --------------------------------------------------------

    df = ensure_source_row_number(
        df
    )

    df = ensure_source_file_name(
        df,
        source_file_name
    )

    df = ensure_batch_id(
        df,
        batch_id
    )

    df = ensure_load_timestamp(
        df,
        load_timestamp
    )

    # --------------------------------------------------------
    # Preserve validation metadata.
    # --------------------------------------------------------

    df, validation_columns = (
        preserve_validation_metadata(df)
    )

    # --------------------------------------------------------
    # Record hash is calculated after all cleaning/validation
    # columns are available, but audit fields are excluded.
    # --------------------------------------------------------

    df = ensure_record_hash(
        df
    )

    return df, validation_columns


# ============================================================
# FIND 04.12 INPUT FILES
# ============================================================

def find_04_12_files():

    pattern = (
        "*_04_12_reject_reason_codes.csv"
    )

    files = sorted(
        PROCESSED_DIR.glob(pattern)
    )

    return files


# ============================================================
# DATASET NAME
# ============================================================

def determine_dataset_name(
    file_name
):

    name = file_name

    suffix = (
        "_04_12_reject_reason_codes.csv"
    )

    if name.endswith(suffix):

        name = name[:-len(suffix)]

    # --------------------------------------------------------
    # Remove previous processing suffixes if present.
    # --------------------------------------------------------

    processing_suffixes = [
        "_04_11_business_validation",
        "_04_10_outlier_flags",
        "_04_09_foreign_key_validation",
        "_04_08_business_key_duplicates_handled",
        "_04_07_duplicates_handled",
        "_04_06_missing_values_handled",
        "_04_05_numeric_cleaned",
        "_04_04_date_standardized",
        "_04_03_product_category_standardized"
    ]

    for suffix_value in processing_suffixes:

        if name.endswith(
            suffix_value
        ):

            name = name[
                :-len(suffix_value)
            ]

    return name


# ============================================================
# CREATE ONE STAGING DATASET
# ============================================================

def create_staging_dataset(
    input_file,
    batch_id,
    load_timestamp
):

    print("\n" + "=" * 80)

    print(
        "04.13 CLEANED STAGING DATASET"
    )

    print("=" * 80)

    print(
        f"Input file : {input_file}"
    )

    # --------------------------------------------------------
    # READ DATA
    # --------------------------------------------------------

    df = pd.read_csv(
        input_file,
        encoding="utf-8-sig",
        low_memory=False
    )

    original_rows = len(df)

    original_columns = len(
        df.columns
    )

    print(
        f"Rows read : {original_rows:,}"
    )

    print(
        f"Columns : {original_columns}"
    )

    # --------------------------------------------------------
    # PREPARE STAGING DATAFRAME
    # --------------------------------------------------------

    df, validation_columns = (
        prepare_staging_dataframe(
            df,
            input_file.name,
            batch_id,
            load_timestamp
        )
    )

    # --------------------------------------------------------
    # DATASET NAME
    # --------------------------------------------------------

    dataset_name = (
        determine_dataset_name(
            input_file.name
        )
    )

    # --------------------------------------------------------
    # OUTPUT FILE
    # --------------------------------------------------------

    output_file = (
        STAGING_DIR
        / f"{dataset_name}_cleaned_staging.csv"
    )

    # --------------------------------------------------------
    # WRITE STAGING DATASET
    # --------------------------------------------------------

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # VERIFY OUTPUT
    # --------------------------------------------------------

    verification_df = pd.read_csv(
        output_file,
        encoding="utf-8-sig",
        low_memory=False
    )

    verification_rows = len(
        verification_df
    )

    verification_columns = len(
        verification_df.columns
    )

    # --------------------------------------------------------
    # REQUIRED METADATA CHECK
    # --------------------------------------------------------

    required_metadata = [
        "source_file_name",
        "batch_id",
        "source_row_number",
        "record_hash",
        "load_timestamp"
    ]

    missing_metadata = [
        column
        for column in required_metadata
        if column not in verification_df.columns
    ]

    if missing_metadata:

        status = "FAIL"

        message = (
            "Missing required staging metadata: "
            + ", ".join(missing_metadata)
        )

    elif verification_rows != len(df):

        status = "FAIL"

        message = (
            "Output row count does not match "
            "the processed dataframe."
        )

    else:

        status = "PASS"

        message = (
            "Cleaned staging dataset created "
            "and verified successfully."
        )

    # --------------------------------------------------------
    # VALIDATION METADATA SUMMARY
    # --------------------------------------------------------

    validation_count = len(
        validation_columns
    )

    reject_count = 0

    if "reject_reason_code" in df.columns:

        reject_values = (
            df["reject_reason_code"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        reject_count = int(
            (
                (reject_values != "")
                &
                (
                    reject_values.str.lower()
                    != "nan"
                )
            ).sum()
        )

    # --------------------------------------------------------
    # OUTPUT SUMMARY
    # --------------------------------------------------------

    print("\nSTAGING DATASET SUMMARY")
    print("-" * 80)

    print(
        f"Dataset : {dataset_name}"
    )

    print(
        f"Rows processed : {len(df):,}"
    )

    print(
        f"Rows written : {verification_rows:,}"
    )

    print(
        f"Columns written : {verification_columns}"
    )

    print(
        f"Validation metadata columns : "
        f"{validation_count}"
    )

    print(
        f"Rows with reject reason : "
        f"{reject_count:,}"
    )

    print(
        f"Source file metadata : "
        f"{'YES' if 'source_file_name' in verification_df.columns else 'NO'}"
    )

    print(
        f"Batch ID metadata : "
        f"{'YES' if 'batch_id' in verification_df.columns else 'NO'}"
    )

    print(
        f"Source row metadata : "
        f"{'YES' if 'source_row_number' in verification_df.columns else 'NO'}"
    )

    print(
        f"Record hash metadata : "
        f"{'YES' if 'record_hash' in verification_df.columns else 'NO'}"
    )

    print(
        f"Load timestamp metadata : "
        f"{'YES' if 'load_timestamp' in verification_df.columns else 'NO'}"
    )

    print(
        f"Status : {status}"
    )

    print(
        f"Message : {message}"
    )

    print(
        f"Output : {output_file}"
    )

    return {
        "dataset": dataset_name,
        "input_file": str(input_file),
        "output_file": str(output_file),
        "rows_read": original_rows,
        "rows_written": verification_rows,
        "columns_written": verification_columns,
        "validation_metadata_columns": validation_count,
        "reject_rows": reject_count,
        "status": status,
        "message": message
    }


# ============================================================
# WRITE 04.13 AUDIT SUMMARY
# ============================================================

def write_audit_summary(
    results,
    batch_id,
    load_timestamp
):

    audit_file = (
        PROCESSED_DIR
        / "04_13_cleaned_staging_audit.csv"
    )

    audit_df = pd.DataFrame(
        results
    )

    audit_df.insert(
        0,
        "batch_id",
        batch_id
    )

    audit_df.insert(
        1,
        "load_timestamp",
        load_timestamp
    )

    audit_df.to_csv(
        audit_file,
        index=False,
        encoding="utf-8-sig"
    )

    return audit_file


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)

    print(
        "TRACKER 04.13 - CREATE CLEANED STAGING DATASETS"
    )

    print("=" * 80)

    batch_id = create_batch_id()

    load_timestamp = (
        datetime.now()
        .strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print(
        f"Batch ID : {batch_id}"
    )

    print(
        f"Load timestamp : {load_timestamp}"
    )

    print(
        f"Processed dir : {PROCESSED_DIR.resolve()}"
    )

    print(
        f"Staging dir : {STAGING_DIR.resolve()}"
    )

    # --------------------------------------------------------
    # FIND 04.12 FILES
    # --------------------------------------------------------

    input_files = find_04_12_files()

    if not input_files:

        print("\nERROR")
        print(
            "No 04.12 reject-reason-code files were found."
        )

        print(
            f"Expected location: "
            f"{PROCESSED_DIR.resolve()}"
        )

        return

    print(
        f"\n04.12 input files found : "
        f"{len(input_files)}"
    )

    # --------------------------------------------------------
    # PROCESS ALL DATASETS
    # --------------------------------------------------------

    results = []

    for input_file in input_files:

        try:

            result = create_staging_dataset(
                input_file,
                batch_id,
                load_timestamp
            )

            results.append(
                result
            )

        except Exception as error:

            print("\nPROCESSING ERROR")
            print(
                f"File : {input_file.name}"
            )

            print(
                f"Error : "
                f"{type(error).__name__}: {error}"
            )

            results.append(
                {
                    "dataset":
                        determine_dataset_name(
                            input_file.name
                        ),
                    "input_file":
                        str(input_file),
                    "output_file":
                        "",
                    "rows_read":
                        0,
                    "rows_written":
                        0,
                    "columns_written":
                        0,
                    "validation_metadata_columns":
                        0,
                    "reject_rows":
                        0,
                    "status":
                        "FAIL",
                    "message":
                        f"{type(error).__name__}: {error}"
                }
            )

    # --------------------------------------------------------
    # WRITE AUDIT SUMMARY
    # --------------------------------------------------------

    audit_file = write_audit_summary(
        results,
        batch_id,
        load_timestamp
    )

    # --------------------------------------------------------
    # OVERALL STATUS
    # --------------------------------------------------------

    failed = [
        result
        for result in results
        if result["status"] == "FAIL"
    ]

    passed = [
        result
        for result in results
        if result["status"] == "PASS"
    ]

    overall_status = (
        "FAIL"
        if failed
        else "PASS"
    )

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    print("\n" + "=" * 80)

    print(
        "04.13 OVERALL RESULT"
    )

    print("=" * 80)

    print(
        f"Datasets discovered : "
        f"{len(input_files)}"
    )

    print(
        f"Datasets passed : "
        f"{len(passed)}"
    )

    print(
        f"Datasets failed : "
        f"{len(failed)}"
    )

    print(
        f"Overall status : "
        f"{overall_status}"
    )

    print(
        f"\nStaging directory : "
        f"{STAGING_DIR.resolve()}"
    )

    print(
        f"Audit summary : "
        f"{audit_file.resolve()}"
    )

    print(
        "\nCleaned staging datasets were created "
        "without modifying the source CSV files."
    )

    print(
        "Existing validation and audit metadata "
        "was preserved."
    )

    print(
        "Duplicate metadata columns were not created."
    )

    print("\n" + "=" * 80)

    if overall_status == "PASS":

        print(
            "Tracker 04.13 cleaned staging dataset "
            "processing completed."
        )

    else:

        print(
            "Tracker 04.13 processing completed "
            "with one or more failures. Review the "
            "audit summary before marking complete."
        )

    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
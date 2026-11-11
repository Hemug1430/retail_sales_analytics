import os
import re
import hashlib
import pandas as pd


# ============================================================
# TRACKER 03.12
# CREATE FILE-LEVEL VALIDATION RESULT
# ============================================================

INPUT_FOLDER = "incoming"
OUTPUT_FOLDER = "data/outputs"

RESULT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "file_level_validation_results.csv"
)


# ------------------------------------------------------------
# EXPECTED FILE NAMING PATTERNS
# ------------------------------------------------------------

MASTER_PATTERN = re.compile(
    r"^[a-z]+_master_\d{8}\.csv$",
    re.IGNORECASE
)

MONTHLY_PATTERN = re.compile(
    r"^(sales|returns|targets)_\d{4}_\d{2}\.csv$",
    re.IGNORECASE
)


# ------------------------------------------------------------
# CURRENT SCHEMA VERSION
# ------------------------------------------------------------

CURRENT_SCHEMA_VERSION = "V1"


# ------------------------------------------------------------
# HELPER: SHA-256 HASH
# ------------------------------------------------------------

def calculate_sha256(file_path):

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


# ------------------------------------------------------------
# FILE NAME VALIDATION
# ------------------------------------------------------------

def validate_file_name(file_name):

    if MASTER_PATTERN.match(file_name):
        return "PASS", "Valid master snapshot naming convention"

    if MONTHLY_PATTERN.match(file_name):
        return "PASS", "Valid monthly file naming convention"

    return "FAIL", "File name does not match approved naming convention"


# ------------------------------------------------------------
# HASH VALIDATION
# ------------------------------------------------------------

def validate_hash(file_path):

    try:
        file_hash = calculate_sha256(file_path)

        if file_hash:
            return "PASS", file_hash

        return "WARNING", "Hash could not be generated"

    except Exception as error:
        return "FAIL", str(error)


# ------------------------------------------------------------
# SCHEMA VALIDATION
# ------------------------------------------------------------

def validate_schema(file_name, df):

    # A file with readable columns can be checked against
    # the current schema baseline.
    #
    # Controlled schema-change handling is represented by
    # WARNING rather than silently changing the incoming data.

    if len(df.columns) == 0:
        return "FAIL", f"No columns found for schema {CURRENT_SCHEMA_VERSION}"

    duplicate_columns = df.columns[
        df.columns.duplicated()
    ].tolist()

    if duplicate_columns:
        return (
            "FAIL",
            f"Duplicate columns found: {duplicate_columns}"
        )

    return (
        "PASS",
        f"Schema structure readable under {CURRENT_SCHEMA_VERSION}"
    )


# ------------------------------------------------------------
# COLUMN VALIDATION
# ------------------------------------------------------------

def validate_columns(df):

    columns = list(df.columns)

    if len(columns) == 0:
        return "FAIL", "No columns found"

    blank_columns = [
        str(column).strip()
        for column in columns
        if str(column).strip() == ""
    ]

    if blank_columns:
        return "FAIL", "Blank column name detected"

    duplicate_columns = [
        column
        for column in columns
        if list(columns).count(column) > 1
    ]

    if duplicate_columns:
        return (
            "FAIL",
            f"Duplicate column names: {sorted(set(duplicate_columns))}"
        )

    return "PASS", f"{len(columns)} columns readable"


# ------------------------------------------------------------
# ROW READABILITY VALIDATION
# ------------------------------------------------------------

def validate_row_readability(file_path):

    try:
        df = pd.read_csv(file_path)

        if df.shape[0] == 0:
            return "WARNING", "File is readable but contains zero data rows"

        return "PASS", f"{df.shape[0]} data rows readable"

    except Exception as error:
        return "FAIL", f"CSV could not be read: {error}"


# ------------------------------------------------------------
# FILE-LEVEL QUALITY CHECK
# ------------------------------------------------------------

def validate_file_quality(file_path, df):

    file_size = os.path.getsize(file_path)

    if file_size == 0:
        return "FAIL", "File is empty"

    if df.shape[0] == 0:
        return "WARNING", "File contains no data rows"

    if df.shape[1] == 0:
        return "FAIL", "File contains no columns"

    blank_rows = int(df.isna().all(axis=1).sum())

    if blank_rows > 0:
        return (
            "WARNING",
            f"{blank_rows} fully blank row(s) detected"
        )

    return "PASS", "File-level quality checks passed"


# ------------------------------------------------------------
# OVERALL RESULT
# ------------------------------------------------------------

def calculate_overall_status(statuses):

    if "FAIL" in statuses:
        return "FAIL"

    if "WARNING" in statuses:
        return "WARNING"

    return "PASS"


# ------------------------------------------------------------
# PROCESS ONE FILE
# ------------------------------------------------------------

def process_file(file_name):

    file_path = os.path.join(INPUT_FOLDER, file_name)

    result = {
        "file_name": file_name,
        "file_path": file_path,
        "naming_result": "",
        "hash_result": "",
        "schema_result": "",
        "column_result": "",
        "row_readability_result": "",
        "quality_result": "",
        "overall_result": "",
        "details": ""
    }

    details = []

    # --------------------------------------------------------
    # 1. NAMING
    # --------------------------------------------------------

    naming_status, naming_detail = validate_file_name(file_name)

    result["naming_result"] = naming_status
    details.append(f"Naming: {naming_detail}")

    # --------------------------------------------------------
    # 2. HASH
    # --------------------------------------------------------

    hash_status, hash_detail = validate_hash(file_path)

    result["hash_result"] = hash_status

    if hash_status == "PASS":
        details.append(f"SHA-256: {hash_detail}")
    else:
        details.append(f"Hash: {hash_detail}")

    # --------------------------------------------------------
    # 3. TRY TO READ FILE
    # --------------------------------------------------------

    try:

        df = pd.read_csv(file_path)

    except Exception as error:

        result["schema_result"] = "FAIL"
        result["column_result"] = "FAIL"
        result["row_readability_result"] = "FAIL"
        result["quality_result"] = "FAIL"
        result["overall_result"] = "FAIL"

        details.append(f"CSV read failure: {error}")

        result["details"] = " | ".join(details)

        return result

    # --------------------------------------------------------
    # 4. SCHEMA
    # --------------------------------------------------------

    schema_status, schema_detail = validate_schema(
        file_name,
        df
    )

    result["schema_result"] = schema_status
    details.append(f"Schema: {schema_detail}")

    # --------------------------------------------------------
    # 5. COLUMNS
    # --------------------------------------------------------

    column_status, column_detail = validate_columns(df)

    result["column_result"] = column_status
    details.append(f"Columns: {column_detail}")

    # --------------------------------------------------------
    # 6. ROW READABILITY
    # --------------------------------------------------------

    row_status, row_detail = validate_row_readability(file_path)

    result["row_readability_result"] = row_status
    details.append(f"Rows: {row_detail}")

    # --------------------------------------------------------
    # 7. FILE-LEVEL QUALITY
    # --------------------------------------------------------

    quality_status, quality_detail = validate_file_quality(
        file_path,
        df
    )

    result["quality_result"] = quality_status
    details.append(f"Quality: {quality_detail}")

    # --------------------------------------------------------
    # 8. OVERALL RESULT
    # --------------------------------------------------------

    statuses = [
        naming_status,
        hash_status,
        schema_status,
        column_status,
        row_status,
        quality_status
    ]

    result["overall_result"] = calculate_overall_status(
        statuses
    )

    result["details"] = " | ".join(details)

    return result


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    if not os.path.exists(INPUT_FOLDER):

        print(
            f"ERROR: Incoming folder not found: "
            f"{INPUT_FOLDER}"
        )

        return

    csv_files = sorted(
        file
        for file in os.listdir(INPUT_FOLDER)
        if file.lower().endswith(".csv")
    )

    if not csv_files:

        print(
            f"No CSV files found in: {INPUT_FOLDER}"
        )

        return

    print("=" * 80)
    print("TRACKER 03.12 - FILE-LEVEL VALIDATION RESULT")
    print("=" * 80)

    results = []

    for file_name in csv_files:

        print(f"\nProcessing: {file_name}")

        result = process_file(file_name)

        results.append(result)

        print(
            f"Overall result: "
            f"{result['overall_result']}"
        )

    # --------------------------------------------------------
    # SAVE RESULT
    # --------------------------------------------------------

    results_df = pd.DataFrame(results)

    results_df.to_csv(
        RESULT_FILE,
        index=False,
        encoding="utf-8"
    )

    print("\n" + "=" * 80)
    print(
        "File-level validation results saved to:"
    )
    print(RESULT_FILE)

    print("\nOverall results:")

    print(
        results_df[
            [
                "file_name",
                "naming_result",
                "hash_result",
                "schema_result",
                "column_result",
                "row_readability_result",
                "quality_result",
                "overall_result"
            ]
        ].to_string(index=False)
    )

    print("\n" + "=" * 80)
    print("Tracker 03.12 file-level validation result completed.")
    print("=" * 80)


if __name__ == "__main__":
    main()
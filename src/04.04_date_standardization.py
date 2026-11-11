"""
Retail Sales Analytics
Tracker Step: 04.04 Standardize dates

Requirement:
Parse supported incoming date formats and convert accepted dates
to the project standard.

Project standard:
YYYY-MM-DD

Rules:
- Parse the expected YYYY-MM-DD format first.
- Allow only deterministic, unambiguous alternate formats.
- Reject impossible calendar dates.
- Preserve original values in the audit output.
- Do not modify files under incoming/.
- Write standardized files to data/processed/.
"""

from pathlib import Path
import pandas as pd
import re


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = PROJECT_ROOT / "incoming"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# DATE COLUMN DEFINITIONS
# ============================================================

DATE_COLUMNS = {
    "customers_master.csv": [
        "date_of_birth",
        "registration_date",
    ],

    "products_master.csv": [
        "launch_date",
    ],

    "stores_master.csv": [
        "opening_date",
    ],

    "salespersons_master.csv": [
        "joining_date",
    ],

    "promotions_master.csv": [
        "start_date",
        "end_date",
    ],

    "sales_YYYY_MM.csv": [
        "order_date",
    ],

    "returns_YYYY_MM.csv": [
        "return_date",
    ],

    "targets_YYYY_MM.csv": [
        "target_month",
    ],
}


# ============================================================
# HELPER: DETERMINE DATE COLUMNS
# ============================================================

def get_date_columns(filename, dataframe):
    """
    Return the date columns applicable to the current file.

    Monthly files are identified by their filename pattern.
    """

    if filename in DATE_COLUMNS:
        expected = DATE_COLUMNS[filename]

    elif re.match(r"^sales_\d{4}_\d{2}\.csv$", filename):
        expected = DATE_COLUMNS["sales_YYYY_MM.csv"]

    elif re.match(r"^returns_\d{4}_\d{2}\.csv$", filename):
        expected = DATE_COLUMNS["returns_YYYY_MM.csv"]

    elif re.match(r"^targets_\d{4}_\d{2}\.csv$", filename):
        expected = DATE_COLUMNS["targets_YYYY_MM.csv"]

    else:
        expected = []

    return [column for column in expected if column in dataframe.columns]


# ============================================================
# HELPER: PARSE ONE DATE VALUE
# ============================================================

def parse_date_value(value):
    """
    Parse a date deterministically.

    Accepted:
        YYYY-MM-DD
        YYYY/MM/DD
        DD-MM-YYYY
        DD/MM/YYYY

    The primary project format YYYY-MM-DD is checked first.

    Ambiguous formats such as:
        MM/DD/YYYY
        DD/MM/YYYY

    are not interpreted using guesswork.

    Since DD/MM/YYYY is explicitly treated as a deterministic
    day-first format, it is accepted.

    Impossible dates return None.
    """

    if pd.isna(value):
        return None, "BLANK", ""

    raw = str(value).strip()

    if raw == "":
        return None, "BLANK", ""

    # --------------------------------------------------------
    # 1. Project standard: YYYY-MM-DD
    # --------------------------------------------------------

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):

        parsed = pd.to_datetime(
            raw,
            format="%Y-%m-%d",
            errors="coerce"
        )

        if pd.isna(parsed):
            return None, "INVALID_DATE", raw

        return parsed.strftime("%Y-%m-%d"), "STANDARD", raw

    # --------------------------------------------------------
    # 2. Deterministic alternate: YYYY/MM/DD
    # --------------------------------------------------------

    if re.fullmatch(r"\d{4}/\d{2}/\d{2}", raw):

        parsed = pd.to_datetime(
            raw,
            format="%Y/%m/%d",
            errors="coerce"
        )

        if pd.isna(parsed):
            return None, "INVALID_DATE", raw

        return parsed.strftime("%Y-%m-%d"), "REPAIRED", raw

    # --------------------------------------------------------
    # 3. Deterministic alternate: DD-MM-YYYY
    # --------------------------------------------------------

    if re.fullmatch(r"\d{2}-\d{2}-\d{4}", raw):

        parsed = pd.to_datetime(
            raw,
            format="%d-%m-%Y",
            errors="coerce"
        )

        if pd.isna(parsed):
            return None, "INVALID_DATE", raw

        return parsed.strftime("%Y-%m-%d"), "REPAIRED", raw

    # --------------------------------------------------------
    # 4. Deterministic alternate: DD/MM/YYYY
    # --------------------------------------------------------

    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", raw):

        parsed = pd.to_datetime(
            raw,
            format="%d/%m/%Y",
            errors="coerce"
        )

        if pd.isna(parsed):
            return None, "INVALID_DATE", raw

        return parsed.strftime("%Y-%m-%d"), "REPAIRED", raw

    # --------------------------------------------------------
    # 5. Anything else is unsupported
    # --------------------------------------------------------

    return None, "UNSUPPORTED_FORMAT", raw


# ============================================================
# PROCESS ONE FILE
# ============================================================

def process_file(input_path):

    filename = input_path.name

    print("\n" + "=" * 80)
    print("04.04 DATE STANDARDIZATION")
    print("=" * 80)

    print(f"Input file : {input_path}")

    try:
        df = pd.read_csv(
            input_path,
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False
        )
    except Exception as exc:
        print(f"ERROR reading file: {exc}")
        return {
            "file_name": filename,
            "status": "FAIL",
            "rows": 0,
            "date_columns": "",
            "standardized_values": 0,
            "repaired_values": 0,
            "invalid_dates": 0,
            "unsupported_formats": 0,
            "blank_dates": 0,
            "error": str(exc)
        }

    date_columns = get_date_columns(filename, df)

    print(f"Rows read  : {len(df):,}")
    print(f"Columns     : {len(df.columns)}")
    print(
        "Date columns: "
        + (", ".join(date_columns) if date_columns else "None")
    )

    # --------------------------------------------------------
    # No applicable date columns
    # --------------------------------------------------------

    if not date_columns:

        output_path = OUTPUT_DIR / f"{input_path.stem}_date_standardized.csv"

        df.to_csv(
            output_path,
            index=False,
            encoding="utf-8-sig"
        )

        print("No applicable date columns found.")
        print(f"Output: {output_path}")

        return {
            "file_name": filename,
            "status": "PASS",
            "rows": len(df),
            "date_columns": "",
            "standardized_values": 0,
            "repaired_values": 0,
            "invalid_dates": 0,
            "unsupported_formats": 0,
            "blank_dates": 0,
            "error": ""
        }

    # --------------------------------------------------------
    # Audit records
    # --------------------------------------------------------

    audit_records = []

    standardized_count = 0
    repaired_count = 0
    invalid_count = 0
    unsupported_count = 0
    blank_count = 0

    # --------------------------------------------------------
    # Process each date column
    # --------------------------------------------------------

    for column in date_columns:

        original_values = df[column].copy()

        for row_index, value in original_values.items():

            normalized, result_type, raw_value = parse_date_value(value)

            row_number = row_index + 2

            if result_type == "STANDARD":

                standardized_count += 1

                df.at[row_index, column] = normalized

            elif result_type == "REPAIRED":

                repaired_count += 1

                df.at[row_index, column] = normalized

                audit_records.append({
                    "file_name": filename,
                    "row_number": row_number,
                    "column_name": column,
                    "original_value": raw_value,
                    "normalized_value": normalized,
                    "result": "REPAIRED",
                    "reason": "Deterministic date format normalization"
                })

            elif result_type == "BLANK":

                blank_count += 1

                # Keep legitimate blank values unchanged.
                df.at[row_index, column] = ""

                audit_records.append({
                    "file_name": filename,
                    "row_number": row_number,
                    "column_name": column,
                    "original_value": "",
                    "normalized_value": "",
                    "result": "BLANK",
                    "reason": "Source date value is blank"
                })

            elif result_type == "INVALID_DATE":

                invalid_count += 1

                # Do not silently convert an impossible date.
                df.at[row_index, column] = raw_value

                audit_records.append({
                    "file_name": filename,
                    "row_number": row_number,
                    "column_name": column,
                    "original_value": raw_value,
                    "normalized_value": "",
                    "result": "INVALID_DATE",
                    "reason": "Impossible calendar date"
                })

            elif result_type == "UNSUPPORTED_FORMAT":

                unsupported_count += 1

                # Preserve original value for investigation.
                df.at[row_index, column] = raw_value

                audit_records.append({
                    "file_name": filename,
                    "row_number": row_number,
                    "column_name": column,
                    "original_value": raw_value,
                    "normalized_value": "",
                    "result": "UNSUPPORTED_FORMAT",
                    "reason": "Date format is not an approved deterministic format"
                })

    # --------------------------------------------------------
    # Output standardized file
    # --------------------------------------------------------

    output_path = OUTPUT_DIR / f"{input_path.stem}_date_standardized.csv"

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Audit output
    # --------------------------------------------------------

    audit_path = (
        OUTPUT_DIR
        / f"{input_path.stem}_04_04_date_standardization_audit.csv"
    )

    if audit_records:

        audit_df = pd.DataFrame(audit_records)

    else:

        audit_df = pd.DataFrame(
            columns=[
                "file_name",
                "row_number",
                "column_name",
                "original_value",
                "normalized_value",
                "result",
                "reason"
            ]
        )

    audit_df.to_csv(
        audit_path,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Determine status
    # --------------------------------------------------------

    if invalid_count > 0 or unsupported_count > 0:
        status = "REVIEW"

    else:
        status = "PASS"

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print("\nDATE STANDARDIZATION SUMMARY")
    print("-" * 80)

    print(f"Total rows processed       : {len(df):,}")
    print(f"Date columns processed     : {len(date_columns)}")
    print(f"Standard dates             : {standardized_count:,}")
    print(f"Dates deterministically repaired: {repaired_count:,}")
    print(f"Blank dates                : {blank_count:,}")
    print(f"Invalid dates              : {invalid_count:,}")
    print(f"Unsupported formats        : {unsupported_count:,}")
    print(f"Overall status             : {status}")

    print("\nStandardized output:")
    print(output_path)

    print("\nAudit output:")
    print(audit_path)

    return {
        "file_name": filename,
        "status": status,
        "rows": len(df),
        "date_columns": ", ".join(date_columns),
        "standardized_values": standardized_count,
        "repaired_values": repaired_count,
        "invalid_dates": invalid_count,
        "unsupported_formats": unsupported_count,
        "blank_dates": blank_count,
        "error": ""
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TRACKER 04.04 - STANDARDIZE DATES")
    print("=" * 80)

    if not INPUT_DIR.exists():

        print(f"ERROR: Input directory not found: {INPUT_DIR}")
        return

    csv_files = sorted(INPUT_DIR.glob("*.csv"))

    if not csv_files:

        print("ERROR: No CSV files found in incoming directory.")
        return

    results = []

    for input_path in csv_files:

        result = process_file(input_path)
        results.append(result)

    # --------------------------------------------------------
    # Overall summary
    # --------------------------------------------------------

    summary_df = pd.DataFrame(results)

    summary_path = (
        OUTPUT_DIR
        / "04_04_date_standardization_summary.csv"
    )

    summary_df.to_csv(
        summary_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 80)

    if any(
        result["status"] == "FAIL"
        for result in results
    ):

        print("04.04 OVERALL RESULT : FAIL")
        print("Date standardization could not be completed for one or more files.")

    elif any(
        result["status"] == "REVIEW"
        for result in results
    ):

        print("04.04 OVERALL RESULT : REVIEW")
        print(
            "Date processing completed, but invalid or unsupported "
            "date values require review."
        )

    else:

        print("04.04 OVERALL RESULT : PASS")
        print(
            "All processed date values comply with the "
            "project date standard."
        )

    print(f"\nSummary output:")
    print(summary_path)

    print("\n" + "=" * 80)
    print("Tracker 04.04 date standardization processing completed.")
    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
    
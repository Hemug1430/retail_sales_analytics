"""
Retail Sales Analytics
Tracker 04.12 - Create Reject Reason Codes

Requirement:
Assign standardized reject categories so invalid records can be
traced and analyzed.

Approved reject-code families from Document 04:
    REQ_NULL
    TYPE_PARSE
    DOMAIN_INVALID
    FK_UNKNOWN
    DUP_CONFLICT
    RETURN_EXCEEDS_SALE
    PROMO_INELIGIBLE
    SCHEMA_CHANGE

Important:
- Source CSV files are NEVER modified.
- Valid rows are retained.
- Only rows carrying an identifiable validation/review/reject
  condition receive a reject code.
- Existing validation evidence is preserved.
"""

from pathlib import Path
import json
import re
from datetime import datetime

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_SUFFIX = "_04_12_reject_reason_codes.csv"
AUDIT_FILE = PROCESSED_DIR / "04_12_reject_reason_code_audit.csv"


# ============================================================
# APPROVED REJECT CODE DEFINITIONS
# ============================================================

REJECT_CODES = {
    "REQ_NULL": (
        "Required key/value is missing."
    ),
    "TYPE_PARSE": (
        "Invalid date or numeric value could not be safely parsed."
    ),
    "DOMAIN_INVALID": (
        "Value violates an approved domain or documented business rule."
    ),
    "FK_UNKNOWN": (
        "Referenced customer, product, store, salesperson, "
        "promotion, sales line, or other parent key is unknown."
    ),
    "DUP_CONFLICT": (
        "Same business key contains conflicting content."
    ),
    "RETURN_EXCEEDS_SALE": (
        "Cumulative return quantity exceeds the eligible sold quantity."
    ),
    "PROMO_INELIGIBLE": (
        "Promotion does not match the applicable date, category, "
        "or sales channel."
    ),
    "SCHEMA_CHANGE": (
        "File contains an unexpected structural/schema change."
    ),
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalize_text(value):
    """Convert a value into normalized searchable text."""
    if pd.isna(value):
        return ""

    text = str(value).strip().lower()

    text = text.replace("_", " ")
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)

    return text


def row_text(row):
    """
    Build searchable text from validation-related columns.

    We intentionally do NOT use every numeric/business value as
    evidence because legitimate business values must not be
    interpreted as reject reasons.
    """

    evidence = []

    for column in row.index:

        column_text = normalize_text(column)

        if any(
            keyword in column_text
            for keyword in [
                "validation",
                "valid",
                "review",
                "reject",
                "reason",
                "error",
                "flag",
                "business",
                "rule",
                "reference",
                "duplicate",
                "schema",
                "status",
                "message",
            ]
        ):
            value = row[column]

            if not pd.isna(value):
                evidence.append(
                    f"{column_text}: {normalize_text(value)}"
                )

    return " | ".join(evidence)


def determine_reject_code(row):
    """
    Assign exactly one approved reject code where the existing
    validation evidence supports it.

    Priority follows the most specific business/data-quality
    condition first.
    """

    text = row_text(row)

    if not text:
        return ""

    # --------------------------------------------------------
    # RETURN QUANTITY
    # --------------------------------------------------------

    if (
        "return exceeds sale" in text
        or "return quantity exceeds" in text
        or "exceeds eligible sold" in text
        or "returned quantity" in text and "exceed" in text
    ):
        return "RETURN_EXCEEDS_SALE"

    # --------------------------------------------------------
    # PROMOTION ELIGIBILITY
    # --------------------------------------------------------

    if (
        "promo ineligible" in text
        or "promotion ineligible" in text
        or "promotion does not match" in text
        or "promotion mismatch" in text
        or "promotion timing" in text and (
            "invalid" in text or "review" in text
        )
        or "promotion category" in text and (
            "invalid" in text or "review" in text
        )
        or "promotion channel" in text and (
            "invalid" in text or "review" in text
        )
    ):
        return "PROMO_INELIGIBLE"

    # --------------------------------------------------------
    # FOREIGN KEY
    # --------------------------------------------------------

    if (
        "fk unknown" in text
        or "unknown foreign" in text
        or "foreign key" in text and (
            "unknown" in text
            or "invalid" in text
            or "unresolved" in text
            or "missing parent" in text
            or "orphan" in text
        )
        or "unknown customer" in text
        or "unknown product" in text
        or "unknown store" in text
        or "unknown salesperson" in text
        or "unknown promotion" in text
        or "unknown sales line" in text
        or "reference cannot be confirmed" in text
    ):
        return "FK_UNKNOWN"

    # --------------------------------------------------------
    # DUPLICATE CONFLICT
    # --------------------------------------------------------

    if (
        "dup conflict" in text
        or "duplicate conflict" in text
        or "business key conflict" in text
        or "same key" in text and "conflict" in text
        or "conflicting content" in text
        or "conflicting record" in text
    ):
        return "DUP_CONFLICT"

    # --------------------------------------------------------
    # SCHEMA CHANGE
    # --------------------------------------------------------

    if (
        "schema change" in text
        or "unexpected column" in text
        or "unexpected columns" in text
        or "missing column" in text
        or "missing columns" in text
        or "structural change" in text
        or "schema mismatch" in text
    ):
        return "SCHEMA_CHANGE"

    # --------------------------------------------------------
    # TYPE / PARSE
    # --------------------------------------------------------

    if (
        "type parse" in text
        or "parse error" in text
        or "parse failure" in text
        or "invalid date" in text
        or "invalid numeric" in text
        or "numeric parse" in text
        or "date parse" in text
        or "cannot parse" in text
        or "conversion error" in text
        or "conversion failure" in text
    ):
        return "TYPE_PARSE"

    # --------------------------------------------------------
    # REQUIRED NULL
    # --------------------------------------------------------

    if (
        "req null" in text
        or "required null" in text
        or "required missing" in text
        or "required field missing" in text
        or "mandatory missing" in text
        or "mandatory field missing" in text
        or "required key" in text and (
            "missing" in text
            or "blank" in text
            or "null" in text
        )
    ):
        return "REQ_NULL"

    # --------------------------------------------------------
    # DOMAIN / BUSINESS INVALID
    # --------------------------------------------------------

    if (
        "domain invalid" in text
        or "invalid domain" in text
        or "invalid value" in text
        or "invalid category" in text
        or "invalid status" in text
        or "invalid channel" in text
        or "invalid payment" in text
        or "invalid business rule" in text
        or "business rule violation" in text
        or "business validation failed" in text
        or "quantity <= 0" in text
        or "quantity invalid" in text
        or "discount > 100" in text
        or "negative discount" in text
        or "negative price" in text
        or "zero price" in text
    ):
        return "DOMAIN_INVALID"

    # --------------------------------------------------------
    # NO SUPPORTED REJECT EVIDENCE
    # --------------------------------------------------------

    return ""


def determine_message(code):
    """Return the approved human-readable message."""
    return REJECT_CODES.get(code, "")


def build_raw_evidence(row):
    """
    Preserve the row values as JSON evidence.

    This is not a replacement for the future ETL rejected-record
    table; it provides traceability at this tracker stage.
    """

    payload = {}

    for column in row.index:

        value = row[column]

        if pd.isna(value):
            payload[column] = None
        else:
            payload[column] = str(value)

    return json.dumps(
        payload,
        ensure_ascii=False,
        default=str
    )


def find_business_key(df):
    """
    Identify the documented business key where available.
    """

    candidates = [
        "customer_id",
        "product_id",
        "store_id",
        "salesperson_id",
        "promotion_id",
        "sales_line_id",
        "return_id",
        "target_id",
    ]

    for column in candidates:
        if column in df.columns:
            return column

    return ""


def find_source_row_number(df):
    """
    Preserve existing source row number when available.
    Otherwise create a deterministic row locator.

    +2 accounts for a normal CSV header and one-based data rows.
    """

    possible_columns = [
        "source_row_number",
        "source_row",
        "row_number",
        "source_row_id",
    ]

    for column in possible_columns:
        if column in df.columns:
            return df[column]

    return pd.Series(
        range(2, len(df) + 2),
        index=df.index,
        name="source_row_number"
    )


def find_validation_files():
    """
    Locate outputs created by Tracker 04.11.

    Only files containing the 04.11 business-validation marker
    are considered.
    """

    files = []

    for file_path in PROCESSED_DIR.glob("*04_11_business_validation*.csv"):

        if file_path.name.startswith("04_11_"):
            continue

        if file_path.name.endswith(OUTPUT_SUFFIX):
            continue

        files.append(file_path)

    return sorted(files)


# ============================================================
# PROCESS ONE FILE
# ============================================================

def process_file(input_file):

    print("\n" + "=" * 80)
    print("04.12 REJECT REASON CODE ASSIGNMENT")
    print("=" * 80)

    print(f"Input file : {input_file}")

    try:
        df = pd.read_csv(
            input_file,
            encoding="utf-8-sig",
            low_memory=False
        )
    except Exception as exc:
        print(f"ERROR reading file: {exc}")
        return {
            "file_name": input_file.name,
            "rows_read": 0,
            "reject_rows": 0,
            "status": "FAILED",
            "error": str(exc),
        }

    print(f"Rows read  : {len(df):,}")
    print(f"Columns    : {len(df.columns)}")

    # --------------------------------------------------------
    # SOURCE ROW NUMBER
    # --------------------------------------------------------

    source_rows = find_source_row_number(df)

    # --------------------------------------------------------
    # BUSINESS KEY
    # --------------------------------------------------------

    business_key = find_business_key(df)

    # --------------------------------------------------------
    # ASSIGN REJECT CODE
    # --------------------------------------------------------

    reject_codes = []

    for _, row in df.iterrows():

        code = determine_reject_code(row)

        reject_codes.append(code)

    df["reject_code"] = reject_codes

    df["reject_message"] = df["reject_code"].apply(
        determine_message
    )

    df["source_row_number"] = source_rows.values

    if business_key:
        df["business_key_for_reject"] = df[business_key].astype(
            "string"
        )
    else:
        df["business_key_for_reject"] = ""

    # --------------------------------------------------------
    # RAW ROW EVIDENCE
    # --------------------------------------------------------

    df["raw_row_evidence"] = df.apply(
        build_raw_evidence,
        axis=1
    )

    # --------------------------------------------------------
    # REJECT STATUS
    # --------------------------------------------------------

    df["reject_status"] = df["reject_code"].apply(
        lambda value: (
            "REJECT_REASON_ASSIGNED"
            if str(value).strip()
            else "NO_REJECT_CODE"
        )
    )

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    output_file = PROCESSED_DIR / (
        input_file.stem + OUTPUT_SUFFIX
    )

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    reject_df = df[
        df["reject_code"].astype(str).str.strip() != ""
    ]

    code_counts = (
        reject_df["reject_code"]
        .value_counts()
        .to_dict()
    )

    print("\nREJECT REASON SUMMARY")
    print("-" * 80)

    print(f"Total rows processed : {len(df):,}")
    print(f"Rows with reject code: {len(reject_df):,}")
    print(
        f"Rows without reject : "
        f"{len(df) - len(reject_df):,}"
    )

    for code in REJECT_CODES:

        print(
            f"{code:<22}: "
            f"{code_counts.get(code, 0):,}"
        )

    print("\nOutput:")
    print(output_file)

    return {
        "file_name": input_file.name,
        "rows_read": len(df),
        "reject_rows": len(reject_df),
        "status": "PASS",
        "error": "",
        "output_file": str(output_file),
        "business_key": business_key,
        "code_counts": code_counts,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TRACKER 04.12 - CREATE REJECT REASON CODES")
    print("=" * 80)

    print("\nApproved reject-code families:")
    for code, description in REJECT_CODES.items():
        print(f"  {code:<22} - {description}")

    input_files = find_validation_files()

    print("\n04.11 validation files discovered:")
    print(f"Count: {len(input_files)}")

    if not input_files:

        print(
            "\nNo 04.11 business-validation output files were found."
        )

        print(
            "\nExpected pattern:"
        )

        print(
            "data/processed/*04_11_business_validation*.csv"
        )

        print(
            "\nTracker 04.12 was NOT completed."
        )

        return

    results = []

    for input_file in input_files:

        result = process_file(input_file)

        results.append(result)

    # ========================================================
    # AUDIT LOG
    # ========================================================

    audit_rows = []

    run_timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    for result in results:

        code_counts = result.get("code_counts", {})

        audit_rows.append(
            {
                "run_timestamp": run_timestamp,
                "source_file_name": result.get(
                    "file_name", ""
                ),
                "rows_read": result.get(
                    "rows_read", 0
                ),
                "reject_rows": result.get(
                    "reject_rows", 0
                ),
                "business_key": result.get(
                    "business_key", ""
                ),
                "REQ_NULL": code_counts.get(
                    "REQ_NULL", 0
                ),
                "TYPE_PARSE": code_counts.get(
                    "TYPE_PARSE", 0
                ),
                "DOMAIN_INVALID": code_counts.get(
                    "DOMAIN_INVALID", 0
                ),
                "FK_UNKNOWN": code_counts.get(
                    "FK_UNKNOWN", 0
                ),
                "DUP_CONFLICT": code_counts.get(
                    "DUP_CONFLICT", 0
                ),
                "RETURN_EXCEEDS_SALE": code_counts.get(
                    "RETURN_EXCEEDS_SALE", 0
                ),
                "PROMO_INELIGIBLE": code_counts.get(
                    "PROMO_INELIGIBLE", 0
                ),
                "SCHEMA_CHANGE": code_counts.get(
                    "SCHEMA_CHANGE", 0
                ),
                "status": result.get(
                    "status", ""
                ),
                "error": result.get(
                    "error", ""
                ),
            }
        )

    audit_df = pd.DataFrame(audit_rows)

    audit_df.to_csv(
        AUDIT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    failed = [
        r for r in results
        if r.get("status") == "FAILED"
    ]

    total_rows = sum(
        r.get("rows_read", 0)
        for r in results
    )

    total_rejects = sum(
        r.get("reject_rows", 0)
        for r in results
    )

    print("\n" + "=" * 80)
    print("04.12 OVERALL RESULT")
    print("=" * 80)

    print(
        f"Validation files processed : {len(results)}"
    )

    print(
        f"Rows processed             : {total_rows:,}"
    )

    print(
        f"Rows with reject codes     : {total_rejects:,}"
    )

    print(
        f"Rows without reject codes  : "
        f"{total_rows - total_rejects:,}"
    )

    print(
        f"Files failed               : {len(failed)}"
    )

    print(
        f"\nAudit output: {AUDIT_FILE}"
    )

    if failed:

        print(
            "\n04.12 STATUS : REVIEW"
        )

        print(
            "One or more validation outputs could not be processed."
        )

    else:

        print(
            "\n04.12 STATUS : PASS"
        )

        print(
            "Standardized reject reason codes were assigned "
            "where documented validation evidence supports them."
        )

        print(
            "No source CSV files were modified or deleted."
        )

    print("\n" + "=" * 80)

    if failed:

        print(
            "Tracker 04.12 processing completed with REVIEW status."
        )

    else:

        print(
            "Tracker 04.12 reject reason code processing completed."
        )

    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
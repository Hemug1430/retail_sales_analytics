"""
Retail Sales Analytics
Tracker 04.05 - Clean Numeric Values

Requirement:
Remove formatting artifacts and safely convert quantities, prices,
discounts, targets, and refund values to numeric types.

Important:
- Original files in incoming/ are NEVER modified.
- Only deterministic numeric formatting is cleaned.
- Legitimate blanks remain blank.
- Invalid/unresolved numeric values are preserved and flagged.
- Negative/zero values are NOT silently changed because they may be
  deliberate invalid-data scenarios that must remain detectable.
"""

from pathlib import Path
import re
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT_ROOT / "incoming"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# NUMERIC FIELD DEFINITIONS
# ============================================================

NUMERIC_FIELDS = {
    "customers_master.csv": {
        # No business numeric fields required for this step.
    },

    "products_master.csv": {
        "unit_cost": "money",
        "list_price": "money",
        "tax_rate_pct": "percentage",
    },

    "stores_master.csv": {
        "floor_area_sqft": "integer",
    },

    "salespersons_master.csv": {
        # No business numeric fields required.
    },

    "promotions_master.csv": {
        "discount_pct": "percentage",
        "minimum_order_value": "money",
    },

    "sales_2024_01.csv": {
        "quantity": "integer",
        "unit_selling_price": "money",
        "discount_pct": "percentage",
    },

    "returns_2024_01.csv": {
        "quantity_returned": "integer",
        "refund_amount": "money",
    },

    "targets_2024_01.csv": {
        "revenue_target": "money",
        "profit_target": "money",
        "order_target": "integer",
        "return_rate_target_pct": "percentage",
    },
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def is_blank(value):
    """Return True when the source value is blank/null."""
    if pd.isna(value):
        return True

    text = str(value).strip()

    return text == ""


def clean_numeric_text(value):
    """
    Remove only deterministic formatting artifacts.

    Examples:
        "2,500"       -> "2500"
        "$2,999.00"   -> "2999.00"
        "₹2,999.00"   -> "2999.00"
        "15%"         -> "15"
        "  25.50 "    -> "25.50"
        "(125.50)"    -> "-125.50"

    Returns:
        cleaned_text, was_cleaned, status
    """

    if is_blank(value):
        return "", False, "BLANK"

    text = str(value).strip()

    original = text

    # Remove common currency symbols.
    text = re.sub(r"[$€£₹]", "", text)

    # Remove common thousands separators.
    text = text.replace(",", "")

    # Remove percentage symbol.
    text = text.replace("%", "")

    # Remove ordinary spaces inside numeric strings.
    text = text.replace(" ", "")

    # Accounting-style negative numbers:
    # (123.45) -> -123.45
    if text.startswith("(") and text.endswith(")"):
        inner = text[1:-1].strip()

        if inner:
            text = "-" + inner

    # Allow only a safe numeric representation.
    if re.fullmatch(r"[+-]?\d+(\.\d+)?", text):
        return text, text != original, "VALID"

    # Also allow values such as .50 or -.50
    if re.fullmatch(r"[+-]?(\d+\.\d+|\.\d+)", text):
        return text, text != original, "VALID"

    return original, False, "UNRESOLVED"


def convert_numeric_value(value, numeric_type):
    """
    Clean and safely convert one numeric value.

    Returns:
        converted_value,
        status,
        was_cleaned
    """

    cleaned_text, was_cleaned, status = clean_numeric_text(value)

    if status == "BLANK":
        return pd.NA, "BLANK", False

    if status == "UNRESOLVED":
        return value, "UNRESOLVED", False

    try:
        number = float(cleaned_text)

        if numeric_type == "integer":
            # Only convert to integer when it is actually whole.
            if number.is_integer():
                return int(number), "VALID", was_cleaned

            return value, "NON_INTEGER", was_cleaned

        if numeric_type in {"money", "percentage"}:
            return round(number, 2), "VALID", was_cleaned

        return number, "VALID", was_cleaned

    except (ValueError, TypeError):
        return value, "UNRESOLVED", False


def process_numeric_column(df, column_name, numeric_type, audit_rows):
    """Clean one numeric column and collect audit information."""

    if column_name not in df.columns:
        audit_rows.append(
            {
                "column_name": column_name,
                "numeric_type": numeric_type,
                "rows_processed": 0,
                "values_cleaned": 0,
                "valid_numeric_values": 0,
                "blank_values": 0,
                "unresolved_values": 0,
                "non_integer_values": 0,
                "negative_values": 0,
                "zero_values": 0,
                "status": "COLUMN_NOT_PRESENT",
            }
        )

        return

    cleaned_values = []

    values_cleaned = 0
    valid_numeric_values = 0
    blank_values = 0
    unresolved_values = 0
    non_integer_values = 0
    negative_values = 0
    zero_values = 0

    for value in df[column_name]:

        converted, status, was_cleaned = convert_numeric_value(
            value,
            numeric_type
        )

        cleaned_values.append(converted)

        if was_cleaned:
            values_cleaned += 1

        if status == "VALID":
            valid_numeric_values += 1

            try:
                number = float(converted)

                if number < 0:
                    negative_values += 1

                if number == 0:
                    zero_values += 1

            except (ValueError, TypeError):
                pass

        elif status == "BLANK":
            blank_values += 1

        elif status == "UNRESOLVED":
            unresolved_values += 1

        elif status == "NON_INTEGER":
            non_integer_values += 1

    df[column_name] = cleaned_values

    # Apply appropriate pandas numeric type.
    if numeric_type == "integer":
        df[column_name] = pd.to_numeric(
            df[column_name],
            errors="coerce"
        ).astype("Int64")

    else:
        df[column_name] = pd.to_numeric(
            df[column_name],
            errors="coerce"
        ).round(2)

    column_status = "PASS"

    if unresolved_values > 0 or non_integer_values > 0:
        column_status = "REVIEW"

    audit_rows.append(
        {
            "column_name": column_name,
            "numeric_type": numeric_type,
            "rows_processed": len(df),
            "values_cleaned": values_cleaned,
            "valid_numeric_values": valid_numeric_values,
            "blank_values": blank_values,
            "unresolved_values": unresolved_values,
            "non_integer_values": non_integer_values,
            "negative_values": negative_values,
            "zero_values": zero_values,
            "status": column_status,
        }
    )


# ============================================================
# FILE PROCESSING
# ============================================================

def process_file(file_path):
    """Process one incoming CSV file."""

    file_name = file_path.name

    print("\n" + "=" * 80)
    print("TRACKER 04.05 - CLEAN NUMERIC VALUES")
    print("=" * 80)

    print(f"Input file : {file_path}")

    try:
        df = pd.read_csv(
            file_path,
            encoding="utf-8-sig"
        )
    except UnicodeDecodeError:
        df = pd.read_csv(
            file_path,
            encoding="utf-8"
        )

    print(f"Rows read  : {len(df):,}")
    print(f"Columns    : {len(df.columns)}")

    field_rules = NUMERIC_FIELDS.get(file_name, {})

    audit_rows = []

    if not field_rules:

        print("\nNo numeric fields are defined for this file.")

        audit_rows.append(
            {
                "column_name": "",
                "numeric_type": "",
                "rows_processed": len(df),
                "values_cleaned": 0,
                "valid_numeric_values": 0,
                "blank_values": 0,
                "unresolved_values": 0,
                "non_integer_values": 0,
                "negative_values": 0,
                "zero_values": 0,
                "status": "NO_NUMERIC_FIELDS",
            }
        )

    else:

        for column_name, numeric_type in field_rules.items():

            process_numeric_column(
                df,
                column_name,
                numeric_type,
                audit_rows
            )

    # --------------------------------------------------------
    # OUTPUT FILE
    # --------------------------------------------------------

    output_name = file_path.stem + "_numeric_cleaned.csv"
    output_path = OUTPUT_DIR / output_name

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # AUDIT FILE
    # --------------------------------------------------------

    audit_df = pd.DataFrame(audit_rows)

    audit_name = (
        file_path.stem
        + "_04_05_numeric_cleaning_audit.csv"
    )

    audit_path = OUTPUT_DIR / audit_name

    audit_df.to_csv(
        audit_path,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    total_cleaned = int(
        audit_df["values_cleaned"].sum()
    )

    total_unresolved = int(
        audit_df["unresolved_values"].sum()
    )

    total_non_integer = int(
        audit_df["non_integer_values"].sum()
    )

    total_negative = int(
        audit_df["negative_values"].sum()
    )

    total_zero = int(
        audit_df["zero_values"].sum()
    )

    if total_unresolved > 0 or total_non_integer > 0:
        overall_status = "REVIEW"
    else:
        overall_status = "PASS"

    print("\n" + "-" * 80)
    print("NUMERIC CLEANING SUMMARY")
    print("-" * 80)

    print(f"Total rows processed      : {len(df):,}")
    print(f"Numeric fields processed  : {len(field_rules)}")
    print(f"Values cleaned            : {total_cleaned:,}")
    print(f"Unresolved values         : {total_unresolved:,}")
    print(f"Non-integer values        : {total_non_integer:,}")
    print(f"Negative values detected  : {total_negative:,}")
    print(f"Zero values detected      : {total_zero:,}")
    print(f"Overall status            : {overall_status}")

    print("\nStandardized output:")
    print(output_path)

    print("\nAudit output:")
    print(audit_path)

    return overall_status


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TRACKER 04.05 - NUMERIC VALUE CLEANING")
    print("=" * 80)

    if not INPUT_DIR.exists():
        print(f"ERROR: Input directory not found: {INPUT_DIR}")
        return

    files = sorted(
        INPUT_DIR.glob("*.csv")
    )

    if not files:
        print("ERROR: No CSV files found in incoming directory.")
        return

    print(f"\nIncoming CSV files found: {len(files)}")

    statuses = []

    for file_path in files:

        status = process_file(file_path)

        statuses.append(
            (
                file_path.name,
                status
            )
        )

    # ========================================================
    # OVERALL RESULT
    # ========================================================

    print("\n" + "=" * 80)
    print("04.05 OVERALL RESULT")
    print("=" * 80)

    review_files = [
        name
        for name, status in statuses
        if status == "REVIEW"
    ]

    if review_files:

        print("STATUS : REVIEW")
        print("\nFiles requiring numeric-value review:")

        for name in review_files:
            print(f" - {name}")

        print(
            "\nNumeric cleaning completed, but unresolved/non-integer "
            "values were preserved and flagged."
        )

    else:

        print("STATUS : PASS")
        print(
            "All supported numeric values were safely cleaned "
            "and converted."
        )

    print("\n" + "=" * 80)
    print("Tracker 04.05 numeric value cleaning processing completed.")
    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
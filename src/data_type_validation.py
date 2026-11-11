"""
Retail Sales Analytics
Tracker 03.08 - Validate Column Data Types

Requirement:
Check each incoming field against expected string, integer,
decimal, date, time, and categorical types before transformation.

Important project rules:
- Incoming source files are never modified.
- Validation only reports findings.
- Blank/null values are not treated as datatype failures.
  Mandatory-field validation is handled separately by Tracker 03.09.
- Dataset identification follows the approved project naming convention.
- Sales order_time is validated as a TIME value, not as a generic datetime.
"""

from pathlib import Path
from datetime import datetime, time
import re

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INCOMING_DIR = PROJECT_ROOT / "incoming"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "data_type_validation_results.csv"


# ============================================================
# DATASET IDENTIFICATION
# ============================================================

def identify_dataset(file_name: str):
    """
    Identify the logical dataset from the approved filename.

    Examples:
        customers_master.csv
        products_master.csv
        stores_master.csv
        salespersons_master.csv
        promotions_master.csv
        sales_2024_01.csv
        returns_2024_01.csv
        targets_2024_01.csv
    """

    name = Path(file_name).name.lower()

    # --------------------------------------------------------
    # Master datasets
    # --------------------------------------------------------

    if name.startswith("customers_master") and name.endswith(".csv"):
        return "customers_master"

    if name.startswith("products_master") and name.endswith(".csv"):
        return "products_master"

    if name.startswith("stores_master") and name.endswith(".csv"):
        return "stores_master"

    if name.startswith("salespersons_master") and name.endswith(".csv"):
        return "salespersons_master"

    if name.startswith("promotions_master") and name.endswith(".csv"):
        return "promotions_master"

    # --------------------------------------------------------
    # Monthly transaction datasets
    # --------------------------------------------------------

    if re.match(r"^sales_\d{4}[_-]\d{2}\.csv$", name):
        return "sales"

    if re.match(r"^returns_\d{4}[_-]\d{2}\.csv$", name):
        return "returns"

    if re.match(r"^targets_\d{4}[_-]\d{2}\.csv$", name):
        return "targets"

    return None


# ============================================================
# EXPECTED DATA TYPES
# ============================================================

# Project frozen field definitions.
#
# Type meanings:
#   string   -> text/categorical/identifier
#   integer  -> whole numeric value
#   decimal  -> numeric value allowing decimals
#   date     -> calendar date
#   time     -> time of day

EXPECTED_TYPES = {

    # --------------------------------------------------------
    # CUSTOMERS
    # --------------------------------------------------------

    "customers_master": {
        "customer_id": "string",
        "customer_name": "string",
        "gender": "string",
        "date_of_birth": "date",
        "email": "string",
        "phone": "string",
        "city": "string",
        "state": "string",
        "region": "string",
        "postal_code": "string",
        "registration_date": "date",
        "customer_segment": "string",
        "preferred_channel": "string",
        "status": "string",
    },

    # --------------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------------

    "products_master": {
        "product_id": "string",
        "product_name": "string",
        "category": "string",
        "subcategory": "string",
        "brand": "string",
        "unit_cost": "decimal",
        "list_price": "decimal",
        "tax_rate_pct": "decimal",
        "launch_date": "date",
        "status": "string",
    },

    # --------------------------------------------------------
    # STORES
    # --------------------------------------------------------

    "stores_master": {
        "store_id": "string",
        "store_name": "string",
        "store_type": "string",
        "city": "string",
        "state": "string",
        "region": "string",
        "postal_code": "string",
        "opening_date": "date",
        "floor_area_sqft": "integer",
        "status": "string",
        "manager_name": "string",
    },

    # --------------------------------------------------------
    # SALESPERSONS
    # --------------------------------------------------------

    "salespersons_master": {
        "salesperson_id": "string",
        "salesperson_name": "string",
        "store_id": "string",
        "joining_date": "date",
        "role": "string",
        "status": "string",
    },

    # --------------------------------------------------------
    # PROMOTIONS
    # --------------------------------------------------------

    "promotions_master": {
        "promotion_id": "string",
        "promotion_name": "string",
        "promotion_type": "string",
        "start_date": "date",
        "end_date": "date",
        "discount_pct": "decimal",
        "applicable_category": "string",
        "applicable_channel": "string",
        "minimum_order_value": "decimal",
        "status": "string",
    },

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    "sales": {
        "sales_line_id": "string",
        "order_id": "string",
        "order_date": "date",
        "order_time": "time",
        "customer_id": "string",
        "product_id": "string",
        "store_id": "string",
        "salesperson_id": "string",
        "promotion_id": "string",
        "sales_channel": "string",
        "quantity": "integer",
        "unit_selling_price": "decimal",
        "discount_pct": "decimal",
        "payment_method": "string",
        "order_status": "string",
    },

    # --------------------------------------------------------
    # RETURNS
    # --------------------------------------------------------

    "returns": {
        "return_id": "string",
        "sales_line_id": "string",
        "return_date": "date",
        "quantity_returned": "integer",
        "return_reason": "string",
        "return_status": "string",
        "refund_method": "string",
        "refund_amount": "decimal",
        "processed_store_id": "string",
    },

    # --------------------------------------------------------
    # TARGETS
    # --------------------------------------------------------

    "targets": {
        "target_id": "string",
        "target_month": "date",
        "store_id": "string",
        "category": "string",
        "revenue_target": "decimal",
        "profit_target": "decimal",
        "order_target": "integer",
        "return_rate_target_pct": "decimal",
    },
}


# ============================================================
# HELPERS
# ============================================================

def is_blank(value) -> bool:
    """
    Blank/null values are not datatype failures.
    Tracker 03.09 handles mandatory-field completeness.
    """

    if pd.isna(value):
        return True

    return str(value).strip() == ""


def validate_string(value) -> bool:
    """
    Strings are valid when the value is not blank.

    Blank values are intentionally treated as valid here because
    datatype validation and mandatory-field validation are separate
    tracker steps.
    """

    if is_blank(value):
        return True

    return isinstance(value, (str, int, float, bool))


def validate_integer(value) -> bool:
    """
    Validate a whole-number value.

    Accept:
        10
        "10"
        "10.0"

    Reject:
        "10.5"
        "abc"
    """

    if is_blank(value):
        return True

    try:
        numeric = float(str(value).strip())

        if pd.isna(numeric):
            return False

        return numeric.is_integer()

    except (ValueError, TypeError):
        return False


def validate_decimal(value) -> bool:
    """
    Validate a numeric decimal value.
    """

    if is_blank(value):
        return True

    try:
        numeric = float(str(value).strip())

        return not pd.isna(numeric)

    except (ValueError, TypeError):
        return False


def validate_date(value) -> bool:
    """
    Validate a calendar date.

    Project standard date format is YYYY-MM-DD,
    but this step validates the datatype rather than performing
    date transformation.
    """

    if is_blank(value):
        return True

    raw = str(value).strip()

    # --------------------------------------------------------
    # Project-standard format first
    # --------------------------------------------------------

    try:
        datetime.strptime(raw, "%Y-%m-%d")
        return True
    except ValueError:
        pass

    # --------------------------------------------------------
    # Deterministic supported formats
    # --------------------------------------------------------

    supported_formats = [
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ]

    for fmt in supported_formats:
        try:
            datetime.strptime(raw, fmt)
            return True
        except ValueError:
            continue

    # --------------------------------------------------------
    # Pandas fallback for already-readable date values
    # --------------------------------------------------------

    try:
        parsed = pd.to_datetime(
            raw,
            errors="coerce",
            dayfirst=False,
        )

        return not pd.isna(parsed)

    except Exception:
        return False


def validate_time(value) -> bool:
    """
    Validate a time-of-day value.

    Accepted examples:

        08:36:01
        08:36
        23:59:59
        0 days 08:36:01

    The important distinction is that this validates TIME,
    not a full calendar datetime.
    """

    if is_blank(value):
        return True

    raw = str(value).strip()

    # --------------------------------------------------------
    # Standard HH:MM:SS
    # --------------------------------------------------------

    formats = [
        "%H:%M:%S",
        "%H:%M",
    ]

    for fmt in formats:
        try:
            datetime.strptime(raw, fmt)
            return True
        except ValueError:
            continue

    # --------------------------------------------------------
    # Pandas / Python timedelta representation
    #
    # Example:
    # 0 days 08:36:01
    # --------------------------------------------------------

    timedelta_match = re.fullmatch(
        r"(?:(\d+)\s+days?\s+)?"
        r"(\d{1,2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?",
        raw,
    )

    if timedelta_match:

        days = int(timedelta_match.group(1) or 0)
        hours = int(timedelta_match.group(2))
        minutes = int(timedelta_match.group(3))
        seconds = int(timedelta_match.group(4) or 0)

        if days >= 0 and hours < 24 and minutes < 60 and seconds < 60:
            return True

    # --------------------------------------------------------
    # Python datetime.time representation
    # --------------------------------------------------------

    if isinstance(value, time):
        return True

    # --------------------------------------------------------
    # Pandas Timedelta representation
    # --------------------------------------------------------

    try:

        parsed = pd.to_timedelta(
            raw,
            errors="coerce",
        )

        if not pd.isna(parsed):

            total_seconds = parsed.total_seconds()

            # A time-of-day value must represent less than 24 hours.
            return 0 <= total_seconds < 24 * 60 * 60

    except Exception:
        pass

    return False


def validate_value(value, expected_type: str) -> bool:
    """
    Dispatch validation according to the expected project datatype.
    """

    if expected_type == "string":
        return validate_string(value)

    if expected_type == "integer":
        return validate_integer(value)

    if expected_type == "decimal":
        return validate_decimal(value)

    if expected_type == "date":
        return validate_date(value)

    if expected_type == "time":
        return validate_time(value)

    return False


# ============================================================
# PROCESS ONE FILE
# ============================================================

def process_file(file_path: Path):
    """
    Validate the datatypes of one incoming CSV file.
    """

    dataset = identify_dataset(file_path.name)

    # --------------------------------------------------------
    # Unknown dataset
    # --------------------------------------------------------

    if dataset is None:

        return [
            {
                "file_name": file_path.name,
                "dataset": "UNKNOWN",
                "column": "",
                "expected_type": "",
                "invalid_count": 0,
                "result": "WARNING",
                "details": (
                    "Dataset could not be identified from filename."
                ),
            }
        ]

    expected_columns = EXPECTED_TYPES[dataset]

    # --------------------------------------------------------
    # Read file
    # --------------------------------------------------------

    try:

        df = pd.read_csv(
            file_path,
            encoding="utf-8-sig",
            low_memory=False,
        )

    except Exception as exc:

        return [
            {
                "file_name": file_path.name,
                "dataset": dataset,
                "column": "",
                "expected_type": "",
                "invalid_count": 0,
                "result": "FAIL",
                "details": (
                    f"Unable to read CSV file: "
                    f"{type(exc).__name__}: {exc}"
                ),
            }
        ]

    results = []

    # --------------------------------------------------------
    # Validate expected fields
    # --------------------------------------------------------

    for column, expected_type in expected_columns.items():

        # ----------------------------------------------------
        # Missing column
        #
        # Missing-column validation belongs primarily to 03.06.
        # Here we report it as FAIL because the datatype cannot
        # be validated when the field itself is absent.
        # ----------------------------------------------------

        if column not in df.columns:

            results.append(
                {
                    "file_name": file_path.name,
                    "dataset": dataset,
                    "column": column,
                    "expected_type": expected_type,
                    "invalid_count": 0,
                    "result": "FAIL",
                    "details": (
                        "Expected column is missing from incoming file."
                    ),
                }
            )

            continue

        # ----------------------------------------------------
        # Validate values
        # ----------------------------------------------------

        invalid_mask = ~df[column].apply(
            lambda value: validate_value(
                value,
                expected_type,
            )
        )

        invalid_count = int(invalid_mask.sum())

        if invalid_count == 0:

            result = "PASS"

            details = (
                f"All non-blank values match expected "
                f"{expected_type} datatype."
            )

        else:

            result = "FAIL"

            details = (
                f"{invalid_count:,} value(s) do not match "
                f"expected {expected_type} datatype."
            )

        results.append(
            {
                "file_name": file_path.name,
                "dataset": dataset,
                "column": column,
                "expected_type": expected_type,
                "invalid_count": invalid_count,
                "result": result,
                "details": details,
            }
        )

    return results


# ============================================================
# PROCESS ALL INCOMING FILES
# ============================================================

def process_all_files():
    """
    Validate all CSV files currently present in incoming/.
    """

    if not INCOMING_DIR.exists():

        print(
            f"Incoming directory not found: {INCOMING_DIR}"
        )

        return []

    csv_files = sorted(
        INCOMING_DIR.glob("*.csv")
    )

    if not csv_files:

        print(
            f"No CSV files found in: {INCOMING_DIR}"
        )

        return []

    all_results = []

    for file_path in csv_files:

        print()
        print("=" * 80)
        print(
            f"FILE: {file_path.name}"
        )
        print("=" * 80)

        file_results = process_file(
            file_path
        )

        all_results.extend(
            file_results
        )

    return all_results


# ============================================================
# SUMMARY
# ============================================================

def print_summary(results):
    """
    Print detailed datatype validation results.
    """

    print()
    print("=" * 80)
    print("TRACKER 03.08 - DATA TYPE VALIDATION")
    print("=" * 80)

    if not results:

        print("No validation results were generated.")

        return

    # --------------------------------------------------------
    # Display individual results
    # --------------------------------------------------------

    for result in results:

        print()
        print(
            f"FILE           : {result['file_name']}"
        )

        print(
            f"DATASET        : {result['dataset']}"
        )

        print(
            f"COLUMN         : {result['column']}"
        )

        print(
            f"EXPECTED TYPE  : {result['expected_type']}"
        )

        print(
            f"INVALID COUNT  : {result['invalid_count']}"
        )

        print(
            f"RESULT         : {result['result']}"
        )

        print(
            f"DETAILS        : {result['details']}"
        )

    # --------------------------------------------------------
    # Overall counts
    # --------------------------------------------------------

    results_df = pd.DataFrame(
        results
    )

    passed = int(
        (
            results_df["result"]
            == "PASS"
        ).sum()
    )

    failed = int(
        (
            results_df["result"]
            == "FAIL"
        ).sum()
    )

    warnings = int(
        (
            results_df["result"]
            == "WARNING"
        ).sum()
    )

    # --------------------------------------------------------
    # Overall result
    # --------------------------------------------------------

    if failed > 0:

        overall_result = "FAIL"

    elif warnings > 0:

        overall_result = "WARNING"

    else:

        overall_result = "PASS"

    # --------------------------------------------------------
    # Save report
    # --------------------------------------------------------

    results_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("DATA TYPE VALIDATION SUMMARY")
    print("=" * 80)

    print(
        f"Fields checked : {len(results_df):,}"
    )

    print(
        f"PASS           : {passed:,}"
    )

    print(
        f"FAIL           : {failed:,}"
    )

    print(
        f"WARNING        : {warnings:,}"
    )

    print(
        f"OVERALL RESULT : {overall_result}"
    )

    print()
    print(
        f"Report saved to: {OUTPUT_FILE}"
    )

    print()
    print("=" * 80)
    print("Tracker 03.08 completed.")
    print("=" * 80)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("Starting Tracker 03.08 - Data Type Validation")
    print("=" * 80)

    results = process_all_files()

    print_summary(
        results
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
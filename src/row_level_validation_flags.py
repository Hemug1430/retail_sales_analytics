from pathlib import Path
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation


# ============================================================
# TRACKER 03.13
# CREATE ROW-LEVEL VALIDATION FLAGS
# ============================================================
#
# Requirement:
# Attach validation outcomes/reason codes to rows that
# violate field-level or business-level intake rules.
#
# This module VALIDATES ONLY.
# It does NOT modify the incoming source files.
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_DIR = Path("incoming")
OUTPUT_DIR = Path("data/outputs")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# APPROVED DATA TYPES
# ============================================================

SCHEMAS = {

    "customers": {
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

    "products": {
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

    "stores": {
        "store_id": "string",
        "store_name": "string",
        "store_type": "string",
        "city": "string",
        "state": "string",
        "region": "string",
        "postal_code": "string",
        "opening_date": "date",
        "floor_area_sqft": "integer",
        "manager_name": "string",
        "status": "string",
    },

    "salespersons": {
        "salesperson_id": "string",
        "salesperson_name": "string",
        "store_id": "string",
        "joining_date": "date",
        "role": "string",
        "status": "string",
    },

    "promotions": {
        "promotion_id": "string",
        "promotion_name": "string",
        "promotion_type": "string",
        "start_date": "date",
        "end_date": "date",
        "discount_pct": "decimal",
        "applicable_channel": "string",
        "applicable_category": "string",
        "minimum_order_value": "decimal",
        "status": "string",
    },

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
# APPROVED CATEGORICAL VALUES
# ============================================================

ALLOWED_VALUES = {

    "gender": {
        "Male",
        "Female",
        "Other",
    },

    "customer_segment": {
        "Occasional",
        "Regular",
        "Premium",
        "VIP",
    },

    "preferred_channel": {
        "Store",
        "Online",
    },

    "status": {
        "Active",
        "Inactive",
        "Discontinued",
        "Suspended",
        "Temporarily Closed",
        "Closed",
        "Planned",
        "Expired",
        "Cancelled",
    },

    "category": {
        "Electronics",
        "Home & Kitchen",
        "Fashion",
        "Beauty & Personal Care",
        "Sports & Fitness",
        "Grocery",
    },

    "region": {
        "North",
        "South",
        "East",
        "West",
        "Central",
    },

    "store_type": {
        "Mall",
        "High Street",
        "Outlet",
        "Neighborhood",
    },

    "role": {
        "Sales Associate",
        "Senior Sales Associate",
        "Store Supervisor",
    },

    "promotion_type": {
        "Seasonal",
        "Category",
        "Storewide",
        "Channel",
    },

    "applicable_channel": {
        "Store",
        "Online",
        "ALL",
    },

    "sales_channel": {
        "Store",
        "Online",
    },

    "payment_method": {
        "Cash",
        "Card",
        "UPI",
        "Wallet",
        "Net Banking",
    },

    "order_status": {
        "Completed",
        "Cancelled",
    },

    "return_reason": {
        "Damaged",
        "Wrong Product",
        "Quality Issue",
        "Size/Fit Issue",
        "Customer Changed Mind",
        "Late Delivery",
        "Other",
    },

    "return_status": {
        "Requested",
        "Approved",
        "Rejected",
        "Refunded",
    },

    "refund_method": {
        "Original Payment",
        "Store Credit",
        "Cash",
    },
}


# ============================================================
# MANDATORY FIELDS
# ============================================================

MANDATORY_FIELDS = {

    "customers": {
        "customer_id",
        "customer_name",
        "city",
        "state",
        "region",
        "registration_date",
        "customer_segment",
        "status",
    },

    "products": {
        "product_id",
        "product_name",
        "category",
        "subcategory",
        "brand",
        "unit_cost",
        "list_price",
        "tax_rate_pct",
        "launch_date",
        "status",
    },

    "stores": {
        "store_id",
        "store_name",
        "store_type",
        "city",
        "state",
        "region",
        "postal_code",
        "opening_date",
        "status",
    },

    "salespersons": {
        "salesperson_id",
        "salesperson_name",
        "store_id",
        "joining_date",
        "role",
        "status",
    },

    "promotions": {
        "promotion_id",
        "promotion_name",
        "promotion_type",
        "start_date",
        "end_date",
        "discount_pct",
        "applicable_channel",
        "status",
    },

    "sales": {
        "sales_line_id",
        "order_id",
        "order_date",
        "order_time",
        "product_id",
        "store_id",
        "sales_channel",
        "quantity",
        "unit_selling_price",
        "discount_pct",
        "payment_method",
        "order_status",
    },

    "returns": {
        "return_id",
        "sales_line_id",
        "return_date",
        "quantity_returned",
        "return_reason",
        "return_status",
    },

    "targets": {
        "target_id",
        "target_month",
        "store_id",
        "category",
        "revenue_target",
        "profit_target",
        "order_target",
        "return_rate_target_pct",
    },
}


# ============================================================
# DATASET IDENTIFICATION
# ============================================================

def identify_dataset(file_name):

    name = file_name.lower()

    if name.startswith("customers_master_"):
        return "customers"

    if name.startswith("products_master_"):
        return "products"

    if name.startswith("stores_master_"):
        return "stores"

    if name.startswith("salespersons_master_"):
        return "salespersons"

    if name.startswith("promotions_master_"):
        return "promotions"

    if name.startswith("sales_"):
        return "sales"

    if name.startswith("returns_"):
        return "returns"

    if name.startswith("targets_"):
        return "targets"

    return None


# ============================================================
# HELPERS
# ============================================================

def is_blank(value):

    return value is None or str(value).strip() == ""


def valid_integer(value):

    if is_blank(value):
        return True

    try:
        number = float(str(value).strip())
        return number.is_integer()

    except ValueError:
        return False


def valid_decimal(value):

    if is_blank(value):
        return True

    try:
        Decimal(str(value).strip())
        return True

    except (InvalidOperation, ValueError):
        return False


def valid_date(value):

    if is_blank(value):
        return True

    try:
        datetime.strptime(
            str(value).strip(),
            "%Y-%m-%d"
        )
        return True

    except ValueError:
        return False


def valid_time(value):

    if is_blank(value):
        return True

    try:
        datetime.strptime(
            str(value).strip(),
            "%H:%M:%S"
        )
        return True

    except ValueError:
        return False


def validate_type(value, expected_type):

    if is_blank(value):
        return True

    if expected_type == "string":
        return True

    if expected_type == "integer":
        return valid_integer(value)

    if expected_type == "decimal":
        return valid_decimal(value)

    if expected_type == "date":
        return valid_date(value)

    if expected_type == "time":
        return valid_time(value)

    return False


# ============================================================
# ROW VALIDATION
# ============================================================

def validate_row(row, dataset):

    reasons = []

    schema = SCHEMAS[dataset]

    mandatory_fields = MANDATORY_FIELDS[dataset]

    # --------------------------------------------------------
    # 1. MANDATORY FIELD VALIDATION
    # --------------------------------------------------------

    for field in mandatory_fields:

        if field not in row:

            reasons.append(
                f"MANDATORY_FIELD_MISSING:{field}"
            )

        elif is_blank(row.get(field)):

            reasons.append(
                f"MANDATORY_VALUE_BLANK:{field}"
            )

    # --------------------------------------------------------
    # 2. DATA TYPE VALIDATION
    # --------------------------------------------------------

    for field, expected_type in schema.items():

        if field not in row:
            continue

        value = row.get(field)

        if not validate_type(
            value,
            expected_type
        ):

            reasons.append(
                f"INVALID_DATA_TYPE:{field}"
            )

    # --------------------------------------------------------
    # 3. CATEGORICAL VALUE VALIDATION
    # --------------------------------------------------------

    for field, allowed_values in ALLOWED_VALUES.items():

        if field not in row:
            continue

        value = row.get(field)

        if is_blank(value):
            continue

        if str(value).strip() not in allowed_values:

            reasons.append(
                f"INVALID_CATEGORICAL_VALUE:{field}"
            )

    # --------------------------------------------------------
    # 4. BUSINESS-LEVEL CHECKS
    # --------------------------------------------------------

    # Quantity must be positive for sales and returns.
    if dataset == "sales":

        value = row.get("quantity")

        if not is_blank(value):

            try:

                if int(float(value)) <= 0:

                    reasons.append(
                        "INVALID_QUANTITY"
                    )

            except ValueError:

                pass

    if dataset == "returns":

        value = row.get("quantity_returned")

        if not is_blank(value):

            try:

                if int(float(value)) <= 0:

                    reasons.append(
                        "INVALID_RETURN_QUANTITY"
                    )

            except ValueError:

                pass

    # Discount percentage should not be negative.
    if "discount_pct" in row:

        value = row.get("discount_pct")

        if not is_blank(value):

            try:

                if Decimal(str(value)) < 0:

                    reasons.append(
                        "INVALID_DISCOUNT_PCT"
                    )

            except InvalidOperation:

                pass

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    if reasons:

        status = "FAIL"

    else:

        status = "PASS"

    return status, reasons


# ============================================================
# PROCESS ONE FILE
# ============================================================

def process_file(file_path):

    file_name = file_path.name

    dataset = identify_dataset(file_name)

    print("\n" + "=" * 80)
    print(f"FILE: {file_name}")
    print("=" * 80)

    if dataset is None:

        print(
            "WARNING: Dataset could not be identified."
        )

        return []

    print(f"Dataset: {dataset}")

    output_rows = []

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            if not reader.fieldnames:

                print(
                    "FAIL: No columns found."
                )

                return []

            for row_number, row in enumerate(
                reader,
                start=2
            ):

                status, reasons = validate_row(
                    row,
                    dataset
                )

                output_row = dict(row)

                output_row["source_file"] = file_name
                output_row["row_number"] = row_number
                output_row["validation_status"] = status

                if reasons:

                    output_row["reason_codes"] = ";".join(
                        reasons
                    )

                    output_row["reason_details"] = (
                        f"{len(reasons)} validation issue(s)"
                    )

                else:

                    output_row["reason_codes"] = ""
                    output_row["reason_details"] = ""

                output_rows.append(
                    output_row
                )

        total_rows = len(output_rows)

        failed_rows = sum(
            1
            for row in output_rows
            if row["validation_status"] == "FAIL"
        )

        passed_rows = (
            total_rows - failed_rows
        )

        print(f"Rows checked : {total_rows}")
        print(f"PASS rows    : {passed_rows}")
        print(f"FAIL rows    : {failed_rows}")

        return output_rows

    except Exception as error:

        print(
            f"ERROR processing {file_name}: {error}"
        )

        return []


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TRACKER 03.13 - ROW-LEVEL VALIDATION FLAGS")
    print("=" * 80)

    if not INPUT_DIR.exists():

        print(
            f"ERROR: Incoming folder not found: "
            f"{INPUT_DIR}"
        )

        return

    csv_files = sorted(
        INPUT_DIR.glob("*.csv")
    )

    if not csv_files:

        print(
            f"WARNING: No CSV files found in: "
            f"{INPUT_DIR}"
        )

        return

    print(
        f"Found {len(csv_files)} CSV file(s) "
        f"in: {INPUT_DIR}"
    )

    all_rows = []

    for file_path in csv_files:

        file_rows = process_file(
            file_path
        )

        all_rows.extend(
            file_rows
        )

    # --------------------------------------------------------
    # SAVE ROW-LEVEL RESULTS
    # --------------------------------------------------------

    output_file = (
        OUTPUT_DIR /
        "row_level_validation_flags.csv"
    )

    if all_rows:

        # Collect all possible columns.
        fieldnames = []

        for row in all_rows:

            for field in row.keys():

                if field not in fieldnames:
                    fieldnames.append(field)

        with open(
            output_file,
            "w",
            encoding="utf-8",
            newline=""
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
                extrasaction="ignore"
            )

            writer.writeheader()

            for row in all_rows:

                writer.writerow(row)

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    total_rows = len(all_rows)

    failed_rows = sum(
        1
        for row in all_rows
        if row["validation_status"] == "FAIL"
    )

    passed_rows = (
        total_rows - failed_rows
    )

    print("\n" + "=" * 80)
    print("ROW-LEVEL VALIDATION SUMMARY")
    print("=" * 80)

    print(f"Total rows checked : {total_rows}")
    print(f"PASS rows          : {passed_rows}")
    print(f"FAIL rows          : {failed_rows}")

    print(
        f"\nOutput saved to:"
        f"\n{output_file}"
    )

    print("\n" + "=" * 80)
    print(
        "Tracker 03.13 row-level validation "
        "flags completed."
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
import csv
from pathlib import Path


# ============================================================
# TRACKER 03.09 - MANDATORY FIELD VALIDATION
# ============================================================

INPUT_DIR = Path("incoming")


# Mandatory fields from the approved Data Specification
MANDATORY_FIELDS = {
    "customers_master": [
        "customer_id",
        "customer_name",
        "city",
        "state",
        "region",
        "registration_date",
        "customer_segment",
        "status",
    ],

    "products_master": [
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
    ],

    "stores_master": [
        "store_id",
        "store_name",
        "store_type",
        "city",
        "state",
        "region",
        "postal_code",
        "opening_date",
        "status",
    ],

    "salespersons_master": [
        "salesperson_id",
        "salesperson_name",
        "store_id",
        "joining_date",
        "role",
        "status",
    ],

    "promotions_master": [
        "promotion_id",
        "promotion_name",
        "promotion_type",
        "start_date",
        "end_date",
        "discount_pct",
        "applicable_channel",
        "status",
    ],

    "sales": [
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
    ],

    "returns": [
        "return_id",
        "sales_line_id",
        "return_date",
        "quantity_returned",
        "return_reason",
        "return_status",
    ],

    "targets": [
        "target_id",
        "target_month",
        "store_id",
        "category",
        "revenue_target",
        "profit_target",
        "order_target",
        "return_rate_target_pct",
    ],
}


def get_dataset_type(filename):
    """Identify dataset type from the approved filename pattern."""

    name = filename.lower()

    if name.startswith("customers_master"):
        return "customers_master"

    if name.startswith("products_master"):
        return "products_master"

    if name.startswith("stores_master"):
        return "stores_master"

    if name.startswith("salespersons_master"):
        return "salespersons_master"

    if name.startswith("promotions_master"):
        return "promotions_master"

    # Monthly transaction files: sales_YYYY-MM.csv
    if name.startswith("sales_"):
        return "sales"

    if name.startswith("returns"):
        return "returns"

    if name.startswith("targets"):
        return "targets"

    return None


def is_blank(value):
    """Identify blank mandatory values."""

    return value is None or value.strip() == ""


def validate_file(file_path, mandatory_fields):

    print("\n" + "-" * 70)
    print(f"FILE: {file_path.name}")
    print("-" * 70)

    missing_columns = []
    missing_values = []

    try:
        with file_path.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                print("RESULT: INVALID")
                print("Reason: CSV has no header row.")
                return False

            actual_columns = [
                column.strip()
                for column in reader.fieldnames
            ]

            # ------------------------------------------------
            # Check mandatory columns
            # ------------------------------------------------
            for field in mandatory_fields:
                if field not in actual_columns:
                    missing_columns.append(field)

            if missing_columns:
                print("Missing mandatory columns:")

                for field in missing_columns:
                    print(f"  - {field}")

            # ------------------------------------------------
            # Check mandatory values
            # ------------------------------------------------
            for row_number, row in enumerate(reader, start=2):

                for field in mandatory_fields:

                    # Column itself is missing
                    if field not in actual_columns:
                        continue

                    value = row.get(field)

                    if is_blank(value):
                        missing_values.append(
                            (row_number, field)
                        )

        # ----------------------------------------------------
        # Display missing values
        # ----------------------------------------------------
        if missing_values:
            print("Missing mandatory values:")

            for row_number, field in missing_values:
                print(
                    f"  - Row {row_number}: "
                    f"{field} is blank"
                )

        # ----------------------------------------------------
        # Final result
        # ----------------------------------------------------
        if not missing_columns and not missing_values:
            print("RESULT: PASS")
            print("All mandatory fields contain values.")
            return True

        print("RESULT: INVALID")
        return False

    except Exception as error:
        print("RESULT: ERROR")
        print(f"Error: {error}")
        return False


def main():

    print("=" * 70)
    print("TRACKER 03.09 - MANDATORY FIELD VALIDATION")
    print("=" * 70)

    if not INPUT_DIR.exists():
        print(f"ERROR: Input folder not found: {INPUT_DIR}")
        return

    csv_files = sorted(INPUT_DIR.glob("*.csv"))

    if not csv_files:
        print(f"WARNING: No CSV files found in: {INPUT_DIR}")
        return

    overall_pass = True

    for file_path in csv_files:

        dataset_type = get_dataset_type(file_path.name)

        print("\n" + "=" * 70)
        print(f"DATASET: {file_path.name}")
        print("=" * 70)

        if dataset_type is None:
            print("STATUS: SKIPPED")
            print(
                "Reason: No mandatory-field definition "
                "for this dataset."
            )
            continue

        result = validate_file(
            file_path,
            MANDATORY_FIELDS[dataset_type]
        )

        if not result:
            overall_pass = False

    # --------------------------------------------------------
    # Overall result
    # --------------------------------------------------------
    print("\n" + "=" * 70)
    print("TRACKER 03.09 SUMMARY")
    print("=" * 70)

    if overall_pass:
        print("STATUS: PASS")
        print("Mandatory-field validation completed successfully.")
    else:
        print("STATUS: INVALID")
        print("Mandatory-field issues were detected.")

    print("Source files were not modified.")


if __name__ == "__main__":
    main()
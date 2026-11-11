import csv
from pathlib import Path


# ============================================================
# TRACKER 03.10 - ALLOWED CATEGORICAL VALUE VALIDATION
# ============================================================

INPUT_DIR = Path("incoming")


# Approved categorical domains from Document 02
ALLOWED_VALUES = {

    # -------------------------
    # Customer
    # -------------------------
    "customer.gender": {
        "Male",
        "Female",
        "Other",
    },

    "customer.customer_segment": {
        "Occasional",
        "Regular",
        "Premium",
        "VIP",
    },

    "customer.preferred_channel": {
        "Store",
        "Online",
    },

    "customer.status": {
        "Active",
        "Inactive",
    },

    # -------------------------
    # Product
    # -------------------------
    "product.category": {
        "Electronics",
        "Home & Kitchen",
        "Fashion",
        "Beauty & Personal Care",
        "Sports & Fitness",
        "Grocery",
    },

    "product.status": {
        "Active",
        "Discontinued",
        "Suspended",
    },

    # -------------------------
    # Store
    # -------------------------
    "store.store_type": {
        "Mall",
        "High Street",
        "Outlet",
        "Neighborhood",
    },

    "store.region": {
        "North",
        "South",
        "East",
        "West",
        "Central",
    },

    "store.status": {
        "Active",
        "Temporarily Closed",
        "Closed",
    },

    # -------------------------
    # Salesperson
    # -------------------------
    "salesperson.role": {
        "Sales Associate",
        "Senior Sales Associate",
        "Store Supervisor",
    },

    "salesperson.status": {
        "Active",
        "Inactive",
    },

    # -------------------------
    # Promotion
    # -------------------------
    "promotion.promotion_type": {
        "Seasonal",
        "Category",
        "Storewide",
        "Channel",
    },

    "promotion.applicable_channel": {
        "Store",
        "Online",
        "ALL",
    },

    "promotion.status": {
        "Planned",
        "Active",
        "Expired",
        "Cancelled",
    },

    # -------------------------
    # Sales
    # -------------------------
    "sales.sales_channel": {
        "Store",
        "Online",
    },

    "sales.payment_method": {
        "Cash",
        "Card",
        "UPI",
        "Wallet",
        "Net Banking",
    },

    "sales.order_status": {
        "Completed",
        "Cancelled",
    },

    # -------------------------
    # Returns
    # -------------------------
    "return.return_reason": {
        "Damaged",
        "Wrong Product",
        "Quality Issue",
        "Size/Fit Issue",
        "Customer Changed Mind",
        "Late Delivery",
        "Other",
    },

    "return.return_status": {
        "Requested",
        "Approved",
        "Rejected",
        "Refunded",
    },

    "return.refund_method": {
        "Original Payment",
        "Store Credit",
        "Cash",
    },
}


# Map each incoming dataset to the categorical fields
# that belong to that dataset.
DATASET_FIELDS = {

    "customers_master": {
        "gender": "customer.gender",
        "customer_segment": "customer.customer_segment",
        "preferred_channel": "customer.preferred_channel",
        "status": "customer.status",
        "region": "store.region",
    },

    "products_master": {
        "category": "product.category",
        "status": "product.status",
    },

    "stores_master": {
        "store_type": "store.store_type",
        "region": "store.region",
        "status": "store.status",
    },

    "salespersons_master": {
        "role": "salesperson.role",
        "status": "salesperson.status",
    },

    "promotions_master": {
        "promotion_type": "promotion.promotion_type",
        "applicable_channel": "promotion.applicable_channel",
        "status": "promotion.status",
    },

    "sales": {
        "sales_channel": "sales.sales_channel",
        "payment_method": "sales.payment_method",
        "order_status": "sales.order_status",
    },

    "returns": {
        "return_reason": "return.return_reason",
        "return_status": "return.return_status",
        "refund_method": "return.refund_method",
    },

    "targets": {
        "category": "product.category",
    },
}


def get_dataset_type(filename):
    """Identify the dataset from the approved file naming pattern."""

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

    if name.startswith("sales_"):
        return "sales"

    if name.startswith("returns"):
        return "returns"

    if name.startswith("targets"):
        return "targets"

    return None


def validate_file(file_path, field_rules):

    print("\n" + "-" * 70)
    print(f"FILE: {file_path.name}")
    print("-" * 70)

    invalid_values = []

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

            # Check each constrained field
            for column_name, domain_name in field_rules.items():

                # Field not present in this file
                if column_name not in actual_columns:
                    continue

                allowed = ALLOWED_VALUES[domain_name]

                for row_number, row in enumerate(reader, start=2):

                    value = row.get(column_name)

                    # Blank is handled by Tracker 03.09.
                    # Do not classify blank as an invalid category here.
                    if value is None or value.strip() == "":
                        continue

                    value = value.strip()

                    if value not in allowed:
                        invalid_values.append(
                            (
                                row_number,
                                column_name,
                                value,
                                domain_name,
                            )
                        )

                # DictReader is consumed after first field.
                # Re-read the file for the next categorical field.
                file.seek(0)
                reader = csv.DictReader(file)

            if invalid_values:

                print("INVALID CATEGORICAL VALUES:")

                for row_number, field, value, domain_name in invalid_values:
                    allowed_display = ", ".join(
                        sorted(ALLOWED_VALUES[domain_name])
                    )

                    print(
                        f"  - Row {row_number}: "
                        f"{field} = '{value}'"
                    )
                    print(
                        f"    Allowed values: {allowed_display}"
                    )

                print("RESULT: INVALID")
                return False

            print("RESULT: PASS")
            print("All populated constrained categorical values are valid.")
            return True

    except Exception as error:

        print("RESULT: ERROR")
        print(f"Error: {error}")
        return False


def main():

    print("=" * 70)
    print("TRACKER 03.10 - ALLOWED CATEGORICAL VALUE VALIDATION")
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
            print("Reason: No categorical rules defined for this dataset.")
            continue

        result = validate_file(
            file_path,
            DATASET_FIELDS[dataset_type]
        )

        if not result:
            overall_pass = False

    print("\n" + "=" * 70)
    print("TRACKER 03.10 SUMMARY")
    print("=" * 70)

    if overall_pass:
        print("STATUS: PASS")
        print("Allowed categorical value validation completed successfully.")
    else:
        print("STATUS: INVALID")
        print("Invalid categorical values were detected.")

    print("Source files were not modified.")


if __name__ == "__main__":
    main()
    
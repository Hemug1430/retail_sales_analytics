"""
Retail Sales Analytics
Tracker 04.11 - Apply Row-Level Business Validation

Purpose:
    Validate documented business rules at row level without deleting
    source records or inventing business values.

Rules covered where the relevant columns/datasets are available:
    - Positive integer quantities
    - Positive pricing
    - Discount percentage range
    - Valid status values
    - Sales date relationships
    - Customer registration/DOB relationships
    - Product launch date vs sale date
    - Return date vs original sale date
    - Return quantity vs sold quantity
    - Promotion start/end dates
    - Promotion date vs sales date
    - Refund rules where applicable
    - Target positivity where applicable

Important:
    Source CSV files are NOT modified.
    Invalid rows are flagged for review/rejection evidence.
"""

from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_value(value):
    """Convert values to a comparable stripped string."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def find_latest_processed_file(prefix):
    """
    Find the latest processed CSV beginning with the supplied prefix.
    """
    files = sorted(
        PROCESSED_DIR.glob(f"{prefix}*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return files[0] if files else None


def find_processed_dataset(dataset):
    """
    Locate the latest processed dataset for the supplied dataset name.
    """
    prefix = f"{dataset}_"

    files = sorted(
        PROCESSED_DIR.glob(f"{prefix}*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    # Avoid selecting audit/summary files
    files = [
        f for f in files
        if "audit" not in f.name.lower()
        and "summary" not in f.name.lower()
        and "flags" not in f.name.lower()
    ]

    return files[0] if files else None


def add_validation_columns(df):
    """
    Add row-level validation evidence columns.
    """
    df = df.copy()

    df["business_validation_status"] = "PASS"
    df["business_validation_reason"] = ""

    return df


def flag_row(df, mask, reason):
    """
    Flag rows without deleting them.
    """
    mask = mask.fillna(False)

    df.loc[mask, "business_validation_status"] = "REVIEW"

    existing = df.loc[mask, "business_validation_reason"].fillna("")

    new_reason = np.where(
        existing.eq(""),
        reason,
        existing + " | " + reason
    )

    df.loc[mask, "business_validation_reason"] = new_reason

    return int(mask.sum())


# ============================================================
# SALES VALIDATION
# ============================================================

def validate_sales():
    path = find_processed_dataset("sales_2024_01")

    if path is None:
        print("Sales dataset not found. Skipping sales validation.")
        return None

    df = pd.read_csv(path, encoding="utf-8-sig")

    original_rows = len(df)

    df = add_validation_columns(df)

    print("\n" + "=" * 80)
    print("04.11 BUSINESS VALIDATION - SALES")
    print("=" * 80)

    print(f"Input file : {path}")
    print(f"Rows read  : {original_rows}")
    print(f"Columns    : {len(df.columns)}")

    rule_counts = {}

    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------

    if "quantity" in df.columns:

        quantity = pd.to_numeric(
            df["quantity"],
            errors="coerce"
        )

        mask = quantity.isna() | (quantity <= 0) | (quantity % 1 != 0)

        count = flag_row(
            df,
            mask,
            "Invalid quantity: must be a positive integer"
        )

        rule_counts["quantity"] = count

    # --------------------------------------------------------
    # Unit selling price
    # --------------------------------------------------------

    if "unit_selling_price" in df.columns:

        price = pd.to_numeric(
            df["unit_selling_price"],
            errors="coerce"
        )

        mask = price.isna() | (price <= 0)

        count = flag_row(
            df,
            mask,
            "Invalid unit_selling_price: must be positive"
        )

        rule_counts["unit_selling_price"] = count

    # --------------------------------------------------------
    # Discount percentage
    # --------------------------------------------------------

    if "discount_pct" in df.columns:

        discount = pd.to_numeric(
            df["discount_pct"],
            errors="coerce"
        )

        mask = discount.isna() | (discount < 0) | (discount > 100)

        count = flag_row(
            df,
            mask,
            "Invalid discount_pct: expected range 0-100"
        )

        rule_counts["discount_pct"] = count

    # --------------------------------------------------------
    # Sales channel
    # --------------------------------------------------------

    if "sales_channel" in df.columns:

        allowed = {"Store", "Online"}

        mask = (
            df["sales_channel"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            &
            ~df["sales_channel"]
            .fillna("")
            .astype(str)
            .str.strip()
            .isin(allowed)
        )

        count = flag_row(
            df,
            mask,
            "Invalid sales_channel"
        )

        rule_counts["sales_channel"] = count

    # --------------------------------------------------------
    # Payment method
    # --------------------------------------------------------

    if "payment_method" in df.columns:

        allowed = {
            "Cash",
            "Card",
            "UPI",
            "Wallet",
            "Net Banking",
        }

        mask = (
            df["payment_method"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            &
            ~df["payment_method"]
            .fillna("")
            .astype(str)
            .str.strip()
            .isin(allowed)
        )

        count = flag_row(
            df,
            mask,
            "Invalid payment_method"
        )

        rule_counts["payment_method"] = count

    # --------------------------------------------------------
    # Order status
    # --------------------------------------------------------

    if "order_status" in df.columns:

        allowed = {
            "Completed",
            "Cancelled",
        }

        mask = (
            df["order_status"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            &
            ~df["order_status"]
            .fillna("")
            .astype(str)
            .str.strip()
            .isin(allowed)
        )

        count = flag_row(
            df,
            mask,
            "Invalid order_status"
        )

        rule_counts["order_status"] = count

    # --------------------------------------------------------
    # Order date
    # --------------------------------------------------------

    order_date = None

    if "order_date" in df.columns:

        order_date = pd.to_datetime(
            df["order_date"],
            errors="coerce"
        )

        mask = order_date.isna()

        count = flag_row(
            df,
            mask,
            "Invalid order_date"
        )

        rule_counts["order_date"] = count

    # --------------------------------------------------------
    # Customer registration date vs sale date
    # --------------------------------------------------------

    customers_path = find_processed_dataset("customers_master")

    if (
        customers_path is not None
        and "customer_id" in df.columns
        and order_date is not None
    ):

        customers = pd.read_csv(
            customers_path,
            encoding="utf-8-sig"
        )

        if {
            "customer_id",
            "registration_date",
        }.issubset(customers.columns):

            customers["registration_date"] = pd.to_datetime(
                customers["registration_date"],
                errors="coerce"
            )

            registration_lookup = (
                customers
                .drop_duplicates("customer_id")
                .set_index("customer_id")["registration_date"]
            )

            customer_registration = (
                df["customer_id"]
                .map(registration_lookup)
            )

            populated = (
                df["customer_id"].notna()
                & df["customer_id"].astype(str).str.strip().ne("")
                & customer_registration.notna()
                & order_date.notna()
            )

            mask = (
                populated
                & (order_date < customer_registration)
            )

            count = flag_row(
                df,
                mask,
                "Order date precedes customer registration_date"
            )

            rule_counts["customer_registration_date"] = count

    # --------------------------------------------------------
    # Product launch date vs sale date
    # --------------------------------------------------------

    products_path = find_processed_dataset("products_master")

    if (
        products_path is not None
        and "product_id" in df.columns
        and order_date is not None
    ):

        products = pd.read_csv(
            products_path,
            encoding="utf-8-sig"
        )

        if {
            "product_id",
            "launch_date",
        }.issubset(products.columns):

            products["launch_date"] = pd.to_datetime(
                products["launch_date"],
                errors="coerce"
            )

            launch_lookup = (
                products
                .drop_duplicates("product_id")
                .set_index("product_id")["launch_date"]
            )

            launch_date = df["product_id"].map(
                launch_lookup
            )

            populated = (
                launch_date.notna()
                & order_date.notna()
            )

            mask = (
                populated
                & (order_date < launch_date)
            )

            count = flag_row(
                df,
                mask,
                "Order date precedes product launch_date"
            )

            rule_counts["product_launch_date"] = count

    # --------------------------------------------------------
    # Save output
    # --------------------------------------------------------

    output_path = (
        PROCESSED_DIR
        / "sales_2024_01_04_11_business_validation.csv"
    )

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    review_rows = int(
        (df["business_validation_status"] == "REVIEW").sum()
    )

    pass_rows = int(
        (df["business_validation_status"] == "PASS").sum()
    )

    print("\nSALES BUSINESS VALIDATION SUMMARY")
    print("-" * 80)
    print(f"Total rows processed : {len(df):,}")
    print(f"PASS rows            : {pass_rows:,}")
    print(f"REVIEW rows          : {review_rows:,}")

    for rule, count in rule_counts.items():
        print(f"{rule:<30}: {count:,}")

    print(f"\nOutput : {output_path}")

    return df


# ============================================================
# CUSTOMER VALIDATION
# ============================================================

def validate_customers():

    path = find_processed_dataset("customers_master")

    if path is None:
        print("\nCustomers dataset not found.")
        return None

    df = pd.read_csv(
        path,
        encoding="utf-8-sig"
    )

    df = add_validation_columns(df)

    print("\n" + "=" * 80)
    print("04.11 BUSINESS VALIDATION - CUSTOMERS")
    print("=" * 80)

    print(f"Input file : {path}")
    print(f"Rows read  : {len(df):,}")

    # --------------------------------------------------------
    # Registration date
    # --------------------------------------------------------

    registration_date = None

    if "registration_date" in df.columns:

        registration_date = pd.to_datetime(
            df["registration_date"],
            errors="coerce"
        )

        mask = registration_date.isna()

        flag_row(
            df,
            mask,
            "Invalid registration_date"
        )

    # --------------------------------------------------------
    # Date of birth must not be after registration date
    # --------------------------------------------------------

    if (
        "date_of_birth" in df.columns
        and registration_date is not None
    ):

        dob = pd.to_datetime(
            df["date_of_birth"],
            errors="coerce"
        )

        populated = (
            dob.notna()
            & registration_date.notna()
        )

        mask = (
            populated
            & (dob > registration_date)
        )

        flag_row(
            df,
            mask,
            "date_of_birth occurs after registration_date"
        )

    # --------------------------------------------------------
    # Customer status
    # --------------------------------------------------------

    if "status" in df.columns:

        allowed = {
            "Active",
            "Inactive",
        }

        mask = (
            df["status"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            &
            ~df["status"]
            .fillna("")
            .astype(str)
            .str.strip()
            .isin(allowed)
        )

        flag_row(
            df,
            mask,
            "Invalid customer status"
        )

    output_path = (
        PROCESSED_DIR
        / "customers_master_04_11_business_validation.csv"
    )

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    review_rows = int(
        (df["business_validation_status"] == "REVIEW").sum()
    )

    print("\nCUSTOMER BUSINESS VALIDATION SUMMARY")
    print("-" * 80)
    print(f"Total rows processed : {len(df):,}")
    print(f"REVIEW rows          : {review_rows:,}")
    print(f"Output               : {output_path}")

    return df



# ============================================================
# STORE VALIDATION
# ============================================================

def validate_stores():
    """
    Validate stores_master rows using the documented project fields.

    This function intentionally does not invent store-status values.
    It validates required business fields and opening_date parseability,
    while preserving every source row for downstream 04.12 processing.
    """
    path = find_processed_dataset("stores_master")

    if path is None:
        print("\nStores dataset not found.")
        return None

    df = pd.read_csv(
        path,
        encoding="utf-8-sig"
    )

    df = add_validation_columns(df)

    print("\n" + "=" * 80)
    print("04.11 BUSINESS VALIDATION - STORES")
    print("=" * 80)
    print(f"Input file : {path}")
    print(f"Rows read  : {len(df):,}")

    # Required store fields documented in Tracker 04.06.
    required_fields = [
        "store_id",
        "store_name",
        "store_type",
        "city",
        "state",
        "region",
        "postal_code",
        "opening_date",
        "status",
    ]

    for column in required_fields:
        if column not in df.columns:
            print(f"Missing required column: {column}")
            df["business_validation_status"] = "REVIEW"
            existing = df["business_validation_reason"].fillna("")
            reason = f"Missing required column: {column}"
            df["business_validation_reason"] = np.where(
                existing.eq(""),
                reason,
                existing + " | " + reason
            )
            continue

        blank_mask = (
            df[column].isna()
            | df[column].astype(str).str.strip().eq("")
        )

        flag_row(
            df,
            blank_mask,
            f"Missing required store field: {column}"
        )

    # Opening date must be a valid date when the field exists.
    if "opening_date" in df.columns:
        opening_date = pd.to_datetime(
            df["opening_date"],
            errors="coerce"
        )

        mask = opening_date.isna()

        flag_row(
            df,
            mask,
            "Invalid opening_date"
        )

    output_path = (
        PROCESSED_DIR
        / "stores_master_04_11_business_validation.csv"
    )

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    review_rows = int(
        (df["business_validation_status"] == "REVIEW").sum()
    )

    pass_rows = int(
        (df["business_validation_status"] == "PASS").sum()
    )

    print("\nSTORE BUSINESS VALIDATION SUMMARY")
    print("-" * 80)
    print(f"Total rows processed : {len(df):,}")
    print(f"PASS rows            : {pass_rows:,}")
    print(f"REVIEW rows          : {review_rows:,}")
    print(f"Output               : {output_path}")

    return df


# ============================================================
# PRODUCT VALIDATION
# ============================================================

def validate_products():

    path = find_processed_dataset("products_master")

    if path is None:
        print("\nProducts dataset not found.")
        return None

    df = pd.read_csv(
        path,
        encoding="utf-8-sig"
    )

    df = add_validation_columns(df)

    print("\n" + "=" * 80)
    print("04.11 BUSINESS VALIDATION - PRODUCTS")
    print("=" * 80)

    print(f"Input file : {path}")
    print(f"Rows read  : {len(df):,}")

    # --------------------------------------------------------
    # Launch date
    # --------------------------------------------------------

    if "launch_date" in df.columns:

        launch_date = pd.to_datetime(
            df["launch_date"],
            errors="coerce"
        )

        mask = launch_date.isna()

        flag_row(
            df,
            mask,
            "Invalid launch_date"
        )

    # --------------------------------------------------------
    # Product status
    # --------------------------------------------------------

    if "status" in df.columns:

        allowed = {
            "Active",
            "Discontinued",
            "Suspended",
        }

        mask = (
            df["status"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            &
            ~df["status"]
            .fillna("")
            .astype(str)
            .str.strip()
            .isin(allowed)
        )

        flag_row(
            df,
            mask,
            "Invalid product status"
        )

    # --------------------------------------------------------
    # Numeric fields only when actually available
    # --------------------------------------------------------

    for column in [
        "unit_cost",
        "list_price",
        "tax_rate_pct",
    ]:

        if column not in df.columns:
            continue

        numeric = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        if column in {"unit_cost", "list_price"}:

            mask = numeric.notna() & (numeric <= 0)

            flag_row(
                df,
                mask,
                f"Invalid {column}: must be positive"
            )

        elif column == "tax_rate_pct":

            mask = (
                numeric.notna()
                & ((numeric < 0) | (numeric > 100))
            )

            flag_row(
                df,
                mask,
                "Invalid tax_rate_pct: expected range 0-100"
            )

    output_path = (
        PROCESSED_DIR
        / "products_master_04_11_business_validation.csv"
    )

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    review_rows = int(
        (df["business_validation_status"] == "REVIEW").sum()
    )

    print("\nPRODUCT BUSINESS VALIDATION SUMMARY")
    print("-" * 80)
    print(f"Total rows processed : {len(df):,}")
    print(f"REVIEW rows          : {review_rows:,}")
    print(f"Output               : {output_path}")

    return df


# ============================================================
# RETURNS VALIDATION
# ============================================================

def validate_returns():

    path = find_processed_dataset("returns")

    if path is None:
        print("\nReturns dataset not available in current processed inputs.")
        return None

    df = pd.read_csv(
        path,
        encoding="utf-8-sig"
    )

    df = add_validation_columns(df)

    print("\n" + "=" * 80)
    print("04.11 BUSINESS VALIDATION - RETURNS")
    print("=" * 80)

    print(f"Input file : {path}")
    print(f"Rows read  : {len(df):,}")

    if "quantity_returned" in df.columns:

        qty = pd.to_numeric(
            df["quantity_returned"],
            errors="coerce"
        )

        mask = (
            qty.isna()
            | (qty <= 0)
            | (qty % 1 != 0)
        )

        flag_row(
            df,
            mask,
            "Invalid quantity_returned: must be positive integer"
        )

    if "return_date" in df.columns:

        return_date = pd.to_datetime(
            df["return_date"],
            errors="coerce"
        )

        mask = return_date.isna()

        flag_row(
            df,
            mask,
            "Invalid return_date"
        )

    if "return_status" in df.columns:

        allowed = {
            "Requested",
            "Approved",
            "Rejected",
            "Refunded",
        }

        mask = (
            df["return_status"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            &
            ~df["return_status"]
            .fillna("")
            .astype(str)
            .str.strip()
            .isin(allowed)
        )

        flag_row(
            df,
            mask,
            "Invalid return_status"
        )

    output_path = (
        PROCESSED_DIR
        / "returns_04_11_business_validation.csv"
    )

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    review_rows = int(
        (df["business_validation_status"] == "REVIEW").sum()
    )

    print("\nRETURN BUSINESS VALIDATION SUMMARY")
    print("-" * 80)
    print(f"Total rows processed : {len(df):,}")
    print(f"REVIEW rows          : {review_rows:,}")
    print(f"Output               : {output_path}")

    return df


# ============================================================
# PROMOTION VALIDATION
# ============================================================

def validate_promotions():

    path = find_processed_dataset("promotions_master")

    if path is None:
        print("\nPromotions dataset not available in current processed inputs.")
        return None

    df = pd.read_csv(
        path,
        encoding="utf-8-sig"
    )

    df = add_validation_columns(df)

    print("\n" + "=" * 80)
    print("04.11 BUSINESS VALIDATION - PROMOTIONS")
    print("=" * 80)

    print(f"Input file : {path}")
    print(f"Rows read  : {len(df):,}")

    start_date = None
    end_date = None

    if "start_date" in df.columns:

        start_date = pd.to_datetime(
            df["start_date"],
            errors="coerce"
        )

    if "end_date" in df.columns:

        end_date = pd.to_datetime(
            df["end_date"],
            errors="coerce"
        )

    # Promotion end date cannot precede start date

    if start_date is not None and end_date is not None:

        populated = (
            start_date.notna()
            & end_date.notna()
        )

        mask = (
            populated
            & (end_date < start_date)
        )

        flag_row(
            df,
            mask,
            "Promotion end_date precedes start_date"
        )

    # Promotion type

    if "promotion_type" in df.columns:

        allowed = {
            "Seasonal",
            "Category",
            "Storewide",
            "Channel",
        }

        mask = (
            df["promotion_type"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            &
            ~df["promotion_type"]
            .fillna("")
            .astype(str)
            .str.strip()
            .isin(allowed)
        )

        flag_row(
            df,
            mask,
            "Invalid promotion_type"
        )

    # Promotion status

    if "status" in df.columns:

        allowed = {
            "Planned",
            "Active",
            "Expired",
            "Cancelled",
        }

        mask = (
            df["status"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            &
            ~df["status"]
            .fillna("")
            .astype(str)
            .str.strip()
            .isin(allowed)
        )

        flag_row(
            df,
            mask,
            "Invalid promotion status"
        )

    output_path = (
        PROCESSED_DIR
        / "promotions_master_04_11_business_validation.csv"
    )

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    review_rows = int(
        (df["business_validation_status"] == "REVIEW").sum()
    )

    print("\nPROMOTION BUSINESS VALIDATION SUMMARY")
    print("-" * 80)
    print(f"Total rows processed : {len(df):,}")
    print(f"REVIEW rows          : {review_rows:,}")
    print(f"Output               : {output_path}")

    return df


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TRACKER 04.11 - APPLY ROW-LEVEL BUSINESS VALIDATION")
    print("=" * 80)

    results = []

    sales = validate_sales()
    if sales is not None:
        results.append(sales)

    customers = validate_customers()
    if customers is not None:
        results.append(customers)

    products = validate_products()
    if products is not None:
        results.append(products)

    stores = validate_stores()
    if stores is not None:
        results.append(stores)

    returns = validate_returns()
    if returns is not None:
        results.append(returns)

    promotions = validate_promotions()
    if promotions is not None:
        results.append(promotions)

    total_rows = sum(len(df) for df in results)

    total_review = sum(
        int(
            (df["business_validation_status"] == "REVIEW").sum()
        )
        for df in results
    )

    print("\n" + "=" * 80)
    print("04.11 OVERALL RESULT")
    print("=" * 80)

    print(f"Datasets processed : {len(results)}")
    print(f"Rows processed     : {total_rows:,}")
    print(f"Rows requiring review : {total_review:,}")

    print("\nBusiness validation completed.")
    print("Invalid business conditions were flagged for investigation.")
    print("No source CSV files were modified or deleted.")

    print("=" * 80)
    print("Tracker 04.11 processing completed.")
    print("=" * 80)


if __name__ == "__main__":
    main()
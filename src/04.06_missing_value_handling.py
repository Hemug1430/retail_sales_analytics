"""
TRACKER 04.06 - HANDLE MISSING VALUES

Requirement:
Apply field-specific rules:
- Reject required-key nulls
- Preserve legitimate optional nulls
- Impute only where the project document allows

Project rule:
Do NOT invent business values to make a record pass.
Required missing values are flagged as INVALID.
Legitimate optional missing values are preserved.
"""

from pathlib import Path
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_DIR = BASE_DIR / "incoming"
OUTPUT_DIR = BASE_DIR / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# REQUIRED / OPTIONAL FIELD RULES
# ============================================================

DATASET_RULES = {

    "customers_master": {
        "required": [
            "customer_id",
            "customer_name",
            "city",
            "state",
            "region",
            "registration_date",
            "customer_segment",
            "status",
        ],
        "optional": [
            "gender",
            "date_of_birth",
            "email",
            "phone",
            "postal_code",
            "preferred_channel",
        ],
    },

    "products_master": {
        "required": [
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
        "optional": [],
    },

    "stores_master": {
        "required": [
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
        "optional": [
            "floor_area_sqft",
            "manager_name",
        ],
    },

    "salespersons_master": {
        "required": [
            "salesperson_id",
            "salesperson_name",
            "store_id",
            "joining_date",
            "role",
            "status",
        ],
        "optional": [],
    },

    "promotions_master": {
        "required": [
            "promotion_id",
            "promotion_name",
            "promotion_type",
            "start_date",
            "end_date",
            "discount_pct",
            "applicable_channel",
            "status",
        ],
        "optional": [
            "applicable_category",
            "minimum_order_value",
        ],
    },

    "sales": {
        "required": [
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
        "optional": [
            "customer_id",
            "salesperson_id",
            "promotion_id",
        ],
    },

    "returns": {
        "required": [
            "return_id",
            "sales_line_id",
            "return_date",
            "quantity_returned",
            "return_reason",
            "return_status",
        ],
        "optional": [
            "refund_method",
            "refund_amount",
            "processed_store_id",
        ],
    },

    "targets": {
        "required": [
            "target_id",
            "target_month",
            "store_id",
            "category",
            "revenue_target",
            "profit_target",
            "order_target",
            "return_rate_target_pct",
        ],
        "optional": [],
    },
}


# ============================================================
# DATASET IDENTIFICATION
# ============================================================

def identify_dataset(file_name):
    """
    Identify dataset from the approved project naming convention.
    """

    stem = Path(file_name).stem.lower()

    if stem.startswith("customers_master"):
        return "customers_master"

    if stem.startswith("products_master"):
        return "products_master"

    if stem.startswith("stores_master"):
        return "stores_master"

    if stem.startswith("salespersons_master"):
        return "salespersons_master"

    if stem.startswith("promotions_master"):
        return "promotions_master"

    if stem.startswith("sales_"):
        return "sales"

    if stem.startswith("returns_"):
        return "returns"

    if stem.startswith("targets_"):
        return "targets"

    return None


# ============================================================
# BLANK DETECTION
# ============================================================

def is_blank(series):
    """
    Treat empty strings and whitespace-only strings as missing.
    Existing NaN values are also treated as missing.
    """

    return series.isna() | series.astype("string").str.strip().eq("")


# ============================================================
# PROCESS ONE FILE
# ============================================================

def process_file(input_file):
    dataset = identify_dataset(input_file.name)

    if dataset is None:
        return {
            "file_name": input_file.name,
            "dataset": "UNKNOWN",
            "status": "SKIPPED",
            "rows_processed": 0,
            "required_missing_rows": 0,
            "required_missing_values": 0,
            "optional_missing_values": 0,
            "conditional_missing_values": 0,
            "error": "Unsupported dataset name",
        }

    try:
        df = pd.read_csv(
            input_file,
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
        )
    except Exception as exc:
        return {
            "file_name": input_file.name,
            "dataset": dataset,
            "status": "ERROR",
            "rows_processed": 0,
            "required_missing_rows": 0,
            "required_missing_values": 0,
            "optional_missing_values": 0,
            "conditional_missing_values": 0,
            "error": str(exc),
        }

    rules = DATASET_RULES[dataset]

    required_fields = rules["required"]
    optional_fields = rules["optional"]

    # --------------------------------------------------------
    # Check required columns
    # --------------------------------------------------------

    missing_required_columns = [
        column for column in required_fields
        if column not in df.columns
    ]

    # --------------------------------------------------------
    # Row-level flags
    # --------------------------------------------------------

    df["_04_06_required_missing"] = False
    df["_04_06_optional_missing"] = False
    df["_04_06_conditional_missing"] = False
    df["_04_06_missing_reason"] = ""

    required_missing_values = 0
    optional_missing_values = 0
    conditional_missing_values = 0

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    for column in required_fields:

        if column not in df.columns:
            continue

        blank_mask = is_blank(df[column])

        count = int(blank_mask.sum())
        required_missing_values += count

        if count > 0:
            df.loc[blank_mask, "_04_06_required_missing"] = True

            reason = (
                df.loc[blank_mask, "_04_06_missing_reason"]
                .astype("string")
            )

            df.loc[
                blank_mask,
                "_04_06_missing_reason"
            ] = reason.where(
                reason.eq(""),
                reason + "; "
            ) + f"REQ_NULL:{column}"

    # --------------------------------------------------------
    # Optional fields
    # --------------------------------------------------------

    for column in optional_fields:

        if column not in df.columns:
            continue

        blank_mask = is_blank(df[column])

        count = int(blank_mask.sum())
        optional_missing_values += count

        if count > 0:
            df.loc[blank_mask, "_04_06_optional_missing"] = True

            reason = (
                df.loc[blank_mask, "_04_06_missing_reason"]
                .astype("string")
            )

            df.loc[
                blank_mask,
                "_04_06_missing_reason"
            ] = reason.where(
                reason.eq(""),
                reason + "; "
            ) + f"OPTIONAL_NULL:{column}"

    # --------------------------------------------------------
    # Conditional sales rules
    # --------------------------------------------------------

    if dataset == "sales":

        if "sales_channel" in df.columns and "salesperson_id" in df.columns:

            channel = (
                df["sales_channel"]
                .astype("string")
                .str.strip()
                .str.lower()
            )

            salesperson_blank = is_blank(df["salesperson_id"])

            # Online sales may legitimately have NULL salesperson_id.
            # Store sales require salesperson_id.

            store_missing_salesperson = (
                channel.eq("store")
                & salesperson_blank
            )

            count = int(store_missing_salesperson.sum())
            conditional_missing_values += count

            if count > 0:
                df.loc[
                    store_missing_salesperson,
                    "_04_06_conditional_missing"
                ] = True

                reason = (
                    df.loc[
                        store_missing_salesperson,
                        "_04_06_missing_reason"
                    ]
                    .astype("string")
                )

                df.loc[
                    store_missing_salesperson,
                    "_04_06_missing_reason"
                ] = reason.where(
                    reason.eq(""),
                    reason + "; "
                ) + "REQ_NULL:salesperson_id_for_store_sale"

    # --------------------------------------------------------
    # Returns conditional rules
    # --------------------------------------------------------

    if dataset == "returns":

        if (
            "return_status" in df.columns
            and "refund_method" in df.columns
        ):

            status = (
                df["return_status"]
                .astype("string")
                .str.strip()
                .str.lower()
            )

            refund_method_blank = is_blank(df["refund_method"])

            # Document rule:
            # refund_method may be blank while Requested/Rejected.
            # It is applicable for Approved/Refunded states.

            applicable_status = status.isin(
                ["approved", "refunded"]
            )

            missing_refund_method = (
                applicable_status
                & refund_method_blank
            )

            count = int(missing_refund_method.sum())
            conditional_missing_values += count

            if count > 0:
                df.loc[
                    missing_refund_method,
                    "_04_06_conditional_missing"
                ] = True

                reason = (
                    df.loc[
                        missing_refund_method,
                        "_04_06_missing_reason"
                    ]
                    .astype("string")
                )

                df.loc[
                    missing_refund_method,
                    "_04_06_missing_reason"
                ] = reason.where(
                    reason.eq(""),
                    reason + "; "
                ) + "REQ_NULL:refund_method_for_applicable_return"

        if (
            "return_status" in df.columns
            and "refund_amount" in df.columns
        ):

            status = (
                df["return_status"]
                .astype("string")
                .str.strip()
                .str.lower()
            )

            refund_amount_blank = is_blank(df["refund_amount"])

            applicable_status = status.isin(
                ["approved", "refunded"]
            )

            missing_refund_amount = (
                applicable_status
                & refund_amount_blank
            )

            count = int(missing_refund_amount.sum())
            conditional_missing_values += count

            if count > 0:
                df.loc[
                    missing_refund_amount,
                    "_04_06_conditional_missing"
                ] = True

                reason = (
                    df.loc[
                        missing_refund_amount,
                        "_04_06_missing_reason"
                    ]
                    .astype("string")
                )

                df.loc[
                    missing_refund_amount,
                    "_04_06_missing_reason"
                ] = reason.where(
                    reason.eq(""),
                    reason + "; "
                ) + "REQ_NULL:refund_amount_for_applicable_return"

    # --------------------------------------------------------
    # Final row status
    # --------------------------------------------------------

    df["_04_06_status"] = "PASS"

    invalid_mask = (
        df["_04_06_required_missing"]
        | df["_04_06_conditional_missing"]
    )

    df.loc[invalid_mask, "_04_06_status"] = "INVALID"

    # --------------------------------------------------------
    # Do NOT impute anything.
    # Legitimate optional blanks remain blank.
    # --------------------------------------------------------

    output_name = (
        f"{input_file.stem}_04_06_missing_values_handled.csv"
    )

    output_file = OUTPUT_DIR / output_name

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    invalid_rows = int(invalid_mask.sum())

    if missing_required_columns:
        overall_status = "INVALID"
    elif invalid_rows > 0:
        overall_status = "INVALID"
    else:
        overall_status = "PASS"

    return {
        "file_name": input_file.name,
        "dataset": dataset,
        "status": overall_status,
        "rows_processed": len(df),
        "required_missing_rows": invalid_rows,
        "required_missing_values": required_missing_values,
        "optional_missing_values": optional_missing_values,
        "conditional_missing_values": conditional_missing_values,
        "missing_required_columns": ", ".join(missing_required_columns),
        "output_file": str(output_file),
        "error": "",
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TRACKER 04.06 - HANDLE MISSING VALUES")
    print("=" * 80)

    input_files = sorted(INPUT_DIR.glob("*.csv"))

    if not input_files:
        print("ERROR: No CSV files found in incoming folder.")
        return

    results = []

    for input_file in input_files:

        print("\n" + "-" * 80)
        print(f"Processing: {input_file.name}")

        result = process_file(input_file)

        results.append(result)

        print(f"Dataset                 : {result['dataset']}")
        print(f"Rows processed          : {result['rows_processed']}")
        print(
            f"Required missing values : "
            f"{result['required_missing_values']}"
        )
        print(
            f"Optional missing values : "
            f"{result['optional_missing_values']}"
        )
        print(
            f"Conditional missing     : "
            f"{result['conditional_missing_values']}"
        )
        print(f"Status                  : {result['status']}")

        if result.get("missing_required_columns"):
            print(
                "Missing required columns: "
                f"{result['missing_required_columns']}"
            )

        if result.get("error"):
            print(f"Error                   : {result['error']}")

        if result.get("output_file"):
            print(f"Output                  : {result['output_file']}")

    # --------------------------------------------------------
    # Audit summary
    # --------------------------------------------------------

    summary_file = (
        OUTPUT_DIR /
        "04_06_missing_value_handling_summary.csv"
    )

    summary_df = pd.DataFrame(results)

    summary_df.to_csv(
        summary_file,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Overall result
    # --------------------------------------------------------

    failed = summary_df[
        summary_df["status"].isin(["ERROR"])
    ]

    print("\n" + "=" * 80)
    print("04.06 OVERALL RESULT")
    print("=" * 80)

    if len(failed) > 0:
        print("STATUS : ERROR")
        print("One or more files could not be processed.")
    else:
        print("STATUS : PASS")
        print(
            "Missing-value rules were applied without "
            "inventing or imputing business values."
        )

    print("\nSummary output:")
    print(summary_file)

    print("\n" + "=" * 80)
    print("Tracker 04.06 missing value handling processing completed.")
    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
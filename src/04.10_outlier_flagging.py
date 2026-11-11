"""
Retail Sales Analytics
Tracker 04.10 - Flag Outliers for Investigation

Requirement:
Use domain thresholds/IQR or approved logic to flag unusual
records; do not blindly delete valid business extremes.

Important:
- Outliers are flagged, never deleted.
- Approved project fields are used only when available.
- Missing approved fields are reported as REVIEW.
- No source CSV is modified.
"""

from pathlib import Path
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# APPROVED NUMERIC FIELDS
# ============================================================

SALES_NUMERIC_FIELDS = [
    "quantity",
    "unit_selling_price",
    "discount_pct",
]

PRODUCT_NUMERIC_FIELDS = [
    "unit_cost",
    "list_price",
    "tax_rate_pct",
]

MIN_GROUP_SIZE = 10


# ============================================================
# LOAD CSV
# ============================================================

def load_csv(file_path):

    return pd.read_csv(
        file_path,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False
    )


# ============================================================
# FIND LATEST 04.08 OUTPUT
# ============================================================

def find_latest_file(dataset):

    candidates = []

    for file_path in PROCESSED_DIR.glob("*.csv"):

        name = file_path.name.lower()

        if dataset == "sales":

            if (
                "sales_2024_01" in name
                and "04_08_business_key_duplicates_handled" in name
            ):
                candidates.append(file_path)

        elif dataset == "products":

            if (
                "products_master" in name
                and "04_08_business_key_duplicates_handled" in name
            ):
                candidates.append(file_path)

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda p: p.stat().st_mtime
    )


# ============================================================
# IQR CALCULATION
# ============================================================

def calculate_iqr_bounds(series):

    numeric = pd.to_numeric(
        series,
        errors="coerce"
    ).dropna()

    count = len(numeric)

    if count < MIN_GROUP_SIZE:
        return None, None, count

    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)

    iqr = q3 - q1

    lower_bound = q1 - (1.5 * iqr)
    upper_bound = q3 + (1.5 * iqr)

    return lower_bound, upper_bound, count


# ============================================================
# FLAG ONE FIELD
# ============================================================

def flag_field(df, field, group_column=None):

    result = pd.DataFrame(index=df.index)

    result["source_row"] = df.index + 2
    result["field_name"] = field

    values = pd.to_numeric(
        df[field],
        errors="coerce"
    )

    result["value"] = values

    result["group_column"] = (
        group_column if group_column else ""
    )

    result["group_value"] = ""

    result["observation_count"] = 0
    result["lower_threshold"] = ""
    result["upper_threshold"] = ""

    result["outlier_flag"] = False
    result["flag_reason"] = ""

    # --------------------------------------------------------
    # GROUPED IQR
    # --------------------------------------------------------

    if group_column and group_column in df.columns:

        groups = (
            df[group_column]
            .astype(str)
            .str.strip()
            .replace("", "UNKNOWN")
        )

        result["group_value"] = groups

        for group_value in groups.unique():

            mask = groups == group_value

            lower, upper, count = calculate_iqr_bounds(
                values[mask]
            )

            result.loc[
                mask,
                "observation_count"
            ] = count

            if lower is None:

                result.loc[
                    mask,
                    "flag_reason"
                ] = (
                    "Insufficient observations for "
                    "stable IQR threshold"
                )

                continue

            result.loc[
                mask,
                "lower_threshold"
            ] = lower

            result.loc[
                mask,
                "upper_threshold"
            ] = upper

            outlier_mask = (
                mask
                & (
                    (values < lower)
                    | (values > upper)
                )
            )

            result.loc[
                outlier_mask,
                "outlier_flag"
            ] = True

            result.loc[
                outlier_mask,
                "flag_reason"
            ] = (
                "Value outside 1.5*IQR range "
                "within group; investigate"
            )

    # --------------------------------------------------------
    # OVERALL IQR
    # --------------------------------------------------------

    else:

        lower, upper, count = calculate_iqr_bounds(
            values
        )

        result["observation_count"] = count

        if lower is None:

            result["flag_reason"] = (
                "Insufficient observations for "
                "stable IQR threshold"
            )

        else:

            result["lower_threshold"] = lower
            result["upper_threshold"] = upper

            outlier_mask = (
                (values < lower)
                | (values > upper)
            )

            result.loc[
                outlier_mask,
                "outlier_flag"
            ] = True

            result.loc[
                outlier_mask,
                "flag_reason"
            ] = (
                "Value outside 1.5*IQR range; "
                "investigate"
            )

    return result


# ============================================================
# PROCESS SALES
# ============================================================

def process_sales(file_path):

    print()
    print("=" * 80)
    print("04.10 OUTLIER FLAGGING - SALES")
    print("=" * 80)

    print(f"Input file : {file_path}")

    df = load_csv(file_path)

    print(f"Rows read  : {len(df):,}")
    print(f"Columns    : {len(df.columns)}")

    available_fields = [
        field
        for field in SALES_NUMERIC_FIELDS
        if field in df.columns
    ]

    missing_fields = [
        field
        for field in SALES_NUMERIC_FIELDS
        if field not in df.columns
    ]

    print()
    print("Approved numeric fields available:")
    print(
        ", ".join(available_fields)
        if available_fields
        else "None"
    )

    if missing_fields:

        print()
        print("Approved numeric fields missing:")
        print(", ".join(missing_fields))

    all_flags = []

    for field in available_fields:

        group_column = (
            "category"
            if "category" in df.columns
            else None
        )

        flags = flag_field(
            df=df,
            field=field,
            group_column=group_column
        )

        all_flags.append(flags)

    if not all_flags:

        print("No approved numeric sales fields found.")

        return {
            "status": "REVIEW",
            "flags": 0,
            "fields": 0
        }

    flags_df = pd.concat(
        all_flags,
        ignore_index=True
    )

    output_file = (
        OUTPUT_DIR
        / "04_10_sales_outlier_flags.csv"
    )

    flags_df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    flagged_count = int(
        flags_df["outlier_flag"].sum()
    )

    print()
    print("SALES OUTLIER SUMMARY")
    print("-" * 80)

    print(
        f"Numeric fields investigated : "
        f"{flags_df['field_name'].nunique()}"
    )

    print(
        f"Field-level observations    : "
        f"{len(flags_df):,}"
    )

    print(
        f"Outlier flags generated     : "
        f"{flagged_count:,}"
    )

    print()
    print(f"Audit output : {output_file}")

    return {
        "status": "PASS",
        "flags": flagged_count,
        "fields": flags_df["field_name"].nunique()
    }


# ============================================================
# PROCESS PRODUCTS
# ============================================================

def process_products(file_path):

    print()
    print("=" * 80)
    print("04.10 OUTLIER FLAGGING - PRODUCTS")
    print("=" * 80)

    print(f"Input file : {file_path}")

    df = load_csv(file_path)

    print(f"Rows read  : {len(df):,}")
    print(f"Columns    : {len(df.columns)}")

    available_fields = [
        field
        for field in PRODUCT_NUMERIC_FIELDS
        if field in df.columns
    ]

    missing_fields = [
        field
        for field in PRODUCT_NUMERIC_FIELDS
        if field not in df.columns
    ]

    print()
    print("Approved product numeric fields available:")

    print(
        ", ".join(available_fields)
        if available_fields
        else "None"
    )

    print()
    print("Approved product numeric fields missing:")

    print(
        ", ".join(missing_fields)
        if missing_fields
        else "None"
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Do NOT substitute unit_price for list_price.
    # Do NOT invent unit_cost or tax_rate_pct.
    # --------------------------------------------------------

    if not available_fields:

        output_file = (
            OUTPUT_DIR
            / "04_10_products_outlier_flags.csv"
        )

        review_df = pd.DataFrame(
            [{
                "dataset": "products",
                "status": "REVIEW",
                "reason": (
                    "Approved numeric product fields are "
                    "not available in the current processed input."
                ),
                "missing_fields": ", ".join(
                    missing_fields
                ),
                "action": (
                    "No substitute fields used; "
                    "no product values modified."
                )
            }]
        )

        review_df.to_csv(
            output_file,
            index=False,
            encoding="utf-8-sig"
        )

        print()
        print("PRODUCT OUTLIER SUMMARY")
        print("-" * 80)
        print("Status                      : REVIEW")
        print(
            "Reason                      : Approved numeric "
            "product fields unavailable"
        )
        print(
            f"Audit output                : {output_file}"
        )

        return {
            "status": "REVIEW",
            "flags": 0,
            "fields": 0
        }

    all_flags = []

    for field in available_fields:

        group_column = (
            "category"
            if "category" in df.columns
            else None
        )

        flags = flag_field(
            df=df,
            field=field,
            group_column=group_column
        )

        all_flags.append(flags)

    flags_df = pd.concat(
        all_flags,
        ignore_index=True
    )

    output_file = (
        OUTPUT_DIR
        / "04_10_products_outlier_flags.csv"
    )

    flags_df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    flagged_count = int(
        flags_df["outlier_flag"].sum()
    )

    print()
    print("PRODUCT OUTLIER SUMMARY")
    print("-" * 80)

    print(
        f"Numeric fields investigated : "
        f"{flags_df['field_name'].nunique()}"
    )

    print(
        f"Field-level observations    : "
        f"{len(flags_df):,}"
    )

    print(
        f"Outlier flags generated     : "
        f"{flagged_count:,}"
    )

    print()
    print(f"Audit output : {output_file}")

    return {
        "status": "PASS",
        "flags": flagged_count,
        "fields": flags_df["field_name"].nunique()
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TRACKER 04.10 - FLAG OUTLIERS FOR INVESTIGATION")
    print("=" * 80)

    sales_file = find_latest_file("sales")
    products_file = find_latest_file("products")

    sales_result = {
        "status": "REVIEW",
        "flags": 0,
        "fields": 0
    }

    products_result = {
        "status": "REVIEW",
        "flags": 0,
        "fields": 0
    }

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    if sales_file:

        sales_result = process_sales(
            sales_file
        )

    else:

        print()
        print("Sales 04.08 processed file not found.")

    # --------------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------------

    if products_file:

        products_result = process_products(
            products_file
        )

    else:

        print()
        print("Products 04.08 processed file not found.")

    # --------------------------------------------------------
    # OVERALL RESULT
    # --------------------------------------------------------

    statuses = [
        sales_result["status"],
        products_result["status"]
    ]

    overall_status = (
        "PASS"
        if all(status == "PASS" for status in statuses)
        else "REVIEW"
    )

    print()
    print("=" * 80)
    print("04.10 OVERALL RESULT")
    print("=" * 80)

    print(
        f"Sales status    : {sales_result['status']}"
    )

    print(
        f"Products status : {products_result['status']}"
    )

    print(
        f"Overall status   : {overall_status}"
    )

    print()

    if overall_status == "PASS":

        print(
            "Outlier detection completed successfully."
        )

    else:

        print(
            "Outlier detection completed with REVIEW "
            "for unavailable approved numeric fields."
        )

    print(
        "Outliers were flagged for investigation "
        "and were NOT deleted."
    )

    print(
        "No source CSV files were modified."
    )

    print()
    print("=" * 80)

    if overall_status == "PASS":

        print(
            "Tracker 04.10 outlier flagging "
            "processing completed successfully."
        )

    else:

        print(
            "Tracker 04.10 processing completed "
            "with documented review status."
        )

    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
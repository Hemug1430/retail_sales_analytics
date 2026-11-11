"""
Retail Sales Analytics
Tracker 04.09 - Validate Foreign-Key Candidates

Requirement:
Check customer, product, store, salesperson, promotion,
transaction, and other references before core loading.

Rules are based on the approved Data Specification.

Important:
- Do not create missing master records.
- Optional NULL references remain valid.
- Required missing references are flagged.
- Conditional references are validated according to the
  project rules.
- targets.category is a logical category match, not a
  physical MySQL foreign key.
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
# FOREIGN-KEY DEFINITIONS
# ============================================================

FOREIGN_KEYS = {
    "sales": [
        {
            "child_column": "customer_id",
            "parent_dataset": "customers",
            "parent_column": "customer_id",
            "rule": "OPTIONAL",
        },
        {
            "child_column": "product_id",
            "parent_dataset": "products",
            "parent_column": "product_id",
            "rule": "REQUIRED",
        },
        {
            "child_column": "store_id",
            "parent_dataset": "stores",
            "parent_column": "store_id",
            "rule": "REQUIRED",
        },
        {
            "child_column": "salesperson_id",
            "parent_dataset": "salespersons",
            "parent_column": "salesperson_id",
            "rule": "CONDITIONAL",
        },
        {
            "child_column": "promotion_id",
            "parent_dataset": "promotions",
            "parent_column": "promotion_id",
            "rule": "OPTIONAL",
        },
    ],

    "salespersons": [
        {
            "child_column": "store_id",
            "parent_dataset": "stores",
            "parent_column": "store_id",
            "rule": "REQUIRED",
        },
    ],

    "returns": [
        {
            "child_column": "sales_line_id",
            "parent_dataset": "sales",
            "parent_column": "sales_line_id",
            "rule": "REQUIRED",
        },
        {
            "child_column": "processed_store_id",
            "parent_dataset": "stores",
            "parent_column": "store_id",
            "rule": "OPTIONAL",
        },
    ],

    "targets": [
        {
            "child_column": "store_id",
            "parent_dataset": "stores",
            "parent_column": "store_id",
            "rule": "REQUIRED",
        }
    ],
}


# ============================================================
# PRIMARY KEY DEFINITIONS
# ============================================================

PRIMARY_KEYS = {
    "customers": "customer_id",
    "products": "product_id",
    "stores": "store_id",
    "salespersons": "salesperson_id",
    "promotions": "promotion_id",
    "sales": "sales_line_id",
    "returns": "return_id",
    "targets": "target_id",
}


# ============================================================
# FIND LATEST 04.08 OUTPUT FOR EACH DATASET
# ============================================================

def find_latest_04_08_files():

    files = list(
        PROCESSED_DIR.glob("*04_08_business_key_duplicates_handled*.csv")
    )

    latest = {}

    for file_path in files:

        name = file_path.name.lower()

        for dataset in PRIMARY_KEYS:

            if dataset in name:

                if dataset not in latest:
                    latest[dataset] = file_path

                else:
                    current_time = latest[dataset].stat().st_mtime
                    new_time = file_path.stat().st_mtime

                    if new_time > current_time:
                        latest[dataset] = file_path

                break

    return latest


# ============================================================
# LOAD DATASET
# ============================================================

def load_dataset(file_path):

    return pd.read_csv(
        file_path,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False
    )


# ============================================================
# BUILD PARENT KEY SET
# ============================================================

def build_parent_key_set(
    dataset_name,
    parent_files,
    parent_column
):

    if dataset_name not in parent_files:
        return None

    parent_file = parent_files[dataset_name]

    try:
        df = load_dataset(parent_file)
    except Exception as exc:
        print(
            f"ERROR loading parent dataset "
            f"{dataset_name}: {exc}"
        )
        return None

    if parent_column not in df.columns:
        return None

    values = (
        df[parent_column]
        .astype(str)
        .str.strip()
    )

    values = values[values != ""]

    return set(values.tolist())


# ============================================================
# VALIDATE ONE FOREIGN KEY
# ============================================================

def validate_foreign_key(
    df,
    child_column,
    parent_dataset,
    parent_column,
    rule,
    parent_files
):

    result = {
        "child_column": child_column,
        "parent_dataset": parent_dataset,
        "parent_column": parent_column,
        "rule": rule,
        "status": "NOT_CHECKED",
        "rows_checked": len(df),
        "blank_values": 0,
        "valid_references": 0,
        "invalid_references": 0,
        "parent_dataset_available": False,
        "message": "",
    }

    # --------------------------------------------------------
    # Child column check
    # --------------------------------------------------------

    if child_column not in df.columns:

        result["status"] = "NOT_APPLICABLE"
        result["message"] = (
            f"Child column '{child_column}' is not present."
        )

        return result, None

    child_values = (
        df[child_column]
        .astype(str)
        .str.strip()
    )

    blank_mask = child_values.eq("")
    result["blank_values"] = int(blank_mask.sum())

    # --------------------------------------------------------
    # Build parent key set
    # --------------------------------------------------------

    parent_keys = build_parent_key_set(
        parent_dataset,
        parent_files,
        parent_column
    )

    # --------------------------------------------------------
    # Parent unavailable
    # --------------------------------------------------------

    if parent_keys is None:

        result["status"] = "REVIEW"
        result["message"] = (
            "Parent dataset/key is not available in the "
            "current processed inputs. Reference cannot "
            "be confirmed yet."
        )

        return result, None

    result["parent_dataset_available"] = True

    # --------------------------------------------------------
    # Optional blank values
    # --------------------------------------------------------

    non_blank_mask = ~blank_mask

    if rule == "OPTIONAL":

        result["valid_references"] = int(
            (
                non_blank_mask
                & child_values.isin(parent_keys)
            ).sum()
        )

        result["invalid_references"] = int(
            (
                non_blank_mask
                & ~child_values.isin(parent_keys)
            ).sum()
        )

        if result["invalid_references"] > 0:
            result["status"] = "INVALID"
            result["message"] = (
                "Non-blank optional references must resolve "
                "to an existing parent key."
            )
        else:
            result["status"] = "PASS"
            result["message"] = (
                "Optional blank references preserved; "
                "all populated references resolve."
            )

    # --------------------------------------------------------
    # Required references
    # --------------------------------------------------------

    elif rule == "REQUIRED":

        result["valid_references"] = int(
            (
                non_blank_mask
                & child_values.isin(parent_keys)
            ).sum()
        )

        result["invalid_references"] = int(
            (
                non_blank_mask
                & ~child_values.isin(parent_keys)
            ).sum()
        )

        if (
            result["blank_values"] > 0
            or result["invalid_references"] > 0
        ):
            result["status"] = "INVALID"
            result["message"] = (
                "Required reference contains blank or "
                "unresolved parent keys."
            )
        else:
            result["status"] = "PASS"
            result["message"] = (
                "All required references resolve "
                "to existing parent keys."
            )

    # --------------------------------------------------------
    # Conditional references
    # --------------------------------------------------------

    elif rule == "CONDITIONAL":

        result["valid_references"] = int(
            (
                non_blank_mask
                & child_values.isin(parent_keys)
            ).sum()
        )

        result["invalid_references"] = int(
            (
                non_blank_mask
                & ~child_values.isin(parent_keys)
            ).sum()
        )

        if result["invalid_references"] > 0:

            result["status"] = "INVALID"
            result["message"] = (
                "Populated conditional references contain "
                "unresolved parent keys."
            )

        else:

            result["status"] = "PASS"
            result["message"] = (
                "Conditional references are either blank "
                "where allowed or resolve to parent keys."
            )

    else:

        result["status"] = "REVIEW"
        result["message"] = (
            f"Unknown reference rule: {rule}"
        )

    # --------------------------------------------------------
    # Row-level flags
    # --------------------------------------------------------

    flags = pd.DataFrame({
        "source_row": df.index + 2,
        "child_column": child_column,
        "child_value": child_values,
        "parent_dataset": parent_dataset,
        "parent_column": parent_column,
        "rule": rule,
        "validation_status": "VALID"
    })

    if rule == "OPTIONAL":

        flags.loc[
            blank_mask,
            "validation_status"
        ] = "OPTIONAL_NULL"

        flags.loc[
            non_blank_mask
            & ~child_values.isin(parent_keys),
            "validation_status"
        ] = "INVALID_REFERENCE"

    elif rule == "REQUIRED":

        flags.loc[
            blank_mask,
            "validation_status"
        ] = "MISSING_REQUIRED_REFERENCE"

        flags.loc[
            non_blank_mask
            & ~child_values.isin(parent_keys),
            "validation_status"
        ] = "INVALID_REFERENCE"

    elif rule == "CONDITIONAL":

        flags.loc[
            blank_mask,
            "validation_status"
        ] = "CONDITIONAL_NULL"

        flags.loc[
            non_blank_mask
            & ~child_values.isin(parent_keys),
            "validation_status"
        ] = "INVALID_REFERENCE"

    return result, flags


# ============================================================
# PROCESS DATASET
# ============================================================

def process_dataset(
    dataset,
    input_file,
    parent_files
):

    print()
    print("=" * 80)
    print(f"04.09 FOREIGN-KEY VALIDATION - {dataset.upper()}")
    print("=" * 80)

    print(f"Input file : {input_file}")

    try:
        df = load_dataset(input_file)
    except Exception as exc:
        print(f"ERROR reading file: {exc}")
        return False

    print(f"Rows read  : {len(df):,}")
    print(f"Columns    : {len(df.columns)}")

    rules = FOREIGN_KEYS.get(dataset, [])

    if not rules:

        print()
        print(
            "No foreign-key relationships are defined "
            f"for dataset '{dataset}' in the approved specification."
        )

        return True

    all_results = []
    all_flags = []

    for rule in rules:

        result, flags = validate_foreign_key(
            df=df,
            child_column=rule["child_column"],
            parent_dataset=rule["parent_dataset"],
            parent_column=rule["parent_column"],
            rule=rule["rule"],
            parent_files=parent_files
        )

        all_results.append(result)

        if flags is not None:
            all_flags.append(flags)

        print()
        print(
            f"{rule['child_column']} -> "
            f"{rule['parent_dataset']}."
            f"{rule['parent_column']}"
        )
        print(f"Rule                 : {rule['rule']}")
        print(f"Status               : {result['status']}")
        print(f"Blank values         : {result['blank_values']:,}")
        print(
            f"Valid references     : "
            f"{result['valid_references']:,}"
        )
        print(
            f"Invalid references   : "
            f"{result['invalid_references']:,}"
        )
        print(f"Message              : {result['message']}")

    # --------------------------------------------------------
    # Audit output
    # --------------------------------------------------------

    audit_df = pd.DataFrame(all_results)

    audit_file = (
        OUTPUT_DIR
        / f"04_09_{dataset}_foreign_key_validation_audit.csv"
    )

    audit_df.to_csv(
        audit_file,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Row-level reference flags
    # --------------------------------------------------------

    if all_flags:

        flags_df = pd.concat(
            all_flags,
            ignore_index=True
        )

        flags_file = (
            OUTPUT_DIR
            / f"04_09_{dataset}_foreign_key_flags.csv"
        )

        flags_df.to_csv(
            flags_file,
            index=False,
            encoding="utf-8-sig"
        )

    # --------------------------------------------------------
    # Dataset status
    # --------------------------------------------------------

    statuses = audit_df["status"].tolist()

    if "INVALID" in statuses:
        dataset_status = "INVALID"

    elif "REVIEW" in statuses:
        dataset_status = "REVIEW"

    else:
        dataset_status = "PASS"

    print()
    print(f"DATASET RESULT : {dataset_status}")
    print(f"Audit output   : {audit_file}")

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TRACKER 04.09 - VALIDATE FOREIGN-KEY CANDIDATES")
    print("=" * 80)

    parent_files = find_latest_04_08_files()

    print()
    print(
        f"04.08 processed datasets available: "
        f"{len(parent_files)}"
    )

    for dataset, file_path in sorted(parent_files.items()):
        print(f"  {dataset:<15} -> {file_path.name}")

    if not parent_files:
        print()
        print(
            "ERROR: No 04.08 processed files were found."
        )
        return

    # --------------------------------------------------------
    # Only process datasets for which FK rules exist.
    # --------------------------------------------------------

    processed_count = 0

    for dataset, input_file in sorted(parent_files.items()):

        if dataset not in FOREIGN_KEYS:
            continue

        success = process_dataset(
            dataset=dataset,
            input_file=input_file,
            parent_files=parent_files
        )

        if success:
            processed_count += 1

    # --------------------------------------------------------
    # Overall result
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("04.09 OVERALL RESULT")
    print("=" * 80)

    print(
        f"Datasets with FK rules processed : "
        f"{processed_count}"
    )

    print()
    print(
        "Foreign-key candidate validation completed. "
        "No parent records are fabricated when a reference "
        "cannot be resolved."
    )

    print()
    print("=" * 80)
    print(
        "Tracker 04.09 foreign-key candidate validation "
        "processing completed."
    )
    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
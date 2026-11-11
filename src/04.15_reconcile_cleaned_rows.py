"""
Retail Sales Analytics
Tracker 04.15 - Reconcile Cleaned Rows to Source

Requirement:
    Confirm source rows equal accepted + corrected +
    duplicated + rejected/other documented outcomes
    before database loading.

Important:
    Reconciliation is performed at DATASET level so that
    processed/staging filenames do not have to exactly match
    the original incoming filename.

No source CSV files are modified.
"""

from pathlib import Path
from datetime import datetime
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INCOMING_DIR = PROJECT_ROOT / "incoming"

PROCESSED_DIR = (
    PROJECT_ROOT / "data" / "processed"
)

QUALITY_SUMMARY = (
    PROCESSED_DIR /
    "04_14_data_quality_summary.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR /
    "04_15_source_to_cleaned_reconciliation.csv"
)

AUDIT_FILE = (
    PROCESSED_DIR /
    "04_15_reconciliation_audit.csv"
)


# ============================================================
# DATASET IDENTIFICATION
# ============================================================

def dataset_name(filename):
    """
    Determine the business dataset from a filename.
    """

    name = str(filename).lower()

    if "customer" in name:
        return "customers"

    if "product" in name:
        return "products"

    if "store" in name:
        return "stores"

    if "salesperson" in name:
        return "salespersons"

    if "promotion" in name:
        return "promotions"

    if "return" in name:
        return "returns"

    if "target" in name:
        return "targets"

    if "sales" in name:
        return "sales"

    return "unknown"


# ============================================================
# NORMALIZE DATASET VALUE
# ============================================================

def normalize_dataset(value):
    """
    Normalize dataset names from different processing stages.
    """

    value = str(value).strip().lower()

    mapping = {
        "customer": "customers",
        "customers": "customers",

        "product": "products",
        "products": "products",

        "store": "stores",
        "stores": "stores",

        "salesperson": "salespersons",
        "salespersons": "salespersons",

        "promotion": "promotions",
        "promotions": "promotions",

        "return": "returns",
        "returns": "returns",

        "target": "targets",
        "targets": "targets",

        "sale": "sales",
        "sales": "sales",
    }

    return mapping.get(value, value)


# ============================================================
# READ SOURCE ROW COUNT
# ============================================================

def read_source_rows(source_file):

    df = pd.read_csv(
        source_file,
        low_memory=False
    )

    return len(df)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TRACKER 04.15 - RECONCILE CLEANED ROWS TO SOURCE")
    print("=" * 80)

    print(
        f"Source directory  : {INCOMING_DIR}"
    )

    print(
        f"Quality summary   : {QUALITY_SUMMARY}"
    )

    # --------------------------------------------------------
    # CHECK 04.14 OUTPUT
    # --------------------------------------------------------

    if not QUALITY_SUMMARY.exists():

        print("\nERROR:")
        print(
            "04.14 data-quality summary was not found."
        )

        print(
            "Run 04.14 before running 04.15."
        )

        return

    quality_df = pd.read_csv(
        QUALITY_SUMMARY,
        low_memory=False
    )

    print(
        f"\n04.14 summary rows : {len(quality_df):,}"
    )

    print(
        f"04.14 summary columns : {len(quality_df.columns)}"
    )

    # --------------------------------------------------------
    # CHECK REQUIRED COLUMNS
    # --------------------------------------------------------

    required_columns = [
        "dataset",
        "total_rows",
        "accepted_rows",
        "corrected_rows",
        "duplicated_rows",
        "rejected_rows",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in quality_df.columns
    ]

    if missing_columns:

        print("\nERROR:")
        print(
            "04.14 summary is missing required columns:"
        )

        for column in missing_columns:
            print(
                f"  - {column}"
            )

        return

    # --------------------------------------------------------
    # NORMALIZE DATASET NAMES
    # --------------------------------------------------------

    quality_df["dataset_normalized"] = (
        quality_df["dataset"]
        .apply(normalize_dataset)
    )

    # --------------------------------------------------------
    # SOURCE FILE DISCOVERY
    # --------------------------------------------------------

    if not INCOMING_DIR.exists():

        print("\nERROR:")
        print(
            f"Source directory does not exist: "
            f"{INCOMING_DIR}"
        )

        return

    source_files = sorted(
        INCOMING_DIR.glob("*.csv")
    )

    if not source_files:

        print("\nERROR:")
        print(
            "No source CSV files found in incoming/."
        )

        return

    print(
        f"\nSource files discovered : {len(source_files)}"
    )

    # --------------------------------------------------------
    # RECONCILIATION
    # --------------------------------------------------------

    reconciliation_rows = []

    print("\n" + "=" * 80)
    print("SOURCE-TO-CLEANED RECONCILIATION")
    print("=" * 80)

    for source_file in source_files:

        file_name = source_file.name

        dataset = dataset_name(
            file_name
        )

        print("\n" + "-" * 80)

        print(
            f"FILE    : {file_name}"
        )

        print(
            f"DATASET : {dataset}"
        )

        # ----------------------------------------------------
        # READ SOURCE ROWS
        # ----------------------------------------------------

        try:

            source_rows = read_source_rows(
                source_file
            )

        except Exception as exc:

            print(
                f"Source read error: {exc}"
            )

            reconciliation_rows.append(
                {
                    "source_file": file_name,
                    "dataset": dataset,
                    "source_rows": 0,
                    "accepted_rows": 0,
                    "corrected_rows": 0,
                    "duplicated_rows": 0,
                    "rejected_rows": 0,
                    "other_documented_rows": 0,
                    "classified_rows": 0,
                    "difference": 0,
                    "status": "REVIEW",
                    "reason": (
                        f"Source read error: {exc}"
                    ),
                }
            )

            continue

        # ----------------------------------------------------
        # MATCH BY DATASET
        # ----------------------------------------------------

        matching = quality_df[
            quality_df["dataset_normalized"]
            == normalize_dataset(dataset)
        ]

        if matching.empty:

            print(
                "No matching 04.14 dataset summary found."
            )

            reconciliation_rows.append(
                {
                    "source_file": file_name,
                    "dataset": dataset,
                    "source_rows": source_rows,
                    "accepted_rows": 0,
                    "corrected_rows": 0,
                    "duplicated_rows": 0,
                    "rejected_rows": 0,
                    "other_documented_rows": 0,
                    "classified_rows": 0,
                    "difference": source_rows,
                    "status": "REVIEW",
                    "reason": (
                        "No matching dataset in 04.14 summary."
                    ),
                }
            )

            continue

        # ----------------------------------------------------
        # ENSURE ONE DATASET SUMMARY
        # ----------------------------------------------------

        if len(matching) > 1:

            print(
                f"Multiple 04.14 summary rows found "
                f"for dataset: {dataset}"
            )

            # Aggregate multiple rows belonging to the
            # same dataset, if applicable.
            accepted_rows = int(
                matching["accepted_rows"].sum()
            )

            corrected_rows = int(
                matching["corrected_rows"].sum()
            )

            duplicated_rows = int(
                matching["duplicated_rows"].sum()
            )

            rejected_rows = int(
                matching["rejected_rows"].sum()
            )

        else:

            summary = matching.iloc[0]

            accepted_rows = int(
                summary["accepted_rows"]
            )

            corrected_rows = int(
                summary["corrected_rows"]
            )

            duplicated_rows = int(
                summary["duplicated_rows"]
            )

            rejected_rows = int(
                summary["rejected_rows"]
            )

        # ----------------------------------------------------
        # OTHER DOCUMENTED OUTCOMES
        # ----------------------------------------------------
        #
        # Missing, invalid and outlier counts are quality
        # attributes and must not automatically be added
        # again as separate row outcomes.
        #
        # Doing so would double-count rows already classified
        # as accepted/rejected.
        # ----------------------------------------------------

        other_documented_rows = 0

        # ----------------------------------------------------
        # CLASSIFIED ROWS
        # ----------------------------------------------------

        classified_rows = (
            accepted_rows
            + corrected_rows
            + duplicated_rows
            + rejected_rows
            + other_documented_rows
        )

        difference = (
            source_rows
            - classified_rows
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        if difference == 0:

            status = "PASS"

            reason = (
                "Source rows reconcile exactly with "
                "documented processing outcomes."
            )

        else:

            status = "REVIEW"

            reason = (
                "Source rows do not reconcile with "
                "documented processing outcomes."
            )

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        print(
            f"Source rows            : {source_rows:,}"
        )

        print(
            f"Accepted rows          : {accepted_rows:,}"
        )

        print(
            f"Corrected rows         : {corrected_rows:,}"
        )

        print(
            f"Duplicated rows        : {duplicated_rows:,}"
        )

        print(
            f"Rejected rows          : {rejected_rows:,}"
        )

        print(
            f"Other documented rows : "
            f"{other_documented_rows:,}"
        )

        print(
            f"Classified rows        : {classified_rows:,}"
        )

        print(
            f"Difference             : {difference:,}"
        )

        print(
            f"Status                 : {status}"
        )

        reconciliation_rows.append(
            {
                "source_file": file_name,
                "dataset": dataset,
                "source_rows": source_rows,
                "accepted_rows": accepted_rows,
                "corrected_rows": corrected_rows,
                "duplicated_rows": duplicated_rows,
                "rejected_rows": rejected_rows,
                "other_documented_rows":
                    other_documented_rows,
                "classified_rows": classified_rows,
                "difference": difference,
                "status": status,
                "reason": reason,
            }
        )

    # ========================================================
    # CREATE OUTPUT
    # ========================================================

    reconciliation_df = pd.DataFrame(
        reconciliation_rows
    )

    reconciliation_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # AUDIT OUTPUT
    # ========================================================

    audit_df = reconciliation_df.copy()

    audit_df[
        "reconciliation_timestamp"
    ] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    audit_df.to_csv(
        AUDIT_FILE,
        index=False
    )

    # ========================================================
    # OVERALL RESULT
    # ========================================================

    total_files = len(
        reconciliation_df
    )

    passed_files = int(
        (
            reconciliation_df["status"]
            == "PASS"
        ).sum()
    )

    review_files = (
        total_files
        - passed_files
    )

    total_source_rows = int(
        reconciliation_df[
            "source_rows"
        ].sum()
    )

    total_classified_rows = int(
        reconciliation_df[
            "classified_rows"
        ].sum()
    )

    total_difference = (
        total_source_rows
        - total_classified_rows
    )

    print("\n" + "=" * 80)
    print("04.15 OVERALL RESULT")
    print("=" * 80)

    print(
        f"Files reconciled       : {total_files}"
    )

    print(
        f"Files PASS             : {passed_files}"
    )

    print(
        f"Files requiring review : {review_files}"
    )

    print(
        f"Total source rows      : "
        f"{total_source_rows:,}"
    )

    print(
        f"Total classified rows  : "
        f"{total_classified_rows:,}"
    )

    print(
        f"Total difference       : "
        f"{total_difference:,}"
    )

    print(
        f"\nReconciliation output  : "
        f"{OUTPUT_FILE}"
    )

    print(
        f"Audit output           : "
        f"{AUDIT_FILE}"
    )

    # ========================================================
    # FINAL STATUS
    # ========================================================

    if (
        review_files == 0
        and total_difference == 0
    ):

        print("\nSTATUS : PASS")

        print(
            "Source rows reconcile exactly with "
            "documented processing outcomes."
        )

        print(
            "No source CSV files were modified."
        )

        print(
            "\nTracker 04.15 reconciliation "
            "processing completed."
        )

    else:

        print("\nSTATUS : REVIEW")

        print(
            "One or more datasets require "
            "reconciliation review."
        )

        print(
            "Do not proceed to database loading "
            "until the difference is explained."
        )

        print(
            "\nTracker 04.15 processing completed "
            "with review status."
        )

    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
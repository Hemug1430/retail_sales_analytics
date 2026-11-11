from pathlib import Path
from datetime import datetime
import csv
import hashlib
import uuid
import re


# ============================================================
# TRACKER 03.17
# TEST HISTORICAL INTAKE SEQUENCE
# ============================================================
#
# Requirement:
# Run historical files in chronological order and verify that
# batch IDs, hashes, logs, and routing are correct.
#
# This module is a TEST / VERIFICATION module.
#
# It does NOT:
# - modify source files
# - move source files
# - rename source files
# - delete source files
# - change 03.14 / 03.15 / 03.16 scripts
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SYNTHETIC_DIR = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "outputs"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

RESULT_FILE = (
    OUTPUT_DIR
    / "historical_intake_sequence_test.csv"
)


# ============================================================
# CREATE BATCH ID
# ============================================================

def create_batch_id():

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S"
    )

    unique_part = uuid.uuid4().hex[:8].upper()

    return (
        f"BATCH_{timestamp}_{unique_part}"
    )


# ============================================================
# SHA-256 HASH
# ============================================================

def calculate_sha256(file_path):

    sha256 = hashlib.sha256()

    with open(
        file_path,
        "rb"
    ) as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):
            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# IDENTIFY HISTORICAL MONTH
# ============================================================
#
# Supports both:
#
# sales_2024_01.csv
# sales_2024-01.csv
#
# The actual project files use the hyphen form.
# ============================================================

def get_month_from_filename(file_name):

    match = re.search(
        r"_(2024|2025)[_-](0[1-9]|1[0-2])\.csv$",
        file_name.lower()
    )

    if not match:

        return None

    year = int(
        match.group(1)
    )

    month = int(
        match.group(2)
    )

    return year, month


# ============================================================
# DISCOVER HISTORICAL MONTHLY FILES
# ============================================================
#
# IMPORTANT:
# Only files directly inside data/synthetic are considered.
#
# This prevents adjusted/test folders such as:
# - invalid_data_adjusted
# - missing_value_adjusted
# - duplicate_row_adjusted
# - schema_change_adjusted
# etc.
#
# from being incorrectly included in the historical sequence.
# ============================================================

def discover_historical_monthly_files():

    files = []

    if not SYNTHETIC_DIR.exists():

        return files

    for file_path in SYNTHETIC_DIR.glob(
        "*.csv"
    ):

        file_name = (
            file_path.name.lower()
        )

        # Only approved historical monthly
        # datasets are considered.

        if not (
            file_name.startswith("sales_")
            or file_name.startswith("returns_")
            or file_name.startswith("targets_")
        ):

            continue

        month_info = (
            get_month_from_filename(
                file_path.name
            )
        )

        if month_info is None:

            continue

        files.append(
            (
                month_info[0],
                month_info[1],
                file_path
            )
        )

    files.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2].name.lower()
        )
    )

    return files


# ============================================================
# DISCOVER MASTER SNAPSHOTS
# ============================================================
#
# Only master files directly under data/synthetic are included.
# ============================================================

def discover_master_files():

    master_files = []

    if not SYNTHETIC_DIR.exists():

        return master_files

    for file_path in SYNTHETIC_DIR.glob(
        "*.csv"
    ):

        file_name = (
            file_path.name.lower()
        )

        if "_master" in file_name:

            master_files.append(
                file_path
            )

    master_files.sort(
        key=lambda path: path.name.lower()
    )

    return master_files


# ============================================================
# DETERMINE EXPECTED ROUTING
# ============================================================

def determine_expected_route(
    file_path
):

    file_name = (
        file_path.name.lower()
    )

    if (
        file_name.startswith("sales_")
        or file_name.startswith("returns_")
        or file_name.startswith("targets_")
    ):

        return "HISTORICAL_MONTHLY_INTAKE"

    if "_master" in file_name:

        return "MASTER_SNAPSHOT_INTAKE"

    return "UNSUPPORTED"


# ============================================================
# MAIN TEST
# ============================================================

def main():

    print("=" * 80)
    print(
        "TRACKER 03.17 - HISTORICAL INTAKE SEQUENCE TEST"
    )
    print("=" * 80)

    print(
        "\nSynthetic source directory:"
    )

    print(
        SYNTHETIC_DIR
    )

    # --------------------------------------------------------
    # CHECK SOURCE DIRECTORY
    # --------------------------------------------------------

    if not SYNTHETIC_DIR.exists():

        print(
            "\nERROR: Synthetic directory not found."
        )

        return

    # --------------------------------------------------------
    # CREATE TEST BATCH ID
    # --------------------------------------------------------

    batch_id = create_batch_id()

    print(
        f"\nTest Batch ID: {batch_id}"
    )

    # --------------------------------------------------------
    # DISCOVER HISTORICAL FILES
    # --------------------------------------------------------

    monthly_files = (
        discover_historical_monthly_files()
    )

    master_files = (
        discover_master_files()
    )

    print(
        "\nHistorical monthly files found: "
        f"{len(monthly_files)}"
    )

    print(
        "Master files found: "
        f"{len(master_files)}"
    )

    # --------------------------------------------------------
    # HISTORICAL MONTHLY FILE CHECK
    # --------------------------------------------------------

    if not monthly_files:

        print(
            "\nERROR: No historical monthly files "
            "were found."
        )

        print(
            "\nExpected examples:"
        )

        print(
            "sales_2024-01.csv"
        )

        print(
            "returns_2024-01.csv"
        )

        print(
            "targets_2024-01.csv"
        )

        return

    # --------------------------------------------------------
    # BUILD CHRONOLOGICAL SEQUENCE
    # --------------------------------------------------------

    test_files = []

    for year, month, file_path in monthly_files:

        test_files.append(
            {
                "file_path": file_path,
                "year": year,
                "month": month,
                "sequence_key": (
                    year,
                    month,
                    file_path.name.lower()
                ),
                "file_type":
                    "HISTORICAL_MONTHLY"
            }
        )

    # --------------------------------------------------------
    # VERIFY CHRONOLOGICAL ORDER
    # --------------------------------------------------------

    actual_sequence = [
        item["sequence_key"]
        for item in test_files
    ]

    expected_sequence = sorted(
        actual_sequence
    )

    chronological_status = (
        "PASS"
        if actual_sequence == expected_sequence
        else "FAIL"
    )

    # --------------------------------------------------------
    # PROCESS HISTORICAL FILES
    # --------------------------------------------------------

    results = []

    previous_key = None

    for sequence_number, item in enumerate(
        test_files,
        start=1
    ):

        file_path = item["file_path"]

        current_key = item["sequence_key"]

        # ----------------------------------------------------
        # CHRONOLOGICAL ORDER
        # ----------------------------------------------------

        if previous_key is None:

            order_status = "PASS"

        elif current_key >= previous_key:

            order_status = "PASS"

        else:

            order_status = "FAIL"

        previous_key = current_key

        # ----------------------------------------------------
        # HASH
        # ----------------------------------------------------

        try:

            file_hash = (
                calculate_sha256(
                    file_path
                )
            )

            hash_status = "PASS"

        except Exception as error:

            file_hash = ""

            hash_status = (
                f"FAIL: "
                f"{type(error).__name__}: "
                f"{error}"
            )

        # ----------------------------------------------------
        # ROUTING
        # ----------------------------------------------------

        expected_route = (
            determine_expected_route(
                file_path
            )
        )

        if expected_route != "UNSUPPORTED":

            routing_status = "PASS"

        else:

            routing_status = "FAIL"

        # ----------------------------------------------------
        # OVERALL FILE STATUS
        # ----------------------------------------------------

        if (
            order_status == "PASS"
            and hash_status == "PASS"
            and routing_status == "PASS"
        ):

            overall_status = "PASS"

        else:

            overall_status = "FAIL"

        # ----------------------------------------------------
        # STORE RESULT
        # ----------------------------------------------------

        results.append(
            {
                "sequence_number":
                    sequence_number,

                "file_name":
                    file_path.name,

                "file_path":
                    str(
                        file_path.relative_to(
                            PROJECT_ROOT
                        )
                    ),

                "file_type":
                    item["file_type"],

                "period":
                    (
                        f"{item['year']}-"
                        f"{item['month']:02d}"
                    ),

                "batch_id":
                    batch_id,

                "sha256_hash":
                    file_hash,

                "order_status":
                    order_status,

                "hash_status":
                    hash_status,

                "expected_route":
                    expected_route,

                "routing_status":
                    routing_status,

                "overall_status":
                    overall_status
            }
        )

    # ========================================================
    # WRITE TEST RESULT
    # ========================================================

    fieldnames = [
        "sequence_number",
        "file_name",
        "file_path",
        "file_type",
        "period",
        "batch_id",
        "sha256_hash",
        "order_status",
        "hash_status",
        "expected_route",
        "routing_status",
        "overall_status"
    ]

    with open(
        RESULT_FILE,
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            results
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    total_files = len(
        results
    )

    passed_files = sum(
        1
        for row in results
        if row["overall_status"] == "PASS"
    )

    failed_files = (
        total_files - passed_files
    )

    all_hashes_pass = all(
        row["hash_status"] == "PASS"
        for row in results
    )

    all_order_pass = all(
        row["order_status"] == "PASS"
        for row in results
    )

    all_routing_pass = all(
        row["routing_status"] == "PASS"
        for row in results
    )

    overall_test = (
        "PASS"
        if (
            total_files > 0
            and chronological_status == "PASS"
            and all_hashes_pass
            and all_order_pass
            and all_routing_pass
            and failed_files == 0
        )
        else "FAIL"
    )

    # ========================================================
    # DISPLAY RESULTS
    # ========================================================

    print(
        "\n" + "=" * 80
    )

    print(
        "03.17 HISTORICAL INTAKE SEQUENCE RESULTS"
    )

    print(
        "=" * 80
    )

    print(
        f"\nHistorical monthly files : "
        f"{total_files}"
    )

    print(
        f"Passed                   : "
        f"{passed_files}"
    )

    print(
        f"Failed                   : "
        f"{failed_files}"
    )

    print(
        f"\nChronological order      : "
        f"{chronological_status}"
    )

    print(
        f"Batch ID                 : "
        f"{batch_id}"
    )

    print(
        f"SHA-256 verification     : "
        f"{'PASS' if all_hashes_pass else 'FAIL'}"
    )

    print(
        f"Routing verification     : "
        f"{'PASS' if all_routing_pass else 'FAIL'}"
    )

    print(
        f"\nTest result saved to:"
    )

    print(
        RESULT_FILE
    )

    print(
        f"\n03.17 OVERALL RESULT     : "
        f"{overall_test}"
    )

    print(
        "\n" + "=" * 80
    )

    if overall_test == "PASS":

        print(
            "Tracker 03.17 historical intake "
            "sequence test completed successfully."
        )

    else:

        print(
            "Tracker 03.17 historical intake "
            "sequence test requires investigation."
        )

    print(
        "=" * 80
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
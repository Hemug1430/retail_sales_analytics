from pathlib import Path
import csv
import shutil
from datetime import datetime


# ============================================================
# TRACKER 03.15
# QUARANTINE INVALID FILES
# ============================================================
#
# Requirement:
# Move completely invalid or unsupported files to a rejected /
# quarantine location without loading them into business tables.
#
# This module handles FILE-LEVEL quarantine only.
# Row-level rejects are NOT moved to quarantine here.
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_DIR = Path("incoming")
QUARANTINE_DIR = Path("data/quarantine")
OUTPUT_DIR = Path("data/outputs")

QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

QUARANTINE_LOG = OUTPUT_DIR / "quarantine_log.csv"


# ============================================================
# FATAL FILE-LEVEL CONDITIONS
# ============================================================

FATAL_STATUSES = {
    "FAIL"
}


# ============================================================
# READ FILE-LEVEL VALIDATION RESULTS
# ============================================================

def read_file_level_results():

    result_file = (
        OUTPUT_DIR /
        "file_level_validation_results.csv"
    )

    results = {}

    if not result_file.exists():

        print(
            f"WARNING: File-level validation result not found: "
            f"{result_file}"
        )

        return results

    try:

        with open(
            result_file,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                file_name = row.get(
                    "file_name",
                    ""
                )

                if file_name:

                    results[file_name] = row

    except Exception as error:

        print(
            f"ERROR reading file-level validation results: "
            f"{error}"
        )

    return results


# ============================================================
# DETERMINE QUARANTINE REASON
# ============================================================

def determine_quarantine_reason(validation):

    if not validation:

        return None

    # --------------------------------------------------------
    # Structural/schema failures are fatal.
    # --------------------------------------------------------

    schema_result = validation.get(
        "schema_result",
        ""
    )

    column_result = validation.get(
        "column_result",
        ""
    )

    row_readability_result = validation.get(
        "row_readability_result",
        ""
    )

    quality_result = validation.get(
        "quality_result",
        ""
    )

    # Schema failure
    if schema_result == "FAIL":

        return "FATAL_SCHEMA_FAILURE"

    # Column/header failure
    if column_result == "FAIL":

        return "FATAL_COLUMN_FAILURE"

    # Unreadable file
    if row_readability_result == "FAIL":

        return "FATAL_UNREADABLE_FILE"

    # File quality failure
    if quality_result == "FAIL":

        return "FATAL_FILE_QUALITY_FAILURE"

    return None


# ============================================================
# MOVE FILE TO QUARANTINE
# ============================================================

def quarantine_file(
    file_path,
    reason
):

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    destination_name = (
        f"{timestamp}__{file_path.name}"
    )

    destination = (
        QUARANTINE_DIR /
        destination_name
    )

    try:

        shutil.move(
            str(file_path),
            str(destination)
        )

        return destination, ""

    except Exception as error:

        return None, str(error)


# ============================================================
# WRITE QUARANTINE LOG
# ============================================================

def write_quarantine_log(records):

    fieldnames = [
        "file_name",
        "quarantine_path",
        "quarantine_reason",
        "quarantine_time",
        "status",
        "error_details"
    ]

    file_exists = QUARANTINE_LOG.exists()

    with open(
        QUARANTINE_LOG,
        "a",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        if not file_exists:

            writer.writeheader()

        writer.writerows(records)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TRACKER 03.15 - QUARANTINE INVALID FILES")
    print("=" * 80)

    if not INPUT_DIR.exists():

        print(
            f"ERROR: Incoming folder not found: "
            f"{INPUT_DIR}"
        )

        return

    # --------------------------------------------------------
    # Read existing file-level validation results.
    # --------------------------------------------------------

    validation_results = (
        read_file_level_results()
    )

    if not validation_results:

        print(
            "WARNING: No file-level validation results "
            "available."
        )

        return

    csv_files = sorted(
        INPUT_DIR.glob("*.csv")
    )

    if not csv_files:

        print(
            f"No CSV files currently in: "
            f"{INPUT_DIR}"
        )

        print(
            "No files require quarantine."
        )

        return

    quarantine_records = []

    for file_path in csv_files:

        file_name = file_path.name

        validation = validation_results.get(
            file_name
        )

        reason = determine_quarantine_reason(
            validation
        )

        # ----------------------------------------------------
        # File does not have a fatal file-level condition.
        # ----------------------------------------------------

        if reason is None:

            print(
                f"\nKEEP: {file_name}"
            )

            print(
                "Reason: No fatal file-level condition "
                "requires quarantine."
            )

            continue

        # ----------------------------------------------------
        # Quarantine fatal file.
        # ----------------------------------------------------

        print(
            f"\nQUARANTINE: {file_name}"
        )

        print(
            f"Reason: {reason}"
        )

        destination, error = quarantine_file(
            file_path,
            reason
        )

        if destination:

            status = "QUARANTINED"

            print(
                f"Moved to: {destination}"
            )

        else:

            status = "QUARANTINE_FAILED"

            print(
                f"ERROR moving file: {error}"
            )

        quarantine_records.append({
            "file_name": file_name,
            "quarantine_path": (
                str(destination)
                if destination
                else ""
            ),
            "quarantine_reason": reason,
            "quarantine_time": datetime.now().isoformat(
                timespec="seconds"
            ),
            "status": status,
            "error_details": error
        })

    # --------------------------------------------------------
    # Write audit record.
    # --------------------------------------------------------

    if quarantine_records:

        write_quarantine_log(
            quarantine_records
        )

    print("\n" + "=" * 80)
    print("QUARANTINE SUMMARY")
    print("=" * 80)

    quarantined_count = sum(
        1
        for record in quarantine_records
        if record["status"] == "QUARANTINED"
    )

    failed_count = sum(
        1
        for record in quarantine_records
        if record["status"] == "QUARANTINE_FAILED"
    )

    print(
        f"Files quarantined : {quarantined_count}"
    )

    print(
        f"Quarantine errors : {failed_count}"
    )

    print(
        f"\nQuarantine folder:"
        f"\n{QUARANTINE_DIR}"
    )

    print(
        f"\nQuarantine log:"
        f"\n{QUARANTINE_LOG}"
    )

    print("\n" + "=" * 80)
    print(
        "Tracker 03.15 quarantine process completed."
    )
    print("=" * 80)


if __name__ == "__main__":

    main()
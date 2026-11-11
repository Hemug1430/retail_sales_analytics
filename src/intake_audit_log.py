from pathlib import Path
from datetime import datetime
import csv
import hashlib
import uuid


# ============================================================
# TRACKER 03.14
# WRITE INTAKE AUDIT LOG
# ============================================================
#
# Requirement:
# Record file name, hash, batch, rows read, processing
# start/end, validation status, and error details.
#
# This module records audit information only.
# It does NOT modify the incoming source files.
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_DIR = Path("incoming")
OUTPUT_DIR = Path("data/outputs")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_LOG_FILE = OUTPUT_DIR / "intake_audit_log.csv"


# ============================================================
# SHA-256 HASH
# ============================================================

def calculate_sha256(file_path):

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):
            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# BATCH ID
# ============================================================

def create_batch_id():

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S"
    )

    unique_part = uuid.uuid4().hex[:8].upper()

    return f"BATCH_{timestamp}_{unique_part}"


# ============================================================
# COUNT READABLE DATA ROWS
# ============================================================

def count_rows(file_path):

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.reader(file)

        # Header
        next(reader, None)

        row_count = 0

        for row in reader:

            # Skip completely empty physical rows
            if not row or all(
                str(value).strip() == ""
                for value in row
            ):
                continue

            row_count += 1

    return row_count


# ============================================================
# GET VALIDATION STATUS
# ============================================================

def get_validation_status(
    file_name,
    row_validation_results
):

    statuses = []

    # --------------------------------------------------------
    # File-level validation result
    # --------------------------------------------------------

    file_level_file = (
        OUTPUT_DIR /
        "file_level_validation_results.csv"
    )

    if file_level_file.exists():

        try:

            with open(
                file_level_file,
                "r",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                reader = csv.DictReader(file)

                for row in reader:

                    if row.get("file_name") == file_name:

                        status = row.get(
                            "overall_result",
                            ""
                        )

                        if status:
                            statuses.append(status)

        except Exception:
            pass

    # --------------------------------------------------------
    # Row-level validation
    # --------------------------------------------------------

    if row_validation_results:

        statuses.extend(row_validation_results)

    # --------------------------------------------------------
    # Determine final validation status
    # --------------------------------------------------------

    if "FAIL" in statuses:

        return "FAIL"

    if "WARNING" in statuses:

        return "WARNING"

    if statuses:

        return "PASS"

    return "WARNING"


# ============================================================
# PROCESS ONE FILE
# ============================================================

def process_file(
    file_path,
    batch_id
):

    start_time = datetime.now()

    file_name = file_path.name

    file_hash = ""
    rows_read = 0
    validation_status = "WARNING"
    error_details = ""

    row_validation_results = []

    try:

        # ----------------------------------------------------
        # HASH
        # ----------------------------------------------------

        file_hash = calculate_sha256(
            file_path
        )

        # ----------------------------------------------------
        # ROW COUNT
        # ----------------------------------------------------

        rows_read = count_rows(
            file_path
        )

        # ----------------------------------------------------
        # READ ROW-LEVEL VALIDATION RESULTS
        # ----------------------------------------------------

        row_level_file = (
            OUTPUT_DIR /
            "row_level_validation_flags.csv"
        )

        if row_level_file.exists():

            with open(
                row_level_file,
                "r",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                reader = csv.DictReader(file)

                for row in reader:

                    if row.get("source_file") == file_name:

                        row_validation_results.append(
                            row.get(
                                "validation_status",
                                ""
                            )
                        )

        # ----------------------------------------------------
        # VALIDATION STATUS
        # ----------------------------------------------------

        validation_status = get_validation_status(
            file_name,
            row_validation_results
        )

    except Exception as error:

        validation_status = "FAIL"

        error_details = (
            f"{type(error).__name__}: {error}"
        )

    end_time = datetime.now()

    duration_seconds = round(
        (end_time - start_time).total_seconds(),
        3
    )

    # --------------------------------------------------------
    # AUDIT RECORD
    # --------------------------------------------------------

    return {
        "file_name": file_name,
        "sha256_hash": file_hash,
        "batch_id": batch_id,
        "rows_read": rows_read,
        "processing_start": start_time.isoformat(
            timespec="seconds"
        ),
        "processing_end": end_time.isoformat(
            timespec="seconds"
        ),
        "duration_seconds": duration_seconds,
        "validation_status": validation_status,
        "error_details": error_details
    }


# ============================================================
# WRITE AUDIT LOG
# ============================================================

def write_audit_log(records):

    fieldnames = [
        "file_name",
        "sha256_hash",
        "batch_id",
        "rows_read",
        "processing_start",
        "processing_end",
        "duration_seconds",
        "validation_status",
        "error_details"
    ]

    file_exists = AUDIT_LOG_FILE.exists()

    with open(
        AUDIT_LOG_FILE,
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
    print("TRACKER 03.14 - INTAKE AUDIT LOG")
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

    # One batch ID for this intake run.
    batch_id = create_batch_id()

    print(f"\nBatch ID: {batch_id}")
    print(
        f"Found {len(csv_files)} CSV file(s) "
        f"in: {INPUT_DIR}"
    )

    audit_records = []

    for file_path in csv_files:

        print(
            f"\nProcessing audit record: "
            f"{file_path.name}"
        )

        record = process_file(
            file_path,
            batch_id
        )

        audit_records.append(record)

        print(
            f"Rows read          : "
            f"{record['rows_read']}"
        )

        print(
            f"Validation status  : "
            f"{record['validation_status']}"
        )

        if record["error_details"]:

            print(
                f"Error details      : "
                f"{record['error_details']}"
            )

    write_audit_log(
        audit_records
    )

    print("\n" + "=" * 80)
    print("INTAKE AUDIT LOG SUMMARY")
    print("=" * 80)

    for record in audit_records:

        print(
            f"{record['file_name']} | "
            f"Rows: {record['rows_read']} | "
            f"Status: {record['validation_status']}"
        )

    print("\nAudit log saved to:")

    print(AUDIT_LOG_FILE)

    print("\n" + "=" * 80)
    print(
        "Tracker 03.14 intake audit log completed."
    )
    print("=" * 80)


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
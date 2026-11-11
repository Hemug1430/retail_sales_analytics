from pathlib import Path
from datetime import datetime
import csv
import shutil
import hashlib


# ============================================================
# TRACKER 03.16
# ARCHIVE SUCCESSFULLY RECEIVED FILES
# ============================================================
#
# Requirement:
# Move successfully processed source files to the archive
# structure while preserving the original file unchanged.
#
# Archive structure:
# data/archive/YYYY/MM
#
# Only successfully processed files are archived.
# Failed files remain in incoming/.
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_DIR = Path("incoming")

ARCHIVE_ROOT = Path("data/archive")

OUTPUT_DIR = Path("data/outputs")

AUDIT_LOG_FILE = OUTPUT_DIR / "intake_audit_log.csv"

ARCHIVE_LOG_FILE = OUTPUT_DIR / "archive_log.csv"


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

ARCHIVE_ROOT.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# CALCULATE SHA-256
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
# READ INTAKE AUDIT LOG
# ============================================================

def read_audit_log():

    if not AUDIT_LOG_FILE.exists():

        print(
            f"ERROR: Intake audit log not found:\n"
            f"{AUDIT_LOG_FILE}"
        )

        return []

    records = []

    with open(
        AUDIT_LOG_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            records.append(row)

    return records


# ============================================================
# GET ACTUAL ARCHIVE DIRECTORY
# ============================================================

def get_archive_directory():

    now = datetime.now()

    year = f"{now.year:04d}"

    month = f"{now.month:02d}"

    archive_directory = (
        ARCHIVE_ROOT /
        year /
        month
    )

    archive_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    return archive_directory


# ============================================================
# CHECK SUCCESS STATUS
# ============================================================

def is_successful(record):

    status = (
        record.get(
            "validation_status",
            ""
        )
        .strip()
        .upper()
    )

    return status == "PASS"


# ============================================================
# WRITE ARCHIVE LOG
# ============================================================

def write_archive_log(records):

    fieldnames = [
        "file_name",
        "sha256_hash",
        "batch_id",
        "validation_status",
        "archive_path",
        "archive_time",
        "outcome",
        "error_details"
    ]

    with open(
        ARCHIVE_LOG_FILE,
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(records)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TRACKER 03.16 - ARCHIVE SUCCESSFULLY RECEIVED FILES")
    print("=" * 80)

    # --------------------------------------------------------
    # Check incoming folder
    # --------------------------------------------------------

    if not INPUT_DIR.exists():

        print(
            f"ERROR: Incoming folder not found:\n"
            f"{INPUT_DIR}"
        )

        return

    # --------------------------------------------------------
    # Read audit log
    # --------------------------------------------------------

    audit_records = read_audit_log()

    if not audit_records:

        print(
            "ERROR: No records found in intake audit log."
        )

        return

    # --------------------------------------------------------
    # Get actual archive directory
    # --------------------------------------------------------

    archive_directory = (
        get_archive_directory()
    )

    print(
        f"\nArchive directory:"
        f"\n{archive_directory}"
    )

    archive_records = []

    archived_count = 0
    retained_count = 0
    error_count = 0

    # --------------------------------------------------------
    # Process every audit record
    # --------------------------------------------------------

    for record in audit_records:

        file_name = (
            record.get(
                "file_name",
                ""
            )
            .strip()
        )

        validation_status = (
            record.get(
                "validation_status",
                ""
            )
            .strip()
            .upper()
        )

        if not file_name:

            continue

        source_file = (
            INPUT_DIR /
            file_name
        )

        print("\n" + "-" * 60)

        print(
            f"File: {file_name}"
        )

        print(
            f"Validation status: "
            f"{validation_status}"
        )

        # ----------------------------------------------------
        # Only PASS files are eligible for archive.
        # ----------------------------------------------------

        if not is_successful(record):

            print(
                "ACTION: KEEP IN INCOMING"
            )

            retained_count += 1

            archive_records.append({
                "file_name": file_name,
                "sha256_hash": record.get(
                    "sha256_hash",
                    ""
                ),
                "batch_id": record.get(
                    "batch_id",
                    ""
                ),
                "validation_status":
                    validation_status,
                "archive_path": "",
                "archive_time": "",
                "outcome": "NOT_ARCHIVED",
                "error_details":
                    "File validation status is not PASS"
            })

            continue

        # ----------------------------------------------------
        # PASS file must exist in incoming.
        # ----------------------------------------------------

        if not source_file.exists():

            print(
                "ERROR: PASS file not found in incoming."
            )

            error_count += 1

            archive_records.append({
                "file_name": file_name,
                "sha256_hash": record.get(
                    "sha256_hash",
                    ""
                ),
                "batch_id": record.get(
                    "batch_id",
                    ""
                ),
                "validation_status":
                    validation_status,
                "archive_path": "",
                "archive_time":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                "outcome":
                    "ARCHIVE_FAILED",
                "error_details":
                    "PASS file not found in incoming"
            })

            continue

        # ----------------------------------------------------
        # Destination
        # ----------------------------------------------------

        destination = (
            archive_directory /
            file_name
        )

        # ----------------------------------------------------
        # Prevent accidental overwrite.
        # ----------------------------------------------------

        if destination.exists():

            print(
                "ERROR: Archive destination already exists."
            )

            error_count += 1

            archive_records.append({
                "file_name": file_name,
                "sha256_hash": record.get(
                    "sha256_hash",
                    ""
                ),
                "batch_id": record.get(
                    "batch_id",
                    ""
                ),
                "validation_status":
                    validation_status,
                "archive_path":
                    str(destination),
                "archive_time":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                "outcome":
                    "ARCHIVE_FAILED",
                "error_details":
                    "Archive destination already exists"
            })

            continue

        # ----------------------------------------------------
        # Capture original hash before moving.
        # ----------------------------------------------------

        original_hash = calculate_sha256(
            source_file
        )

        expected_hash = (
            record.get(
                "sha256_hash",
                ""
            )
            .strip()
        )

        # ----------------------------------------------------
        # If audit hash exists, verify source file.
        # ----------------------------------------------------

        if expected_hash:

            if original_hash.lower() != expected_hash.lower():

                print(
                    "ERROR: Source file hash does not "
                    "match intake audit hash."
                )

                error_count += 1

                archive_records.append({
                    "file_name": file_name,
                    "sha256_hash": original_hash,
                    "batch_id": record.get(
                        "batch_id",
                        ""
                    ),
                    "validation_status":
                        validation_status,
                    "archive_path": "",
                    "archive_time":
                        datetime.now().isoformat(
                            timespec="seconds"
                        ),
                    "outcome":
                        "ARCHIVE_FAILED",
                    "error_details":
                        "Source hash mismatch"
                })

                continue

        # ----------------------------------------------------
        # Move file to archive.
        # ----------------------------------------------------

        try:

            shutil.move(
                str(source_file),
                str(destination)
            )

            # ------------------------------------------------
            # Verify archived file hash.
            # ------------------------------------------------

            archived_hash = calculate_sha256(
                destination
            )

            if archived_hash.lower() != original_hash.lower():

                print(
                    "ERROR: Archived file hash does "
                    "not match original hash."
                )

                error_count += 1

                archive_records.append({
                    "file_name": file_name,
                    "sha256_hash":
                        original_hash,
                    "batch_id": record.get(
                        "batch_id",
                        ""
                    ),
                    "validation_status":
                        validation_status,
                    "archive_path":
                        str(destination),
                    "archive_time":
                        datetime.now().isoformat(
                            timespec="seconds"
                        ),
                    "outcome":
                        "ARCHIVE_FAILED",
                    "error_details":
                        "Archived hash mismatch"
                })

                continue

            # ------------------------------------------------
            # Successful archive.
            # ------------------------------------------------

            print(
                "ACTION: ARCHIVED"
            )

            print(
                f"Archive path:"
                f"\n{destination}"
            )

            print(
                "Hash verification: PASS"
            )

            archive_records.append({
                "file_name": file_name,
                "sha256_hash":
                    original_hash,
                "batch_id": record.get(
                    "batch_id",
                    ""
                ),
                "validation_status":
                    validation_status,
                "archive_path":
                    str(destination),
                "archive_time":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                "outcome":
                    "ARCHIVED",
                "error_details": ""
            })

            archived_count += 1

        except Exception as error:

            print(
                f"ERROR archiving file: {error}"
            )

            error_count += 1

            archive_records.append({
                "file_name": file_name,
                "sha256_hash":
                    original_hash,
                "batch_id": record.get(
                    "batch_id",
                    ""
                ),
                "validation_status":
                    validation_status,
                "archive_path": "",
                "archive_time":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                "outcome":
                    "ARCHIVE_FAILED",
                "error_details":
                    str(error)
            })

    # --------------------------------------------------------
    # Save archive log.
    # --------------------------------------------------------

    write_archive_log(
        archive_records
    )

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("ARCHIVE SUMMARY")
    print("=" * 80)

    print(
        f"Files archived : {archived_count}"
    )

    print(
        f"Files retained : {retained_count}"
    )

    print(
        f"Archive errors : {error_count}"
    )

    print(
        f"\nArchive root:"
        f"\n{ARCHIVE_ROOT}"
    )

    print(
        f"\nArchive log:"
        f"\n{ARCHIVE_LOG_FILE}"
    )

    # --------------------------------------------------------
    # Tracker status
    # --------------------------------------------------------

    if error_count == 0:

        print("\n" + "=" * 80)

        print(
            "Tracker 03.16 archive process completed."
        )

        print("=" * 80)

    else:

        print("\n" + "=" * 80)

        print(
            "Tracker 03.16 completed with archive errors."
        )

        print("=" * 80)


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
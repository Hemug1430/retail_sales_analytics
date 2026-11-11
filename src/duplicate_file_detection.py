"""
Tracker 03.04 - Duplicate File Detection

Requirement:
Compare file hash and identity against prior loads;
do not reprocess an exact duplicate file.

Frozen ETL behavior:
- Same name + same hash + previous SUCCESS/SUCCESS_WITH_REJECTS
  -> SKIPPED_DUPLICATE
- Same name + different hash
  -> CORRECTION_CANDIDATE
- Otherwise
  -> ACCEPT_FOR_PROCESSING
"""

from pathlib import Path
import csv
import hashlib
import logging


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_DIR = Path("incoming")
AUDIT_DIR = Path("logs")
AUDIT_LOG_FILE = AUDIT_DIR / "file_audit_log.csv"

CHUNK_SIZE = 1024 * 1024  # 1 MB

SUCCESS_STATUSES = {
    "SUCCESS",
    "SUCCESS_WITH_REJECTS",
}


# ============================================================
# LOGGING
# ============================================================

AUDIT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("duplicate_file_detection")


# ============================================================
# SHA-256
# ============================================================

def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA-256 hash for the incoming file."""

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# LOAD PREVIOUS FILE AUDIT RECORDS
# ============================================================

def load_previous_audit_records() -> list[dict]:
    """Load previous file-processing records from the audit log."""

    if not AUDIT_LOG_FILE.exists():
        logger.info(
            "Audit log not found: %s",
            AUDIT_LOG_FILE
        )
        return []

    with AUDIT_LOG_FILE.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        return list(csv.DictReader(file))


# ============================================================
# DUPLICATE / CORRECTION CLASSIFICATION
# ============================================================

def classify_file(
    file_path: Path,
    file_hash: str,
    previous_records: list[dict]
) -> str:
    """
    Classify an incoming file according to the frozen ETL rules.
    """

    file_name = file_path.name

    same_name_records = [
        record
        for record in previous_records
        if record.get("file_name", "").strip() == file_name
    ]

    # --------------------------------------------------------
    # Same name + different hash
    # -> CORRECTION_CANDIDATE
    # --------------------------------------------------------

    for record in same_name_records:

        previous_hash = record.get(
            "sha256_hash",
            ""
        ).strip()

        if previous_hash and previous_hash != file_hash:

            return "CORRECTION_CANDIDATE"

    # --------------------------------------------------------
    # Same name + same hash
    # Only skip if previous load succeeded
    # --------------------------------------------------------

    for record in same_name_records:

        previous_hash = record.get(
            "sha256_hash",
            ""
        ).strip()

        previous_status = record.get(
            "status",
            ""
        ).strip().upper()

        if (
            previous_hash == file_hash
            and previous_status in SUCCESS_STATUSES
        ):
            return "SKIPPED_DUPLICATE"

    # --------------------------------------------------------
    # No successful previous load
    # --------------------------------------------------------

    return "ACCEPT_FOR_PROCESSING"


# ============================================================
# CHECK INCOMING FILES
# ============================================================

def check_incoming_files() -> None:
    """Check every supported incoming file."""

    if not INPUT_DIR.exists():

        logger.error(
            "Incoming directory does not exist: %s",
            INPUT_DIR
        )

        return

    previous_records = load_previous_audit_records()

    incoming_files = sorted(
        file_path
        for file_path in INPUT_DIR.iterdir()
        if file_path.is_file()
        and file_path.suffix.lower() in {
            ".csv",
            ".xlsx",
            ".xls",
        }
    )

    if not incoming_files:

        logger.info(
            "No supported incoming files found."
        )

        return

    for file_path in incoming_files:

        try:

            file_hash = calculate_sha256(file_path)

            classification = classify_file(
                file_path,
                file_hash,
                previous_records
            )

            if classification == "SKIPPED_DUPLICATE":

                logger.warning(
                    "SKIPPED_DUPLICATE | "
                    "file=%s | hash=%s | "
                    "action=DO_NOT_REPROCESS",
                    file_path.name,
                    file_hash
                )

            elif classification == "CORRECTION_CANDIDATE":

                logger.warning(
                    "CORRECTION_CANDIDATE | "
                    "file=%s | hash=%s | "
                    "action=DO_NOT_SILENTLY_RELOAD",
                    file_path.name,
                    file_hash
                )

            else:

                logger.info(
                    "ACCEPT_FOR_PROCESSING | "
                    "file=%s | hash=%s",
                    file_path.name,
                    file_hash
                )

        except Exception as error:

            logger.exception(
                "Duplicate detection failed | "
                "file=%s | error=%s",
                file_path.name,
                error
            )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    logger.info(
        "Starting Tracker 03.04 - Duplicate File Detection"
    )

    check_incoming_files()

    logger.info(
        "Tracker 03.04 duplicate detection check completed"
    )
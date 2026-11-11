"""
Tracker 03.03 - Calculate file hash

Requirement:
Calculate SHA-256 for each incoming file before processing
and store it in the audit log.
"""

from pathlib import Path
from datetime import datetime
import hashlib
import csv
import logging


# ============================================================
# CONFIGURATION
# ============================================================

# Incoming files directory
INPUT_DIR = Path("incoming")

# Audit log directory
AUDIT_DIR = Path("logs")

# Audit log file
AUDIT_LOG_FILE = AUDIT_DIR / "file_audit_log.csv"

# SHA-256 read block size
CHUNK_SIZE = 1024 * 1024  # 1 MB


# ============================================================
# LOGGING
# ============================================================

AUDIT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# SHA-256 CALCULATION
# ============================================================

def calculate_sha256(file_path: Path) -> str:
    """
    Calculate SHA-256 hash for a file.

    The file is read in chunks so that large files
    do not need to be loaded completely into memory.
    """

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# AUDIT LOG
# ============================================================

def create_audit_log_if_missing():
    """
    Create the audit log file with headers if it does not exist.
    """

    if not AUDIT_LOG_FILE.exists():

        with AUDIT_LOG_FILE.open(
            mode="w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "timestamp",
                "file_name",
                "file_path",
                "file_size_bytes",
                "sha256_hash",
                "status",
                "error"
            ])


def write_audit_log(
    file_path: Path,
    sha256_hash: str,
    status: str,
    error: str = ""
):
    """
    Store file hash and processing information
    in the audit log.
    """

    with AUDIT_LOG_FILE.open(
        mode="a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            file_path.name,
            str(file_path),
            file_path.stat().st_size,
            sha256_hash,
            status,
            error
        ])


# ============================================================
# PROCESS ALL INCOMING FILES
# ============================================================

def calculate_hash_for_incoming_files():
    """
    Calculate SHA-256 for every incoming file
    before processing.
    """

    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    create_audit_log_if_missing()

    files = [
        file
        for file in INPUT_DIR.iterdir()
        if file.is_file()
    ]

    if not files:
        logger.warning(
            "No incoming files found in: %s",
            INPUT_DIR
        )
        return

    logger.info(
        "Found %d incoming file(s) in %s",
        len(files),
        INPUT_DIR
    )

    for file_path in files:

        try:

            # ------------------------------------------------
            # STEP 1: Calculate SHA-256 BEFORE processing
            # ------------------------------------------------

            sha256_hash = calculate_sha256(file_path)

            # ------------------------------------------------
            # STEP 2: Store hash in audit log
            # ------------------------------------------------

            write_audit_log(
                file_path=file_path,
                sha256_hash=sha256_hash,
                status="HASH_CALCULATED"
            )

            logger.info(
                "SHA-256 calculated | file=%s | hash=%s",
                file_path.name,
                sha256_hash
            )

            # ------------------------------------------------
            # IMPORTANT:
            # Actual file processing should happen AFTER
            # this point.
            # ------------------------------------------------

        except Exception as error:

            error_message = str(error)

            write_audit_log(
                file_path=file_path,
                sha256_hash="",
                status="HASH_FAILED",
                error=error_message
            )

            logger.exception(
                "Failed to calculate SHA-256 for %s",
                file_path.name
            )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    logger.info("Starting Tracker 03.03 - File Hash Calculation")

    calculate_hash_for_incoming_files()

    logger.info("Tracker 03.03 completed")
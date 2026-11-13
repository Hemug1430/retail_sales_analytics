
"""
Configuration file for Retail Sales Analytics Project.

Loads database credentials and project paths securely from .env.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# -----------------------------
# Project Root Folder
# -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# -----------------------------
# Load Environment Variables
# -----------------------------
ENV_FILE = PROJECT_ROOT / ".env"

if not ENV_FILE.exists():
    raise FileNotFoundError(
        f".env file not found at: {ENV_FILE}"
    )

load_dotenv(ENV_FILE)


# -----------------------------
# Environment Variable Helpers
# -----------------------------
def get_required_env(name):
    """Return a required environment variable."""
    value = os.getenv(name)

    if value is None or not value.strip():
        raise ValueError(
            f"Required environment variable '{name}' "
            "is missing or empty in .env"
        )

    return value.strip()


def get_path_env(name, default):
    """Return a project path from .env or use its default."""
    value = os.getenv(name, default)

    if not value.strip():
        value = default

    return PROJECT_ROOT / value.strip()


# -----------------------------
# Database Configuration
# -----------------------------
try:
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
except ValueError:
    raise ValueError(
        "DB_PORT must be a valid integer in .env"
    )

if not 1 <= DB_PORT <= 65535:
    raise ValueError(
        "DB_PORT must be between 1 and 65535"
    )

DB_CONFIG = {
    "host": get_required_env("DB_HOST"),
    "port": DB_PORT,
    "database": get_required_env("DB_NAME"),
    "user": get_required_env("DB_USER"),
    "password": get_required_env("DB_PASSWORD"),
}


# -----------------------------
# Project Paths
# -----------------------------
RAW_DATA_PATH = get_path_env(
    "RAW_DATA_PATH", "data/raw"
)

PROCESSED_DATA_PATH = get_path_env(
    "PROCESSED_DATA_PATH", "data/processed"
)

OUTPUT_FOLDER = get_path_env(
    "OUTPUT_FOLDER", "reports"
)

LOG_FOLDER = get_path_env(
    "LOG_FOLDER", "logs"
)

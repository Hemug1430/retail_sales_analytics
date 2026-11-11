"""
Configuration file for Retail Sales Analytics Project
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# -----------------------------
# Project Root Folder
# -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

# -----------------------------
# Database Configuration
# -----------------------------
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

# -----------------------------
# Project Paths
# -----------------------------
RAW_DATA_PATH = PROJECT_ROOT / os.getenv("RAW_DATA_PATH")
PROCESSED_DATA_PATH = PROJECT_ROOT / os.getenv("PROCESSED_DATA_PATH")
OUTPUT_FOLDER = PROJECT_ROOT / os.getenv("OUTPUT_FOLDER")
LOG_FOLDER = PROJECT_ROOT / os.getenv("LOG_FOLDER")


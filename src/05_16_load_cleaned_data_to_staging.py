"""
05.16 - Load cleaned data into staging tables

Tracker requirement
-------------------
Use Python bulk/chunk loading to push validated cleaned rows
to staging tables.

Technical metadata
------------------
batch_id
source_file_name
source_row_number
record_hash
load_timestamp

Important rules
---------------
1. Only *_cleaned_staging.csv files are processed.
2. Reject/audit files are never loaded.
3. Missing business columns are REVIEW.
4. No business values are invented.
5. Existing source rows are protected against duplicate reload.
6. Data is inserted in chunks.
7. Database-generated auto-increment columns are never inserted.
8. Target staging-table column names are detected dynamically.
9. Existing staging schema is respected.
10. Detailed database errors are printed and written to the log.
"""

from __future__ import annotations

import csv
import hashlib
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


# ============================================================
# 01. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
STAGING_DIR = PROCESSED_DIR / "staging"
LOG_DIR = PROJECT_ROOT / "logs"

AUDIT_FILE = (
    PROCESSED_DIR
    / "05_16_staging_load_audit.csv"
)

LOG_FILE = (
    LOG_DIR
    / "05_16_load_cleaned_data_to_staging.log"
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

STAGING_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# 02. LOGGING
# ============================================================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "05.16 | "
        "%(message)s"
    ),
)

logger = logging.getLogger("05.16")


# ============================================================
# 03. LOAD ENVIRONMENT
# ============================================================

load_dotenv(
    PROJECT_ROOT / ".env"
)


# ============================================================
# 04. DATABASE CONFIGURATION
# ============================================================

def get_env(
    *names: str,
    default: str | None = None,
) -> str | None:

    for name in names:

        value = os.getenv(name)

        if (
            value is not None
            and str(value).strip() != ""
        ):
            return str(value).strip()

    return default


DB_HOST = get_env(
    "MYSQL_HOST",
    "DB_HOST",
    default="localhost",
)

DB_PORT = get_env(
    "MYSQL_PORT",
    "DB_PORT",
    default="3306",
)

DB_NAME = get_env(
    "MYSQL_DATABASE",
    "MYSQL_DB",
    "DB_NAME",
    default="retail_sales_db",
)

DB_USER = get_env(
    "MYSQL_USER",
    "DB_USER",
    default="root",
)

DB_PASSWORD = get_env(
    "MYSQL_PASSWORD",
    "DB_PASSWORD",
    default="Root",
)


# ============================================================
# 05. DATABASE ENGINE
# ============================================================

def create_db_engine() -> Engine:

    password = str(DB_PASSWORD)

    password_encoded = (
        password
        .replace("%", "%25")
        .replace("@", "%40")
        .replace(":", "%3A")
        .replace("/", "%2F")
        .replace("#", "%23")
        .replace("?", "%3F")
    )

    connection_url = (
        "mysql+pymysql://"
        f"{DB_USER}:"
        f"{password_encoded}@"
        f"{DB_HOST}:"
        f"{DB_PORT}/"
        f"{DB_NAME}"
        "?charset=utf8mb4"
    )

    return create_engine(
        connection_url,
        pool_pre_ping=True,
        future=True,
    )


# ============================================================
# 06. DATASET -> STAGING TABLE
# ============================================================

DATASET_TABLE_MAP = {

    "customers":
        "stg_customers",

    "products":
        "stg_products",

    "stores":
        "stg_stores",

    "salespersons":
        "stg_salespersons",

    "promotions":
        "stg_promotions",

    "sales":
        "stg_sales",

    "returns":
        "stg_returns",

    "targets":
        "stg_targets",
}


# ============================================================
# 07. REQUIRED BUSINESS COLUMNS
# ============================================================

REQUIRED_COLUMNS = {

    "customers": [
        "customer_id",
        "customer_name",
        "gender",
        "date_of_birth",
        "city",
        "state",
        "region",
        "registration_date",
        "customer_segment",
        "email",
        "phone",
        "status",
    ],

    "products": [
        "product_id",
        "product_name",
        "category",
        "subcategory",
        "brand",
        "unit_cost",
        "list_price",
        "tax_rate_pct",
        "launch_date",
        "status",
    ],

    "sales": [
        "sales_line_id",
        "order_id",
        "order_date",
        "order_time",
        "customer_id",
        "product_id",
        "store_id",
        "salesperson_id",
        "promotion_id",
        "sales_channel",
        "quantity",
        "unit_selling_price",
        "discount_pct",
        "payment_method",
        "order_status",
    ],

    "stores": [
        "store_id",
        "store_name",
        "store_type",
        "city",
        "state",
        "region",
        "opening_date",
        "status",
    ],

    "salespersons": [
        "salesperson_id",
        "salesperson_name",
        "store_id",
        "joining_date",
        "role",
        "status",
    ],

    "promotions": [
        "promotion_id",
        "promotion_name",
        "start_date",
        "end_date",
        "discount_pct",
        "applicable_category",
        "applicable_channel",
        "minimum_order_value",
        "status",
    ],

    "returns": [
        "return_id",
        "sales_line_id",
        "return_date",
        "return_quantity",
        "return_reason",
        "return_status",
    ],

    "targets": [
        "target_month",
        "store_id",
        "category",
        "target_amount",
    ],
}


# ============================================================
# 08. SOURCE COLUMN ALIASES
# ============================================================

SOURCE_ALIASES = {

    "customers": {
        "customer_segment": [
            "customer_segment",
            "segment",
        ],
    },

    "products": {
        "unit_cost": [
            "unit_cost",
            "cost_price",
        ],
        "list_price": [
            "list_price",
            "unit_price",
        ],
        "tax_rate_pct": [
            "tax_rate_pct",
            "gst_percent",
        ],
    },
}


# ============================================================
# 09. DATASET IDENTIFICATION
# ============================================================

def identify_dataset(
    file_name: str,
) -> str | None:

    name = file_name.lower()

    if name == (
        "customers_master_cleaned_staging.csv"
    ):
        return "customers"

    if name == (
        "products_master_cleaned_staging.csv"
    ):
        return "products"

    if name == (
        "stores_master_cleaned_staging.csv"
    ):
        return "stores"

    if name == (
        "salespersons_master_cleaned_staging.csv"
    ):
        return "salespersons"

    if name == (
        "promotions_master_cleaned_staging.csv"
    ):
        return "promotions"

    if re.fullmatch(
        r"sales_\d{4}_\d{2}_cleaned_staging\.csv",
        name,
    ):
        return "sales"

    if re.fullmatch(
        r"returns_\d{4}_\d{2}_cleaned_staging\.csv",
        name,
    ):
        return "returns"

    if re.fullmatch(
        r"targets_\d{4}_\d{2}_cleaned_staging\.csv",
        name,
    ):
        return "targets"

    return None


# ============================================================
# 10. DISCOVER APPROVED CLEANED FILES
# ============================================================

def discover_cleaned_files() -> list[Path]:

    if not STAGING_DIR.exists():
        return []

    files = sorted(
        STAGING_DIR.glob(
            "*_cleaned_staging.csv"
        )
    )

    approved_files = []

    for file_path in files:

        if not file_path.is_file():
            continue

        dataset = identify_dataset(
            file_path.name
        )

        if dataset is None:

            logger.warning(
                "Skipped unrecognized cleaned "
                "file: %s",
                file_path.name,
            )

            continue

        approved_files.append(
            file_path
        )

    return approved_files


# ============================================================
# 11. NORMALIZE COLUMN NAMES
# ============================================================

def normalize_column_name(
    column_name: str,
) -> str:

    return re.sub(
        r"[^a-z0-9_]",
        "_",
        str(column_name)
        .strip()
        .lower(),
    )


# ============================================================
# 12. NORMALIZE DATAFRAME COLUMNS
# ============================================================

def normalize_dataframe_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    df.columns = [
        normalize_column_name(
            column
        )
        for column in df.columns
    ]

    unnamed_columns = [
        column
        for column in df.columns
        if column.startswith("unnamed_")
    ]

    if unnamed_columns:

        df = df.drop(
            columns=unnamed_columns
        )

    return df


# ============================================================
# 13. CLEAN NULL-LIKE VALUES
# ============================================================

def clean_null_values(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    for column in df.columns:

        def clean_value(value):

            if value is None:
                return None

            try:
                if pd.isna(value):
                    return None
            except Exception:
                pass

            value = str(value).strip()

            if value == "":
                return None

            if value.lower() in {
                "nan",
                "nat",
                "none",
                "null",
            }:
                return None

            return value

        df[column] = (
            df[column]
            .apply(clean_value)
        )

    return df


# ============================================================
# 14. NORMALIZE ORDER TIME
# ============================================================

def normalize_order_time(
    value: Any,
) -> str | None:

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    value = str(value).strip()

    if not value:
        return None

    if value.lower() in {
        "nan",
        "nat",
        "none",
        "null",
    }:
        return None

    match = re.fullmatch(
        r"(\d+)\s+days?\s+"
        r"(\d{1,2}):(\d{2}):(\d{2})",
        value,
        flags=re.IGNORECASE,
    )

    if match:

        days = int(
            match.group(1)
        )

        hours = int(
            match.group(2)
        )

        minutes = int(
            match.group(3)
        )

        seconds = int(
            match.group(4)
        )

        total_seconds = (
            days * 86400
            + hours * 3600
            + minutes * 60
            + seconds
        )

        total_seconds %= 86400

        hours = (
            total_seconds // 3600
        )

        minutes = (
            total_seconds % 3600
        ) // 60

        seconds = (
            total_seconds % 60
        )

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )

    match = re.fullmatch(
        r"(\d{1,2}):"
        r"(\d{2}):"
        r"(\d{2})",
        value,
    )

    if match:

        hours = int(
            match.group(1)
        )

        minutes = int(
            match.group(2)
        )

        seconds = int(
            match.group(3)
        )

        if (
            hours <= 23
            and minutes <= 59
            and seconds <= 59
        ):

            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{seconds:02d}"
            )

    match = re.fullmatch(
        r"(\d{1,2}):(\d{2})",
        value,
    )

    if match:

        hours = int(
            match.group(1)
        )

        minutes = int(
            match.group(2)
        )

        if (
            hours <= 23
            and minutes <= 59
        ):

            return (
                f"{hours:02d}:"
                f"{minutes:02d}:00"
            )

    try:

        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if pd.notna(parsed):

            return parsed.strftime(
                "%H:%M:%S"
            )

    except Exception:
        pass

    return value


# ============================================================
# 15. NORMALIZE DATE COLUMNS
# ============================================================

DATE_COLUMNS = [
    "order_date",
    "date_of_birth",
    "registration_date",
    "launch_date",
    "joining_date",
    "opening_date",
    "start_date",
    "end_date",
    "return_date",
    "target_month",
]


def normalize_dates(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    for column in DATE_COLUMNS:

        if column not in df.columns:
            continue

        parsed = pd.to_datetime(
            df[column],
            errors="coerce",
        )

        formatted = (
            parsed.dt.strftime(
                "%Y-%m-%d"
            )
        )

        df[column] = (
            formatted.where(
                parsed.notna(),
                None,
            )
        )

    return df


# ============================================================
# 16. READ CLEANED CSV
# ============================================================

def read_cleaned_csv(
    file_path: Path,
) -> pd.DataFrame:

    logger.info(
        "Reading cleaned staging file: %s",
        file_path.name,
    )

    return pd.read_csv(
        file_path,
        dtype=object,
        keep_default_na=True,
        encoding="utf-8-sig",
    )


# ============================================================
# 17. DATABASE TABLE COLUMNS
# ============================================================

def get_table_columns(
    engine: Engine,
    table_name: str,
) -> dict[str, dict[str, Any]]:

    inspector = inspect(engine)

    columns = inspector.get_columns(
        table_name
    )

    return {
        column["name"]: column
        for column in columns
    }


# ============================================================
# 18. TABLE EXISTS
# ============================================================

def table_exists(
    engine: Engine,
    table_name: str,
) -> bool:

    return inspect(
        engine
    ).has_table(
        table_name
    )


# ============================================================
# 19. RESOLVE BUSINESS COLUMN ALIASES
# ============================================================

def resolve_business_aliases(
    df: pd.DataFrame,
    dataset: str,
    table_columns: dict[str, dict[str, Any]],
) -> pd.DataFrame:

    df = df.copy()

    aliases = SOURCE_ALIASES.get(
        dataset,
        {},
    )

    for approved_name, candidates in aliases.items():

        target_column = None

        # ----------------------------------------------------
        # Prefer the exact target-table column
        # ----------------------------------------------------

        for candidate in candidates:

            if (
                candidate in table_columns
                and candidate in df.columns
            ):

                target_column = candidate
                break

        # ----------------------------------------------------
        # If target table has approved_name,
        # rename a source candidate into it.
        # ----------------------------------------------------

        if approved_name in table_columns:

            if approved_name in df.columns:
                continue

            for candidate in candidates:

                if candidate in df.columns:

                    df = df.rename(
                        columns={
                            candidate:
                            approved_name
                        }
                    )

                    logger.info(
                        "Column alias applied: "
                        "%s -> %s "
                        "(dataset=%s)",
                        candidate,
                        approved_name,
                        dataset,
                    )

                    break

        elif target_column:

            # Existing target-table name already present.
            continue

    return df


# ============================================================
# 20. PREPARE DATAFRAME
# ============================================================

def prepare_dataframe(
    df: pd.DataFrame,
    dataset: str,
    table_columns: dict[str, dict[str, Any]],
) -> pd.DataFrame:

    df = normalize_dataframe_columns(
        df
    )

    df = resolve_business_aliases(
        df,
        dataset,
        table_columns,
    )

    df = clean_null_values(
        df
    )

    if (
        dataset == "sales"
        and "order_time" in df.columns
    ):

        df["order_time"] = (
            df["order_time"]
            .apply(
                normalize_order_time
            )
        )

    df = normalize_dates(
        df
    )

    return df


# ============================================================
# 21. VALIDATE REQUIRED BUSINESS COLUMNS
# ============================================================

def get_missing_business_columns(
    df: pd.DataFrame,
    dataset: str,
    table_columns: dict[str, dict[str, Any]],
) -> list[str]:

    required = REQUIRED_COLUMNS.get(
        dataset,
        [],
    )

    missing = []

    for required_column in required:

        # ----------------------------------------------------
        # Direct match
        # ----------------------------------------------------

        if required_column in df.columns:
            continue

        # ----------------------------------------------------
        # Customer compatibility:
        # project staging table used by 05.18 expects
        # customer_segment.
        # ----------------------------------------------------

        if (
            dataset == "customers"
            and required_column
            == "customer_segment"
            and "segment" in df.columns
        ):
            continue

        missing.append(
            required_column
        )

    return missing


# ============================================================
# 22. GENERATE BATCH ID
# ============================================================

def generate_batch_id(
    file_path: Path,
) -> str:

    file_hash = hashlib.sha256(
        file_path.read_bytes()
    ).hexdigest()

    return (
        "BATCH_"
        + file_hash[:16].upper()
    )


# ============================================================
# 23. GENERATE RECORD HASH
# ============================================================

def generate_record_hash(
    row: pd.Series,
    business_columns: list[str],
) -> str:

    values = []

    for column in business_columns:

        value = row.get(
            column,
            None,
        )

        if value is None:
            value = ""

        values.append(
            str(value).strip()
        )

    normalized_record = (
        "|".join(values)
    )

    return hashlib.sha256(
        normalized_record.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# 24. ADD TECHNICAL METADATA
# ============================================================

def add_technical_metadata(
    df: pd.DataFrame,
    file_path: Path,
    dataset: str,
) -> pd.DataFrame:

    df = df.copy()

    batch_id = generate_batch_id(
        file_path
    )

    load_timestamp = datetime.now()

    df["source_file_name"] = (
        file_path.name
    )

    df["source_row_number"] = range(
        2,
        len(df) + 2,
    )

    df["batch_id"] = (
        batch_id
    )

    business_columns = [
        column
        for column in REQUIRED_COLUMNS.get(
            dataset,
            [],
        )
        if column in df.columns
    ]

    # Customer compatibility
    if (
        dataset == "customers"
        and "customer_segment"
        not in business_columns
        and "segment" in df.columns
    ):

        business_columns.append(
            "segment"
        )

    df["record_hash"] = (
        df.apply(
            lambda row:
            generate_record_hash(
                row,
                business_columns,
            ),
            axis=1,
        )
    )

    df["load_timestamp"] = (
        load_timestamp
    )

    return df


# ============================================================
# 25. GET EXISTING SOURCE KEYS
# ============================================================

def get_existing_source_keys(
    engine: Engine,
    table_name: str,
) -> set[tuple[str, int]]:

    table_columns = (
        get_table_columns(
            engine,
            table_name,
        )
    )

    if (
        "source_file_name"
        not in table_columns
        or
        "source_row_number"
        not in table_columns
    ):

        return set()

    query = text(
        f"""
        SELECT
            source_file_name,
            source_row_number
        FROM `{table_name}`
        WHERE source_file_name IS NOT NULL
          AND source_row_number IS NOT NULL
        """
    )

    existing = set()

    with engine.connect() as connection:

        rows = connection.execute(
            query
        ).fetchall()

        for row in rows:

            try:

                existing.add(
                    (
                        str(row[0]),
                        int(row[1]),
                    )
                )

            except Exception:
                continue

    return existing


# ============================================================
# 26. FILTER ALREADY LOADED ROWS
# ============================================================

def filter_new_rows(
    df: pd.DataFrame,
    existing_keys: set[tuple[str, int]],
) -> tuple[pd.DataFrame, int]:

    if not existing_keys:
        return df, 0

    keep_mask = []
    skipped = 0

    for _, row in df.iterrows():

        source_file = row.get(
            "source_file_name"
        )

        source_row = row.get(
            "source_row_number"
        )

        try:

            key = (
                str(source_file),
                int(source_row),
            )

        except Exception:

            keep_mask.append(
                True
            )

            continue

        if key in existing_keys:

            keep_mask.append(
                False
            )

            skipped += 1

        else:

            keep_mask.append(
                True
            )

    filtered = df.loc[
        keep_mask
    ].copy()

    return (
        filtered,
        skipped,
    )


# ============================================================
# 27. PREPARE INSERT DATAFRAME
# ============================================================

def prepare_insert_dataframe(
    df: pd.DataFrame,
    table_columns: dict[str, dict[str, Any]],
) -> pd.DataFrame:

    insert_columns = []

    for column in df.columns:

        if column not in table_columns:
            continue

        metadata = table_columns[
            column
        ]

        # Never insert auto-increment IDs.
        if (
            metadata.get(
                "autoincrement"
            )
            is True
        ):
            continue

        insert_columns.append(
            column
        )

    if not insert_columns:
        return pd.DataFrame()

    return df[
        insert_columns
    ].copy()


# ============================================================
# 28. INSERT DATA IN CHUNKS
# ============================================================

def insert_dataframe(
    engine: Engine,
    table_name: str,
    df: pd.DataFrame,
) -> int:

    if df.empty:
        return 0

    records = df.to_dict(
        orient="records"
    )

    columns = list(
        df.columns
    )

    column_sql = ", ".join(
        f"`{column}`"
        for column in columns
    )

    parameter_sql = ", ".join(
        f":{column}"
        for column in columns
    )

    insert_sql = text(
        f"""
        INSERT INTO `{table_name}`
        ({column_sql})
        VALUES
        ({parameter_sql})
        """
    )

    loaded_count = 0

    chunk_size = 1000

    for start in range(
        0,
        len(records),
        chunk_size,
    ):

        chunk = records[
            start:
            start + chunk_size
        ]

        logger.info(
            "Loading chunk: "
            "dataset table=%s "
            "start=%s "
            "size=%s",
            table_name,
            start,
            len(chunk),
        )

        try:

            with engine.begin() as connection:

                connection.execute(
                    insert_sql,
                    chunk,
                )

            loaded_count += len(
                chunk
            )

        except Exception as exc:

            logger.exception(
                "Chunk insert failed "
                "for table=%s "
                "start=%s "
                "size=%s",
                table_name,
                start,
                len(chunk),
            )

            raise RuntimeError(
                "Chunk insert failed for "
                f"{table_name}. "
                f"Chunk start={start}, "
                f"chunk size={len(chunk)}. "
                f"Database error: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ) from exc

    return loaded_count


# ============================================================
# 29. PROCESS ONE DATASET
# ============================================================

def process_dataset(
    engine: Engine,
    file_path: Path,
) -> dict[str, Any]:

    dataset = identify_dataset(
        file_path.name
    )

    if dataset is None:

        return {
            "file":
                file_path.name,
            "dataset":
                "",
            "table":
                "",
            "status":
                "SKIPPED",
            "rows_read":
                0,
            "rows_loaded":
                0,
            "rows_skipped_existing":
                0,
            "reason":
                "Dataset could not be identified.",
        }

    table_name = (
        DATASET_TABLE_MAP[
            dataset
        ]
    )

    print()
    print("=" * 70)
    print(
        f"DATASET : {dataset}"
    )
    print(
        f"TABLE   : {table_name}"
    )
    print(
        f"FILE    : {file_path.name}"
    )
    print("=" * 70)

    logger.info(
        "START dataset=%s "
        "table=%s file=%s",
        dataset,
        table_name,
        file_path.name,
    )

    df = pd.DataFrame()

    try:

        # ----------------------------------------------------
        # READ CSV
        # ----------------------------------------------------

        df = read_cleaned_csv(
            file_path
        )

        rows_read = len(df)

        print(
            f"ROWS READ : {rows_read}"
        )

        if rows_read == 0:

            return {
                "file":
                    file_path.name,
                "dataset":
                    dataset,
                "table":
                    table_name,
                "status":
                    "REVIEW",
                "rows_read":
                    0,
                "rows_loaded":
                    0,
                "rows_skipped_existing":
                    0,
                "reason":
                    "Cleaned staging file contains zero rows.",
            }

        # ----------------------------------------------------
        # CHECK TARGET TABLE
        # ----------------------------------------------------

        if not table_exists(
            engine,
            table_name,
        ):

            reason = (
                f"Target staging table "
                f"'{table_name}' "
                f"was not found."
            )

            print(
                "STATUS : REVIEW"
            )

            print(
                f"REASON : {reason}"
            )

            return {
                "file":
                    file_path.name,
                "dataset":
                    dataset,
                "table":
                    table_name,
                "status":
                    "REVIEW",
                "rows_read":
                    rows_read,
                "rows_loaded":
                    0,
                "rows_skipped_existing":
                    0,
                "reason":
                    reason,
            }

        # ----------------------------------------------------
        # GET ACTUAL TARGET TABLE COLUMNS
        # ----------------------------------------------------

        table_columns = (
            get_table_columns(
                engine,
                table_name,
            )
        )

        target_columns = list(
            table_columns.keys()
        )

        logger.info(
            "Target table columns "
            "for %s: %s",
            table_name,
            target_columns,
        )

        print(
            "TARGET TABLE COLUMNS : "
            f"{target_columns}"
        )

        # ----------------------------------------------------
        # NORMALIZE DATA
        # ----------------------------------------------------

        df = prepare_dataframe(
            df,
            dataset,
            table_columns,
        )

        print(
            "NORMALIZED COLUMNS : "
            f"{list(df.columns)}"
        )

        logger.info(
            "Normalized columns for "
            "%s: %s",
            dataset,
            list(df.columns),
        )

        # ----------------------------------------------------
        # VALIDATE REQUIRED BUSINESS COLUMNS
        # ----------------------------------------------------

        missing_columns = (
            get_missing_business_columns(
                df,
                dataset,
                table_columns,
            )
        )

        if missing_columns:

            reason = (
                "Missing required business "
                "columns after normalization: "
                f"{missing_columns}. "
                f"CSV columns={list(df.columns)}. "
                f"Target columns={target_columns}"
            )

            print(
                "STATUS : REVIEW"
            )

            print(
                f"REASON : {reason}"
            )

            logger.warning(
                "REVIEW dataset=%s "
                "reason=%s",
                dataset,
                reason,
            )

            return {
                "file":
                    file_path.name,
                "dataset":
                    dataset,
                "table":
                    table_name,
                "status":
                    "REVIEW",
                "rows_read":
                    rows_read,
                "rows_loaded":
                    0,
                "rows_skipped_existing":
                    0,
                "reason":
                    reason,
            }

        # ----------------------------------------------------
        # ADD TECHNICAL METADATA
        # ----------------------------------------------------

        df = add_technical_metadata(
            df,
            file_path,
            dataset,
        )

        # ----------------------------------------------------
        # VALIDATE TECHNICAL COLUMNS
        # ----------------------------------------------------

        required_technical_columns = [
            "batch_id",
            "source_file_name",
            "source_row_number",
            "record_hash",
            "load_timestamp",
        ]

        missing_technical_columns = [
            column
            for column
            in required_technical_columns
            if column
            not in table_columns
        ]

        if missing_technical_columns:

            reason = (
                "Target staging table is "
                "missing required technical "
                "columns: "
                f"{missing_technical_columns}"
            )

            print(
                "STATUS : REVIEW"
            )

            print(
                f"REASON : {reason}"
            )

            return {
                "file":
                    file_path.name,
                "dataset":
                    dataset,
                "table":
                    table_name,
                "status":
                    "REVIEW",
                "rows_read":
                    rows_read,
                "rows_loaded":
                    0,
                "rows_skipped_existing":
                    0,
                "reason":
                    reason,
            }

        # ----------------------------------------------------
        # EXISTING ROW PROTECTION
        # ----------------------------------------------------

        existing_keys = (
            get_existing_source_keys(
                engine,
                table_name,
            )
        )

        (
            df,
            skipped_existing,
        ) = filter_new_rows(
            df,
            existing_keys,
        )

        print(
            f"ALREADY LOADED : "
            f"{skipped_existing}"
        )

        logger.info(
            "Existing source rows skipped "
            "for dataset=%s: %s",
            dataset,
            skipped_existing,
        )

        # ----------------------------------------------------
        # PREPARE INSERT DATAFRAME
        # ----------------------------------------------------

        insert_df = (
            prepare_insert_dataframe(
                df,
                table_columns,
            )
        )

        print(
            "INSERT COLUMNS : "
            f"{list(insert_df.columns)}"
        )

        logger.info(
            "Insert columns for "
            "dataset=%s: %s",
            dataset,
            list(insert_df.columns),
        )

        if insert_df.empty:

            print(
                "STATUS : PASS"
            )

            return {
                "file":
                    file_path.name,
                "dataset":
                    dataset,
                "table":
                    table_name,
                "status":
                    "PASS",
                "rows_read":
                    rows_read,
                "rows_loaded":
                    0,
                "rows_skipped_existing":
                    skipped_existing,
                "reason":
                    "All rows were already loaded "
                    "or no insertable columns remained.",
            }

        # ----------------------------------------------------
        # INSERT
        # ----------------------------------------------------

        rows_loaded = (
            insert_dataframe(
                engine,
                table_name,
                insert_df,
            )
        )

        # ----------------------------------------------------
        # RECONCILIATION
        # ----------------------------------------------------

        expected_to_load = (
            rows_read
            - skipped_existing
        )

        if rows_loaded != expected_to_load:

            reason = (
                f"Rows read={rows_read}, "
                f"already loaded="
                f"{skipped_existing}, "
                f"expected new rows="
                f"{expected_to_load}, "
                f"actual loaded="
                f"{rows_loaded}"
            )

            logger.error(
                "RECONCILIATION FAILURE: %s",
                reason,
            )

            print(
                "STATUS : FAIL"
            )

            print(
                f"REASON : {reason}"
            )

            return {
                "file":
                    file_path.name,
                "dataset":
                    dataset,
                "table":
                    table_name,
                "status":
                    "FAIL",
                "rows_read":
                    rows_read,
                "rows_loaded":
                    rows_loaded,
                "rows_skipped_existing":
                    skipped_existing,
                "reason":
                    reason,
            }

        print(
            f"ROWS LOADED : "
            f"{rows_loaded}"
        )

        print(
            "STATUS : PASS"
        )

        logger.info(
            "PASS dataset=%s "
            "table=%s "
            "rows_read=%s "
            "rows_loaded=%s "
            "existing=%s",
            dataset,
            table_name,
            rows_read,
            rows_loaded,
            skipped_existing,
        )

        return {
            "file":
                file_path.name,
            "dataset":
                dataset,
            "table":
                table_name,
            "status":
                "PASS",
            "rows_read":
                rows_read,
            "rows_loaded":
                rows_loaded,
            "rows_skipped_existing":
                skipped_existing,
            "reason":
                "",
        }

    except Exception as exc:

        reason = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        print()
        print(
            "STATUS : FAIL"
        )

        print(
            f"REASON : {reason}"
        )

        logger.exception(
            "FAILED dataset=%s "
            "table=%s "
            "file=%s",
            dataset,
            table_name,
            file_path.name,
        )

        return {
            "file":
                file_path.name,
            "dataset":
                dataset,
            "table":
                table_name,
            "status":
                "FAIL",
            "rows_read":
                len(df),
            "rows_loaded":
                0,
            "rows_skipped_existing":
                0,
            "reason":
                reason,
        }


# ============================================================
# 30. WRITE AUDIT FILE
# ============================================================

def write_audit_file(
    results: list[dict[str, Any]],
) -> None:

    fieldnames = [
        "file",
        "dataset",
        "table",
        "status",
        "rows_read",
        "rows_loaded",
        "rows_skipped_existing",
        "reason",
    ]

    with AUDIT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            results
        )


# ============================================================
# 31. MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "05.16 LOAD CLEANED DATA "
        "INTO STAGING"
    )
    print("=" * 70)

    logger.info(
        "========== 05.16 START =========="
    )

    # --------------------------------------------------------
    # Validate password
    # --------------------------------------------------------

    if (
        DB_PASSWORD is None
        or str(DB_PASSWORD).strip() == ""
    ):

        print()
        print(
            "DATABASE PASSWORD NOT CONFIGURED"
        )

        logger.error(
            "Database password is not configured."
        )

        return

    # --------------------------------------------------------
    # Database connection
    # --------------------------------------------------------

    try:

        engine = create_db_engine()

        with engine.connect() as connection:

            database_name = (
                connection.execute(
                    text(
                        "SELECT DATABASE()"
                    )
                ).scalar()
            )

        print()
        print(
            "DATABASE CONNECTION SUCCESS"
        )

        print(
            f"DATABASE : "
            f"{database_name}"
        )

        logger.info(
            "Database connection successful: "
            "%s",
            database_name,
        )

    except Exception as exc:

        reason = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        print()
        print(
            "DATABASE CONNECTION ERROR"
        )

        print(
            f"REASON : {reason}"
        )

        logger.exception(
            "Database connection failed."
        )

        return

    # --------------------------------------------------------
    # Discover files
    # --------------------------------------------------------

    files = (
        discover_cleaned_files()
    )

    print()
    print(
        "APPROVED CLEANED FILES : "
        f"{len(files)}"
    )

    if not files:

        reason = (
            "No approved "
            "*_cleaned_staging.csv "
            "files found."
        )

        print(
            "05.16 STATUS: REVIEW"
        )

        print(
            f"REASON : {reason}"
        )

        write_audit_file(
            [
                {
                    "file": "",
                    "dataset": "",
                    "table": "",
                    "status": "REVIEW",
                    "rows_read": 0,
                    "rows_loaded": 0,
                    "rows_skipped_existing": 0,
                    "reason": reason,
                }
            ]
        )

        return

    # --------------------------------------------------------
    # Process datasets
    # --------------------------------------------------------

    results = []

    for file_path in files:

        result = process_dataset(
            engine,
            file_path,
        )

        results.append(
            result
        )

    # --------------------------------------------------------
    # Write audit
    # --------------------------------------------------------

    write_audit_file(
        results
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    passed = sum(
        1
        for result in results
        if result["status"]
        == "PASS"
    )

    review = sum(
        1
        for result in results
        if result["status"]
        == "REVIEW"
    )

    failed = sum(
        1
        for result in results
        if result["status"]
        == "FAIL"
    )

    total_read = sum(
        int(
            result["rows_read"]
        )
        for result in results
    )

    total_loaded = sum(
        int(
            result["rows_loaded"]
        )
        for result in results
    )

    total_existing = sum(
        int(
            result[
                "rows_skipped_existing"
            ]
        )
        for result in results
    )

    print()
    print("=" * 70)
    print(
        "05.16 LOAD SUMMARY"
    )
    print("=" * 70)

    print(
        f"Datasets processed : "
        f"{len(results)}"
    )

    print(
        f"Datasets passed    : "
        f"{passed}"
    )

    print(
        f"Datasets review    : "
        f"{review}"
    )

    print(
        f"Datasets failed    : "
        f"{failed}"
    )

    print(
        f"Rows read          : "
        f"{total_read}"
    )

    print(
        f"Rows loaded        : "
        f"{total_loaded}"
    )

    print(
        f"Rows already loaded: "
        f"{total_existing}"
    )

    print(
        f"Audit file         : "
        f"{AUDIT_FILE}"
    )

    print(
        f"Log file           : "
        f"{LOG_FILE}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    if failed > 0:

        print(
            "05.16 STATUS: FAIL"
        )

        logger.error(
            "05.16 completed with FAIL results."
        )

    elif review > 0:

        print(
            "05.16 STATUS: REVIEW"
        )

        logger.warning(
            "05.16 completed with REVIEW results."
        )

    else:

        print(
            "05.16 STATUS: PASS"
        )

        logger.info(
            "05.16 completed successfully."
        )

    logger.info(
        "========== 05.16 END =========="
    )


# ============================================================
# 32. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
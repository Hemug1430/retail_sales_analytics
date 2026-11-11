"""
Module: Schema Validation

Trackers:
    03.06 - Validate expected columns
    03.07 - Validate schema version

Purpose:
    Compare incoming CSV files against the frozen project schema,
    identify missing/unexpected/renamed fields, and determine whether
    the file matches the current schema version.

Project rules:
    - Do not silently add, drop, or rename columns.
    - Unexpected extra columns are schema-change failures.
    - Column order changes are allowed because processing is name-based,
      but the mismatch is reported.
    - stores_master.csv is an approved master-data filename.
    - Store optional fields are allowed to be absent.
"""

from pathlib import Path
import hashlib
import logging
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

CURRENT_SCHEMA_VERSION = "V1"

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INCOMING_DIR = PROJECT_ROOT / "incoming"
QUARANTINE_DIR = PROJECT_ROOT / "data" / "quarantine"

LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "application.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | schema_validation | %(message)s",
)

logger = logging.getLogger("schema_validation")


# ============================================================
# FROZEN SCHEMA - SALES
# ============================================================

SALES_SCHEMA_V1 = [
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
]


# ============================================================
# SUPPORTED FILE TYPES / SCHEMA DETECTION
# ============================================================

def detect_schema_type(filename: str) -> str:
    """
    Determine the business schema represented by the filename.

    Approved master filenames include:
        customers_master.csv
        products_master.csv
        stores_master.csv
        salespersons_master.csv
        promotions_master.csv

    Monthly files use:
        sales_YYYY_MM.csv
        returns_YYYY_MM.csv
        targets_YYYY_MM.csv
    """

    name = filename.lower()

    # --------------------------------------------------------
    # Monthly transaction datasets
    # --------------------------------------------------------

    if name.startswith("sales_") and name.endswith(".csv"):
        return "sales"

    if name.startswith("returns_") and name.endswith(".csv"):
        return "returns"

    if name.startswith("targets_") and name.endswith(".csv"):
        return "targets"

    # --------------------------------------------------------
    # Master datasets
    # --------------------------------------------------------

    if name == "customers_master.csv":
        return "customers_master"

    if name == "products_master.csv":
        return "products_master"

    if name == "stores_master.csv":
        return "stores_master"

    if name == "salespersons_master.csv":
        return "salespersons_master"

    if name == "promotions_master.csv":
        return "promotions_master"

    # --------------------------------------------------------
    # Controlled/derived master filenames
    # --------------------------------------------------------

    if name.startswith("customers_master_") and name.endswith(".csv"):
        return "customers_master"

    if name.startswith("products_master_") and name.endswith(".csv"):
        return "products_master"

    if name.startswith("stores_master_") and name.endswith(".csv"):
        return "stores_master"

    if name.startswith("salespersons_master_") and name.endswith(".csv"):
        return "salespersons_master"

    if name.startswith("promotions_master_") and name.endswith(".csv"):
        return "promotions_master"

    return "UNKNOWN"


# ============================================================
# SCHEMA DEFINITIONS
# ============================================================

SCHEMAS = {

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    "sales": {
        "version": "V1",
        "required_columns": SALES_SCHEMA_V1,
        "optional_columns": [],
    },

    # --------------------------------------------------------
    # CUSTOMERS
    # --------------------------------------------------------

    "customers_master": {
        "version": "V1",

        "required_columns": [
            "customer_id",
            "customer_name",
            "gender",
            "date_of_birth",
            "email",
            "phone",
            "city",
            "state",
            "region",
            "postal_code",
            "registration_date",
            "customer_segment",
            "preferred_channel",
            "status",
        ],

        "optional_columns": [],
    },

    # --------------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------------

    "products_master": {
        "version": "V1",

        "required_columns": [
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

        "optional_columns": [],
    },

    # --------------------------------------------------------
    # STORES
    #
    # Project requirement:
    # Required:
    #   store_id
    #   store_name
    #   store_type
    #   city
    #   state
    #   region
    #   postal_code
    #   opening_date
    #   status
    #
    # Optional:
    #   floor_area_sqft
    #   manager_name
    # --------------------------------------------------------

    "stores_master": {
        "version": "V1",

        "required_columns": [
            "store_id",
            "store_name",
            "store_type",
            "city",
            "state",
            "region",
            "postal_code",
            "opening_date",
            "status",
        ],

        "optional_columns": [
            "floor_area_sqft",
            "manager_name",
        ],
    },

    # --------------------------------------------------------
    # SALESPERSONS
    # --------------------------------------------------------

    "salespersons_master": {
        "version": "V1",

        "required_columns": [
            "salesperson_id",
            "salesperson_name",
            "store_id",
            "joining_date",
            "role",
            "status",
        ],

        "optional_columns": [],
    },

    # --------------------------------------------------------
    # PROMOTIONS
    # --------------------------------------------------------

    "promotions_master": {
        "version": "V1",

        "required_columns": [
            "promotion_id",
            "promotion_name",
            "promotion_type",
            "start_date",
            "end_date",
            "discount_pct",
            "applicable_channel",
            "status",
        ],

        "optional_columns": [
            "applicable_category",
            "minimum_order_value",
        ],
    },
}


# ============================================================
# FILE HASH
# ============================================================

def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA-256 fingerprint of the incoming file.
    """

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:

        while True:

            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# COLUMN VALIDATION - TRACKER 03.06
# ============================================================

def validate_columns(
    incoming_columns: list[str],
    required_columns: list[str],
    optional_columns: list[str] | None = None,
) -> dict:
    """
    Compare incoming columns with the approved project schema.

    Required columns:
        Must be present.

    Optional columns:
        May be present or absent.

    Unexpected columns:
        Are not allowed.

    A missing required field + unexpected incoming field is
    reported as a possible rename.
    """

    if optional_columns is None:
        optional_columns = []

    incoming = list(incoming_columns)
    required = list(required_columns)
    optional = list(optional_columns)

    incoming_set = set(incoming)
    required_set = set(required)
    allowed_set = required_set | set(optional)

    # --------------------------------------------------------
    # Missing required columns
    # --------------------------------------------------------

    missing_columns = [
        column
        for column in required
        if column not in incoming_set
    ]

    # --------------------------------------------------------
    # Unexpected columns
    # --------------------------------------------------------

    unexpected_columns = [
        column
        for column in incoming
        if column not in allowed_set
    ]

    # --------------------------------------------------------
    # Determine whether the incoming order differs from the
    # canonical required/optional project order.
    #
    # Only report order change when the same approved columns
    # are present.
    # --------------------------------------------------------

    canonical_columns = required + optional

    order_changed = False

    if not missing_columns and not unexpected_columns:

        # If all optional fields are present, compare with
        # complete canonical order.
        if set(incoming) == set(canonical_columns):

            order_changed = incoming != canonical_columns

        # If some optional fields are absent, compare the
        # incoming order against the canonical order after
        # removing absent optional fields.
        else:

            expected_present_order = [
                column
                for column in canonical_columns
                if column in incoming_set
            ]

            order_changed = incoming != expected_present_order

    # --------------------------------------------------------
    # Possible renamed fields
    # --------------------------------------------------------

    possible_renames = []

    if missing_columns and unexpected_columns:

        for missing in missing_columns:

            for unexpected in unexpected_columns:

                possible_renames.append(
                    {
                        "expected": missing,
                        "incoming": unexpected,
                    }
                )

    # --------------------------------------------------------
    # Final column status
    # --------------------------------------------------------

    if not missing_columns and not unexpected_columns:

        column_status = "PASS"

    else:

        column_status = "FAIL"

    return {
        "column_status": column_status,
        "missing_columns": missing_columns,
        "unexpected_columns": unexpected_columns,
        "possible_renames": possible_renames,
        "order_changed": order_changed,
    }


# ============================================================
# SCHEMA FINGERPRINT
# ============================================================

def calculate_schema_fingerprint(
    columns: list[str],
) -> str:
    """
    Create a deterministic fingerprint from the ordered
    incoming column list.
    """

    ordered_columns = "|".join(columns)

    return hashlib.sha256(
        ordered_columns.encode("utf-8")
    ).hexdigest()


# ============================================================
# TRACKER 03.07 - SCHEMA VERSION VALIDATION
# ============================================================

def validate_schema_version(
    schema_type: str,
    column_result: dict,
) -> dict:
    """
    Determine whether the incoming file matches the current
    approved schema version.

    Returns:
        CURRENT_SCHEMA
        SCHEMA_CHANGE
        UNKNOWN_SCHEMA
    """

    if schema_type not in SCHEMAS:

        return {
            "current_schema_version": CURRENT_SCHEMA_VERSION,
            "detected_schema_version": "UNKNOWN",
            "schema_version_status": "UNKNOWN_SCHEMA",
            "action": "QUARANTINED",
        }

    expected_version = SCHEMAS[schema_type]["version"]

    # --------------------------------------------------------
    # Exact approved columns
    # --------------------------------------------------------

    if (
        column_result["column_status"] == "PASS"
        and not column_result["order_changed"]
    ):

        return {
            "current_schema_version": expected_version,
            "detected_schema_version": expected_version,
            "schema_version_status": "CURRENT_SCHEMA",
            "action": "ACCEPT",
        }

    # --------------------------------------------------------
    # Same approved columns but order changed
    # --------------------------------------------------------

    if (
        column_result["column_status"] == "PASS"
        and column_result["order_changed"]
    ):

        return {
            "current_schema_version": expected_version,
            "detected_schema_version": expected_version,
            "schema_version_status": "CURRENT_SCHEMA",
            "action": "ACCEPT_WITH_ORDER_WARNING",
        }

    # --------------------------------------------------------
    # Missing/unexpected required structural fields
    # --------------------------------------------------------

    return {
        "current_schema_version": expected_version,
        "detected_schema_version": "UNKNOWN",
        "schema_version_status": "SCHEMA_CHANGE",
        "action": "QUARANTINED",
    }


# ============================================================
# SINGLE FILE VALIDATION
# ============================================================

def validate_file(file_path: Path) -> dict:
    """
    Perform Tracker 03.06 and Tracker 03.07 validation
    for one incoming CSV file.
    """

    result = {
        "file_name": file_path.name,
        "schema": "UNKNOWN",
        "file_hash": None,
        "column_status": "FAIL",
        "schema_version_status": "UNKNOWN_SCHEMA",
        "action": "QUARANTINED",
        "missing_columns": [],
        "unexpected_columns": [],
        "possible_renames": [],
        "order_changed": False,
        "schema_fingerprint": None,
    }

    # ========================================================
    # FILE HASH
    # ========================================================

    try:

        result["file_hash"] = calculate_file_hash(
            file_path
        )

    except Exception as error:

        logger.exception(
            "Unable to calculate file hash | file=%s | error=%s",
            file_path.name,
            error,
        )

        result["action"] = "QUARANTINED"

        return result

    # ========================================================
    # READ CSV
    # ========================================================

    try:

        df = pd.read_csv(file_path)

    except Exception as error:

        logger.exception(
            "CSV read failed | file=%s | error=%s",
            file_path.name,
            error,
        )

        result["action"] = "QUARANTINED"

        return result

    # ========================================================
    # DETECT SCHEMA TYPE
    # ========================================================

    schema_type = detect_schema_type(
        file_path.name
    )

    result["schema"] = schema_type

    if schema_type not in SCHEMAS:

        result["schema_version_status"] = (
            "UNKNOWN_SCHEMA"
        )

        result["action"] = "QUARANTINED"

        logger.warning(
            "Unknown schema | file=%s",
            file_path.name,
        )

        return result

    # ========================================================
    # TRACKER 03.06
    # ========================================================

    schema_definition = SCHEMAS[schema_type]

    required_columns = schema_definition[
        "required_columns"
    ]

    optional_columns = schema_definition[
        "optional_columns"
    ]

    column_result = validate_columns(
        incoming_columns=list(df.columns),
        required_columns=required_columns,
        optional_columns=optional_columns,
    )

    result.update(column_result)

    # ========================================================
    # SCHEMA FINGERPRINT
    # ========================================================

    result["schema_fingerprint"] = (
        calculate_schema_fingerprint(
            list(df.columns)
        )
    )

    # ========================================================
    # TRACKER 03.07
    # ========================================================

    version_result = validate_schema_version(
        schema_type,
        column_result,
    )

    result.update(version_result)

    # ========================================================
    # LOG RESULT
    # ========================================================

    if (
        result["schema_version_status"]
        == "CURRENT_SCHEMA"
    ):

        logger.info(
            "Schema validation passed | "
            "file=%s | schema=%s | version=%s | "
            "action=%s | hash=%s",
            file_path.name,
            schema_type,
            result["detected_schema_version"],
            result["action"],
            result["file_hash"],
        )

    else:

        logger.warning(
            "Schema validation failed | "
            "file=%s | schema=%s | status=%s | "
            "missing=%s | unexpected=%s | action=%s",
            file_path.name,
            schema_type,
            result["schema_version_status"],
            result["missing_columns"],
            result["unexpected_columns"],
            result["action"],
        )

    return result


# ============================================================
# VALIDATE ALL INCOMING FILES
# ============================================================

def validate_incoming_files(
    incoming_directory: str = "incoming",
) -> list[dict]:
    """
    Validate all CSV files in the incoming directory.
    """

    incoming_path = Path(incoming_directory)

    if not incoming_path.exists():

        logger.warning(
            "Incoming directory does not exist | path=%s",
            incoming_path,
        )

        return []

    csv_files = sorted(
        incoming_path.glob("*.csv")
    )

    if not csv_files:

        logger.warning(
            "No CSV files found in incoming directory | path=%s",
            incoming_path,
        )

        return []

    results = []

    for file_path in csv_files:

        results.append(
            validate_file(file_path)
        )

    return results


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    results: list[dict],
) -> None:
    """
    Print Tracker 03.06 + 03.07 validation results.
    """

    print()
    print("=" * 70)
    print(
        "TRACKER 03.06 + 03.07 - "
        "SCHEMA VALIDATION SUMMARY"
    )
    print("=" * 70)

    if not results:

        print(
            "No incoming CSV files found."
        )

        return

    for result in results:

        print()
        print("-" * 70)

        print(
            f"File: {result['file_name']}"
        )

        print(
            f"Schema: {result['schema']}"
        )

        print(
            "Current Schema Version: "
            f"{result.get('current_schema_version', 'UNKNOWN')}"
        )

        print(
            "Detected Schema Version: "
            f"{result.get('detected_schema_version', 'UNKNOWN')}"
        )

        print(
            "Schema Version Status: "
            f"{result.get('schema_version_status', 'UNKNOWN')}"
        )

        print(
            "Column Validation: "
            f"{result.get('column_status', 'FAIL')}"
        )

        print(
            "Action: "
            f"{result.get('action', 'QUARANTINED')}"
        )

        # ----------------------------------------------------
        # Missing columns
        # ----------------------------------------------------

        if result.get("missing_columns"):

            print("Missing Columns:")

            for column in result[
                "missing_columns"
            ]:

                print(
                    f"  - {column}"
                )

        # ----------------------------------------------------
        # Unexpected columns
        # ----------------------------------------------------

        if result.get(
            "unexpected_columns"
        ):

            print(
                "Unexpected Columns:"
            )

            for column in result[
                "unexpected_columns"
            ]:

                print(
                    f"  - {column}"
                )

        # ----------------------------------------------------
        # Possible renamed fields
        # ----------------------------------------------------

        if result.get(
            "possible_renames"
        ):

            print(
                "Possible Renamed Fields:"
            )

            for rename in result[
                "possible_renames"
            ]:

                print(
                    f"  - Expected: "
                    f"{rename['expected']} "
                    f"| Incoming: "
                    f"{rename['incoming']}"
                )

        # ----------------------------------------------------
        # Column order
        # ----------------------------------------------------

        if result.get(
            "order_changed"
        ):

            print(
                "Column Order: CHANGED "
                "(allowed; processing is name-based)"
            )

        # ----------------------------------------------------
        # Fingerprint
        # ----------------------------------------------------

        print(
            "Schema Fingerprint: "
            f"{result.get('schema_fingerprint')}"
        )

        # ----------------------------------------------------
        # Hash
        # ----------------------------------------------------

        print(
            "SHA-256: "
            f"{result.get('file_hash')}"
        )

    print()
    print("=" * 70)
    print(
        "Tracker 03.06 schema validation completed."
    )
    print(
        "Tracker 03.07 schema version validation completed."
    )
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print(
        "Starting Tracker 03.06 - Schema Validation"
    )
    print(
        "Starting Tracker 03.07 - Schema Version Validation"
    )
    print("=" * 70)

    results = validate_incoming_files(
        "incoming"
    )

    print_summary(results)

    print(
        "\nTracker 03.06 + 03.07 execution completed."
    )
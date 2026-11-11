from pathlib import Path
import csv
import re


# ============================================================
# TRACKER 04.01
# STANDARDIZE TEXT FIELDS
# ============================================================
#
# Requirement:
# Trim whitespace, normalize case, remove unwanted characters,
# and standardize business text without destroying valid values.
#
# Important:
# - Source files are NEVER modified.
# - IDs are only trimmed.
# - Controlled categorical values are normalized to the
#   approved canonical representation.
# - Free-text/business names are trimmed and spaces collapsed,
#   but their meaningful capitalization is preserved.
# - Unknown categorical values are NOT guessed or auto-corrected.
# - Emails are trimmed and lowercased.
# - Phone separators are removed only where safe.
# ============================================================


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT_ROOT / "incoming"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "standardized"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

AUDIT_FILE = (
    PROJECT_ROOT
    / "data"
    / "outputs"
    / "text_standardization_audit.csv"
)

AUDIT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# APPROVED CANONICAL VALUES
# ============================================================
#
# These are based on the project's approved categorical domains.
#
# Only known case/spacing variants are standardized.
# Unknown values are NOT guessed.
# ============================================================

APPROVED_VALUES = {

    "gender": {
        "male": "Male",
        "female": "Female",
        "other": "Other",
    },

    "customer_segment": {
        "occasional": "Occasional",
        "regular": "Regular",
        "premium": "Premium",
        "vip": "VIP",
    },

    "preferred_channel": {
        "store": "Store",
        "online": "Online",
    },

    "status": {
        "active": "Active",
        "inactive": "Inactive",
        "discontinued": "Discontinued",
        "suspended": "Suspended",
        "temporarily closed": "Temporarily Closed",
        "closed": "Closed",
        "planned": "Planned",
        "expired": "Expired",
        "cancelled": "Cancelled",
    },

    "category": {
        "electronics": "Electronics",
        "home & kitchen": "Home & Kitchen",
        "fashion": "Fashion",
        "beauty & personal care":
            "Beauty & Personal Care",
        "sports & fitness":
            "Sports & Fitness",
        "grocery": "Grocery",
    },

    "region": {
        "north": "North",
        "south": "South",
        "east": "East",
        "west": "West",
        "central": "Central",
    },

    "store_type": {
        "mall": "Mall",
        "high street": "High Street",
        "outlet": "Outlet",
        "neighborhood": "Neighborhood",
    },

    "role": {
        "sales associate":
            "Sales Associate",
        "senior sales associate":
            "Senior Sales Associate",
        "store supervisor":
            "Store Supervisor",
    },

    "promotion_type": {
        "seasonal": "Seasonal",
        "category": "Category",
        "storewide": "Storewide",
        "channel": "Channel",
    },

    "applicable_channel": {
        "store": "Store",
        "online": "Online",
        "all": "ALL",
    },

    "sales_channel": {
        "store": "Store",
        "online": "Online",
    },

    "payment_method": {
        "cash": "Cash",
        "card": "Card",
        "upi": "UPI",
        "wallet": "Wallet",
        "net banking": "Net Banking",
    },

    "order_status": {
        "completed": "Completed",
        "cancelled": "Cancelled",
    },

    "return_reason": {
        "damaged": "Damaged",
        "wrong product": "Wrong Product",
        "quality issue": "Quality Issue",
        "size/fit issue": "Size/Fit Issue",
        "customer changed mind":
            "Customer Changed Mind",
        "late delivery": "Late Delivery",
        "other": "Other",
    },

    "return_status": {
        "requested": "Requested",
        "approved": "Approved",
        "rejected": "Rejected",
        "refunded": "Refunded",
    },

    "refund_method": {
        "original payment":
            "Original Payment",
        "store credit":
            "Store Credit",
        "cash": "Cash",
    },
}


# ============================================================
# FIELD GROUPS
# ============================================================

ID_FIELDS = {
    "customer_id",
    "product_id",
    "store_id",
    "salesperson_id",
    "promotion_id",
    "sales_line_id",
    "order_id",
    "return_id",
    "target_id",
    "postal_code",
}


EMAIL_FIELDS = {
    "email",
}


PHONE_FIELDS = {
    "phone",
}


GEOGRAPHIC_FIELDS = {
    "city",
    "state",
    "region",
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_basic_text(value):
    """
    Trim leading/trailing whitespace and collapse
    repeated whitespace to a single space.
    """

    if value is None:
        return ""

    value = str(value)

    value = value.strip()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value


def standardize_controlled_value(
    field_name,
    value
):
    """
    Standardize only approved categorical values.

    Unknown values are retained after basic whitespace
    normalization. They are NOT guessed or replaced.
    """

    cleaned = clean_basic_text(value)

    if cleaned == "":
        return cleaned

    mapping = APPROVED_VALUES.get(
        field_name
    )

    if mapping is None:
        return cleaned

    lookup_key = cleaned.casefold()

    if lookup_key in mapping:

        return mapping[lookup_key]

    # Unknown value:
    # retain it for later validation.
    return cleaned


def standardize_email(value):

    cleaned = clean_basic_text(value)

    if cleaned == "":
        return cleaned

    return cleaned.lower()


def standardize_phone(value):

    cleaned = clean_basic_text(value)

    if cleaned == "":
        return cleaned

    # Remove common formatting separators.
    normalized = re.sub(
        r"[\s().-]",
        "",
        cleaned
    )

    # Normalize an unambiguous Indian +91 prefix.
    if normalized.startswith("+91"):

        normalized = normalized[3:]

    elif normalized.startswith("0091"):

        normalized = normalized[4:]

    return normalized


def standardize_id(value):

    # IDs must only be trimmed.
    # Do NOT change case or business-key characters.
    return clean_basic_text(value)


def standardize_geographic_value(
    field_name,
    value
):

    cleaned = clean_basic_text(value)

    if cleaned == "":
        return cleaned

    if field_name == "region":

        return standardize_controlled_value(
            field_name,
            cleaned
        )

    # City/state are normalized conservatively.
    # We preserve meaningful text instead of applying
    # aggressive title-casing that could alter valid names.
    return cleaned


def standardize_field(
    field_name,
    value
):

    field_name = field_name.strip().lower()

    # IDs
    if field_name in ID_FIELDS:

        return standardize_id(value)

    # Email
    if field_name in EMAIL_FIELDS:

        return standardize_email(value)

    # Phone
    if field_name in PHONE_FIELDS:

        return standardize_phone(value)

    # Geographic fields
    if field_name in GEOGRAPHIC_FIELDS:

        return standardize_geographic_value(
            field_name,
            value
        )

    # Controlled categorical fields
    if field_name in APPROVED_VALUES:

        return standardize_controlled_value(
            field_name,
            value
        )

    # General business text:
    # trim and collapse spaces, but preserve meaningful
    # capitalization such as product/brand names.
    return clean_basic_text(value)


# ============================================================
# DISCOVER INPUT FILES
# ============================================================

def discover_input_files():

    if not INPUT_DIR.exists():

        return []

    return sorted(
        [
            file
            for file in INPUT_DIR.glob("*.csv")
            if file.is_file()
        ],
        key=lambda path: path.name.lower()
    )


# ============================================================
# STANDARDIZE ONE FILE
# ============================================================

def standardize_file(
    input_file
):

    output_file = (
        OUTPUT_DIR
        / input_file.name
    )

    audit_rows = []

    rows_read = 0
    cells_standardized = 0

    with open(
        input_file,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as source:

        reader = csv.DictReader(source)

        if reader.fieldnames is None:

            raise ValueError(
                "File does not contain a valid header."
            )

        fieldnames = reader.fieldnames

        with open(
            output_file,
            "w",
            encoding="utf-8",
            newline=""
        ) as target:

            writer = csv.DictWriter(
                target,
                fieldnames=fieldnames
            )

            writer.writeheader()

            for row_number, row in enumerate(
                reader,
                start=2
            ):

                rows_read += 1

                standardized_row = {}

                for field_name in fieldnames:

                    original_value = row.get(
                        field_name,
                        ""
                    )

                    standardized_value = (
                        standardize_field(
                            field_name,
                            original_value
                        )
                    )

                    standardized_row[
                        field_name
                    ] = standardized_value

                    if (
                        str(original_value)
                        != str(standardized_value)
                    ):

                        cells_standardized += 1

                        audit_rows.append(
                            {
                                "file_name":
                                    input_file.name,

                                "row_number":
                                    row_number,

                                "field_name":
                                    field_name,

                                "original_value":
                                    original_value,

                                "standardized_value":
                                    standardized_value,

                                "standardization_type":
                                    determine_standardization_type(
                                        field_name
                                    )
                            }
                        )

                writer.writerow(
                    standardized_row
                )

    return (
        rows_read,
        cells_standardized,
        audit_rows
    )


# ============================================================
# STANDARDIZATION TYPE
# ============================================================

def determine_standardization_type(
    field_name
):

    field_name = (
        field_name.strip().lower()
    )

    if field_name in ID_FIELDS:

        return "TRIM_ID"

    if field_name in EMAIL_FIELDS:

        return "TRIM_LOWERCASE_EMAIL"

    if field_name in PHONE_FIELDS:

        return "PHONE_FORMAT_NORMALIZATION"

    if field_name in GEOGRAPHIC_FIELDS:

        return "GEOGRAPHIC_TEXT_STANDARDIZATION"

    if field_name in APPROVED_VALUES:

        return "CANONICAL_CATEGORICAL_VALUE"

    return "TRIM_COLLAPSE_WHITESPACE"


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print(
        "TRACKER 04.01 - STANDARDIZE TEXT FIELDS"
    )
    print("=" * 80)

    print(
        f"\nInput directory:"
    )

    print(
        INPUT_DIR
    )

    print(
        f"\nOutput directory:"
    )

    print(
        OUTPUT_DIR
    )

    # --------------------------------------------------------
    # DISCOVER FILES
    # --------------------------------------------------------

    input_files = discover_input_files()

    print(
        f"\nInput CSV files found: "
        f"{len(input_files)}"
    )

    if not input_files:

        print(
            "\nERROR: No CSV files found "
            "in the incoming directory."
        )

        return

    # --------------------------------------------------------
    # PROCESS FILES
    # --------------------------------------------------------

    all_audit_rows = []

    total_rows = 0
    total_cells_standardized = 0

    successful_files = 0
    failed_files = 0

    for input_file in input_files:

        print(
            f"\nProcessing: "
            f"{input_file.name}"
        )

        try:

            (
                rows_read,
                cells_standardized,
                audit_rows
            ) = standardize_file(
                input_file
            )

            total_rows += rows_read

            total_cells_standardized += (
                cells_standardized
            )

            all_audit_rows.extend(
                audit_rows
            )

            successful_files += 1

            print(
                f"Rows processed: "
                f"{rows_read}"
            )

            print(
                f"Cells standardized: "
                f"{cells_standardized}"
            )

            print(
                "Status: PASS"
            )

        except Exception as error:

            failed_files += 1

            print(
                f"Status: FAIL - "
                f"{type(error).__name__}: "
                f"{error}"
            )

    # --------------------------------------------------------
    # WRITE AUDIT LOG
    # --------------------------------------------------------

    audit_fieldnames = [
        "file_name",
        "row_number",
        "field_name",
        "original_value",
        "standardized_value",
        "standardization_type"
    ]

    with open(
        AUDIT_FILE,
        "w",
        encoding="utf-8",
        newline=""
    ) as audit_file:

        writer = csv.DictWriter(
            audit_file,
            fieldnames=audit_fieldnames
        )

        writer.writeheader()

        writer.writerows(
            all_audit_rows
        )

    # --------------------------------------------------------
    # OVERALL RESULT
    # --------------------------------------------------------

    if (
        successful_files > 0
        and failed_files == 0
    ):

        overall_status = "PASS"

    else:

        overall_status = "FAIL"

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print(
        "\n" + "=" * 80
    )

    print(
        "04.01 STANDARDIZATION RESULTS"
    )

    print(
        "=" * 80
    )

    print(
        f"\nFiles processed       : "
        f"{len(input_files)}"
    )

    print(
        f"Successful files      : "
        f"{successful_files}"
    )

    print(
        f"Failed files          : "
        f"{failed_files}"
    )

    print(
        f"Total rows processed  : "
        f"{total_rows}"
    )

    print(
        f"Cells standardized    : "
        f"{total_cells_standardized}"
    )

    print(
        f"Audit records         : "
        f"{len(all_audit_rows)}"
    )

    print(
        f"\nOutput directory:"
    )

    print(
        OUTPUT_DIR
    )

    print(
        f"\nAudit file:"
    )

    print(
        AUDIT_FILE
    )

    print(
        f"\n04.01 OVERALL RESULT  : "
        f"{overall_status}"
    )

    print(
        "\n" + "=" * 80
    )

    if overall_status == "PASS":

        print(
            "Tracker 04.01 text standardization "
            "completed successfully."
        )

    else:

        print(
            "Tracker 04.01 requires investigation."
        )

    print(
        "=" * 80
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
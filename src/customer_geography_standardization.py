from pathlib import Path
import csv
from collections import defaultdict


# ============================================================
# TRACKER 04.02
# STANDARDIZE CUSTOMER GEOGRAPHY
# ============================================================
#
# Requirement:
# Normalize city/state/region values and correct approved
# spelling/case inconsistencies.
#
# Rules:
# - Original incoming/source files are never modified.
# - Geography is standardized using the project's clean
#   customer master as the approved reference.
# - Matching is based on the city + state + region combination.
# - Case and whitespace differences are corrected.
# - Approved canonical values from the reference are preserved.
# - No fuzzy guessing or invented geography values.
# - Incompatible geography combinations are flagged for review.
# ============================================================


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

STANDARDIZED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "standardized"
)

REFERENCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "customers_master.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "geography_standardized"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

AUDIT_FILE = (
    PROJECT_ROOT
    / "data"
    / "outputs"
    / "04.02_customer_geography_audit.csv"
)

AUDIT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# APPROVED REGIONS
# ============================================================

APPROVED_REGIONS = {
    "north": "North",
    "south": "South",
    "east": "East",
    "west": "West",
    "central": "Central",
}


# ============================================================
# NORMALIZATION HELPERS
# ============================================================

def normalize_key(value):
    """
    Normalize only for comparison.

    This does not modify the actual source value.
    """

    if value is None:
        return ""

    value = str(value).strip()

    value = " ".join(
        value.split()
    )

    return value.casefold()


def clean_value(value):
    """
    Remove surrounding whitespace and collapse repeated
    whitespace while preserving the original meaningful
    capitalization.
    """

    if value is None:
        return ""

    value = str(value).strip()

    value = " ".join(
        value.split()
    )

    return value


# ============================================================
# REGION STANDARDIZATION
# ============================================================

def standardize_region(value):

    cleaned = clean_value(value)

    if not cleaned:
        return ""

    key = normalize_key(cleaned)

    if key in APPROVED_REGIONS:
        return APPROVED_REGIONS[key]

    return cleaned


# ============================================================
# LOAD CLEAN CUSTOMER GEOGRAPHY REFERENCE
# ============================================================

def load_geography_reference():

    if not REFERENCE_FILE.exists():

        raise FileNotFoundError(
            "Clean customer geography reference not found:\n"
            f"{REFERENCE_FILE}"
        )

    # --------------------------------------------------------
    # Maps normalized geography to canonical geography.
    # --------------------------------------------------------

    exact_mapping = {}

    city_state_mapping = defaultdict(set)

    state_region_mapping = defaultdict(set)

    with open(
        REFERENCE_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if reader.fieldnames is None:

            raise ValueError(
                "Reference file does not contain a valid header."
            )

        required_fields = {
            "city",
            "state",
            "region",
        }

        missing_fields = (
            required_fields
            - set(reader.fieldnames)
        )

        if missing_fields:

            raise ValueError(
                "Reference file is missing required geography "
                f"fields: {sorted(missing_fields)}"
            )

        for row in reader:

            city = clean_value(
                row.get("city", "")
            )

            state = clean_value(
                row.get("state", "")
            )

            region = clean_value(
                row.get("region", "")
            )

            if not city or not state or not region:
                continue

            # Canonical region from approved project domain.
            canonical_region = (
                standardize_region(region)
            )

            city_key = normalize_key(city)
            state_key = normalize_key(state)
            region_key = normalize_key(
                canonical_region
            )

            exact_key = (
                city_key,
                state_key,
                region_key
            )

            canonical_tuple = (
                city,
                state,
                canonical_region
            )

            exact_mapping[exact_key] = (
                canonical_tuple
            )

            city_state_key = (
                city_key,
                state_key
            )

            city_state_mapping[
                city_state_key
            ].add(
                canonical_tuple
            )

            state_region_mapping[
                state_key
            ].add(
                canonical_region
            )

    return (
        exact_mapping,
        city_state_mapping,
        state_region_mapping
    )


# ============================================================
# STANDARDIZE ONE CUSTOMER GEOGRAPHY RECORD
# ============================================================

def standardize_geography(
    city,
    state,
    region,
    exact_mapping,
    city_state_mapping,
    state_region_mapping
):

    original_city = city
    original_state = state
    original_region = region

    city_clean = clean_value(city)
    state_clean = clean_value(state)

    region_clean = standardize_region(
        region
    )

    city_key = normalize_key(
        city_clean
    )

    state_key = normalize_key(
        state_clean
    )

    region_key = normalize_key(
        region_clean
    )

    # --------------------------------------------------------
    # Case 1:
    # Exact city + state + region combination exists.
    #
    # This is the primary approved mapping.
    # --------------------------------------------------------

    exact_key = (
        city_key,
        state_key,
        region_key
    )

    if exact_key in exact_mapping:

        (
            canonical_city,
            canonical_state,
            canonical_region
        ) = exact_mapping[exact_key]

        changed = (
            city_clean != canonical_city
            or state_clean != canonical_state
            or region_clean != canonical_region
        )

        if changed:

            return (
                canonical_city,
                canonical_state,
                canonical_region,
                "STANDARDIZED",
                "Matched approved city/state/region mapping; canonical spelling/case applied."
            )

        return (
            canonical_city,
            canonical_state,
            canonical_region,
            "UNCHANGED",
            "Already matches approved city/state/region mapping."
        )

    # --------------------------------------------------------
    # Case 2:
    # City + state is recognized uniquely.
    #
    # If region is only a case/spacing variation, use the
    # canonical region.
    # --------------------------------------------------------

    city_state_key = (
        city_key,
        state_key
    )

    city_state_matches = (
        city_state_mapping.get(
            city_state_key,
            set()
        )
    )

    if len(city_state_matches) == 1:

        (
            canonical_city,
            canonical_state,
            canonical_region
        ) = next(
            iter(city_state_matches)
        )

        if (
            not region_key
            or region_key
            == normalize_key(
                canonical_region
            )
        ):

            return (
                canonical_city,
                canonical_state,
                canonical_region,
                "STANDARDIZED",
                "Matched approved city/state mapping and standardized region."
            )

        # Region conflicts with approved mapping.
        return (
            city_clean,
            state_clean,
            region_clean,
            "REVIEW",
            "City/state recognized, but supplied region conflicts with approved mapping."
        )

    # --------------------------------------------------------
    # Case 3:
    # State is recognized and region can be safely
    # standardized, but city cannot be uniquely resolved.
    # --------------------------------------------------------

    state_regions = (
        state_region_mapping.get(
            state_key,
            set()
        )
    )

    if len(state_regions) == 1:

        canonical_region = next(
            iter(state_regions)
        )

        if (
            not region_key
            or region_key
            == normalize_key(
                canonical_region
            )
        ):

            return (
                city_clean,
                state_clean,
                canonical_region,
                "REVIEW",
                "State/region recognized, but city could not be uniquely matched."
            )

    # --------------------------------------------------------
    # Case 4:
    # No approved mapping.
    #
    # Do not invent a correction.
    # --------------------------------------------------------

    return (
        city_clean,
        state_clean,
        region_clean,
        "UNRESOLVED",
        "No approved city/state/region mapping found."
    )


# ============================================================
# FIND STANDARDIZED CUSTOMER FILE
# ============================================================

def find_customer_file():

    expected_file = (
        STANDARDIZED_DIR
        / "customers_master.csv"
    )

    if expected_file.exists():

        return expected_file

    candidates = sorted(
        STANDARDIZED_DIR.glob(
            "*customer*.csv"
        ),
        key=lambda path: path.name.lower()
    )

    if candidates:

        return candidates[0]

    return None


# ============================================================
# PROCESS CUSTOMER FILE
# ============================================================

def process_customer_file(
    input_file,
    exact_mapping,
    city_state_mapping,
    state_region_mapping
):

    output_file = (
        OUTPUT_DIR
        / input_file.name
    )

    audit_rows = []

    rows_read = 0
    rows_standardized = 0
    rows_unchanged = 0
    rows_review = 0
    rows_unresolved = 0

    with open(
        input_file,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as source:

        reader = csv.DictReader(
            source
        )

        if reader.fieldnames is None:

            raise ValueError(
                "Customer file does not contain a valid header."
            )

        required_fields = {
            "city",
            "state",
            "region",
        }

        missing_fields = (
            required_fields
            - set(reader.fieldnames)
        )

        if missing_fields:

            raise ValueError(
                "Customer file is missing geography fields: "
                f"{sorted(missing_fields)}"
            )

        with open(
            output_file,
            "w",
            encoding="utf-8",
            newline=""
        ) as target:

            writer = csv.DictWriter(
                target,
                fieldnames=reader.fieldnames
            )

            writer.writeheader()

            for row_number, row in enumerate(
                reader,
                start=2
            ):

                rows_read += 1

                original_city = row.get(
                    "city",
                    ""
                )

                original_state = row.get(
                    "state",
                    ""
                )

                original_region = row.get(
                    "region",
                    ""
                )

                (
                    standardized_city,
                    standardized_state,
                    standardized_region,
                    status,
                    reason
                ) = standardize_geography(
                    original_city,
                    original_state,
                    original_region,
                    exact_mapping,
                    city_state_mapping,
                    state_region_mapping
                )

                row["city"] = (
                    standardized_city
                )

                row["state"] = (
                    standardized_state
                )

                row["region"] = (
                    standardized_region
                )

                writer.writerow(row)

                # ------------------------------------------------
                # Counters
                # ------------------------------------------------

                if status == "STANDARDIZED":

                    rows_standardized += 1

                elif status == "UNCHANGED":

                    rows_unchanged += 1

                elif status == "REVIEW":

                    rows_review += 1

                elif status == "UNRESOLVED":

                    rows_unresolved += 1

                # ------------------------------------------------
                # Audit only when something changed or requires
                # investigation.
                # ------------------------------------------------

                if (
                    status != "UNCHANGED"
                ):

                    audit_rows.append(
                        {
                            "file_name":
                                input_file.name,

                            "row_number":
                                row_number,

                            "original_city":
                                original_city,

                            "standardized_city":
                                standardized_city,

                            "original_state":
                                original_state,

                            "standardized_state":
                                standardized_state,

                            "original_region":
                                original_region,

                            "standardized_region":
                                standardized_region,

                            "status":
                                status,

                            "reason":
                                reason
                        }
                    )

    return (
        output_file,
        rows_read,
        rows_standardized,
        rows_unchanged,
        rows_review,
        rows_unresolved,
        audit_rows
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print(
        "TRACKER 04.02 - STANDARDIZE CUSTOMER GEOGRAPHY"
    )
    print("=" * 80)

    print(
        "\nStandardized input:"
    )

    print(
        STANDARDIZED_DIR
    )

    print(
        "\nApproved geography reference:"
    )

    print(
        REFERENCE_FILE
    )

    print(
        "\nOutput directory:"
    )

    print(
        OUTPUT_DIR
    )

    # --------------------------------------------------------
    # FIND INPUT
    # --------------------------------------------------------

    input_file = find_customer_file()

    if input_file is None:

        print(
            "\nERROR: Standardized customer file not found."
        )

        print(
            "\nExpected:"
        )

        print(
            STANDARDIZED_DIR
            / "customers_master.csv"
        )

        return

    print(
        "\nCustomer input file:"
    )

    print(
        input_file
    )

    # --------------------------------------------------------
    # LOAD REFERENCE
    # --------------------------------------------------------

    try:

        (
            exact_mapping,
            city_state_mapping,
            state_region_mapping
        ) = load_geography_reference()

    except Exception as error:

        print(
            "\nERROR loading geography reference:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return

    print(
        "\nApproved exact geography mappings:"
        f" {len(exact_mapping)}"
    )

    print(
        "Approved city/state mappings:"
        f" {len(city_state_mapping)}"
    )

    print(
        "Approved state mappings:"
        f" {len(state_region_mapping)}"
    )

    # --------------------------------------------------------
    # PROCESS
    # --------------------------------------------------------

    try:

        (
            output_file,
            rows_read,
            rows_standardized,
            rows_unchanged,
            rows_review,
            rows_unresolved,
            audit_rows
        ) = process_customer_file(
            input_file,
            exact_mapping,
            city_state_mapping,
            state_region_mapping
        )

    except Exception as error:

        print(
            "\nERROR processing customer geography:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return

    # --------------------------------------------------------
    # WRITE AUDIT
    # --------------------------------------------------------

    audit_fields = [
        "file_name",
        "row_number",
        "original_city",
        "standardized_city",
        "original_state",
        "standardized_state",
        "original_region",
        "standardized_region",
        "status",
        "reason"
    ]

    with open(
        AUDIT_FILE,
        "w",
        encoding="utf-8",
        newline=""
    ) as audit_file:

        writer = csv.DictWriter(
            audit_file,
            fieldnames=audit_fields
        )

        writer.writeheader()

        writer.writerows(
            audit_rows
        )

    # --------------------------------------------------------
    # TECHNICAL EXECUTION STATUS
    # --------------------------------------------------------

    execution_status = "PASS"

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print(
        "\n" + "=" * 80
    )

    print(
        "04.02 CUSTOMER GEOGRAPHY RESULTS"
    )

    print(
        "=" * 80
    )

    print(
        f"\nRows processed        : "
        f"{rows_read}"
    )

    print(
        f"Rows standardized     : "
        f"{rows_standardized}"
    )

    print(
        f"Rows already correct  : "
        f"{rows_unchanged}"
    )

    print(
        f"Rows requiring review : "
        f"{rows_review}"
    )

    print(
        f"Rows unresolved       : "
        f"{rows_unresolved}"
    )

    print(
        "\nOutput file:"
    )

    print(
        output_file
    )

    print(
        "\nAudit file:"
    )

    print(
        AUDIT_FILE
    )

    print(
        f"\n04.02 OVERALL RESULT  : "
        f"{execution_status}"
    )

    print(
        "\n" + "=" * 80
    )

    print(
        "Tracker 04.02 customer geography "
        "standardization processing completed."
    )

    if rows_review > 0:

        print(
            f"NOTE: {rows_review} row(s) require review."
        )

    if rows_unresolved > 0:

        print(
            f"NOTE: {rows_unresolved} row(s) are unresolved."
        )

    print(
        "=" * 80
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
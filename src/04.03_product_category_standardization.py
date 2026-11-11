# ============================================================
# TRACKER 04.03
# STANDARDIZE PRODUCT CATEGORIES
# ============================================================
#
# Requirement:
# Normalize category, subcategory, and brand values using
# mapping rules.
#
# Source:
# Project product master generation rules.
#
# Important:
# - Incoming source file is never modified.
# - Only whitespace/case/business spelling variations are
#   standardized.
# - Valid existing business values are preserved.
# - No new categories/subcategories/brands are invented.
# ============================================================

from pathlib import Path
import pandas as pd
import re


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "incoming"
    / "products_master.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "products_master_standardized.csv"
)

AUDIT_FILE = (
    OUTPUT_DIR
    / "04_03_product_category_standardization_audit.csv"
)


# ============================================================
# ACTUAL PRODUCT GENERATOR BUSINESS RULES
# ============================================================

PRODUCT_CATALOG = {

    "Electronics": {
        "subcategories": {
            "mobile": "Mobile",
            "laptop": "Laptop",
            "headphones": "Headphones",
            "smart tv": "Smart TV",
            "smart watch": "Smart Watch",
        },

        "brands": {
            "samsung": "Samsung",
            "apple": "Apple",
            "sony": "Sony",
            "lg": "LG",
            "oneplus": "OnePlus",
        },
    },

    "Grocery": {
        "subcategories": {
            "rice": "Rice",
            "wheat flour": "Wheat Flour",
            "cooking oil": "Cooking Oil",
            "sugar": "Sugar",
            "tea": "Tea",
        },

        "brands": {
            "aashirvaad": "Aashirvaad",
            "fortune": "Fortune",
            "tata": "Tata",
            "india gate": "India Gate",
            "organic india": "Organic India",
        },
    },

    "Fashion": {
        "subcategories": {
            "shirt": "Shirt",
            "jeans": "Jeans",
            "shoes": "Shoes",
            "kurti": "Kurti",
            "jacket": "Jacket",
        },

        "brands": {
            "nike": "Nike",
            "adidas": "Adidas",
            "levis": "Levis",
            "levi's": "Levis",
            "puma": "Puma",
            "allen solly": "Allen Solly",
        },
    },

    "Home & Kitchen": {
        "subcategories": {
            "mixer": "Mixer",
            "cookware": "Cookware",
            "sofa": "Sofa",
            "dining table": "Dining Table",
            "curtains": "Curtains",
        },

        "brands": {
            "prestige": "Prestige",
            "philips": "Philips",
            "ikea": "IKEA",
            "milton": "Milton",
            "cello": "Cello",
        },
    },

    "Beauty & Personal Care": {
        "subcategories": {
            "shampoo": "Shampoo",
            "soap": "Soap",
            "face wash": "Face Wash",
            "perfume": "Perfume",
            "moisturizer": "Moisturizer",
        },

        "brands": {
            "dove": "Dove",
            "nivea": "Nivea",
            "lakme": "Lakme",
            "l'oreal": "L'Oreal",
            "loreal": "L'Oreal",
            "himalaya": "Himalaya",
        },
    },
}


# ============================================================
# NORMALIZATION FUNCTION
# ============================================================

def normalize_key(value):
    """
    Creates a comparison key without changing the business value.
    """

    if pd.isna(value):
        return ""

    value = str(value)

    # Remove tabs/newlines
    value = re.sub(
        r"[\r\n\t]+",
        " ",
        value
    )

    # Collapse repeated whitespace
    value = re.sub(
        r"\s+",
        " ",
        value
    )

    # Trim whitespace
    value = value.strip()

    # Case-insensitive comparison
    return value.casefold()


# ============================================================
# STANDARDIZE CATEGORY
# ============================================================

def standardize_category(value):

    if pd.isna(value):
        return "", "MISSING"

    original = str(value)

    key = normalize_key(original)

    category_lookup = {
        normalize_key(category): category
        for category in PRODUCT_CATALOG
    }

    if key in category_lookup:

        standardized = category_lookup[key]

        if original == standardized:
            return standardized, "UNCHANGED"

        return standardized, "STANDARDIZED"

    return original.strip(), "REVIEW"


# ============================================================
# STANDARDIZE SUBCATEGORY
# ============================================================

def standardize_subcategory(
    category,
    value
):

    if pd.isna(value):
        return "", "MISSING"

    original = str(value)

    if category not in PRODUCT_CATALOG:
        return original.strip(), "REVIEW"

    lookup = PRODUCT_CATALOG[
        category
    ]["subcategories"]

    key = normalize_key(original)

    if key in lookup:

        standardized = lookup[key]

        if original == standardized:
            return standardized, "UNCHANGED"

        return standardized, "STANDARDIZED"

    return original.strip(), "REVIEW"


# ============================================================
# STANDARDIZE BRAND
# ============================================================

def standardize_brand(
    category,
    value
):

    if pd.isna(value):
        return "", "MISSING"

    original = str(value)

    if category not in PRODUCT_CATALOG:
        return original.strip(), "REVIEW"

    lookup = PRODUCT_CATALOG[
        category
    ]["brands"]

    key = normalize_key(original)

    if key in lookup:

        standardized = lookup[key]

        if original == standardized:
            return standardized, "UNCHANGED"

        return standardized, "STANDARDIZED"

    # Do not invent a brand.
    return original.strip(), "REVIEW"


# ============================================================
# VALIDATE CATEGORY / SUBCATEGORY
# ============================================================

def validate_category_subcategory(
    category,
    subcategory
):

    if not category or not subcategory:
        return "REVIEW"

    if category not in PRODUCT_CATALOG:
        return "REVIEW"

    approved_subcategories = (
        PRODUCT_CATALOG[
            category
        ]["subcategories"]
        .values()
    )

    if subcategory in approved_subcategories:
        return "VALID"

    return "REVIEW"


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print(
        "TRACKER 04.03 - PRODUCT CATEGORY STANDARDIZATION"
    )
    print("=" * 80)

    # --------------------------------------------------------
    # CHECK INPUT
    # --------------------------------------------------------

    if not INPUT_FILE.exists():

        print()
        print("ERROR: Input file not found:")
        print(INPUT_FILE)
        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # READ SOURCE
    # --------------------------------------------------------

    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig"
    )

    print()
    print(
        f"Input file: {INPUT_FILE}"
    )

    print(
        f"Rows read: {len(df):,}"
    )

    print(
        f"Columns: {len(df.columns)}"
    )

    # --------------------------------------------------------
    # REQUIRED COLUMNS
    # --------------------------------------------------------

    required_columns = {
        "category",
        "subcategory",
        "brand"
    }

    missing_columns = (
        required_columns
        - set(df.columns)
    )

    if missing_columns:

        print()
        print(
            "ERROR: Missing required columns:"
        )

        for column in sorted(
            missing_columns
        ):
            print(
                f"  - {column}"
            )

        return

    # --------------------------------------------------------
    # PRESERVE ORIGINAL VALUES
    # --------------------------------------------------------

    df[
        "category_original"
    ] = df["category"]

    df[
        "subcategory_original"
    ] = df["subcategory"]

    df[
        "brand_original"
    ] = df["brand"]

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    category_results = []

    for value in df["category"]:

        category_results.append(
            standardize_category(
                value
            )
        )

    df["category"], df[
        "category_action"
    ] = zip(
        *category_results
    )

    # --------------------------------------------------------
    # SUBCATEGORY
    # --------------------------------------------------------

    subcategory_results = []

    for _, row in df.iterrows():

        subcategory_results.append(
            standardize_subcategory(
                row["category"],
                row["subcategory"]
            )
        )

    df["subcategory"], df[
        "subcategory_action"
    ] = zip(
        *subcategory_results
    )

    # --------------------------------------------------------
    # BRAND
    # --------------------------------------------------------

    brand_results = []

    for _, row in df.iterrows():

        brand_results.append(
            standardize_brand(
                row["category"],
                row["brand"]
            )
        )

    df["brand"], df[
        "brand_action"
    ] = zip(
        *brand_results
    )

    # --------------------------------------------------------
    # CATEGORY / SUBCATEGORY VALIDATION
    # --------------------------------------------------------

    df[
        "category_subcategory_validation"
    ] = df.apply(
        lambda row:
        validate_category_subcategory(
            row["category"],
            row["subcategory"]
        ),
        axis=1
    )

    # --------------------------------------------------------
    # REVIEW FLAG
    # --------------------------------------------------------

    df[
        "standardization_review_required"
    ] = (
        (df["category_action"] == "REVIEW")
        |
        (df["subcategory_action"] == "REVIEW")
        |
        (df["brand_action"] == "REVIEW")
        |
        (
            df[
                "category_subcategory_validation"
            ] == "REVIEW"
        )
    )

    # --------------------------------------------------------
    # AUDIT FILE
    # --------------------------------------------------------

    audit_columns = [
        "product_id",
        "category_original",
        "category",
        "category_action",
        "subcategory_original",
        "subcategory",
        "subcategory_action",
        "brand_original",
        "brand",
        "brand_action",
        "category_subcategory_validation",
        "standardization_review_required",
    ]

    audit_columns = [
        column
        for column in audit_columns
        if column in df.columns
    ]

    audit_df = df[
        audit_columns
    ].copy()

    # --------------------------------------------------------
    # SAVE OUTPUT
    # --------------------------------------------------------

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    audit_df.to_csv(
        AUDIT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # COUNTS
    # --------------------------------------------------------

    category_standardized = (
        df["category_action"]
        == "STANDARDIZED"
    ).sum()

    category_review = (
        df["category_action"]
        == "REVIEW"
    ).sum()

    subcategory_standardized = (
        df["subcategory_action"]
        == "STANDARDIZED"
    ).sum()

    subcategory_review = (
        df["subcategory_action"]
        == "REVIEW"
    ).sum()

    brand_standardized = (
        df["brand_action"]
        == "STANDARDIZED"
    ).sum()

    brand_review = (
        df["brand_action"]
        == "REVIEW"
    ).sum()

    compatibility_review = (
        df[
            "category_subcategory_validation"
        ]
        == "REVIEW"
    ).sum()

    rows_review = (
        df[
            "standardization_review_required"
        ]
    ).sum()

    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    print()
    print("-" * 80)
    print(
        "STANDARDIZATION SUMMARY"
    )
    print("-" * 80)

    print(
        f"Total rows processed        : "
        f"{len(df):,}"
    )

    print(
        f"Categories standardized     : "
        f"{category_standardized:,}"
    )

    print(
        f"Categories requiring review : "
        f"{category_review:,}"
    )

    print(
        f"Subcategories standardized  : "
        f"{subcategory_standardized:,}"
    )

    print(
        f"Subcategories requiring review: "
        f"{subcategory_review:,}"
    )

    print(
        f"Brands standardized         : "
        f"{brand_standardized:,}"
    )

    print(
        f"Brands requiring review     : "
        f"{brand_review:,}"
    )

    print(
        f"Category/subcategory review : "
        f"{compatibility_review:,}"
    )

    print(
        f"Rows requiring review       : "
        f"{rows_review:,}"
    )

    print()
    print(
        "Standardized output:"
    )

    print(
        OUTPUT_FILE
    )

    print()
    print(
        "Audit output:"
    )

    print(
        AUDIT_FILE
    )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    print()
    print("=" * 80)

    if rows_review == 0:

        print(
            "04.03 OVERALL RESULT : PASS"
        )

        print()
        print(
            "Tracker 04.03 product category "
            "standardization completed successfully."
        )

    else:

        print(
            "04.03 OVERALL RESULT : REVIEW"
        )

        print()
        print(
            "Tracker 04.03 processing completed "
            "with review flags."
        )

    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
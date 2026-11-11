# ============================================================
# Retail Sales Analytics
# Tracker 02.06 - Promotions Master Generator
# Complete Replacement Version
# ============================================================

import random
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = PROJECT_ROOT / "data" / "synthetic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "promotions_master.csv"


# ============================================================
# 2. REPRODUCIBILITY
# ============================================================

SEED = 42

random.seed(SEED)
np.random.seed(SEED)


# ============================================================
# 3. PROMOTION RULES
# ============================================================

NUM_PROMOTIONS = 72

PROMOTION_TYPES = [
    "Seasonal",
    "Category",
    "Storewide",
    "Channel",
]

PROMOTION_TYPE_PROBABILITIES = [
    0.35,
    0.30,
    0.20,
    0.15,
]

CATEGORIES = [
    "Electronics",
    "Home & Kitchen",
    "Fashion",
    "Beauty & Personal Care",
    "Sports & Fitness",
    "Grocery",
]

CHANNELS = [
    "Store",
    "Online",
    "ALL",
]

PROMOTION_STATUSES = [
    "Planned",
    "Active",
    "Expired",
    "Cancelled",
]


# ============================================================
# 4. PROMOTION NAME POOLS
# ============================================================

SEASONAL_NAMES = [
    "Festive Sale",
    "Diwali Celebration",
    "New Year Sale",
    "Summer Sale",
    "Monsoon Sale",
    "Winter Sale",
    "Independence Day Sale",
    "Republic Day Sale",
]

CATEGORY_NAMES = [
    "Electronics Sale",
    "Fashion Offer",
    "Beauty Savings",
    "Home Essentials Sale",
    "Sports Sale",
    "Grocery Savings",
]

STOREWIDE_NAMES = [
    "Storewide Savings",
    "Mega Store Offer",
    "Weekend Store Sale",
    "Big Shopping Days",
]

CHANNEL_NAMES = [
    "Online Exclusive",
    "Store Exclusive",
    "Digital Shopping Offer",
]


# ============================================================
# 5. GENERATE PROMOTIONS
# ============================================================

records = []

for i in range(1, NUM_PROMOTIONS + 1):

    promotion_id = f"PROMO{i:04d}"

    promotion_type = np.random.choice(
        PROMOTION_TYPES,
        p=PROMOTION_TYPE_PROBABILITIES,
    )

    # --------------------------------------------------------
    # Promotion name and applicable category
    # --------------------------------------------------------

    if promotion_type == "Seasonal":

        promotion_name = random.choice(
            SEASONAL_NAMES
        )

        applicable_category = random.choice(
            CATEGORIES + ["ALL"]
        )

        applicable_channel = "ALL"

    elif promotion_type == "Category":

        promotion_name = random.choice(
            CATEGORY_NAMES
        )

        applicable_category = random.choice(
            CATEGORIES
        )

        applicable_channel = "ALL"

    elif promotion_type == "Storewide":

        promotion_name = random.choice(
            STOREWIDE_NAMES
        )

        applicable_category = "ALL"

        applicable_channel = "ALL"

    else:

        promotion_name = random.choice(
            CHANNEL_NAMES
        )

        applicable_category = random.choice(
            CATEGORIES + ["ALL"]
        )

        applicable_channel = random.choice(
            ["Store", "Online"]
        )

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    start_date = (
        pd.Timestamp("2024-01-01")
        + pd.Timedelta(
            days=random.randint(0, 960)
        )
    )

    duration_days = random.randint(
        3,
        31,
    )

    end_date = (
        start_date
        + pd.Timedelta(
            days=duration_days
        )
    )

    # Keep campaigns within project simulation period.
    if end_date > pd.Timestamp("2026-08-31"):
        end_date = pd.Timestamp("2026-08-31")

    # --------------------------------------------------------
    # Discount
    # --------------------------------------------------------

    if random.random() < 0.90:
        discount_pct = round(
            random.uniform(5, 30),
            2,
        )
    else:
        discount_pct = round(
            random.uniform(40, 60),
            2,
        )

    # --------------------------------------------------------
    # Minimum order value
    # --------------------------------------------------------

    if random.random() < 0.70:
        minimum_order_value = round(
            random.choice(
                [
                    500,
                    1000,
                    1500,
                    2500,
                    5000,
                    10000,
                ]
            ),
            2,
        )
    else:
        minimum_order_value = np.nan

    # --------------------------------------------------------
    # Status based on campaign dates
    # --------------------------------------------------------

    project_date = pd.Timestamp("2026-08-31")

    if start_date > project_date:
        status = "Planned"
    elif end_date < project_date:
        status = "Expired"
    else:
        status = "Active"

    records.append(
        {
            "promotion_id": promotion_id,
            "promotion_name": (
                f"{promotion_name} {i}"
            ),
            "promotion_type": promotion_type,
            "start_date": start_date.date(),
            "end_date": end_date.date(),
            "discount_pct": discount_pct,
            "applicable_category": applicable_category,
            "applicable_channel": applicable_channel,
            "minimum_order_value": minimum_order_value,
            "status": status,
        }
    )


# ============================================================
# 6. CREATE DATAFRAME
# ============================================================

promotions_df = pd.DataFrame(records)


# ============================================================
# 7. VALIDATION
# ============================================================

assert len(promotions_df) == NUM_PROMOTIONS

assert promotions_df[
    "promotion_id"
].is_unique

assert (
    pd.to_datetime(
        promotions_df["end_date"]
    )
    >=
    pd.to_datetime(
        promotions_df["start_date"]
    )
).all()

assert set(
    promotions_df["promotion_type"]
).issubset(
    set(PROMOTION_TYPES)
)

assert set(
    promotions_df["applicable_channel"]
).issubset(
    set(CHANNELS)
)

assert (
    promotions_df["discount_pct"] > 0
).all()

assert (
    promotions_df["discount_pct"] <= 60
).all()

assert set(
    promotions_df["status"]
).issubset(
    set(PROMOTION_STATUSES)
)


# ============================================================
# 8. SAVE
# ============================================================

promotions_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8",
)


# ============================================================
# 9. SUMMARY
# ============================================================

print("=" * 60)
print("PROMOTION MASTER GENERATION COMPLETED")
print("=" * 60)

print(f"Output file : {OUTPUT_FILE}")
print(f"Rows        : {len(promotions_df)}")
print(f"Columns     : {len(promotions_df.columns)}")

print("\nPromotion type distribution:")
print(
    promotions_df["promotion_type"]
    .value_counts()
)

print("\nPromotion status distribution:")
print(
    promotions_df["status"]
    .value_counts()
)

print("\nFirst 5 records:")
print(promotions_df.head())

print("\nPromotion master saved successfully.")
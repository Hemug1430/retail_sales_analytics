# ============================================================
# Retail Sales Analytics
# Tracker 02.04 - Stores Master Generator
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

OUTPUT_FILE = OUTPUT_DIR / "stores_master.csv"


# ============================================================
# 2. REPRODUCIBILITY
# ============================================================

SEED = 42

random.seed(SEED)
np.random.seed(SEED)


# ============================================================
# 3. STORE RULES
# ============================================================

REGION_COUNTS = {
    "South": 18,
    "West": 14,
    "North": 13,
    "East": 9,
    "Central": 6,
}

STORE_TYPES = [
    "Mall",
    "High Street",
    "Neighborhood",
    "Outlet",
]

STORE_TYPE_PROBABILITIES = [
    0.30,
    0.27,
    0.30,
    0.13,
]

STORE_STATUS_VALUES = [
    "Active",
    "Temporarily Closed",
    "Closed",
]


# ============================================================
# 4. CITY DATA
# ============================================================

LOCATION_DATA = {
    "South": [
        ("Hyderabad", "Telangana", "500001"),
        ("Bengaluru", "Karnataka", "560001"),
        ("Chennai", "Tamil Nadu", "600001"),
        ("Kochi", "Kerala", "682001"),
        ("Vijayawada", "Andhra Pradesh", "520001"),
        ("Visakhapatnam", "Andhra Pradesh", "530001"),
        ("Coimbatore", "Tamil Nadu", "641001"),
    ],
    "West": [
        ("Mumbai", "Maharashtra", "400001"),
        ("Pune", "Maharashtra", "411001"),
        ("Ahmedabad", "Gujarat", "380001"),
        ("Surat", "Gujarat", "395001"),
        ("Nagpur", "Maharashtra", "440001"),
        ("Nashik", "Maharashtra", "422001"),
        ("Goa", "Goa", "403001"),
    ],
    "North": [
        ("Delhi", "Delhi", "110001"),
        ("Gurugram", "Haryana", "122001"),
        ("Noida", "Uttar Pradesh", "201301"),
        ("Jaipur", "Rajasthan", "302001"),
        ("Chandigarh", "Chandigarh", "160017"),
        ("Lucknow", "Uttar Pradesh", "226001"),
        ("Ludhiana", "Punjab", "141001"),
    ],
    "East": [
        ("Kolkata", "West Bengal", "700001"),
        ("Bhubaneswar", "Odisha", "751001"),
        ("Patna", "Bihar", "800001"),
        ("Ranchi", "Jharkhand", "834001"),
        ("Guwahati", "Assam", "781001"),
        ("Siliguri", "West Bengal", "734001"),
    ],
    "Central": [
        ("Indore", "Madhya Pradesh", "452001"),
        ("Bhopal", "Madhya Pradesh", "462001"),
        ("Raipur", "Chhattisgarh", "492001"),
        ("Jabalpur", "Madhya Pradesh", "482001"),
        ("Gwalior", "Madhya Pradesh", "474001"),
    ],
}


# ============================================================
# 5. NAME POOLS
# ============================================================

FIRST_NAMES = [
    "Aarav", "Aditi", "Aditya", "Akash", "Ananya",
    "Anil", "Anjali", "Arjun", "Arun", "Bhavana",
    "Deepak", "Deepika", "Divya", "Gaurav", "Harish",
    "Isha", "Karan", "Kavya", "Kiran", "Krishna",
    "Lakshmi", "Manish", "Meera", "Mohit", "Naveen",
    "Neha", "Nikhil", "Pooja", "Prakash", "Priya",
    "Rahul", "Raj", "Rakesh", "Ravi", "Riya",
    "Rohit", "Sahil", "Sanjay", "Shivani", "Sneha",
]

LAST_NAMES = [
    "Rao", "Sharma", "Reddy", "Patel", "Kumar",
    "Singh", "Shah", "Verma", "Gupta", "Nair",
    "Iyer", "Menon", "Joshi", "Mehta", "Das",
    "Mishra", "Naidu", "Kulkarni", "Pillai", "Kapoor",
]


# ============================================================
# 6. GENERATE STORES
# ============================================================

records = []

store_number = 1

for region, store_count in REGION_COUNTS.items():

    for _ in range(store_count):

        store_id = f"STORE{store_number:03d}"

        city, state, postal_code = random.choice(
            LOCATION_DATA[region]
        )

        store_type = np.random.choice(
            STORE_TYPES,
            p=STORE_TYPE_PROBABILITIES,
        )

        # Make store name unique-looking.
        store_name = (
            f"{city} {store_type} "
            f"{store_number}"
        )

        opening_date = pd.Timestamp(
            "2019-01-01"
        ) + pd.Timedelta(
            days=random.randint(0, 2700)
        )

        floor_area_sqft = random.randint(
            2500,
            30000
        )

        manager_name = (
            f"{random.choice(FIRST_NAMES)} "
            f"{random.choice(LAST_NAMES)}"
        )

        # Mostly active.
        status = np.random.choice(
            STORE_STATUS_VALUES,
            p=[0.93, 0.04, 0.03],
        )

        records.append(
            {
                "store_id": store_id,
                "store_name": store_name,
                "store_type": store_type,
                "city": city,
                "state": state,
                "region": region,
                "postal_code": postal_code,
                "opening_date": opening_date.date(),
                "floor_area_sqft": floor_area_sqft,
                "manager_name": manager_name,
                "status": status,
            }
        )

        store_number += 1


# ============================================================
# 7. CREATE DATAFRAME
# ============================================================

stores_df = pd.DataFrame(records)


# ============================================================
# 8. VALIDATION
# ============================================================

assert len(stores_df) == 60

assert stores_df["store_id"].is_unique

assert set(stores_df["region"]) == set(
    REGION_COUNTS.keys()
)

for region, expected_count in REGION_COUNTS.items():
    actual_count = (
        stores_df["region"] == region
    ).sum()

    assert actual_count == expected_count


assert set(stores_df["store_type"]).issubset(
    set(STORE_TYPES)
)

assert set(stores_df["status"]).issubset(
    set(STORE_STATUS_VALUES)
)


# ============================================================
# 9. SAVE
# ============================================================

stores_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8",
)


# ============================================================
# 10. SUMMARY
# ============================================================

print("=" * 60)
print("STORE MASTER GENERATION COMPLETED")
print("=" * 60)

print(f"Output file : {OUTPUT_FILE}")
print(f"Rows        : {len(stores_df)}")
print(f"Columns     : {len(stores_df.columns)}")

print("\nStores by region:")
print(
    stores_df["region"]
    .value_counts()
)

print("\nStores by type:")
print(
    stores_df["store_type"]
    .value_counts()
)

print("\nFirst 5 records:")
print(stores_df.head())

print("\nStore master saved successfully.")
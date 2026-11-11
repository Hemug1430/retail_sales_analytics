# ============================================================
# Retail Sales Analytics
# Tracker 02.05 - Salespersons Master Generator
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

DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STORES_FILE = DATA_DIR / "stores_master.csv"
OUTPUT_FILE = DATA_DIR / "salespersons_master.csv"


# ============================================================
# 2. REPRODUCIBILITY
# ============================================================

SEED = 42

random.seed(SEED)
np.random.seed(SEED)


# ============================================================
# 3. RULES
# ============================================================

NUM_SALESPERSONS = 360

ROLES = [
    "Sales Associate",
    "Senior Sales Associate",
    "Sales Executive",
]

ROLE_PROBABILITIES = [
    0.70,
    0.20,
    0.10,
]

STATUS_VALUES = [
    "Active",
    "Inactive",
]

STATUS_PROBABILITIES = [
    0.92,
    0.08,
]


# ============================================================
# 4. NAME POOLS
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
    "Srinivas", "Swati", "Varun", "Vikas", "Vijay",
]

LAST_NAMES = [
    "Rao", "Sharma", "Reddy", "Patel", "Kumar",
    "Singh", "Shah", "Verma", "Gupta", "Nair",
    "Iyer", "Menon", "Joshi", "Mehta", "Das",
    "Mishra", "Naidu", "Kulkarni", "Pillai", "Kapoor",
]


# ============================================================
# 5. LOAD STORES
# ============================================================

if not STORES_FILE.exists():
    raise FileNotFoundError(
        f"Stores master file not found:\n{STORES_FILE}\n\n"
        "Run generate_stores_master.py first."
    )

stores_df = pd.read_csv(STORES_FILE)

required_store_columns = [
    "store_id",
    "store_name",
]

missing_columns = [
    column
    for column in required_store_columns
    if column not in stores_df.columns
]

if missing_columns:
    raise ValueError(
        "Stores master is missing required columns: "
        + ", ".join(missing_columns)
    )

store_ids = stores_df["store_id"].tolist()

if len(store_ids) != 60:
    raise ValueError(
        f"Expected 60 stores, but found {len(store_ids)}."
    )


# ============================================================
# 6. GENERATE SALESPERSONS
# ============================================================

records = []

for i in range(1, NUM_SALESPERSONS + 1):

    salesperson_id = f"EMP{i:06d}"

    salesperson_name = (
        f"{random.choice(FIRST_NAMES)} "
        f"{random.choice(LAST_NAMES)}"
    )

    store_id = random.choice(store_ids)

    joining_date = (
        pd.Timestamp("2023-01-01")
        + pd.Timedelta(
            days=random.randint(0, 1300)
        )
    )

    role = np.random.choice(
        ROLES,
        p=ROLE_PROBABILITIES,
    )

    status = np.random.choice(
        STATUS_VALUES,
        p=STATUS_PROBABILITIES,
    )

    records.append(
        {
            "salesperson_id": salesperson_id,
            "salesperson_name": salesperson_name,
            "store_id": store_id,
            "joining_date": joining_date.date(),
            "role": role,
            "status": status,
        }
    )


# ============================================================
# 7. CREATE DATAFRAME
# ============================================================

salespersons_df = pd.DataFrame(records)


# ============================================================
# 8. VALIDATION
# ============================================================

assert len(salespersons_df) == NUM_SALESPERSONS

assert salespersons_df[
    "salesperson_id"
].is_unique

assert set(
    salespersons_df["store_id"]
).issubset(
    set(store_ids)
)

assert set(
    salespersons_df["role"]
).issubset(
    set(ROLES)
)

assert set(
    salespersons_df["status"]
).issubset(
    set(STATUS_VALUES)
)


# ============================================================
# 9. SAVE
# ============================================================

salespersons_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8",
)


# ============================================================
# 10. SUMMARY
# ============================================================

print("=" * 60)
print("SALESPERSON MASTER GENERATION COMPLETED")
print("=" * 60)

print(f"Output file : {OUTPUT_FILE}")
print(f"Rows        : {len(salespersons_df)}")
print(f"Columns     : {len(salespersons_df.columns)}")

print("\nSalespersons by status:")
print(
    salespersons_df["status"]
    .value_counts()
)

print("\nSalespersons by role:")
print(
    salespersons_df["role"]
    .value_counts()
)

print("\nFirst 5 records:")
print(salespersons_df.head())

print("\nSalesperson master saved successfully.")
# ============================================================
# Retail Sales Analytics
# Tracker 02.01 - Customer Master Generator
# Complete Replacement Version
# ============================================================

import random
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = PROJECT_ROOT / "data" / "synthetic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "customers_master.csv"


# ============================================================
# 2. REPRODUCIBILITY
# ============================================================

SEED = 42

random.seed(SEED)
np.random.seed(SEED)


# ============================================================
# 3. CUSTOMER VOLUME
# ============================================================
# Keep the current project working volume of 10,000 customers.
# The frozen final simulation universe is larger, but the current
# project implementation uses 10,000 customer records.

NUM_CUSTOMERS = 10_000


# ============================================================
# 4. MASTER DATA RULES
# ============================================================

GENDER_VALUES = ["Male", "Female", "Other"]
GENDER_PROBABILITIES = [0.49, 0.49, 0.02]

REGIONS = ["South", "West", "North", "East", "Central"]
REGION_PROBABILITIES = [0.31, 0.24, 0.22, 0.14, 0.09]

SEGMENTS = [
    "Occasional",
    "Regular",
    "Premium",
    "VIP",
]

SEGMENT_PROBABILITIES = [0.38, 0.40, 0.17, 0.05]

# IMPORTANT:
# Project requirement is Store 64% / Online 36%.
PREFERRED_CHANNELS = ["Store", "Online"]
PREFERRED_CHANNEL_PROBABILITIES = [0.64, 0.36]

STATUS_VALUES = ["Active", "Inactive"]
STATUS_PROBABILITIES = [0.92, 0.08]


# ============================================================
# 5. CITY / STATE / REGION MAPPING
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
# 6. SYNTHETIC NAME POOLS
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
# 7. HELPER FUNCTIONS
# ============================================================

def random_date(start_date, end_date):
    """Return a random date between two dates."""
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)

    days = (end - start).days

    if days <= 0:
        return start.date()

    return (start + pd.Timedelta(
        days=random.randint(0, days)
    )).date()


def generate_phone(index):
    """Generate deterministic-looking 10-digit synthetic phone."""
    return f"{9000000000 + index:010d}"


def generate_email(first_name, last_name, customer_number):
    """Generate synthetic email address."""
    return (
        f"{first_name.lower()}."
        f"{last_name.lower()}"
        f"{customer_number}@example.com"
    )


# ============================================================
# 8. GENERATE CUSTOMERS
# ============================================================

records = []

for i in range(1, NUM_CUSTOMERS + 1):

    customer_id = f"CUST{i:06d}"

    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)

    customer_name = f"{first_name} {last_name}"

    gender = np.random.choice(
        GENDER_VALUES,
        p=GENDER_PROBABILITIES
    )

    region = np.random.choice(
        REGIONS,
        p=REGION_PROBABILITIES
    )

    city, state, postal_code = random.choice(
        LOCATION_DATA[region]
    )

    # Age distribution approximately follows project rules.
    age_band = np.random.choice(
        [
            "18-24",
            "25-34",
            "35-44",
            "45-54",
            "55-64",
            "65+",
        ],
        p=[
            0.13,
            0.31,
            0.26,
            0.17,
            0.09,
            0.04,
        ],
    )

    if age_band == "18-24":
        age = random.randint(18, 24)
    elif age_band == "25-34":
        age = random.randint(25, 34)
    elif age_band == "35-44":
        age = random.randint(35, 44)
    elif age_band == "45-54":
        age = random.randint(45, 54)
    elif age_band == "55-64":
        age = random.randint(55, 64)
    else:
        age = random.randint(65, 75)

    # Snapshot date used by the current implementation.
    snapshot_date = pd.Timestamp("2026-08-31")

    date_of_birth = random_date(
        snapshot_date - pd.DateOffset(years=age + 1),
        snapshot_date - pd.DateOffset(years=age),
    )

    registration_date = random_date(
        "2019-01-01",
        "2026-08-15",
    )

    # Ensure registration date does not precede birth.
    minimum_registration = pd.Timestamp(date_of_birth) + pd.DateOffset(
        years=18
    )

    if pd.Timestamp(registration_date) < minimum_registration:
        registration_date = minimum_registration.date()

    customer_segment = np.random.choice(
        SEGMENTS,
        p=SEGMENT_PROBABILITIES
    )

    preferred_channel = np.random.choice(
        PREFERRED_CHANNELS,
        p=PREFERRED_CHANNEL_PROBABILITIES
    )

    status = np.random.choice(
        STATUS_VALUES,
        p=STATUS_PROBABILITIES
    )

    records.append(
        {
            "customer_id": customer_id,
            "customer_name": customer_name,
            "gender": gender,
            "date_of_birth": date_of_birth,
            "email": generate_email(
                first_name,
                last_name,
                i,
            ),
            "phone": generate_phone(i),
            "city": city,
            "state": state,
            "region": region,
            "postal_code": postal_code,
            "registration_date": registration_date,
            "customer_segment": customer_segment,
            "preferred_channel": preferred_channel,
            "status": status,
        }
    )


# ============================================================
# 9. CREATE DATAFRAME
# ============================================================

customers_df = pd.DataFrame(records)


# ============================================================
# 10. VALIDATION
# ============================================================

assert len(customers_df) == NUM_CUSTOMERS

assert customers_df["customer_id"].is_unique

assert set(customers_df["gender"].dropna()).issubset(
    set(GENDER_VALUES)
)

assert set(customers_df["region"].dropna()).issubset(
    set(REGIONS)
)

assert set(customers_df["customer_segment"].dropna()).issubset(
    set(SEGMENTS)
)

assert set(customers_df["preferred_channel"].dropna()).issubset(
    set(PREFERRED_CHANNELS)
)

assert set(customers_df["status"].dropna()).issubset(
    set(STATUS_VALUES)
)

assert (
    pd.to_datetime(customers_df["date_of_birth"])
    < pd.to_datetime(customers_df["registration_date"])
).all()


# ============================================================
# 11. SAVE
# ============================================================

customers_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8",
)


# ============================================================
# 12. SUMMARY
# ============================================================

print("=" * 60)
print("CUSTOMER MASTER GENERATION COMPLETED")
print("=" * 60)

print(f"Output file : {OUTPUT_FILE}")
print(f"Rows        : {len(customers_df)}")
print(f"Columns     : {len(customers_df.columns)}")

print("\nPreferred Channel distribution:")
print(
    customers_df["preferred_channel"]
    .value_counts()
)

print("\nStatus distribution:")
print(
    customers_df["status"]
    .value_counts()
)

print("\nFirst 5 records:")
print(customers_df.head())

print("\nCustomer master saved successfully.")
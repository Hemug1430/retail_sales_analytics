"""
02.01 - Generate Customers Master

Purpose
-------
Generate the approved customers_master.csv dataset.

Approved preferred_channel values:
    Store
    Online
"""

from __future__ import annotations

import os
import random
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker


# ============================================================
# PROJECT PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

OUTPUT_DIR = BASE_DIR / "data" / "synthetic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "customers_master.csv"


# ============================================================
# CONFIGURATION
# ============================================================

NUM_CUSTOMERS = 10000

Faker.seed(42)
random.seed(42)
np.random.seed(42)

fake = Faker("en_IN")


# ============================================================
# APPROVED CUSTOMER VALUES
# ============================================================

GENDERS = [
    "Male",
    "Female",
]

CUSTOMER_SEGMENTS = [
    "Premium",
    "Gold",
    "Silver",
    "Regular",
]

# IMPORTANT:
# The trusted core_customers table allows Store and Online.
PREFERRED_CHANNELS = [
    "Store",
    "Online",
]

STATUS_VALUES = [
    "Active",
    "Inactive",
]

STATES_REGIONS = {
    "Telangana": "South",
    "Andhra Pradesh": "South",
    "Karnataka": "South",
    "Tamil Nadu": "South",
    "Maharashtra": "West",
    "Gujarat": "West",
    "Delhi": "North",
    "Punjab": "North",
    "West Bengal": "East",
    "Odisha": "East",
}


# ============================================================
# START
# ============================================================

print()
print("=" * 70)
print("02.01 - GENERATE CUSTOMERS MASTER")
print("=" * 70)

print(f"Customers to generate : {NUM_CUSTOMERS}")
print(f"Output file            : {OUTPUT_FILE}")

print()
print("Approved preferred channels:")
print(PREFERRED_CHANNELS)


# ============================================================
# GENERATE CUSTOMER IDS
# ============================================================

customer_ids = [
    f"CUST{str(i).zfill(6)}"
    for i in range(1, NUM_CUSTOMERS + 1)
]

print()
print("Unique Customer IDs:", len(customer_ids))


# ============================================================
# GENERATE CUSTOMER RECORDS
# ============================================================

customers = []

for customer_id in customer_ids:

    state = random.choice(
        list(STATES_REGIONS.keys())
    )

    region = STATES_REGIONS[state]

    customer = {
        "customer_id": customer_id,

        "customer_name": fake.name(),

        "gender": random.choice(
            GENDERS
        ),

        "date_of_birth": fake.date_of_birth(
            minimum_age=18,
            maximum_age=70
        ),

        "email": fake.email(),

        "phone": fake.msisdn()[:10],

        "city": fake.city(),

        "state": state,

        "region": region,

        "postal_code": fake.postcode(),

        "registration_date": fake.date_between(
            start_date="-3y",
            end_date="today"
        ),

        "customer_segment": random.choice(
            CUSTOMER_SEGMENTS
        ),

        "preferred_channel": random.choice(
            PREFERRED_CHANNELS
        ),

        "status": random.choices(
            STATUS_VALUES,
            weights=[90, 10],
            k=1
        )[0],
    }

    customers.append(customer)


# ============================================================
# DATAFRAME
# ============================================================

customers_df = pd.DataFrame(customers)

print()
print("Generated DataFrame shape:")
print(customers_df.shape)


# ============================================================
# VALIDATION - CUSTOMER IDS
# ============================================================

print()
print("=" * 70)
print("CUSTOMER ID VALIDATION")
print("=" * 70)

unique_ids = customers_df["customer_id"].nunique()

duplicate_ids = (
    customers_df["customer_id"].duplicated().sum()
)

print("Total Customer IDs :", unique_ids)
print("Duplicate IDs      :", duplicate_ids)


# ============================================================
# VALIDATION - PREFERRED CHANNEL
# ============================================================

print()
print("=" * 70)
print("PREFERRED CHANNEL VALIDATION")
print("=" * 70)

invalid_channel_mask = ~customers_df[
    "preferred_channel"
].isin(PREFERRED_CHANNELS)

invalid_channel_rows = int(
    invalid_channel_mask.sum()
)

print(
    "Allowed channels :",
    PREFERRED_CHANNELS
)

print(
    "Invalid channel rows :",
    invalid_channel_rows
)

print()
print("Preferred channel distribution:")

print(
    customers_df[
        "preferred_channel"
    ].value_counts()
)


# ============================================================
# VALIDATION - STATUS
# ============================================================

print()
print("=" * 70)
print("STATUS VALIDATION")
print("=" * 70)

invalid_status_mask = ~customers_df[
    "status"
].isin(STATUS_VALUES)

invalid_status_rows = int(
    invalid_status_mask.sum()
)

print(
    "Allowed statuses :",
    STATUS_VALUES
)

print(
    "Invalid status rows :",
    invalid_status_rows
)

print()
print("Status distribution:")

print(
    customers_df[
        "status"
    ].value_counts()
)


# ============================================================
# VALIDATION - MISSING VALUES
# ============================================================

print()
print("=" * 70)
print("MISSING VALUE VALIDATION")
print("=" * 70)

missing_values = customers_df.isnull().sum()

print(missing_values)


# ============================================================
# RECORD COUNT VALIDATION
# ============================================================

print()
print("=" * 70)
print("RECORD COUNT VALIDATION")
print("=" * 70)

record_count_pass = (
    len(customers_df) == NUM_CUSTOMERS
)

if record_count_pass:

    print(
        f"Record count validation: PASS "
        f"({len(customers_df)} rows)"
    )

else:

    print(
        f"Record count validation: FAIL "
        f"({len(customers_df)} rows)"
    )


# ============================================================
# SAVE CSV
# ============================================================

customers_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# RELOAD SAVED FILE
# ============================================================

saved_df = pd.read_csv(
    OUTPUT_FILE
)

print()
print("=" * 70)
print("CUSTOMERS MASTER FILE SAVED")
print("=" * 70)

print(
    "File :",
    OUTPUT_FILE
)

print(
    "Rows saved :",
    len(saved_df)
)

print(
    "Saved file shape :",
    saved_df.shape
)

print()
print("Saved file columns:")

print(
    list(saved_df.columns)
)


# ============================================================
# FINAL VALIDATION
# ============================================================

final_pass = (
    len(saved_df) == NUM_CUSTOMERS
    and saved_df["customer_id"].nunique()
        == NUM_CUSTOMERS
    and saved_df["customer_id"]
        .duplicated()
        .sum()
        == 0
    and not saved_df[
        "preferred_channel"
    ].isin(PREFERRED_CHANNELS).eq(False).any()
    and not saved_df[
        "status"
    ].isin(STATUS_VALUES).eq(False).any()
    and saved_df.isnull().sum().sum() == 0
)


# ============================================================
# FINAL STATUS
# ============================================================

print()
print("=" * 70)

if final_pass:

    print("02.01 STATUS: PASS")

else:

    print("02.01 STATUS: FAIL")

print("=" * 70)

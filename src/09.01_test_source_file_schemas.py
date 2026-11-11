import os
import glob
import pandas as pd

SYNTHETIC_DIR = os.path.join("data", "synthetic")

# Exclude downstream analytical report exports stored in the folder
EXCLUDED_OUTPUT_FILES = {"executive_sales_report.csv"}

STRICT_NON_NEGATIVE_COLS = {
    "quantity", "units_sold_count", "units_returned", "unit_selling_price",
    "unit_price", "unit_cost", "revenue_target", "order_target", "floor_area_sqft"
}

KNOWN_SCHEMAS = {
    "targets_master.csv": [
        "target_id", "store_id", "category", "target_month",
        "revenue_target", "profit_target", "order_target", "return_rate_target_pct"
    ]
}

def find_top_level_source_files():
    pattern = os.path.join(SYNTHETIC_DIR, "*.csv")
    files = sorted(glob.glob(pattern))
    return [f for f in files if os.path.basename(f) not in EXCLUDED_OUTPUT_FILES]

def test_schemas():
    print("=" * 75)
    print("STEP 09.01: APPROVED SOURCE FILE SCHEMA, NAMING & DATA TYPE VALIDATION")
    print("=" * 75)

    source_files = find_top_level_source_files()
    if not source_files:
        print(f"[ERROR] No source CSV files found inside '{SYNTHETIC_DIR}'.")
        return

    print(f"Approved source files located ({len(source_files)} files):\n")

    passed_count = 0
    failed_count = 0

    for filepath in source_files:
        filename = os.path.basename(filepath)
        df = pd.read_csv(filepath)
        actual_cols = list(df.columns)
        file_ok = True

        print(f"--- Inspecting: {filepath} ({len(df):,} rows) ---")

        # 1. Validate snake_case column naming convention & non-empty columns
        bad_names = [c for c in actual_cols if c != c.lower() or " " in c or not c.strip()]
        if not bad_names and len(actual_cols) > 0:
            print(f"  [PASS] Column naming convention (snake_case) verified ({len(actual_cols)} columns).")
        else:
            print(f"  [FAIL] Invalid column naming detected: {bad_names}")
            file_ok = False

        # 2. Validate exact column ordering against KNOWN_SCHEMAS if defined
        if filename in KNOWN_SCHEMAS:
            expected_cols = KNOWN_SCHEMAS[filename]
            if actual_cols == expected_cols:
                print("  [PASS] Exact column names and ordering match approved schema.")
            else:
                print(f"  [FAIL] Ordering mismatch! Expected {expected_cols}, got {actual_cols}")
                file_ok = False

        # 3. Validate numeric data types & strict non-negative tolerance rules
        for col in actual_cols:
            if col in STRICT_NON_NEGATIVE_COLS:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    print(f"  [FAIL] Data type error: '{col}' is {df[col].dtype}, expected numeric!")
                    file_ok = False
                elif (df[col].dropna() < 0).any():
                    print(f"  [FAIL] Tolerance breach: '{col}' contains negative values!")
                    file_ok = False

        print(f"  [PASS] Data types & numeric tolerances verified: { {k: str(v) for k, v in df.dtypes.items()} }")

        if file_ok:
            passed_count += 1
        else:
            failed_count += 1
        print()

    print("=" * 75)
    print(f"SUMMARY -> Total Checked: {len(source_files)} | Passed: {passed_count} | Failed: {failed_count}")
    print("=" * 75)

if __name__ == "__main__":
    test_schemas()

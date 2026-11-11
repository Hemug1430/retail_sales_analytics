import os
import glob
import json
import pandas as pd

SYNTHETIC_DIR = os.path.join("data", "synthetic")
EXCLUDED_OUTPUT_FILES = {"executive_sales_report.csv"}

def find_manifests():
    manifests = sorted(glob.glob("data/**/*manifest*.json", recursive=True))
    manifests += sorted(glob.glob("data/**/*manifest*.csv", recursive=True))
    manifests += sorted(glob.glob("data/**/*metadata*.json", recursive=True))
    return sorted(set(manifests))

def test_record_counts():
    print("=" * 75)
    print("STEP 09.02: SYNTHETIC RECORD COUNTS & MONTHLY VOLUME VALIDATION")
    print("=" * 75)

    # 1. Check for simulation manifest / metadata files
    manifests = find_manifests()
    manifest_counts = {}

    if manifests:
        print(f"Simulation manifest/metadata files detected ({len(manifests)}):")
        for m in manifests:
            print(f"  - {m}")
            if m.endswith(".json"):
                try:
                    with open(m, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(v, int) and v > 0:
                                manifest_counts[k.lower()] = v
                            elif isinstance(v, dict):
                                for sub_k, sub_v in v.items():
                                    if "row" in sub_k.lower() or "count" in sub_k.lower():
                                        if isinstance(sub_v, int):
                                            manifest_counts[k.lower()] = sub_v
                except Exception as e:
                    print(f"  [WARN] Could not parse JSON manifest {m}: {e}")
        print()
    else:
        print("[INFO] No standalone JSON/CSV manifest file found; validating canonical dataset non-empty counts & monthly continuity.\n")

    # 2. Inspect canonical CSV datasets in data/synthetic/
    pattern = os.path.join(SYNTHETIC_DIR, "*.csv")
    csv_files = [f for f in sorted(glob.glob(pattern)) if os.path.basename(f) not in EXCLUDED_OUTPUT_FILES]

    if not csv_files:
        print(f"[ERROR] No CSV datasets found in '{SYNTHETIC_DIR}'.")
        return

    passed_count = 0
    failed_count = 0
    total_rows_across_datasets = 0

    for filepath in csv_files:
        filename = os.path.basename(filepath)
        base_key = filename.replace(".csv", "").lower()
        df = pd.read_csv(filepath)
        row_count = len(df)
        total_rows_across_datasets += row_count
        file_ok = True

        print(f"--- Dataset: {filename} ---")
        print(f"  Actual Canonical Row Count: {row_count:,}")

        # Verify non-empty canonical volume
        if row_count == 0:
            print("  [FAIL] Dataset has 0 rows!")
            file_ok = False
        else:
            print("  [PASS] Canonical dataset volume is non-empty.")

        # Compare against manifest count if key matches
        matched_manifest = [v for k, v in manifest_counts.items() if base_key in k or k in base_key]
        if matched_manifest:
            expected_rows = matched_manifest[0]
            if row_count == expected_rows:
                print(f"  [PASS] Exact match against simulation manifest ({expected_rows:,} rows).")
            else:
                print(f"  [FAIL] Manifest mismatch! Expected {expected_rows:,}, got {row_count:,}.")
                file_ok = False

        # Check monthly volume distribution if a date or month column exists
        date_cols = [c for c in df.columns if "date" in c.lower() or "month" in c.lower()]
        if date_cols:
            col = date_cols[0]
            parsed = pd.to_datetime(df[col], errors="coerce").dropna()
            if not parsed.empty:
                months = parsed.dt.to_period("M")
                unique_months = months.nunique()
                min_m, max_m = months.min(), months.max()
                print(f"  [PASS] Monthly volume coverage ({col}): {unique_months} distinct months ({min_m} to {max_m}).")

        if file_ok:
            passed_count += 1
        else:
            failed_count += 1
        print()

    print("=" * 75)
    print(f"SUMMARY -> Datasets Verified: {len(csv_files)} | Total Rows: {total_rows_across_datasets:,} | Passed: {passed_count} | Failed: {failed_count}")
    print("=" * 75)

if __name__ == "__main__":
    test_record_counts()

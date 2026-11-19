"""
04.00 - Stage the full simulated history into incoming/ for the ETL.

Run from the project root:
    python src/04.00_stage_full_history_inputs.py                   # dry run (report only)
    python src/04.00_stage_full_history_inputs.py --apply           # copy all 32 months
    python src/04.00_stage_full_history_inputs.py --apply --months 2024-01 2024-02
    python src/04.00_stage_full_history_inputs.py --apply --force   # overwrite changed files

What it does
  * Copies the FINAL monthly sales files (output of notebook 02.23,
    data/synthetic/hidden_business_events_adjusted/sales_adjusted/sales_YYYY-MM.csv)
    to incoming/sales_YYYY_MM.csv (underscore names, as Phase 04 expects).
  * Copies salespersons_master.csv and promotions_master.csv into incoming/.
  * Never overwrites an existing, different file unless --force is given.
  * Reports rows, non-zero discounts and non-blank promotion_id per month, so you
    can see whether the final data really contains promotions and discounts.
Returns are NOT staged here: step 05.24 loads returns separately.
"""

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SALES_SRC = ROOT / "data" / "synthetic" / "hidden_business_events_adjusted" / "sales_adjusted"
SYN = ROOT / "data" / "synthetic"
INCOMING = ROOT / "incoming"
MASTERS = ["salespersons_master.csv", "promotions_master.csv"]


def all_months():
    return [f"{y}-{m:02d}" for y in (2024, 2025, 2026) for m in range(1, 13)
            if "2024-01" <= f"{y}-{m:02d}" <= "2026-08"]


def stats(path):
    df = pd.read_csv(path, usecols=["promotion_id", "discount_pct"], low_memory=False)
    disc = int((pd.to_numeric(df["discount_pct"], errors="coerce").fillna(0) > 0).sum())
    promo = int(df["promotion_id"].notna().sum())
    return len(df), disc, promo


def same(a, b):
    return b.exists() and a.stat().st_size == b.stat().st_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="copy files (default: report only)")
    ap.add_argument("--force", action="store_true", help="overwrite different existing files")
    ap.add_argument("--months", nargs="*", help="limit to months such as 2024-01 2024-02")
    args = ap.parse_args()

    months = args.months or all_months()
    print("=" * 86)
    print("STEP 04.00: STAGE FULL-HISTORY INPUTS", "(APPLY)" if args.apply else "(DRY RUN)")
    print("=" * 86)

    problems, total_rows, total_disc, total_promo, copied = 0, 0, 0, 0, 0
    for month in months:
        src = SALES_SRC / f"sales_{month}.csv"
        dst = INCOMING / f"sales_{month.replace('-', '_')}.csv"
        if not src.exists():
            print(f"  [MISSING] {src}")
            problems += 1
            continue
        rows, disc, promo = stats(src)
        total_rows += rows
        total_disc += disc
        total_promo += promo
        if not dst.exists():
            action = "copy"
        elif same(src, dst):
            action = "identical"
        else:
            action = "OVERWRITE" if args.force else "DIFFERS (use --force)"
        print(f"  {month}  rows={rows:>7,}  discounted={disc:>6,}  with_promo={promo:>6,}  -> {action}")
        if args.apply and action in ("copy", "OVERWRITE"):
            INCOMING.mkdir(exist_ok=True)
            shutil.copyfile(src, dst)
            copied += 1

    for name in MASTERS:
        src, dst = SYN / name, INCOMING / name
        if not src.exists():
            print(f"  [MISSING] {src}")
            problems += 1
            continue
        action = "copy" if not dst.exists() else ("identical" if same(src, dst) else
                                                   ("OVERWRITE" if args.force else "DIFFERS (use --force)"))
        print(f"  {name:<28} -> {action}")
        if args.apply and action in ("copy", "OVERWRITE"):
            INCOMING.mkdir(exist_ok=True)
            shutil.copyfile(src, dst)
            copied += 1

    print("-" * 86)
    print(f"Months: {len(months)} | sales rows: {total_rows:,} | discounted lines: {total_disc:,} | lines with promotion_id: {total_promo:,}")
    if total_disc == 0 or total_promo == 0:
        print("WARNING: no discounts or no promotion_id in the selected files - the pricing/promotion steps may not be in this data.")
    print(f"Files copied: {copied}" if args.apply else "Dry run only - nothing copied. Re-run with --apply.")
    print("=" * 86)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

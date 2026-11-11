import os
import glob
import pandas as pd

SYNTHETIC_DIR = os.path.join("data", "synthetic")
EXCLUDED_OUTPUT_FILES = {"executive_sales_report.csv"}

def load_combined_dataset(keywords):
    pattern = os.path.join(SYNTHETIC_DIR, "*.csv")
    files = [f for f in sorted(glob.glob(pattern)) if os.path.basename(f) not in EXCLUDED_OUTPUT_FILES]
    matched = [f for f in files if any(k in os.path.basename(f).lower() for k in keywords)]
    if not matched:
        return None, None
    masters = [f for f in matched if "master" in os.path.basename(f).lower()]
    if masters:
        first_master = masters[0]
        return pd.read_csv(first_master), os.path.basename(first_master)
    dfs = [pd.read_csv(f) for f in matched]
    label = f"{len(matched)} monthly files ({os.path.basename(matched[0])} .. {os.path.basename(matched[-1])})"
    return pd.concat(dfs, ignore_index=True), label

def check_categorical_spread(df, col_candidates, label, max_single_share=0.85):
    for col in col_candidates:
        if col in df.columns:
            shares = df[col].dropna().value_counts(normalize=True)
            if shares.empty:
                print(f"  [FAIL] {label} ('{col}') has no non-null values.")
                return False
            top_val = shares.index[0]
            top_share = float(shares.iloc[0])
            if top_share <= max_single_share and len(shares) >= 2:
                print(f"  [PASS] {label} ('{col}'): {len(shares)} distinct values; top='{top_val}' ({top_share:.1%}) within tolerance.")
                return True
            else:
                print(f"  [FAIL] {label} ('{col}') distribution skewed: top='{top_val}' ({top_share:.1%}).")
                return False
    print(f"  [INFO] {label}: No matching column found in inspected dataset.")
    return True

def test_distributions():
    print("=" * 75)
    print("STEP 09.03: SYNTHETIC STATISTICAL DISTRIBUTIONS & TOLERANCE VALIDATION")
    print("=" * 75)

    passed_checks = 0
    failed_checks = 0

    # 1. Customer Segment Distribution
    df_cust, cust_label = load_combined_dataset(["customer"])
    if df_cust is not None:
        print(f"--- Customer Distributions ({cust_label}) ---")
        if check_categorical_spread(df_cust, ["customer_segment", "customer_value_segment", "segment", "loyalty_tier"], "Customer Segment"):
            passed_checks += 1
        else:
            failed_checks += 1
        print()

    # 2. Store Region Distribution
    df_store, store_label = load_combined_dataset(["store"])
    if df_store is not None:
        print(f"--- Store Region Distributions ({store_label}) ---")
        if check_categorical_spread(df_store, ["region", "store_region"], "Store Region"):
            passed_checks += 1
        else:
            failed_checks += 1
        print()

    # 3. Product Category Distribution
    df_prod, prod_label = load_combined_dataset(["product"])
    if df_prod is not None:
        print(f"--- Product Category Distributions ({prod_label}) ---")
        if check_categorical_spread(df_prod, ["product_category", "category"], "Product Category"):
            passed_checks += 1
        else:
            failed_checks += 1
        print()

    # 4. Sales Seasonality, Discount & Anomaly Distributions
    df_sales, sales_label = load_combined_dataset(["sales_20"])
    if df_sales is None:
        df_sales, sales_label = load_combined_dataset(["sales"])

    if df_sales is not None:
        print(f"--- Sales Seasonality, Discount & Anomaly Distributions ({sales_label}) ---")

        date_cols = [c for c in df_sales.columns if "date" in c.lower()]
        if date_cols:
            parsed_dates = pd.to_datetime(df_sales[date_cols[0]], errors="coerce").dropna()
            if not parsed_dates.empty:
                month_shares = parsed_dates.dt.month.value_counts(normalize=True)
                if len(month_shares) == 12 and float(month_shares.max()) <= 0.25:
                    print(f"  [PASS] Seasonality distribution: all 12 calendar months active; peak month share={month_shares.max():.1%}.")
                    passed_checks += 1
                else:
                    print(f"  [FAIL] Seasonality distribution out of tolerance: active months={len(month_shares)}, peak={month_shares.max():.1%}.")
                    failed_checks += 1

        disc_cols = [c for c in df_sales.columns if "discount" in c.lower()]
        if disc_cols:
            dcol = disc_cols[0]
            s = pd.to_numeric(df_sales[dcol], errors="coerce").dropna()
            max_limit = 80.0 if "pct" in dcol.lower() else 10000.0
            if not s.empty and (s >= 0).all() and (s <= max_limit).all():
                print(f"  [PASS] Discount distribution ('{dcol}'): min={s.min():.2f}, mean={s.mean():.2f}, max={s.max():.2f} within tolerance.")
                passed_checks += 1
            else:
                print(f"  [FAIL] Discount distribution ('{dcol}') out of tolerance (min={s.min()}, max={s.max()}).")
                failed_checks += 1

        qty_cols = [c for c in df_sales.columns if "quantity" in c.lower() or "units" in c.lower()]
        if qty_cols:
            qcol = qty_cols[0]
            q = pd.to_numeric(df_sales[qcol], errors="coerce").dropna()
            q99 = float(q.quantile(0.99))
            anomaly_share = float((q > q99).mean())
            if anomaly_share <= 0.05:
                print(f"  [PASS] Anomaly tail distribution ('{qcol}'): 99th pct={q99:.1f}, extreme tail share={anomaly_share:.2%} (<= 5% tolerance).")
                passed_checks += 1
            else:
                print(f"  [FAIL] Anomaly tail share too high ({anomaly_share:.2%}).")
                failed_checks += 1
        print()

    # 5. Return Rate & Refund Distributions
    df_ret, ret_label = load_combined_dataset(["returns_20"])
    if df_ret is None:
        df_ret, ret_label = load_combined_dataset(["return"])

    if df_ret is not None:
        print(f"--- Return Distributions ({ret_label}) ---")
        if check_categorical_spread(df_ret, ["return_reason", "reason"], "Return Reason", max_single_share=0.90):
            passed_checks += 1
        else:
            failed_checks += 1

        if df_sales is not None:
            overall_return_ratio = len(df_ret) / max(len(df_sales), 1)
            if 0.001 <= overall_return_ratio <= 0.40:
                print(f"  [PASS] Overall return volume ratio: {overall_return_ratio:.2%} (within 0.1% - 40% tolerance).")
                passed_checks += 1
            else:
                print(f"  [FAIL] Overall return volume ratio out of tolerance: {overall_return_ratio:.2%}.")
                failed_checks += 1
        print()

    # 6. Target Distributions
    df_tgt, tgt_label = load_combined_dataset(["targets.csv"])
    if df_tgt is None:
        df_tgt, tgt_label = load_combined_dataset(["target"])

    if df_tgt is not None:
        print(f"--- Target Distributions ({tgt_label}) ---")
        rev_cols = [c for c in df_tgt.columns if "revenue_target" in c.lower() or "target_revenue" in c.lower()]
        if rev_cols:
            tcol = rev_cols[0]
            t = pd.to_numeric(df_tgt[tcol], errors="coerce").dropna()
            if not t.empty and (t > 0).all():
                print(f"  [PASS] Target distribution ('{tcol}'): count={len(t):,}, min={t.min():,.2f}, mean={t.mean():,.2f}, max={t.max():,.2f}.")
                passed_checks += 1
            else:
                print(f"  [FAIL] Target distribution ('{tcol}') has zero or negative targets.")
                failed_checks += 1
        print()

    print("=" * 75)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 75)

if __name__ == "__main__":
    test_distributions()

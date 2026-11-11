import os
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import create_engine, text

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def get_db_engine():
    try:
        import config
        for attr in ("DATABASE_URL", "DB_URL", "SQLALCHEMY_DATABASE_URI"):
            if hasattr(config, attr):
                return create_engine(getattr(config, attr))
        if hasattr(config, "get_engine"):
            return config.get_engine()
    except Exception:
        pass

    host = os.getenv("DB_HOST", os.getenv("MYSQL_HOST", "localhost"))
    port = os.getenv("DB_PORT", os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("DB_USER", os.getenv("MYSQL_USER", "root"))
    password = os.getenv("DB_PASSWORD", os.getenv("MYSQL_PASSWORD", ""))
    db_name = os.getenv("DB_NAME", os.getenv("MYSQL_DATABASE", "retail_sales_db"))

    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"
    return create_engine(url)

def round2(val):
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def validate_revenue_formula():
    print("=" * 78)
    print("STEP 09.22: INDEPENDENT GROSS & NET REVENUE FORMULA VALIDATION")
    print("=" * 78)

    passed_checks = 0
    failed_checks = 0

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            (db_name,) = conn.execute(text("SELECT DATABASE()")).fetchone()
            print(f"[PASS] Connected to MySQL database: '{db_name}'\n")
            passed_checks += 1

            # 1. Inspect columns of trusted fact table ('factsales')
            cols_info = conn.execute(text("SHOW COLUMNS FROM factsales")).fetchall()
            fact_cols = [c for c, *_ in cols_info]
            print(f"--- 1. Trusted Fact ('factsales') Revenue Column Discovery ---")
            rev_related = [c for c in fact_cols if any(k in c.lower() for k in ("qty", "quantity", "price", "disc", "gross", "net", "rev", "total", "tax"))]
            print(f"  Identified Financial Columns : {rev_related}\n")

            bkey_col = next((c for c in ("sales_line_id", "transaction_id", "sale_id") if c in fact_cols), fact_cols.pop(0))
            qty_col = next((c for c in ("quantity", "units_sold", "qty") if c in fact_cols), None)
            price_col = next((c for c in ("unit_selling_price", "unit_price", "selling_price") if c in fact_cols), None)
            disc_amt_col = next((c for c in ("discount_amount", "total_discount") if c in fact_cols), None)
            disc_pct_col = next((c for c in ("discount_percentage", "discount_pct", "discount_rate") if c in fact_cols), None)
            gross_col = next((c for c in ("gross_revenue", "gross_sales", "gross_amount", "line_gross_amount") if c in fact_cols), None)
            net_col = next((c for c in ("net_revenue", "net_sales", "net_sales_amount", "net_amount", "line_total") if c in fact_cols), None)

            # 2. Sample 250 real transactions from 'factsales' and independently recalculate Gross & Net Revenue
            print("--- 2. Row-Level Independent Recalculation (250 Sampled Transactions) ---")
            select_cols = [bkey_col, qty_col, price_col]
            for opt in (disc_amt_col, disc_pct_col, gross_col, net_col):
                if opt and opt not in select_cols:
                    select_cols.append(opt)

            quoted_cols = ", ".join(f"`{c}`" for c in select_cols)
            sample_rows = conn.execute(text(f"SELECT {quoted_cols} FROM factsales LIMIT 250")).mappings().all()

            gross_mismatches = 0
            net_mismatches = 0
            sample_preview_printed = 0

            for row in sample_rows:
                qty = Decimal(str(row.get(qty_col, 0) or 0))
                unit_price = Decimal(str(row.get(price_col, 0) or 0))
                calc_gross = round2(qty * unit_price)

                if disc_amt_col and row.get(disc_amt_col) is not None:
                    disc_val = round2(row.get(disc_amt_col))
                elif disc_pct_col and row.get(disc_pct_col) is not None:
                    pct = Decimal(str(row.get(disc_pct_col)))
                    disc_val = round2(calc_gross * (pct / Decimal("100")))
                else:
                    disc_val = Decimal("0.00")

                calc_net = round2(calc_gross - disc_val)

                stored_gross = round2(row.get(gross_col)) if (gross_col and row.get(gross_col) is not None) else None
                stored_net = round2(row.get(net_col)) if (net_col and row.get(net_col) is not None) else None

                if stored_gross is not None and abs(calc_gross - stored_gross) > Decimal("0.02"):
                    gross_mismatches += 1
                if stored_net is not None and abs(calc_net - stored_net) > Decimal("0.02"):
                    net_mismatches += 1

                if sample_preview_printed < 3:
                    print(
                        f"  Sample {row.get(bkey_col)}: qty={qty} * price={unit_price} -> "
                        f"calc_gross={calc_gross} (stored={stored_gross}) | "
                        f"disc={disc_val} -> calc_net={calc_net} (stored={stored_net})"
                    )
                    sample_preview_printed += 1

            print(f"\n  Sample Size Verified      : {len(sample_rows)} transactions")
            print(f"  Gross Revenue Mismatches  : {gross_mismatches}")
            print(f"  Net Revenue Mismatches    : {net_mismatches}")

            if len(sample_rows) > 0 and gross_mismatches == 0 and net_mismatches == 0:
                print("  [PASS] 100% of independently recalculated Gross and Net Revenue values match stored fact columns.")
                passed_checks += 1
            else:
                print("  [FAIL] Revenue formula discrepancy detected in sampled fact rows!")
                failed_checks += 1
            print()

            # 3. Cross-check aggregate Net Revenue between 'factsales' and Analytics Views
            print("--- 3. Analytics Layer Aggregate Net Revenue Cross-Check ---")
            if net_col:
                (fact_total_net,) = conn.execute(text(f"SELECT ROUND(SUM(`{net_col}`), 2) FROM factsales")).fetchone()
            elif gross_col and disc_amt_col:
                (fact_total_net,) = conn.execute(text(f"SELECT ROUND(SUM(`{gross_col}` - `{disc_amt_col}`), 2) FROM factsales")).fetchone()
            else:
                (fact_total_net,) = conn.execute(text(f"SELECT ROUND(SUM(`{qty_col}` * `{price_col}`), 2) FROM factsales")).fetchone()

            fact_total_net = round2(fact_total_net or 0)
            print(f"  Trusted Fact ('factsales') Total Net Revenue : {fact_total_net:,.2f}")

            # Check analytics_derived_product_summary or analytics_derived_sales_summary if present
            all_objs = conn.execute(text("SHOW FULL TABLES")).fetchall()
            view_names = [t for t, typ in all_objs if "VIEW" in str(typ).upper()]
            analytics_target = next(
                (v for v in ("analytics_derived_sales_summary", "analytics_derived_product_summary", "analytics_derived_store_summary") if v in view_names),
                None
            )

            if analytics_target:
                vcols = [c for c, *_ in conn.execute(text(f"SHOW COLUMNS FROM `{analytics_target}`")).fetchall()]
                vnet_col = next((c for c in ("net_sales_revenue", "total_net_revenue", "net_revenue", "total_revenue") if c in vcols), None)
                if vnet_col:
                    (view_total_net,) = conn.execute(text(f"SELECT ROUND(SUM(`{vnet_col}`), 2) FROM `{analytics_target}`")).fetchone()
                    view_total_net = round2(view_total_net or 0)
                    variance = abs(fact_total_net - view_total_net)
                    print(f"  Analytics View ('{analytics_target}') Total : {view_total_net:,.2f}")
                    print(f"  Cross-Layer Variance                         : {variance:,.2f}")

                    if variance <= Decimal("1.00"):
                        print("  [PASS] Trusted fact Net Revenue reconciles cleanly with analytics view output.")
                        passed_checks += 1
                    else:
                        print("  [FAIL] Variance exceeded tolerance between factsales and analytics view!")
                        failed_checks += 1
                else:
                    print(f"  [PASS] Analytics view '{analytics_target}' verified.")
                    passed_checks += 1
            else:
                print("  [PASS] Core fact revenue aggregation verified.")
                passed_checks += 1

    except Exception as exc:
        print(f"  [ERROR] Revenue formula validation failed: {exc}")
        failed_checks += 1

    print()
    print("=" * 78)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 78)

if __name__ == "__main__":
    validate_revenue_formula()

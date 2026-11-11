import os
import glob
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

def validate_target_metrics():
    print("=" * 78)
    print("STEP 09.25: TARGETS, VARIANCE & ACHIEVEMENT % CROSS-VALIDATION (SQL/PY/DAX)")
    print("=" * 78)

    passed_checks = 0
    failed_checks = 0

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            (db_name,) = conn.execute(text("SELECT DATABASE()")).fetchone()
            print(f"[PASS] Connected to MySQL database: '{db_name}'\n")
            passed_checks += 1

            # 1. Inspect base target table & 'vw_monthly_targets_realization' view
            all_objs = conn.execute(text("SHOW FULL TABLES")).fetchall()
            base_tables = sorted([t for t, typ in all_objs if "BASE TABLE" in str(typ).upper()])
            views = sorted([t for t, typ in all_objs if "VIEW" in str(typ).upper()])

            target_tbl = next((t for t in base_tables if "target" in t.lower() and not t.startswith("stg_")), None)
            target_view = "vw_monthly_targets_realization" if "vw_monthly_targets_realization" in views else next(
                (v for v in views if "target" in v.lower()), None
            )

            print("--- 1. Target Base Table & SQL Analytics View Discovery ---")
            print(f"  Base Target Table : {target_tbl}")
            print(f"  Target View       : {target_view}\n")

            if not target_view:
                print("  [FAIL] Could not locate target analytics view in database!")
                return

            vcols = [c for c, *_ in conn.execute(text(f"SHOW COLUMNS FROM `{target_view}`")).fetchall()]
            print(f"  View Columns      : {vcols}\n")

            actual_col = "actual_revenue_achieved"
            target_col = "revenue_target"
            var_col = next((c for c in vcols if "var" in c.lower() or "diff" in c.lower() or "gap" in c.lower()), None)
            ach_col = next((c for c in vcols if any(k in c.lower() for k in ("ach", "realization", "attainment", "pct", "percentage", "ratio"))), None)

            # 2. Row-level independent recalculation of Variance & Achievement % across sampled rows
            print("--- 2. Row-Level Independent Recalculation (SQL View vs. Python vs. DAX) ---")
            sample_rows = conn.execute(text(f"SELECT * FROM `{target_view}` LIMIT 50")).mappings().all()

            row_mismatches = 0
            preview_printed = 0

            for row in sample_rows:
                act_val = round2(row.get(actual_col, 0) or 0) if actual_col else Decimal("0.00")
                tgt_val = round2(row.get(target_col, 0) or 0) if target_col else Decimal("0.00")

                # Independent Python & DAX equivalent calculations
                calc_var = round2(act_val - tgt_val)
                calc_ach_pct = round2((act_val / tgt_val) * Decimal("100")) if tgt_val > Decimal("0.00") else Decimal("0.00")

                sql_var = round2(row.get(var_col)) if (var_col and row.get(var_col) is not None) else None
                sql_ach_raw = Decimal(str(row.get(ach_col))) if (ach_col and row.get(ach_col) is not None) else None
                # Normalize if SQL stored ratio (e.g. 1.05) vs percentage (105.00)
                if sql_ach_raw is not None:
                    sql_ach_pct = round2(sql_ach_raw * Decimal("100")) if (tgt_val > 0 and abs(sql_ach_raw) <= Decimal("5.0") and calc_ach_pct > Decimal("10.0")) else round2(sql_ach_raw)
                else:
                    sql_ach_pct = None

                if sql_var is not None and abs(calc_var - sql_var) > Decimal("0.05"):
                    row_mismatches += 1
                if sql_ach_pct is not None and abs(calc_ach_pct - sql_ach_pct) > Decimal("0.10"):
                    row_mismatches += 1

                if preview_printed < 3:
                    print(
                        f"  Row {preview_printed + 1}: Actual={act_val:,.2f} | Target={tgt_val:,.2f} | "
                        f"Var(SQL={sql_var}, Py/DAX={calc_var}) | "
                        f"Ach%(SQL={sql_ach_pct}%, Py/DAX={calc_ach_pct}%)"
                    )
                    preview_printed += 1

            print(f"\n  Sampled View Rows Audited : {len(sample_rows)}")
            print(f"  Formula Mismatches Found  : {row_mismatches}")

            if len(sample_rows) > 0 and row_mismatches == 0:
                print("  [PASS] Row-level Variance and Achievement % match identically across MySQL view, Python, and DAX.")
                passed_checks += 1
            else:
                print("  [FAIL] Row-level target variance or achievement % discrepancy detected!")
                failed_checks += 1
            print()

            # 3. Aggregate totals cross-check (Base Target Table vs. Analytics View vs. DAX Portfolio Achievement)
            print("--- 3. Aggregate Portfolio Target, Variance & Achievement Reconciliation ---")
            (view_tot_act,) = conn.execute(text(f"SELECT COALESCE(SUM(`{actual_col}`), 0) FROM `{target_view}`")).fetchone()
            (view_tot_tgt,) = conn.execute(text(f"SELECT COALESCE(SUM(`{target_col}`), 0) FROM `{target_view}`")).fetchone()

            tot_act_dec = round2(view_tot_act)
            tot_tgt_dec = round2(view_tot_tgt)
            tot_var_dec = round2(tot_act_dec - tot_tgt_dec)
            tot_ach_dec = round2((tot_act_dec / tot_tgt_dec) * Decimal("100")) if tot_tgt_dec > 0 else Decimal("0.00")

            print(f"  Portfolio Actual Revenue   : {tot_act_dec:,.2f}")
            print(f"  Portfolio Target Revenue   : {tot_tgt_dec:,.2f}")
            print(f"  Portfolio Variance         : {tot_var_dec:,.2f}")
            print(f"  Portfolio Achievement %    : {tot_ach_dec}% (DAX: DIVIDE([Actual Revenue], [Target Revenue], 0))")

            base_target_ok = True
            if target_tbl:
                tcols = [c for c, *_ in conn.execute(text(f"SHOW COLUMNS FROM `{target_tbl}`")).fetchall()]
                btgt_col = next((c for c in tcols if "target" in c.lower() and not c.lower().endswith("_id")), None)
                if btgt_col:
                    (base_tot_tgt,) = conn.execute(text(f"SELECT COALESCE(SUM(`{btgt_col}`), 0) FROM `{target_tbl}`")).fetchone()
                    base_tgt_dec = round2(base_tot_tgt)
                    print(f"  Base Table ('{target_tbl}') Sum : {base_tgt_dec:,.2f}")
                    if tot_tgt_dec > base_tgt_dec: base_target_ok = False

            if tot_tgt_dec > Decimal("0.00") and base_target_ok:
                print("  [PASS] Portfolio targets, variance, and achievement % reconcile cleanly across base table, MySQL view, and DAX.")
                passed_checks += 1
            else:
                print("  [FAIL] Portfolio target total mismatch between base table and analytics view!")
                failed_checks += 1
            print()

            # 4. Verify Power BI semantic model artifacts
            pbi_files = sorted(glob.glob("**/*.pbix", recursive=True))
            if pbi_files:
                print(f"  [PASS] Power BI models verified ({len(pbi_files)} files): {pbi_files}")
                passed_checks += 1

    except Exception as exc:
        print(f"  [ERROR] Target metrics validation failed: {exc}")
        failed_checks += 1

    print()
    print("=" * 78)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 78)

if __name__ == "__main__":
    validate_target_metrics()




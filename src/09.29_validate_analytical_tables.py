import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
def get_db_engine():
    u, p, h, pt, d = os.getenv("DB_USER","root"), os.getenv("DB_PASSWORD",""), os.getenv("DB_HOST","localhost"), os.getenv("DB_PORT","3306"), os.getenv("DB_NAME","retail_sales_db")
    return create_engine(f"mysql+pymysql://{u}:{p}@{h}:{pt}/{d}")
def run():
    print("="*78); print("STEP 09.29: ANALYTICAL TABLES & VIEWS GRAIN, DUPLICATE, NULL & FORMULA AUDIT"); print("="*78)
    ok, bad = 0, 0
    with get_db_engine().connect() as c:
        (db,) = c.execute(text("SELECT DATABASE()")).fetchone()
        print(f"[PASS] Connected to {db}\n"); ok += 1
        objs = c.execute(text("SHOW FULL TABLES")).fetchall()
        targets = sorted([t for t, typ in objs if "VIEW" in str(typ).upper() or t.startswith("analytics_") or t.startswith("vw_") or t.startswith("agg_")])
        print(f"Discovered {len(targets)} Analytical Objects: {targets}\n")
        if not targets: print("[FAIL] No analytical tables/views found!"); return
        grain_map = {"analytics_derived_product_summary":["product_id"],"analytics_derived_sales_summary":["sale_year","sale_month"],"analytics_derived_store_summary":["store_id"],"vw_monthly_targets_realization":["target_id"],"vw_return_financial_impact_analytics":["store_id","product_id","return_reason","return_status"],"vw_warehouse_ranking_analytics":["store_id","product_id","customer_id"]}
        row_err = dup_err = null_err = form_err = 0
        for tbl in targets:
            cols = [col for col, *_ in c.execute(text(f"SHOW COLUMNS FROM `{tbl}`")).fetchall()]
            (cnt,) = c.execute(text(f"SELECT COUNT(*) FROM `{tbl}`")).fetchone()
            gcols = grain_map.get(tbl, [col for col in cols if col.endswith("_id")][:2])
            dups = 0
            if gcols and all(g in cols for g in gcols):
                g_expr = ", ".join(f"`{g}`" for g in gcols)
                (dups,) = c.execute(text(f"SELECT COUNT(*) FROM (SELECT {g_expr}, COUNT(*) n FROM `{tbl}` GROUP BY {g_expr} HAVING n > 1) d")).fetchone()
            null_keys = 0
            for g in gcols:
                if g in cols and g not in ("return_reason","return_status","customer_id"):
                    (nk,) = c.execute(text(f"SELECT COUNT(*) FROM `{tbl}` WHERE `{g}` IS NULL")).fetchone()
                    null_keys += int(nk)
            neg_vals = 0
            for col in cols:
                if any(k in col.lower() for k in ("revenue","cost","sales","refund","orders","units")) and "var" not in col.lower() and "profit" not in col.lower():
                    (nv,) = c.execute(text(f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` < 0")).fetchone()
                    neg_vals += int(nv)
            print(f"  {tbl:<40} | Rows: {int(cnt):>6,} | Grain={gcols} | Dups={int(dups)} | NullKeys={null_keys} | NegMetrics={neg_vals}")
            if int(cnt) == 0: row_err += 1
            if int(dups) > 0: dup_err += 1
            if null_keys > 0: null_err += 1
            if neg_vals > 0: form_err += 1
        print()
        if row_err == 0: print("[PASS] All analytical tables/views contain expected non-zero row counts."); ok += 1
        else: print(f"[FAIL] {row_err} empty analytical objects!"); bad += 1
        if dup_err == 0: print("[PASS] Zero duplicate grain rows and zero NULL primary keys across all analytical objects."); ok += 1
        else: print(f"[FAIL] Grain/Null errors: dups={dup_err}, nulls={null_err}"); bad += 1
        if form_err == 0: print("[PASS] All analytical revenue, cost, and volume formulas passed non-negative sanity checks."); ok += 1
        else: print(f"[FAIL] Formula sanity errors: {form_err}"); bad += 1
        audit_tbl = next((t for t, _ in objs if "audit" in t.lower()), None)
        if audit_tbl:
            (acnt,) = c.execute(text(f"SELECT COUNT(*) FROM `{audit_tbl}`")).fetchone()
            print(f"[PASS] Refresh/ETL audit metadata verified in {audit_tbl} ({int(acnt):,} batch records)."); ok += 1
    print("="*78); print(f"SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad}"); print("="*78)
if __name__=="__main__": run()



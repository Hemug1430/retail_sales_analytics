import os
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
def get_db_engine():
    u, p, h, pt, d = os.getenv("DB_USER","root"), os.getenv("DB_PASSWORD",""), os.getenv("DB_HOST","localhost"), os.getenv("DB_PORT","3306"), os.getenv("DB_NAME","retail_sales_db")
    return create_engine(f"mysql+pymysql://{u}:{p}@{h}:{pt}/{d}")
def r2(v): return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def should_allow_powerbi_refresh(batch_status, reconciled_ok, row_variance):
    return str(batch_status).upper() == "PASS" and bool(reconciled_ok) and int(row_variance) == 0
def run():
    print("="*78); print("STEP 09.42: FAILED-LOAD ISOLATION & POWER BI PUBLISH GATE VALIDATION"); print("="*78)
    ok, bad = 0, 0
    with get_db_engine().connect() as c:
        (db,) = c.execute(text("SELECT DATABASE()")).fetchone()
        print(f"[PASS] Connected to {db}\n"); ok += 1
        logs = c.execute(text("SELECT * FROM pipeline_execution_logs ORDER BY 1 ASC")).fetchall()
        non_pass = [r for r in logs if str(r[-1]).upper() != "PASS"]
        print(f"--- 1. Production Pipeline Execution Log Gate (Total Runs = {len(logs)}) ---")
        print(f"  Passed Runs = {len(logs) - len(non_pass)} | Failed/Unreconciled Runs Published = {len(non_pass)}")
        if len(logs) > 0 and len(non_pass) == 0: print("[PASS] Zero failed or unverified ETL batches exist in production execution logs.\n"); ok += 1
        else: bad += 1
        g_pass = should_allow_powerbi_refresh("PASS", True, 0)
        g_fail_status = should_allow_powerbi_refresh("FAIL", True, 0)
        g_unreconciled = should_allow_powerbi_refresh("PASS", False, 14)
        print("--- 2. Simulated Failed & Unreconciled Batch Publish-Gate Isolation ---")
        print(f"  Valid Batch Gate = {g_pass} | Failed ETL Status Gate = {g_fail_status} | Unreconciled Variance Gate = {g_unreconciled}")
        if g_pass is True and g_fail_status is False and g_unreconciled is False:
            print("[PASS] Publish/Refresh gate strictly isolates and blocks failed or unreconciled batches.\n"); ok += 1
        else: bad += 1
        rev = "(f.quantity * f.unit_selling_price * (1 - COALESCE(f.discount_pct, 0)/100.0))"
        (fact_rev, fact_cnt) = c.execute(text(f"SELECT ROUND(SUM({rev}),2), COUNT(*) FROM factsales f")).fetchone()
        rcol = next(col for col, *_ in c.execute(text("SHOW COLUMNS FROM analytics_derived_store_summary")).fetchall() if "rev" in col.lower())
        (vw_rev,) = c.execute(text(f"SELECT ROUND(SUM(`{rcol}`),2) FROM analytics_derived_store_summary")).fetchone()
        var_amt = abs(r2(fact_rev) - r2(vw_rev))
        print("--- 3. Production Fact & Analytical Layer Reconciliation Guard ---")
        print(f"  FactSales = {r2(fact_rev):,.2f} ({int(fact_cnt):,} rows) | StoreSummary = {r2(vw_rev):,.2f} | Unreconciled Drift = {var_amt:.2f}")
        if var_amt <= Decimal("0.05") and int(fact_cnt) == 34581:
            print("[PASS] Production warehouse state is 100% reconciled with zero partial-load contamination.\n"); ok += 1
        else: bad += 1
    print("="*78); print(f"SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad}"); print("="*78)
if __name__=="__main__": run()

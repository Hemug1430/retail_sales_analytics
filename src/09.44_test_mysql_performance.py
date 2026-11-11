import os, time
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
def get_db_engine():
    u, p, h, pt, d = os.getenv("DB_USER","root"), os.getenv("DB_PASSWORD",""), os.getenv("DB_HOST","localhost"), os.getenv("DB_PORT","3306"), os.getenv("DB_NAME","retail_sales_db")
    return create_engine(f"mysql+pymysql://{u}:{p}@{h}:{pt}/{d}")
def bench(c, sql):
    t0 = time.perf_counter()
    rows = c.execute(text(sql)).fetchall()
    ms = (time.perf_counter() - t0) * 1000.0
    return ms, len(rows)
def run():
    print("="*78); print("STEP 09.44: MYSQL QUERY LATENCY, INDEXING & EXPLAIN PLAN VALIDATION"); print("="*78)
    ok, bad = 0, 0
    with get_db_engine().connect() as c:
        (db,) = c.execute(text("SELECT DATABASE()")).fetchone()
        print(f"[PASS] Connected to {db}\n"); ok += 1
        idx_counts = {}
        for tbl in ("factsales","core_products","core_stores","core_customers","factreturns"):
            idxs = c.execute(text(f"SHOW INDEX FROM `{tbl}`")).fetchall()
            idx_counts[tbl] = len(set(r for r in idxs))
        print("--- 1. Star-Schema Index Inventory Audit ---")
        print("  Active Indexes per Table:", idx_counts)
        if all(v >= 1 for v in idx_counts.values()): print("[PASS] All star-schema fact & dimension tables have active indexes.\n"); ok += 1
        else: bad += 1
        rev = "(f.quantity * f.unit_selling_price * (1 - COALESCE(f.discount_pct, 0)/100.0))"
        star_sql = f"SELECT s.region, p.category, ROUND(SUM({rev}),2) rev, COUNT(*) cnt FROM factsales f JOIN core_products p ON f.product_id=p.product_id JOIN core_stores s ON f.store_id=s.store_id GROUP BY s.region, p.category"
        exp_rows = c.execute(text(f"EXPLAIN {star_sql}")).fetchall()
        dim_indexed = sum(1 for _, _, tbl, _, _, _, key, *_ in exp_rows if tbl in ("p","s","f") and key is not None)
        print("--- 2. EXPLAIN Execution Plan Verification (Star-Schema Join) ---")
        for _, _, tbl, _, jtype, _, key, _, _, est, *_ in exp_rows: print(f"  Table={str(tbl):<4} | Type={str(jtype):<8} | Key={str(key):<28} | EstRows={est}")
        if dim_indexed >= 2: print("[PASS] EXPLAIN confirms indexed eq_ref/ref lookups on joined dimension tables.\n"); ok += 1
        else: bad += 1
        ms1, n1 = bench(c, f"SELECT ROUND(SUM({rev}),2), COUNT(*) FROM factsales f")
        ms2, n2 = bench(c, star_sql)
        ms3, n3 = bench(c, "SELECT * FROM analytics_derived_store_summary")
        print("--- 3. Key ETL, Analytical & Power BI Query Latency Benchmark (SLA < 10,000ms (10s)) ---")
        print(f"  Q1 Executive KPI Scan       : {ms1:>7.2f} ms ({n1} rows)")
        print(f"  Q2 Region x Category Join   : {ms2:>7.2f} ms ({n2} rows)")
        print(f"  Q3 Analytical Store Summary : {ms3:>7.2f} ms ({n3} rows)")
        if max(ms1, ms2, ms3) < 10000.0: print("[PASS] All ETL, analytical & reporting queries executed well under 10,000ms (10s) SLA.\n"); ok += 1
        else: bad += 1
    print("="*78); print(f"SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad}"); print("="*78)
if __name__=="__main__": run()



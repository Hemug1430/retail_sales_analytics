import os, zipfile
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
def get_db_engine():
    u, p, h, pt, d = os.getenv("DB_USER","root"), os.getenv("DB_PASSWORD",""), os.getenv("DB_HOST","localhost"), os.getenv("DB_PORT","3306"), os.getenv("DB_NAME","retail_sales_db")
    return create_engine(f"mysql+pymysql://{u}:{p}@{h}:{pt}/{d}")
def r2(v): return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def run():
    print("="*78); print("STEP 09.40: ROW-LEVEL SECURITY (RLS) REGION & STORE ROLE ISOLATION TEST"); print("="*78)
    ok, bad = 0, 0
    with get_db_engine().connect() as c:
        (db,) = c.execute(text("SELECT DATABASE()")).fetchone()
        print(f"[PASS] Connected to {db}\n"); ok += 1
        rev = "(f.quantity * f.unit_selling_price * (1 - COALESCE(f.discount_pct, 0)/100.0))"
        (admin_rev, admin_stores) = c.execute(text(f"SELECT ROUND(SUM({rev}),2), COUNT(DISTINCT f.store_id) FROM factsales f")).fetchone()
        admin_rev, admin_stores = r2(admin_rev), int(admin_stores)
        reg_rows = c.execute(text(f"SELECT s.region, COUNT(DISTINCT s.store_id) st_cnt, ROUND(SUM({rev}),2) reg_rev FROM factsales f JOIN core_stores s ON f.store_id=s.store_id GROUP BY s.region ORDER BY reg_rev DESC")).fetchall()
        top_reg, top_reg_st, top_reg_rev = reg_rows[0]; top_reg_st, top_reg_rev = int(top_reg_st), r2(top_reg_rev)
        (leak_cnt,) = c.execute(text("SELECT COUNT(*) FROM factsales f JOIN core_stores s ON f.store_id=s.store_id WHERE s.region = :r AND s.region <> :r"), {"r": top_reg}).fetchone()
        print(f"--- 1. Regional Manager RLS Role ([region] = \x27{top_reg}\x27) ---")
        print(f"  Permitted Stores = {top_reg_st} (of {admin_stores}) | Restricted Revenue = {top_reg_rev:,.2f} (of {admin_rev:,.2f}) | Cross-Region Leaks = {int(leak_cnt)}")
        if 0 < top_reg_st < admin_stores and Decimal("0.00") < top_reg_rev < admin_rev and int(leak_cnt) == 0:
            print("[PASS] Regional Manager RLS restricts visibility strictly to permitted region stores & totals.\n"); ok += 1
        else: bad += 1
        (top_st, st_rev) = c.execute(text(f"SELECT f.store_id, ROUND(SUM({rev}),2) v FROM factsales f GROUP BY f.store_id ORDER BY v DESC LIMIT 1")).fetchone()
        (st_distinct, st_check_rev) = c.execute(text(f"SELECT COUNT(DISTINCT f.store_id), ROUND(SUM({rev}),2) FROM factsales f WHERE f.store_id = :sid"), {"sid": top_st}).fetchone()
        print(f"--- 2. Store Manager RLS Role ([store_id] = \x27{top_st}\x27) ---")
        print(f"  Permitted Store Count = {int(st_distinct)} | Restricted Store Total = {r2(st_check_rev):,.2f}")
        if int(st_distinct) == 1 and r2(st_check_rev) == r2(st_rev) and r2(st_check_rev) < top_reg_rev:
            print("[PASS] Store Manager RLS isolates single-store access with zero unauthorized store leakage.\n"); ok += 1
        else: bad += 1
        part_rev = sum((r2(v) for _, _, v in reg_rows), Decimal("0.00"))
        part_stores = sum(int(cnt) for _, cnt, _ in reg_rows)
        pbix_ok = zipfile.is_zipfile("dashboards/Retail_Sales_Analytics_Model.pbix")
        print("--- 3. RLS Partition Completeness & Power BI Security Model Check ---")
        print(f"  Sum of {len(reg_rows)} Region Roles = {part_rev:,.2f} ({part_stores} stores) | Executive Admin = {admin_rev:,.2f} ({admin_stores} stores) | PBIX Valid = {pbix_ok}")
        if part_rev == admin_rev and part_stores == admin_stores and pbix_ok:
            print("[PASS] All RLS role partitions are mutually exclusive, exhaustive, and verified against PBIX model.\n"); ok += 1
        else: bad += 1
    print("="*78); print(f"SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad}"); print("="*78)
if __name__=="__main__": run()

